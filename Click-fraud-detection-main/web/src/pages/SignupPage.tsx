import { zodResolver } from '@hookform/resolvers/zod'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { z } from 'zod'
import { ApiError } from '@/api/client'
import { useAuth } from '@/auth/AuthProvider'
import { ApiStatusBanner } from '@/components/ApiStatusBanner'
import { Button } from '@/components/ui/button'
import { AuthFrame } from './LoginPage'

const schema = z.object({
  name: z.string().trim().min(1, 'Enter your name').max(100, 'Name must be 100 characters or fewer'),
  email: z.email('Enter a valid email address'),
  password: z.string().min(10, 'Use at least 10 characters').max(128, 'Password must be 128 characters or fewer'),
})
type SignupValues = z.infer<typeof schema>

export default function SignupPage() {
  const { signup, user } = useAuth()
  const navigate = useNavigate()
  const [serverError, setServerError] = useState('')
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<SignupValues>({ resolver: zodResolver(schema) })
  if (user) return <Navigate to="/dashboard" replace />

  async function onSubmit(values: SignupValues) {
    setServerError('')
    try {
      await signup(values)
      navigate('/login', { replace: true, state: { notice: 'Account created. Sign in to continue.' } })
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : 'Account creation failed. Try again.')
    }
  }

  return <AuthFrame title="Create your account" subtitle="Start keeping your campaigns safe.">
    <ApiStatusBanner />
    <form className="space-y-4" onSubmit={handleSubmit(onSubmit)} noValidate>
      <SignupField label="Full name" error={errors.name?.message}><input className="auth-input" autoComplete="name" placeholder="Alex Morgan" {...register('name')} /></SignupField>
      <SignupField label="Email address" error={errors.email?.message}><input className="auth-input" type="email" autoComplete="email" placeholder="you@company.com" {...register('email')} /></SignupField>
      <SignupField label="Password" error={errors.password?.message}><input className="auth-input" type="password" autoComplete="new-password" placeholder="At least 10 characters" {...register('password')} /></SignupField>
      {serverError && <p role="alert" className="text-sm text-danger">{serverError}</p>}
      <Button className="mt-2 w-full" disabled={isSubmitting}>{isSubmitting ? 'Creating account…' : 'Create account'}</Button>
    </form>
    <p className="mt-7 text-center text-sm text-muted">Already have an account? <Link className="font-semibold text-accent hover:underline" to="/login">Sign in</Link></p>
  </AuthFrame>
}

function SignupField({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return <label className="block space-y-2 text-sm font-medium text-slate-200">{label}{children}{error && <span role="alert" className="block text-xs text-danger">{error}</span>}</label>
}
