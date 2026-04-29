import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/',              label: 'Dashboard',       icon: '◈',  roles: ['admin', 'supervisor'] },
  { to: '/conversations', label: 'Conversaciones',  icon: '💬', roles: ['admin', 'supervisor', 'agent'] },
  { to: '/appointments',  label: 'Citas',           icon: '📅', roles: ['admin', 'supervisor', 'agent'] },
  { to: '/deliveries',    label: 'Entregas/Envíos', icon: '📦', roles: ['admin', 'supervisor', 'agent'] },
  { to: '/patients',      label: 'Pacientes',       icon: '👤', roles: ['admin', 'supervisor', 'agent'] },
  { to: '/agents',        label: 'Agentes',         icon: '🎧', roles: ['admin', 'supervisor'] },
  { to: '/faq',           label: 'Base FAQ',        icon: '📚', roles: ['admin', 'supervisor'] },
  { to: '/reports',       label: 'Reportería',      icon: '📊', roles: ['admin', 'supervisor'] },
  { to: '/plan',          label: 'Plan / Uso',      icon: '⚡', roles: ['admin'] },
]

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador', supervisor: 'Supervisor', agent: 'Agente',
}
const ROLE_COLORS: Record<string, string> = {
  admin:      'bg-[#C6A96B]/20 text-[#8a6d3a]',
  supervisor: 'bg-blue-100 text-blue-700',
  agent:      'bg-[#0b4c45]/10 text-[#0b4c45]',
}

export default function AppLayout() {
  const { agent, logout } = useAuth()
  const navigate = useNavigate()
  const role = agent?.role || 'agent'
  const visibleItems = NAV_ITEMS.filter(item => item.roles.includes(role))

  return (
    <div className="flex h-screen overflow-hidden bg-[#f8f6f2]">
      <aside className="w-60 flex-shrink-0 bg-white border-r border-[#e5ddd4] flex flex-col">

        {/* Logo LLV */}
        <div className="px-5 py-5 border-b border-[#e5ddd4]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-[#0b4c45] rounded-xl flex items-center justify-center flex-shrink-0">
              <span className="text-[#C6A96B] font-display font-bold text-sm">LLV</span>
            </div>
            <div>
              <div className="font-display font-bold text-sm text-[#0b4c45] leading-tight">LLV Assistant</div>
              <div className="text-[10px] text-[#7a6a55] font-medium">Wellness Clinic</div>
            </div>
          </div>
        </div>

        {/* Rol badge */}
        <div className="px-4 py-2.5 border-b border-[#e5ddd4]">
          <span className={`badge text-[10px] ${ROLE_COLORS[role]}`}>{ROLE_LABELS[role] || role}</span>
          {role === 'agent' && (
            <p className="text-[9px] text-[#7a6a55] mt-1">Solo ves tus conversaciones</p>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {visibleItems.map(item => (
            <NavLink key={item.to} to={item.to} end={item.to === '/'}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
              <span className="text-base leading-none">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Perfil */}
        <div className="px-3 py-4 border-t border-[#e5ddd4]">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-[#F5F1EB]">
            <div className="w-8 h-8 bg-[#0b4c45] rounded-full flex items-center justify-center text-[#C6A96B] text-xs font-bold flex-shrink-0">
              {agent?.name?.charAt(0) || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-[#0b4c45] truncate">{agent?.name}</div>
              <div className="text-[10px] text-[#7a6a55]">{ROLE_LABELS[role]}</div>
            </div>
            <button onClick={() => { logout(); navigate('/login') }}
              className="text-[#7a6a55] hover:text-red-500 transition-colors p-1" title="Cerrar sesión">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16,17 21,12 16,7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
