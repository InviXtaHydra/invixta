import { useCallback, useEffect, useEffectEvent, useState } from 'react'

export interface ApiState<T> {
  /** The latest data that loaded (kept while a reload is in progress). */
  data: T | undefined
  error: Error | undefined
  loading: boolean
  reload: () => void
}

interface Result<T> {
  key: string
  data?: T
  error?: Error
}

/**
 * Loads data when the component mounts and whenever `deps` (strings/numbers) change.
 * `loading` is derived: true until a response for the current deps has arrived. Responses for
 * older deps are ignored.
 */
export function useApi<T>(load: () => Promise<T>, deps: readonly (string | number | boolean | null | undefined)[]): ApiState<T> {
  const [version, setVersion] = useState(0)
  const [result, setResult] = useState<Result<T>>()
  const key = JSON.stringify([...deps, version])
  const run = useEffectEvent(load)

  useEffect(() => {
    let current = true
    run().then(
      (data) => current && setResult({ key, data }),
      (error: unknown) => current && setResult((previous) => ({ key, data: previous?.data, error: toError(error) })),
    )
    return () => {
      current = false
    }
  }, [key])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  const settled = result?.key === key
  return { data: result?.data, error: settled ? result.error : undefined, loading: !settled, reload }
}

const toError = (error: unknown) => (error instanceof Error ? error : new Error(String(error)))
