/**
 * SAATHI AI — Auth Context
 * Provides authenticated clinician state across the app.
 */
import React, { createContext, useContext, useState, useCallback } from 'react'
import { login as apiLogin } from '@/lib/api'

interface AuthUser {
  id: string
  email: string
  fullName: string
  tenantId: string
}

interface AuthContextType {
  user: AuthUser | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)

  const login = useCallback(async (email: string, password: string) => {
    const { data } = await apiLogin(email, password)
    localStorage.setItem('saathi_token', data.access_token)
    // TODO: Decode JWT or call /users/me to get user details
    setUser({ id: '', email, fullName: '', tenantId: '' })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('saathi_token')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
