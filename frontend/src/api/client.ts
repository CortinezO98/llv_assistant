import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Interceptor: agrega token JWT a cada request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('llv_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Interceptor: redirige al login si el token expira
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('llv_token')
      localStorage.removeItem('llv_agent')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
}

// ── Dashboard ─────────────────────────────────────────────────────────────────
export const dashboardApi = {
  getKpis: (days = 30) => api.get(`/dashboard/kpis?days=${days}`),
  getAgentsRanking: () => api.get('/dashboard/agents-ranking'),
  getRecentActivity: (limit = 20) => api.get(`/dashboard/recent-activity?limit=${limit}`),
}

// ── Agents ────────────────────────────────────────────────────────────────────
export const agentsApi = {
  list: () => api.get('/agents/'),
  create: (data: any) => api.post('/agents/', data),
  update: (id: number, data: any) => api.patch(`/agents/${id}`, data),
}

// ── Patients ──────────────────────────────────────────────────────────────────
export const patientsApi = {
  list: () => api.get('/patients/'),
  get: (id: number) => api.get(`/patients/${id}`),
}

// ── Appointments ──────────────────────────────────────────────────────────────
export const appointmentsApi = {
  list: (status?: string) => api.get(`/appointments/${status ? `?status=${status}` : ''}`),
  confirm: (id: number) => api.patch(`/appointments/${id}/confirm`),
}

// ── FAQ ───────────────────────────────────────────────────────────────────────
export const faqApi = {
  list: (category?: string) => api.get(`/faq/${category ? `?category=${category}` : ''}`),
  create: (data: any) => api.post('/faq/', data),
  update: (id: number, data: any) => api.patch(`/faq/${id}`, data),
  delete: (id: number) => api.delete(`/faq/${id}`),
}

// ── Plan ──────────────────────────────────────────────────────────────────────
export const planApi = {
  getUsage: () => api.get('/plan/usage'),
  renew: (data: { plan_limit: number; payment_reference?: string; notes?: string }) =>
    api.post('/plan/renew', data),
  addConversations: (data: { extra_conversations: number; payment_reference?: string; notes?: string }) =>
    api.post('/plan/add-conversations', data),
  toggleService: (data: { service_active: boolean; notes?: string }) =>
    api.post('/plan/toggle-service', data),
}

// ── Conversations ─────────────────────────────────────────────────────────────
export const conversationsApi = {
  list: (status?: string) => api.get(`/conversations/${status ? `?status=${status}` : ''}`),
  getMessages: (sessionId: number) => api.get(`/conversations/${sessionId}/messages`),
  send: (sessionId: number, message: string) =>
    api.post(`/conversations/${sessionId}/send`, { message }),
  take: (sessionId: number) => api.post(`/conversations/${sessionId}/take`),
  close: (sessionId: number) => api.post(`/conversations/${sessionId}/close`),
  transfer: (sessionId: number, agentId: number) =>
    api.post(`/conversations/${sessionId}/transfer`, { agent_id: agentId }),
  myStats: () => api.get('/conversations/stats/me'),
  createAppointment: (sessionId: number, data: any) =>
    api.post(`/conversations/${sessionId}/appointment`, data),
  createDelivery: (sessionId: number, data: any) =>
    api.post(`/conversations/${sessionId}/delivery`, data),
}