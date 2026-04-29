import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authApi } from '../api/client'

interface Agent {
  agent_id: number
  name: string
  role: string
  access_token: string
}

interface AuthContextType {
  agent: Agent | null
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [agent, setAgent] = useState<Agent | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const stored = localStorage.getItem('llv_agent')
    if (stored) setAgent(JSON.parse(stored))
    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string) => {
    const res = await authApi.login(email, password)
    const data = res.data
    localStorage.setItem('llv_token', data.access_token)
    localStorage.setItem('llv_agent', JSON.stringify(data))
    setAgent(data)
  }

  const logout = () => {
    localStorage.removeItem('llv_token')
    localStorage.removeItem('llv_agent')
    setAgent(null)
  }

  return (
    <AuthContext.Provider value={{ agent, login, logout, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
