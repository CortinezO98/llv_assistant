import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import AppLayout from './components/AppLayout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import AgentsPage from './pages/AgentsPage'
import FaqPage from './pages/FaqPage'
import { AppointmentsPage } from './pages/AppointmentsPage'
import { PatientsPage, ConversationsPage, PlanPage } from './pages/OtherPages'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { agent, isLoading } = useAuth()
  if (isLoading) return (
    <div className="min-h-screen flex items-center justify-center bg-brand-50">
      <svg className="animate-spin w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".2"/>
        <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
      </svg>
    </div>
  )
  if (!agent) return <Navigate to="/login" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }>
            <Route index element={<DashboardPage />} />
            <Route path="conversations" element={<ConversationsPage />} />
            <Route path="appointments" element={<AppointmentsPage />} />
            <Route path="patients" element={<PatientsPage />} />
            <Route path="agents" element={<AgentsPage />} />
            <Route path="faq" element={<FaqPage />} />
            <Route path="plan" element={<PlanPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
