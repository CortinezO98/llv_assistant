import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navItems = [
  { to: '/',              label: 'Dashboard',      icon: '◈' },
  { to: '/conversations', label: 'Conversaciones', icon: '💬' },
  { to: '/appointments',  label: 'Citas',          icon: '📅' },
  { to: '/patients',      label: 'Pacientes',      icon: '👤' },
  { to: '/agents',        label: 'Agentes',        icon: '🎧' },
  { to: '/faq',           label: 'Base FAQ',       icon: '📚' },
  { to: '/reports',       label: 'Reportería',     icon: '📊' },
  { to: '/plan',          label: 'Plan / Uso',     icon: '⚡' },
]

export default function AppLayout() {
  const { agent, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-[#f8faf9]">
      {/* Sidebar */}
      <aside className="w-60 flex-shrink-0 bg-white border-r border-[#e4ede8] flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-[#e4ede8]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-brand-600 rounded-xl flex items-center justify-center flex-shrink-0">
              <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
                <path d="M6 8C6 6.9 6.9 6 8 6h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H10l-4 4V8z" fill="white" fillOpacity=".9"/>
              </svg>
            </div>
            <div>
              <div className="font-display font-bold text-sm text-brand-800 leading-tight">LLV Assistant</div>
              <div className="text-[10px] text-[#6b8a78] font-medium">LRV Clinic Dashboard</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
          {navItems.map((item) => (
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

        {/* Agent info */}
        <div className="px-3 py-4 border-t border-[#e4ede8]">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-brand-50">
            <div className="w-8 h-8 bg-brand-600 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
              {agent?.name?.charAt(0) || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-brand-800 truncate">{agent?.name}</div>
              <div className="text-[10px] text-[#6b8a78] capitalize">{agent?.role}</div>
            </div>
            <button onClick={handleLogout} className="text-[#6b8a78] hover:text-red-500 transition-colors p-1" title="Cerrar sesión">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16,17 21,12 16,7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
