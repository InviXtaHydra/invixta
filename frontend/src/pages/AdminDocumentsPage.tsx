import { FileText, Trash2, Upload } from 'lucide-react'
import { useRef, useState, type DragEvent } from 'react'
import { api } from '../api/endpoints'
import type { DocumentInfo } from '../api/types'
import { PageContainer } from '../components/AppShell'
import { EmptyState, ErrorState, Spinner, SkeletonRows } from '../components/feedback'
import { useToast } from '../components/useToast'
import { Button, Dialog, PageHeader, Panel } from '../components/ui'
import { formatBytes, formatDate, formatDateTime } from '../lib/format'
import { useApi } from '../lib/useApi'

const MAX_MB = 10

export function AdminDocumentsPage() {
  const toast = useToast()
  const state = useApi(() => api.documents(), [])
  const [uploading, setUploading] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [viewing, setViewing] = useState<DocumentInfo | null>(null)
  const [deleting, setDeleting] = useState<DocumentInfo | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  async function upload(files: FileList | null) {
    for (const file of Array.from(files ?? [])) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        toast(`${file.name} is not a PDF`, 'error')
        continue
      }
      if (file.size > MAX_MB * 1024 * 1024) {
        toast(`${file.name} is larger than ${MAX_MB} MB`, 'error')
        continue
      }
      setUploading(file.name)
      try {
        const document = await api.uploadDocument(file)
        toast(`${document.filename} indexed: ${document.chunk_count} chunks from ${document.page_count} pages`)
        state.reload()
      } catch (err) {
        toast(`${file.name}: ${err instanceof Error ? err.message : 'upload failed'}`, 'error')
      } finally {
        setUploading(null)
      }
    }
    if (inputRef.current) inputRef.current.value = ''
  }

  function onDrop(event: DragEvent) {
    event.preventDefault()
    setDragging(false)
    void upload(event.dataTransfer.files)
  }

  async function confirmDelete() {
    if (!deleting) return
    try {
      await api.deleteDocument(deleting.id)
      toast(`${deleting.filename} deleted`)
      state.reload()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'The document could not be deleted', 'error')
    } finally {
      setDeleting(null)
    }
  }

  const totalChunks = state.data?.reduce((sum, d) => sum + d.chunk_count, 0) ?? 0

  return (
    <PageContainer>
      <PageHeader
        title="Knowledge base"
        description="The documents the AI assistant answers policy questions from. Each PDF is split into chunks, embedded and stored in pgvector."
      />

      <div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`mb-6 flex flex-col items-center rounded-xl border-2 border-dashed px-6 py-8 text-center transition-colors ${
          dragging ? 'border-brand bg-brand-soft' : 'border-line-strong bg-surface'
        }`}
      >
        {uploading ? (
          <p className="flex items-center gap-2 text-sm text-ink-2" role="status">
            <Spinner /> Indexing {uploading}… (extracting text and creating embeddings)
          </p>
        ) : (
          <>
            <Upload aria-hidden className="mb-2 size-6 text-brand" />
            <p className="font-medium">Drop PDF files here</p>
            <p className="mt-0.5 text-sm text-muted">Up to {MAX_MB} MB each. Text-based PDFs only (scans without text can't be read).</p>
            <input ref={inputRef} id="pdf-input" type="file" accept="application/pdf,.pdf" multiple className="sr-only" onChange={(e) => void upload(e.target.files)} />
            <Button variant="secondary" className="mt-4" onClick={() => inputRef.current?.click()}>
              Choose files
            </Button>
          </>
        )}
      </div>

      <Panel title={state.data ? `${state.data.length} documents, ${totalChunks} chunks` : 'Documents'} flush>
        {state.loading && !state.data ? (
          <SkeletonRows rows={5} />
        ) : state.error ? (
          <ErrorState error={state.error} onRetry={state.reload} />
        ) : !state.data?.length ? (
          <EmptyState icon={FileText} title="No documents yet">
            Upload your return policy, shipping policy or FAQ so the assistant can answer from them.
          </EmptyState>
        ) : (
          <ul className="divide-y divide-line">
            {state.data.map((doc) => (
              <li key={doc.id} className="flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-3">
                <FileText aria-hidden className="size-5 shrink-0 text-brand" />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{doc.filename}</p>
                  <p className="text-xs text-muted">
                    Uploaded {formatDate(doc.uploaded_at)}, {doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}, {formatBytes(doc.size_bytes)}
                  </p>
                </div>
                <span className="rounded-md bg-surface-2 px-2 py-1 text-xs tabular-nums text-ink-2">Chunks: {doc.chunk_count}</span>
                <div className="flex gap-1">
                  <Button variant="ghost" onClick={() => setViewing(doc)}>
                    View chunks
                  </Button>
                  <Button variant="ghost" onClick={() => setDeleting(doc)} aria-label={`Delete ${doc.filename}`}>
                    <Trash2 aria-hidden className="size-4 text-bad" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <ChunksDialog document={viewing} onClose={() => setViewing(null)} />
      <Dialog open={deleting !== null} onClose={() => setDeleting(null)} title="Delete document?">
        <p className="text-sm text-ink-2">
          <strong>{deleting?.filename}</strong> and its {deleting?.chunk_count} chunks will be removed. The assistant can no longer use it for answers.
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleting(null)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={() => void confirmDelete()}>
            Delete document
          </Button>
        </div>
      </Dialog>
    </PageContainer>
  )
}

function ChunksDialog({ document, onClose }: { document: DocumentInfo | null; onClose: () => void }) {
  const id = document?.id
  const state = useApi(() => (id ? api.document(id) : Promise.resolve(null)), [id])
  return (
    <Dialog open={document !== null} onClose={onClose} title={document?.filename ?? 'Document'}>
      {state.loading ? (
        <SkeletonRows rows={3} />
      ) : state.error ? (
        <ErrorState error={state.error} onRetry={state.reload} />
      ) : state.data ? (
        <>
          <p className="mb-3 text-xs text-muted">
            Document ID {state.data.id}, uploaded {formatDateTime(state.data.uploaded_at)}, {state.data.chunks.length} chunks
          </p>
          <ol className="max-h-[55vh] space-y-2 overflow-y-auto pr-1">
            {state.data.chunks.map((chunk) => (
              <li key={chunk.id} className="rounded-lg border border-line bg-surface-2 p-3 text-xs">
                <p className="mb-1 font-mono text-muted">
                  chunk {chunk.chunk_index}, page {chunk.page_number ?? '?'}, id {chunk.id}
                </p>
                <p className="leading-relaxed text-ink-2">{chunk.content}</p>
              </li>
            ))}
          </ol>
        </>
      ) : null}
    </Dialog>
  )
}
