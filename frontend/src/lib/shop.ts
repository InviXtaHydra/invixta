/** "DE VRIES 10", "DE VRIES", "10" or null: what is printed on the back of a shirt. */
export function printing(line: { personalization_name: string | null; personalization_number: number | null }): string | null {
  const parts = [line.personalization_name, line.personalization_number ?? null].filter((p) => p !== null && p !== '')
  return parts.length ? parts.join(' ') : null
}
