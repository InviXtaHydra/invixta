import { Fragment, type ReactNode } from 'react'

/**
 * Renders the assistant's text with the little Markdown it uses: paragraphs, bullet and numbered
 * lists, **bold**, `code` and source citations like [S1]. It builds React elements (never raw HTML),
 * so text from the model can't inject markup.
 */
export function MessageText({ text }: { text: string }) {
  const blocks = text.trim().split(/\n{2,}/)
  return (
    <div className="space-y-2.5 leading-relaxed">
      {blocks.map((block, i) => {
        const lines = block.split('\n')
        if (lines.every((line) => /^\s*[-*•]\s+/.test(line))) {
          return (
            <ul key={i} className="list-disc space-y-1 pl-5">
              {lines.map((line, j) => (
                <li key={j}>{inline(line.replace(/^\s*[-*•]\s+/, ''))}</li>
              ))}
            </ul>
          )
        }
        if (lines.every((line) => /^\s*\d+[.)]\s+/.test(line))) {
          return (
            <ol key={i} className="list-decimal space-y-1 pl-5">
              {lines.map((line, j) => (
                <li key={j}>{inline(line.replace(/^\s*\d+[.)]\s+/, ''))}</li>
              ))}
            </ol>
          )
        }
        return (
          <p key={i}>
            {lines.map((line, j) => (
              <Fragment key={j}>
                {j > 0 && <br />}
                {inline(line.replace(/^#{1,6}\s+/, ''))}
              </Fragment>
            ))}
          </p>
        )
      })}
    </div>
  )
}

const TOKEN = /(\*\*[^*]+\*\*|`[^`]+`|\[S?\d+\])/g

function inline(text: string): ReactNode[] {
  return text.split(TOKEN).map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**') && part.length > 4) return <strong key={i}>{part.slice(2, -2)}</strong>
    if (part.startsWith('`') && part.endsWith('`') && part.length > 2)
      return (
        <code key={i} className="rounded bg-surface-2 px-1 font-mono text-[0.9em]">
          {part.slice(1, -1)}
        </code>
      )
    if (/^\[S?\d+\]$/.test(part))
      return (
        <sup key={i} className="ml-0.5 rounded bg-brand-soft px-1 font-mono text-[0.7em] font-medium text-brand">
          {part.slice(1, -1)}
        </sup>
      )
    return part
  })
}
