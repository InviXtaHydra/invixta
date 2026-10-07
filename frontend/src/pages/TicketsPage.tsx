import { ArrowLeft, LifeBuoy, Plus } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { api } from '../api/endpoints'
import type { Ticket, TicketPriority, TicketStatus } from '../api/types'
import { isStaff, useUser } from '../auth/useAuth'
import { PageContainer } from '../components/AppShell'
import { EmptyState, ErrorState, SkeletonRows } from '../components/feedback'
import { Pagination } from '../components/Pagination'
import { useToast } from '../components/useToast'
import { Button, Dialog, Field, Input, PageHeader, Panel, PriorityBadge, Select, Textarea, TicketStatusBadge } from '../components/ui'
import { formatDateTime, formatRelative, humanize } from '../lib/format'
import { useApi } from '../lib/useApi'

const STATUSES: TicketStatus[] = ['open', 'in_progress', 'resolved', 'closed']
const PRIORITIES: TicketPriority[] = ['low', 'medium', 'high', 'urgent']
const PAGE_SIZE = 10

export function TicketsPage() {
  const user = useUser()
  const staff = isStaff(user)
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const status = (params.get('status') ?? '') as TicketStatus | ''
  const offset = Number(params.get('offset') ?? 0)
  const state = useApi(() => api.tickets({ status, limit: PAGE_SIZE, offset }), [status, offset])
  const [creating, setCreating] = useState(false)

  const update = (next: Record<string, string>) => setParams({ ...Object.fromEntries(params), ...next }, { replace: true })

  return (
    <PageContainer>
      <PageHeader
        title="Support tickets"
        description={staff ? 'Tickets of all customers, newest first.' : 'Problems our support team is handling for you.'}
        actions={
          <>
            <div className="w-40">
              <label htmlFor="ticket-status" className="sr-only">
                Filter by status
              </label>
              <Select id="ticket-status" value={status} onChange={(e) => update({ status: e.target.value, offset: '0' })}>
                <option value="">All statuses</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {humanize(s)}
                  </option>
                ))}
              </Select>
            </div>
            <Button onClick={() => setCreating(true)}>
              <Plus aria-hidden className="size-4" /> New ticket
            </Button>
          </>
        }
      />
      <Panel flush>
        {state.loading && !state.data ? (
          <SkeletonRows rows={5} />
        ) : state.error ? (
          <ErrorState error={state.error} onRetry={state.reload} />
        ) : !state.data?.items.length ? (
          <EmptyState
            icon={LifeBuoy}
            title={status ? `No ${humanize(status).toLowerCase()} tickets` : 'No tickets'}
            action={!status && <Button onClick={() => setCreating(true)}>Open a ticket</Button>}
          >
            {status ? 'Try another status filter.' : 'If something went wrong with an order, open a ticket or ask the AI assistant.'}
          </EmptyState>
        ) : (
          <div aria-busy={state.loading} className={state.loading ? 'opacity-60 transition-opacity' : 'transition-opacity'}>
            <ul className="divide-y divide-line">
              {state.data.items.map((ticket) => (
                <li key={ticket.id}>
                  <Link to={`/tickets/${ticket.id}`} className="flex flex-col gap-2 px-4 py-3.5 hover:bg-surface-2 sm:flex-row sm:items-center sm:gap-4">
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-medium text-ink">{ticket.subject}</span>
                      <span className="text-xs text-muted">
                        <span className="font-mono">#{ticket.id}</span>, opened {formatRelative(ticket.created_at)}
                        {staff && `, customer ${ticket.customer_id}`}
                      </span>
                    </span>
                    <span className="flex gap-2">
                      <PriorityBadge priority={ticket.priority} />
                      <TicketStatusBadge status={ticket.status} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
            <Pagination total={state.data.total} limit={PAGE_SIZE} offset={offset} onChange={(o) => update({ offset: String(o) })} />
          </div>
        )}
      </Panel>
      <NewTicketDialog
        open={creating}
        staff={staff}
        onClose={() => setCreating(false)}
        onCreated={(ticket) => {
          setCreating(false)
          navigate(`/tickets/${ticket.id}`)
        }}
      />
    </PageContainer>
  )
}

function NewTicketDialog({ open, staff, onClose, onCreated }: { open: boolean; staff: boolean; onClose: () => void; onCreated: (t: Ticket) => void }) {
  const toast = useToast()
  const [form, setForm] = useState({ subject: '', description: '', priority: 'medium' as TicketPriority, customerId: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const subjectError = form.subject && form.subject.trim().length < 3 ? 'At least 3 characters' : undefined
  const descriptionError = form.description && form.description.trim().length < 10 ? 'Please describe the problem in at least 10 characters' : undefined
  const valid = form.subject.trim().length >= 3 && form.description.trim().length >= 10 && (!staff || Number(form.customerId) > 0)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!valid) return
    setBusy(true)
    setError(null)
    try {
      const ticket = await api.createTicket({
        subject: form.subject.trim(),
        description: form.description.trim(),
        priority: form.priority,
        ...(staff ? { customer_id: Number(form.customerId) } : {}),
      })
      toast(`Ticket #${ticket.id} created`)
      setForm({ subject: '', description: '', priority: 'medium', customerId: '' })
      onCreated(ticket)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The ticket could not be created')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onClose={onClose} title="New support ticket">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && (
          <p role="alert" className="rounded-lg bg-bad-soft px-3 py-2 text-sm text-bad">
            {error}
          </p>
        )}
        {staff && (
          <Field label="Customer ID" hint="The ticket is opened on behalf of this customer">
            {(props) => <Input {...props} inputMode="numeric" value={form.customerId} onChange={(e) => setForm({ ...form, customerId: e.target.value })} />}
          </Field>
        )}
        <Field label="Subject" error={subjectError}>
          {(props) => <Input {...props} maxLength={200} value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} />}
        </Field>
        <Field label="What happened?" hint="Mention the order number if it's about an order" error={descriptionError}>
          {(props) => (
            <Textarea {...props} rows={5} maxLength={5000} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          )}
        </Field>
        <Field label="Priority">
          {(props) => (
            <Select {...props} value={form.priority} onChange={(e) => setForm({ ...form, priority: e.target.value as TicketPriority })}>
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {humanize(p)}
                </option>
              ))}
            </Select>
          )}
        </Field>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !valid}>
            {busy ? 'Creating…' : 'Create ticket'}
          </Button>
        </div>
      </form>
    </Dialog>
  )
}

export function TicketDetailPage() {
  const { ticketId } = useParams()
  const id = Number(ticketId)
  const user = useUser()
  const state = useApi(() => api.ticket(id), [id])

  return (
    <PageContainer>
      <Link to="/tickets" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft aria-hidden className="size-4" /> Tickets
      </Link>
      {state.loading && !state.data ? (
        <Panel>
          <SkeletonRows rows={4} />
        </Panel>
      ) : state.error ? (
        <Panel>
          <ErrorState error={state.error} onRetry={state.reload} />
        </Panel>
      ) : state.data ? (
        <TicketView ticket={state.data} staff={isStaff(user)} onChanged={state.reload} />
      ) : null}
    </PageContainer>
  )
}

function TicketView({ ticket, staff, onChanged }: { ticket: Ticket; staff: boolean; onChanged: () => void }) {
  const toast = useToast()
  const [saving, setSaving] = useState(false)

  async function change(body: { status?: TicketStatus; priority?: TicketPriority }) {
    setSaving(true)
    try {
      await api.updateTicket(ticket.id, body)
      toast(`Ticket #${ticket.id} updated`)
      onChanged()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The ticket could not be updated', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <>
      <PageHeader
        title={ticket.subject}
        description={
          <>
            <span className="font-mono">#{ticket.id}</span>, opened {formatDateTime(ticket.created_at)}, last update {formatRelative(ticket.updated_at)}
          </>
        }
        actions={
          <>
            <PriorityBadge priority={ticket.priority} />
            <TicketStatusBadge status={ticket.status} />
          </>
        }
      />
      <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
        <Panel title="Description">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink-2">{ticket.description}</p>
        </Panel>
        {staff ? (
          <Panel title="Handle ticket">
            <div className="space-y-4">
              <Field label="Status">
                {(props) => (
                  <Select {...props} disabled={saving} value={ticket.status} onChange={(e) => void change({ status: e.target.value as TicketStatus })}>
                    {STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {humanize(s)}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <Field label="Priority">
                {(props) => (
                  <Select {...props} disabled={saving} value={ticket.priority} onChange={(e) => void change({ priority: e.target.value as TicketPriority })}>
                    {PRIORITIES.map((p) => (
                      <option key={p} value={p}>
                        {humanize(p)}
                      </option>
                    ))}
                  </Select>
                )}
              </Field>
              <p className="text-xs text-muted">Customer ID {ticket.customer_id}</p>
            </div>
          </Panel>
        ) : (
          <Panel title="What happens next">
            <p className="text-sm text-ink-2">
              {ticket.status === 'open' && 'A support colleague will pick up your ticket, usually within 2 working days.'}
              {ticket.status === 'in_progress' && 'A support colleague is working on your ticket.'}
              {ticket.status === 'resolved' && 'This ticket was resolved. Reply by opening a new ticket if the problem comes back.'}
              {ticket.status === 'closed' && 'This ticket is closed.'}
            </p>
          </Panel>
        )}
      </div>
    </>
  )
}
