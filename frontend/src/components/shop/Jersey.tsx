import { useId } from 'react'
import type { JerseyPattern } from '../../api/types'
import { readableOn, readableOnAll, shade } from './colors'

export type JerseyStyle = 'home' | 'away' | 'training' | 'retro'

export interface JerseyProps {
  primary: string
  secondary: string
  pattern: JerseyPattern | string
  style?: JerseyStyle
  view?: 'front' | 'back'
  crest?: string // short club name on the crest, e.g. "FCD"
  name?: string | null // printed on the back
  number?: number | null
  year?: string | null // retro shirts: printed under the crest
  label: string // accessible description
  className?: string
}

// The outline of a shirt (viewBox 0 0 200 220): collar, shoulders, sleeves, body.
const SHIRT =
  'M70 18 C82 31 118 31 130 18 L172 36 L197 80 L168 94 L160 74 L160 204 Q100 214 40 204 L40 74 L32 94 L3 80 L28 36 Z'
const LEFT_CUFF = 'M3 80 L32 94 L36 85 L8 71 Z'
const RIGHT_CUFF = 'M197 80 L168 94 L164 85 L192 71 Z'

/**
 * A football shirt drawn from a club's colours and pattern (stripes, hoops, halves, sash or plain).
 * Every club in the shop is fictional, so the shirts are drawn instead of photographed.
 */
export function Jersey({
  primary,
  secondary,
  pattern,
  style = 'home',
  view = 'front',
  crest,
  name,
  number,
  year,
  label,
  className = '',
}: JerseyProps) {
  const id = useId().replace(/:/g, '')
  // Away shirts swap the colours and drop the pattern; training tops are a darker plain version.
  const base = style === 'away' ? secondary : style === 'training' ? shade(primary, 0.35) : primary
  const trim = style === 'away' ? primary : style === 'training' ? secondary : secondary
  const fill = style === 'away' || style === 'training' ? 'plain' : pattern
  const ink = readableOn(base, [trim, '#ffffff', '#111111'])
  // On a patterned back the print crosses both colours: pick a colour readable on both, with an outline.
  const patterned = fill !== 'plain'
  const printInk = patterned ? readableOnAll([base, trim], ['#111111', '#ffffff', trim, base]) : ink
  const printOutline = readableOn(printInk, ['#111111', '#ffffff'])

  return (
    <svg viewBox="0 0 200 220" role="img" aria-label={label} className={className}>
      <defs>
        <clipPath id={`body-${id}`}>
          <path d={SHIRT} />
        </clipPath>
        <linearGradient id={`fold-${id}`} x1="0" x2="1">
          <stop offset="0" stopColor="#000" stopOpacity="0.10" />
          <stop offset="0.25" stopColor="#000" stopOpacity="0" />
          <stop offset="0.75" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity="0.12" />
        </linearGradient>
      </defs>

      <g clipPath={`url(#body-${id})`}>
        <rect width="200" height="220" fill={base} />
        {fill === 'stripes' &&
          [48, 80, 112, 144].map((x) => <rect key={x} x={x} y="0" width="16" height="220" fill={trim} />)}
        {fill === 'hoops' && [40, 84, 128, 172].map((y) => <rect key={y} x="0" y={y} width="200" height="22" fill={trim} />)}
        {fill === 'halves' && <rect x="100" y="0" width="100" height="220" fill={trim} />}
        {fill === 'sash' && <path d="M40 40 L72 30 L172 204 L136 214 Z" fill={trim} />}
        {/* sleeves keep the main colour on patterned shirts */}
        {fill !== 'plain' && fill !== 'halves' && (
          <>
            <path d="M28 36 L3 80 L32 94 L40 74 L40 40 Z" fill={base} />
            <path d="M172 36 L197 80 L168 94 L160 74 L160 40 Z" fill={base} />
          </>
        )}
        <path d={LEFT_CUFF} fill={trim} />
        <path d={RIGHT_CUFF} fill={trim} />
        <rect width="200" height="220" fill={`url(#fold-${id})`} />
      </g>

      {/* collar */}
      {style === 'retro' ? (
        <path d="M70 18 L100 52 L130 18 L118 14 L100 34 L82 14 Z" fill="#ffffff" stroke={shade(base, 0.3)} strokeWidth="1.5" />
      ) : style === 'training' ? (
        <>
          <path d="M70 18 C82 31 118 31 130 18" fill="none" stroke={trim} strokeWidth="6" />
          <line x1="100" y1="29" x2="100" y2="70" stroke={trim} strokeWidth="2.5" />
        </>
      ) : (
        <path d="M70 18 C82 31 118 31 130 18" fill="none" stroke={trim} strokeWidth="6" strokeLinecap="round" />
      )}
      <path d={SHIRT} fill="none" stroke={shade(base, 0.25)} strokeWidth="1.5" strokeLinejoin="round" />

      {view === 'front' ? (
        <>
          {/* crest on the left chest (the wearer's left = viewer's right) */}
          <g transform="translate(118 56)">
            <path d="M0 0 H24 V14 Q24 26 12 30 Q0 26 0 14 Z" fill={trim} stroke={ink} strokeWidth="1.5" />
            {crest && (
              <text x="12" y="17" textAnchor="middle" fontFamily="Barlow Condensed, sans-serif" fontWeight="800" fontSize="9" fill={base}>
                {crest}
              </text>
            )}
          </g>
          {/* maker's mark */}
          <path d="M66 62 l7 -5 l7 5 l-7 5 z" fill={ink} opacity="0.85" />
          {style === 'retro' && year && (
            <text x="130" y="100" textAnchor="middle" fontFamily="Barlow Condensed, sans-serif" fontWeight="700" fontSize="10" fill={ink}>
              {year}
            </text>
          )}
        </>
      ) : (
        <>
          {name && (
            <text
              x="100"
              y="72"
              textAnchor="middle"
              fontFamily="Barlow Condensed, sans-serif"
              fontWeight="700"
              fontSize={name.length > 9 ? 15 : 18}
              letterSpacing="1.5"
              fill={printInk}
              stroke={patterned ? printOutline : 'none'}
              strokeWidth={patterned ? 3 : 0}
              paintOrder="stroke"
            >
              {name}
            </text>
          )}
          {number !== null && number !== undefined && (
            <text
              x="100"
              y="158"
              textAnchor="middle"
              fontFamily="Barlow Condensed, sans-serif"
              fontWeight="800"
              fontSize="78"
              fill={printInk}
              stroke={patterned ? printOutline : shade(base, 0.35)}
              strokeWidth={patterned ? 4 : 1}
              paintOrder="stroke"
            >
              {number}
            </text>
          )}
        </>
      )}
    </svg>
  )
}
