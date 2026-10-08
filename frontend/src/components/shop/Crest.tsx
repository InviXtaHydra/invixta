import type { Team } from '../../api/types'
import { readableOn } from './colors'

/** A simple shield in the club colours with its short name. All crests are made up. */
export function Crest({ team, className = '' }: { team: Team; className?: string }) {
  const ink = readableOn(team.primary_color, [team.secondary_color, '#ffffff', '#111111'])
  return (
    <svg viewBox="0 0 40 46" className={className} role="img" aria-label={`${team.name} crest`}>
      <path d="M2 2 H38 V22 Q38 38 20 44 Q2 38 2 22 Z" fill={team.primary_color} stroke={team.secondary_color} strokeWidth="3" />
      <text x="20" y="27" textAnchor="middle" fontFamily="Barlow Condensed, sans-serif" fontWeight="800" fontSize="12" fill={ink}>
        {team.short_name}
      </text>
    </svg>
  )
}
