import { FileText } from 'lucide-react'
import type { Source } from '../../api/types'

/** "Returns and Exchanges.pdf" → "Returns and Exchanges" */
const title = (filename: string) => filename.replace(/\.pdf$/i, '')

/** The help articles an answer is based on; open one to read the passage. */
export function Sources({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null
  // One entry per article, with the passages from it.
  const articles = new Map<string, Source[]>()
  for (const source of sources) articles.set(source.filename, [...(articles.get(source.filename) ?? []), source])
  return (
    <div className="mt-3 border-t border-line pt-3">
      <p className="mb-2 text-xs font-medium text-muted">Based on</p>
      <ul className="space-y-1.5">
        {[...articles.entries()].map(([filename, passages]) => (
          <li key={filename}>
            <details className="rounded-lg border border-line bg-surface-2 px-3 py-2 text-sm">
              <summary className="flex cursor-pointer list-none items-center gap-2">
                <FileText aria-hidden className="size-3.5 shrink-0 text-brand" />
                <span className="truncate font-medium text-ink-2">{title(filename)}</span>
              </summary>
              {passages.map((p) => (
                <p key={p.chunk_id} className="mt-2 text-xs leading-relaxed text-ink-2">
                  {p.excerpt}
                </p>
              ))}
            </details>
          </li>
        ))}
      </ul>
    </div>
  )
}
