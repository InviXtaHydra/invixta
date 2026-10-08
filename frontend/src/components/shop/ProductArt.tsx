import { Backpack, Footprints, Hand, Shield } from 'lucide-react'
import type { ProductCategory, Team } from '../../api/types'
import { Jersey, type JerseyStyle } from './Jersey'
import { shade } from './colors'

interface Props {
  name: string
  category: ProductCategory
  team: Team | null
  season?: string | null
  slug?: string
  view?: 'front' | 'back'
  printName?: string | null
  printNumber?: number | null
  className?: string
}

const STYLE: Partial<Record<ProductCategory, JerseyStyle>> = { home: 'home', kids: 'home', away: 'away', training: 'training', retro: 'retro' }
const KOPBAL = { primary: '#0F5132', secondary: '#F5C518' }

/** The picture of a product: a drawn shirt, scarf or ball in the club colours, or an icon. */
export function ProductArt({ name, category, team, season, slug = '', view = 'front', printName, printNumber, className = '' }: Props) {
  const colors = team ? { primary: team.primary_color, secondary: team.secondary_color } : KOPBAL
  const style = STYLE[category]

  if (style) {
    return (
      <Jersey
        primary={colors.primary}
        secondary={colors.secondary}
        pattern={team?.pattern ?? 'plain'}
        style={style}
        view={view}
        crest={team?.short_name}
        year={category === 'retro' ? season : null}
        name={printName}
        number={printNumber}
        label={`${name}${view === 'back' ? ', back' : ''}`}
        className={className}
      />
    )
  }
  if (slug.endsWith('-scarf')) return <Scarf {...colors} label={name} className={className} />
  if (slug.includes('ball')) return <Ball label={name} className={className} />

  const Icon = slug.includes('gloves') ? Hand : slug.includes('bag') ? Backpack : slug.includes('socks') ? Footprints : Shield
  return (
    <div role="img" aria-label={name} className={`grid aspect-[200/220] place-items-center ${className}`}>
      <Icon aria-hidden className="size-1/2" strokeWidth={1.25} color={colors.primary} />
    </div>
  )
}

function Scarf({ primary, secondary, label, className }: { primary: string; secondary: string; label: string; className: string }) {
  const bands = [0, 1, 2, 3, 4, 5, 6, 7]
  return (
    <svg viewBox="0 0 200 220" role="img" aria-label={label} className={className}>
      <g transform="rotate(-28 100 110)">
        {bands.map((i) => (
          <rect key={i} x={10 + i * 23} y="88" width="23" height="44" fill={i % 2 ? secondary : primary} />
        ))}
        <rect x="10" y="88" width="184" height="44" fill="none" stroke={shade(primary, 0.3)} strokeWidth="1.5" />
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <line key={`l${i}`} x1="10" y1={92 + i * 7.5} x2="0" y2={92 + i * 7.5} stroke={primary} strokeWidth="2" />
        ))}
        {[0, 1, 2, 3, 4, 5].map((i) => (
          <line key={`r${i}`} x1="194" y1={92 + i * 7.5} x2="204" y2={92 + i * 7.5} stroke={primary} strokeWidth="2" />
        ))}
      </g>
    </svg>
  )
}

function Ball({ label, className }: { label: string; className: string }) {
  return (
    <svg viewBox="0 0 200 220" role="img" aria-label={label} className={className}>
      <circle cx="100" cy="110" r="72" fill="#ffffff" stroke="#1d2a22" strokeWidth="3" />
      <path d="M100 82 L126 100 L116 130 L84 130 L74 100 Z" fill="#1d2a22" />
      {[
        'M100 38 L100 82',
        'M126 100 L168 86',
        'M116 130 L140 166',
        'M84 130 L60 166',
        'M74 100 L32 86',
      ].map((d) => (
        <path key={d} d={d} stroke="#1d2a22" strokeWidth="3" />
      ))}
      <path d="M86 40 L100 38 L114 40 L108 52 L92 52 Z" fill="#1d2a22" />
      <path d="M164 74 L168 86 L172 100 L158 98 L156 82 Z" fill="#1d2a22" />
      <path d="M36 74 L32 86 L28 100 L42 98 L44 82 Z" fill="#1d2a22" />
    </svg>
  )
}
