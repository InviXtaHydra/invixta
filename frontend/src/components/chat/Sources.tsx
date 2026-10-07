import { FileText } from 'lucide-react'
import type { Source } from '../../api/types'

/** The knowledge-base passages the answer is based on, with document, page and similarity score. */
export function Sources({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null
  return (
    <div className="mt-3 border-t border-line pt-3">
      <p className="mb-2 text-xs font-medium text-muted">Sources</p>
      <ul className="space-y-1.5">
        {sources.map((source) => (
          <li key={source.chunk_id}>
            <details className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm">
              <summary className="flex cursor-pointer list-none items-center gap-2">
                <FileText aria-hidden className="size-3.5 shrink-0 text-brand" />
                <span className="truncate font-medium text-ink-2">{source.filename}</span>
                {source.page_number && <span className="shrink-0 text-xs text-muted">page {source.page_number}</span>}
                <span className="ml-auto shrink-0 font-mono text-xs text-muted" title="Cosine similarity between your question and this passage">
                  {source.score.toFixed(2)}
                </span>
              </summary>
              <p className="mt-2 text-xs leading-relaxed text-ink-2">{source.excerpt}</p>
            </details>
          </li>
        ))}
      </ul>
    </div>
  )
}
