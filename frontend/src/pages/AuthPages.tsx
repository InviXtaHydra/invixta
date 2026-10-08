import { useState, type FormEvent, type ReactNode } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../auth/useAuth'
import { Logo } from '../components/AppShell'
import { Jersey } from '../components/shop/Jersey'
import { Button, Field, Input } from '../components/ui'
import { CURRENT_YEAR } from '../lib/format'


/** The left half of the auth pages: a shirt with your name, and what an account is for. */
function Showcase() {
  return (
    <div className="relative hidden flex-col justify-between overflow-hidden bg-night p-10 text-night-ink lg:flex">
      <div aria-hidden className="absolute inset-0 opacity-[0.05] [background:repeating-linear-gradient(90deg,#fff_0_60px,transparent_60px_120px)]" />
      <div aria-hidden className="absolute inset-x-0 bottom-0 flex h-1.5">
        <span className="flex-1 bg-accent" />
        <span className="flex-1 bg-brand" />
      </div>
      <Link to="/" className="relative">
        <Logo inverted />
      </Link>
      <div className="relative max-w-md">
        <Jersey primary="#1D4ED8" secondary="#E11D2E" pattern="stripes" view="back" name="INVIXTA" number={10} label="" className="mb-8 w-56 drop-shadow-2xl" />
        <p className="font-display text-5xl font-extrabold uppercase leading-[0.95]">Your shirts, your orders, one account.</p>
        <p className="mt-4 text-white/75">
          Keep your cart, follow your orders from payment to your door, and ask our assistant anything about sizes, delivery or
          returns.
        </p>
      </div>
      <p className="relative text-xs text-white/50">© {CURRENT_YEAR} Invixta</p>
    </div>
  )
}

function AuthLayout({ title, subtitle, children }: { title: string; subtitle: ReactNode; children: ReactNode }) {
  return (
    <div className="grid min-h-dvh lg:grid-cols-2">
      <Showcase />
      <main className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden">
            <Logo />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          <p className="mt-1 text-sm text-muted">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </main>
    </div>
  )
}

function FormError({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p role="alert" className="rounded-lg bg-bad-soft px-3 py-2 text-sm text-bad">
      {message}
    </p>
  )
}

export function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const from = (location.state as { from?: string } | null)?.from

  if (user) return <Navigate to={from ?? '/'} replace />

  async function signIn(emailAddress: string, pw: string) {
    setBusy(true)
    setError(null)
    try {
      const me = await login(emailAddress, pw)
      // Back to where you were (e.g. the checkout); staff go to their dashboard.
      navigate(from ?? (me.role === 'CUSTOMER' ? '/' : '/dashboard'), { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed')
    } finally {
      setBusy(false)
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    void signIn(email.trim(), password)
  }

  return (
    <AuthLayout
      title="Sign in"
      subtitle={
        <>
          No account yet?{' '}
          <Link to="/register" className="font-medium text-brand hover:underline">
            Create one
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <Field label="Email">
          {(props) => (
            <Input {...props} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          )}
        </Field>
        <Field label="Password">
          {(props) => (
            <Input
              {...props}
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          )}
        </Field>
        <Button type="submit" className="w-full" disabled={busy || !email || !password}>
          {busy ? 'Signing in…' : 'Sign in'}
        </Button>
      </form>

    </AuthLayout>
  )
}

export function RegisterPage() {
  const { user, register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  if (user) return <Navigate to="/" replace />

  const passwordError = form.password && form.password.length < 8 ? 'Use at least 8 characters' : undefined
  const confirmError = form.confirm && form.confirm !== form.password ? "The passwords don't match" : undefined
  const canSubmit = form.name.trim() && form.email.trim() && form.password.length >= 8 && form.confirm === form.password

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!canSubmit) return
    setBusy(true)
    setError(null)
    try {
      await register(form.name.trim(), form.email.trim(), form.password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
    } finally {
      setBusy(false)
    }
  }

  const set = (key: keyof typeof form) => (event: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [key]: event.target.value })

  return (
    <AuthLayout
      title="Create your account"
      subtitle={
        <>
          Already registered?{' '}
          <Link to="/login" className="font-medium text-brand hover:underline">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        <FormError message={error} />
        <Field label="Full name">{(props) => <Input {...props} autoComplete="name" value={form.name} onChange={set('name')} />}</Field>
        <Field label="Email">
          {(props) => <Input {...props} type="email" autoComplete="email" value={form.email} onChange={set('email')} />}
        </Field>
        <Field label="Password" hint="At least 8 characters" error={passwordError}>
          {(props) => <Input {...props} type="password" autoComplete="new-password" value={form.password} onChange={set('password')} />}
        </Field>
        <Field label="Repeat password" error={confirmError}>
          {(props) => <Input {...props} type="password" autoComplete="new-password" value={form.confirm} onChange={set('confirm')} />}
        </Field>
        <Button type="submit" className="w-full" disabled={busy || !canSubmit}>
          {busy ? 'Creating account…' : 'Create account'}
        </Button>
      </form>
    </AuthLayout>
  )
}
