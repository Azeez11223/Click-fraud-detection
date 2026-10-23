import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { currentUser, login as loginRequest, signup as signupRequest, type SessionUser, type SignupInput } from '@/api/auth'
import { clearSession, getStoredToken, storeToken } from '@/api/client'

interface AuthContextValue {
  user: SessionUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  signup: (input: SignupInput) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(() => {
    if (!getStoredToken()) return null
    const serialized = sessionStorage.getItem('adshield_user')
    if (!serialized) return null
    try { return JSON.parse(serialized) as SessionUser } catch { return null }
  })
  const [loading, setLoading] = useState(Boolean(getStoredToken()))

  useEffect(() => {
    if (!getStoredToken()) return
    let active = true
    currentUser().then((result) => {
      if (active) {
        setUser(result)
        sessionStorage.setItem('adshield_user', JSON.stringify(result))
      }
    }).catch(() => {
      if (active) setUser(null)
    }).finally(() => {
      if (active) setLoading(false)
    })
    return () => { active = false }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const result = await loginRequest(email, password)
    storeToken(result.access_token)
    sessionStorage.setItem('adshield_user', JSON.stringify(result.user))
    setUser(result.user)
  }, [])

  const signup = useCallback(async (input: SignupInput) => { await signupRequest(input) }, [])
  const logout = useCallback(() => {
    clearSession()
    setUser(null)
  }, [])
  const value = useMemo(() => ({ user, loading, login, signup, logout }), [user, loading, login, signup, logout])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
