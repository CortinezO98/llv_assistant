import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

// Definición de nav con permisos por rol
const NAV_ITEMS = [
  { to: '/',              label: 'Dashboard',      icon: '◈', roles: ['admin', 'supervisor'] },
  { to: '/conversations', label: 'Conversaciones', icon: '💬', roles: ['admin', 'supervisor', 'agent'] },
  { to: '/appointments',  label: 'Citas',          icon: '📅', roles: ['admin', 'supervisor', 'agent'] },
  { to: '/patients',      label: 'Pacientes',      icon: '👤', roles: ['admin', 'supervisor', 'agent'] },
  { to: '/agents',        label: 'Agentes',        icon: '🎧', roles: ['admin', 'supervisor'] },
  { to: '/faq',           label: 'Base FAQ',       icon: '📚', roles: ['admin', 'supervisor'] },
  { to: '/reports',       label: 'Reportería',     icon: '📊', roles: ['admin', 'supervisor'] },
  { to: '/plan',          label: 'Plan / Uso',     icon: '⚡', roles: ['admin'] },
]

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador',
  supervisor: 'Supervisor',
  agent: 'Agente',
}

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-violet-100 text-violet-700',
  supervisor: 'bg-blue-100 text-blue-700',
  agent: 'bg-brand-100 text-brand-700',
}

export default function AppLayout() {
  const { agent, logout } = useAuth()
  const navigate = useNavigate()
  const role = agent?.role || 'agent'

  // Filtrar items de nav según el rol del agente
  const visibleItems = NAV_ITEMS.filter(item => item.roles.includes(role))

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#f8faf9]">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <aside className="w-60 flex-shrink-0 bg-white border-r border-[#e4ede8] flex flex-col">

        {/* Logo */}
        <div className="px-5 py-5 border-b border-[#e4ede8]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center flex-shrink-0">
              <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
                <path d="M6 8C6 6.9 6.9 6 8 6h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H10l-4 4V8z"
                  fill="white" fillOpacity=".9"/>
              </svg>
            </div>
            <div>
              <div className="font-display font-bold text-sm text-brand-800 leading-tight">LLV Assistant</div>
              <div className="text-[10px] text-[#6b8a78] font-medium">LRV Clinic</div>
            </div>
          </div>
        </div>

        {/* Rol badge */}
        <div className="px-4 py-2.5 border-b border-[#e4ede8]">
          <span className={`badge text-[10px] ${ROLE_COLORS[role] || 'bg-gray-100 text-gray-600'}`}>
            {ROLE_LABELS[role] || role}
          </span>
          {role === 'agent' && (
            <p className="text-[9px] text-[#6b8a78] mt-1">Solo ves tus conversaciones asignadas</p>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {visibleItems.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="text-base leading-none">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Perfil del agente */}
        <div className="px-3 py-4 border-t border-[#e4ede8]">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-brand-50">
            <div className="w-8 h-8 bg-brand-600 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {agent?.name?.charAt(0) || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-brand-800 truncate">{agent?.name}</div>
              <div className="text-[10px] text-[#6b8a78]">{ROLE_LABELS[role]}</div>
            </div>
            <button
              onClick={handleLogout}
              className="text-[#6b8a78] hover:text-red-500 transition-colors p-1 flex-shrink-0"
              title="Cerrar sesión"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16,17 21,12 16,7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main content ────────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
