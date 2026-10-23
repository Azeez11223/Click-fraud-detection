import { zodResolver } from '@hookform/resolvers/zod'
import { ShieldCheck } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ApiError } from '@/api/client'
import { useAuth } from '@/auth/AuthProvider'
import { ApiStatusBanner } from '@/components/ApiStatusBanner'
import { Button } from '@/components/ui/button'

const schema = z.object({ email: z.email('Enter a valid email address'), password: z.string().min(1, 'Enter your password') })
type LoginValues = z.infer<typeof schema>

export default function LoginPage() {
  const { login, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [serverError, setServerError] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginValues>({ resolver: zodResolver(schema) })
  if (user) return <Navigate to="/dashboard" replace />

  async function onSubmit(values: LoginValues) {
    setServerError('')
    try {
      await login(values.email, values.password)
      const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/dashboard'
      navigate(from, { replace: true })
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : 'Sign in failed. Try again.')
    }
  }

  return <AuthFrame title="Welcome back" subtitle="Sign in to protect your ad spend.">
    <ApiStatusBanner />
    <form className="space-y-5" onSubmit={handleSubmit(onSubmit)} noValidate>
      <Field label="Email address" error={errors.email?.message}>
        <input className="auth-input" type="email" autoComplete="email" placeholder="you@company.com" {...register('email')} />
      </Field>
      <Field label="Password" error={errors.password?.message}>
        <input className="auth-input" type="password" autoComplete="current-password" placeholder="Your password" {...register('password')} />
      </Field>
      {serverError && <p role="alert" className="text-sm text-danger">{serverError}</p>}
      <Button className="w-full" disabled={isSubmitting}>{isSubmitting ? 'Signing in…' : 'Sign in'}</Button>
    </form>
    <p className="mt-7 text-center text-sm text-muted">New to AdShield? <Link className="font-semibold text-accent hover:underline" to="/signup">Create an account</Link></p>
  </AuthFrame>
}

export function AuthFrame({ title, subtitle, children }: { title: string; subtitle: string; children: React.ReactNode }) {
  return <main className="grid min-h-screen place-items-center bg-background px-5 py-10">
    <section className="w-full max-w-md rounded-2xl border border-border bg-[#090e1b] p-7 shadow-2xl shadow-black/30 sm:p-9">
      <Link to="/login" className="mb-9 flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-accent/10 text-accent"><ShieldCheck size={22} /></span>
        <span className="font-heading text-xl font-bold tracking-tight">AdShield</span>
      </Link>
      <h1 className="font-heading text-3xl font-bold tracking-tight">{title}</h1>
      <p className="mb-7 mt-2 text-sm text-muted">{subtitle}</p>
      {children}
    </section>
  </main>
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return <label className="block space-y-2 text-sm font-medium text-slate-200">{label}{children}{error && <span role="alert" className="block text-xs text-danger">{error}</span>}</label>
}
