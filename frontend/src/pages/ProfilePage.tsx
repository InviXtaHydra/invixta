import { useState, type FormEvent } from 'react'
import { api } from '../api/endpoints'
import { useUser } from '../auth/useAuth'
import { PageContainer } from '../components/AppShell'
import { useToast } from '../components/useToast'
import { Button, Field, Input, Mono, PageHeader, Panel } from '../components/ui'
import { formatDate } from '../lib/format'

const ROLE_TEXT = {
  CUSTOMER: 'Customer: you see your own orders, tickets and conversations.',
  AGENT: 'Support agent: you see and handle the orders and tickets of all customers.',
  ADMIN: 'Administrator: everything an agent can do, plus the knowledge base and metrics.',
}

export function ProfilePage() {
  const user = useUser()
  return (
    <PageContainer>
      <PageHeader title="Profile" description="Your account details and password." />
      <div className="grid max-w-4xl gap-6 lg:grid-cols-2">
        <Panel title="Account">
          <dl className="grid gap-4 text-sm">
            {user.name && (
              <div>
                <dt className="text-xs text-muted">Name</dt>
                <dd className="mt-0.5">{user.name}</dd>
              </div>
            )}
            <div>
              <dt className="text-xs text-muted">Email</dt>
              <dd className="mt-0.5">{user.email}</dd>
            </div>
            <div>
              <dt className="text-xs text-muted">Role</dt>
              <dd className="mt-0.5">{ROLE_TEXT[user.role]}</dd>
            </div>
            {user.customer_id && (
              <div>
                <dt className="text-xs text-muted">Customer number</dt>
                <dd className="mt-0.5">
                  <Mono>{user.customer_id}</Mono>
                </dd>
              </div>
            )}
            <div>
              <dt className="text-xs text-muted">Member since</dt>
              <dd className="mt-0.5">{formatDate(user.created_at)}</dd>
            </div>
          </dl>
        </Panel>
        <ChangePassword />
      </div>
    </PageContainer>
  )
}

function ChangePassword() {
  const toast = useToast()
  const [form, setForm] = useState({ current: '', next: '', confirm: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const nextError = form.next && form.next.length < 8 ? 'Use at least 8 characters' : undefined
  const confirmError = form.confirm && form.confirm !== form.next ? "The passwords don't match" : undefined
  const valid = form.current && form.next.length >= 8 && form.confirm === form.next

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!valid) return
    setBusy(true)
    setError(null)
    try {
      await api.changePassword({ current_password: form.current, new_password: form.next })
      setForm({ current: '', next: '', confirm: '' })
      toast('Password changed')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'The password could not be changed')
    } finally {
      setBusy(false)
    }
  }

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: e.target.value })
  return (
    <Panel title="Change password">
      <form onSubmit={submit} className="space-y-4" noValidate>
        {error && (
          <p role="alert" className="rounded-lg bg-bad-soft px-3 py-2 text-sm text-bad">
            {error}
          </p>
        )}
        <Field label="Current password">
          {(props) => <Input {...props} type="password" autoComplete="current-password" value={form.current} onChange={set('current')} />}
        </Field>
        <Field label="New password" hint="At least 8 characters" error={nextError}>
          {(props) => <Input {...props} type="password" autoComplete="new-password" value={form.next} onChange={set('next')} />}
        </Field>
        <Field label="Repeat new password" error={confirmError}>
          {(props) => <Input {...props} type="password" autoComplete="new-password" value={form.confirm} onChange={set('confirm')} />}
        </Field>
        <Button type="submit" disabled={busy || !valid}>
          {busy ? 'Saving…' : 'Change password'}
        </Button>
      </form>
    </Panel>
  )
}
