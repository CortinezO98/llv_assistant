import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import Icons from './Icons'
import { useAuth } from '../context/AuthContext'
import { conversationsApi } from '../api/client'

const NAV_ITEMS = [
  {
    to: '/',
    label: 'Dashboard',
    Icon: Icons.Dashboard,
    roles: ['admin', 'supervisor', 'superadmin'],
  },
  {
    to: '/conversations',
    label: 'Conversaciones',
    Icon: Icons.Chat,
    roles: ['admin', 'supervisor', 'agent', 'superadmin'],
    badge: true,
  },
  {
    to: '/appointments',
    label: 'Citas',
    Icon: Icons.Calendar,
    roles: ['admin', 'supervisor', 'agent', 'superadmin'],
  },
  {
    to: '/payments',
    label: 'Pagos',
    Icon: Icons.CreditCard,
    roles: ['admin', 'supervisor', 'agent', 'superadmin'],
  },
  {
    to: '/deliveries',
    label: 'Entregas/Envíos',
    Icon: Icons.Package,
    roles: ['admin', 'supervisor', 'agent', 'superadmin'],
  },
  {
    to: '/patients',
    label: 'Pacientes',
    Icon: Icons.Users,
    roles: ['admin', 'supervisor', 'agent', 'superadmin'],
  },
  {
    to: '/agents',
    label: 'Agentes',
    Icon: Icons.Headphones,
    roles: ['admin', 'supervisor', 'superadmin'],
  },
  {
    to: '/faq',
    label: 'Base FAQ',
    Icon: Icons.Book,
    roles: ['admin', 'supervisor', 'superadmin'],
  },
  {
    to: '/reports',
    label: 'Reportería',
    Icon: Icons.BarChart,
    roles: ['admin', 'supervisor', 'superadmin'],
  },
  {
    to: '/plan',
    label: 'Plan / Uso',
    Icon: Icons.Zap,
    roles: ['admin', 'superadmin'],
  },
]

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador',
  supervisor: 'Supervisor',
  agent: 'Agente',
  superadmin: '⚡ Superadmin',
}

export default function AppLayout() {
  const { agent, logout } = useAuth()
  const navigate = useNavigate()

  const role = agent?.role || 'agent'
  const visibleItems = NAV_ITEMS.filter((item) => item.roles.includes(role))

  const [pendingCount, setPendingCount] = useState(0)
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  useEffect(() => {
    const check = () => {
      conversationsApi
        .list('in_agent')
        .then((response) => setPendingCount(response.data?.length || 0))
        .catch(() => {})
    }

    check()

    const interval = window.setInterval(check, 10000)

    return () => window.clearInterval(interval)
  }, [])

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const closeMobileMenu = () => {
    setMobileMenuOpen(false)
  }

  const SidebarContent = () => (
    <>
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/10">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center font-display font-bold text-xs flex-shrink-0"
            style={{ background: '#C6A96B', color: '#0b4c45' }}
          >
            LLV
          </div>

          <div className="min-w-0">
            <div className="font-display font-bold text-white text-sm leading-tight truncate">
              LLV Assistant
            </div>
            <div className="text-[10px] text-white/40 truncate">
              Wellness Clinic
            </div>
          </div>
        </div>
      </div>

      {/* Rol */}
      <div className="px-4 py-2.5 border-b border-white/10">
        <span
          className="text-[10px] font-semibold tracking-wider uppercase px-2 py-1 rounded-md"
          style={{
            background:
              role === 'superadmin'
                ? 'rgba(167,139,250,0.2)'
                : 'rgba(198,169,107,0.15)',
            color: role === 'superadmin' ? '#c4b5fd' : '#C6A96B',
          }}
        >
          {ROLE_LABELS[role] || role}
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
        {visibleItems.map(({ to, label, Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            onClick={closeMobileMenu}
            className={({ isActive }) =>
              `flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 cursor-pointer ${
                isActive
                  ? 'text-[#0b4c45] shadow-sm'
                  : 'text-white/70 hover:text-white hover:bg-white/10'
              }`
            }
            style={({ isActive }) =>
              isActive ? { background: '#C6A96B' } : {}
            }
          >
            <Icon />
            <span className="flex-1 truncate">{label}</span>

            {badge && pendingCount > 0 && (
              <span
                className="flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold animate-pulse-dot"
                style={{ background: '#E24B4A', color: 'white' }}
              >
                {pendingCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Perfil */}
      <div className="px-3 py-4 border-t border-white/10">
        <div
          className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl"
          style={{ background: 'rgba(255,255,255,0.07)' }}
        >
          <div
            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
            style={{
              background: role === 'superadmin' ? '#c4b5fd' : '#C6A96B',
              color: '#0b4c45',
            }}
          >
            {agent?.name?.charAt(0) || 'A'}
          </div>

          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-white truncate">
              {agent?.name || 'Usuario'}
            </div>
            <div className="text-[10px] text-white/40 truncate">
              {ROLE_LABELS[role] || role}
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="text-white/40 hover:text-white transition-colors p-1 flex-shrink-0"
            title="Cerrar sesión"
          >
            <Icons.LogOut />
          </button>
        </div>
      </div>
    </>
  )

  return (
    <div
      className="min-h-screen overflow-hidden"
      style={{ background: '#f8f6f2' }}
    >
      {/* Header mobile */}
      <header
        className="lg:hidden fixed top-0 left-0 right-0 z-40 h-14 px-4 flex items-center justify-between border-b border-[#e5ddd4]"
        style={{ background: '#0b4c45' }}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center font-display font-bold text-xs flex-shrink-0"
            style={{ background: '#C6A96B', color: '#0b4c45' }}
          >
            LLV
          </div>

          <div className="min-w-0">
            <div className="font-display font-bold text-white text-sm leading-tight truncate">
              LLV Assistant
            </div>
            <div className="text-[10px] text-white/50 truncate">
              {ROLE_LABELS[role] || role}
            </div>
          </div>
        </div>

        <button
          onClick={() => setMobileMenuOpen(true)}
          className="w-10 h-10 rounded-xl flex items-center justify-center text-white bg-white/10 active:scale-95 transition-all"
          aria-label="Abrir menú"
        >
          ☰
        </button>
      </header>

      {/* Overlay mobile */}
      {mobileMenuOpen && (
        <button
          type="button"
          aria-label="Cerrar menú"
          onClick={closeMobileMenu}
          className="lg:hidden fixed inset-0 bg-black/40 z-40"
        />
      )}

      {/* Sidebar desktop */}
      <aside
        className="hidden lg:flex fixed top-0 left-0 bottom-0 w-56 flex-col z-30"
        style={{ background: '#0b4c45' }}
      >
        <SidebarContent />
      </aside>

      {/* Sidebar mobile */}
      <aside
        className={`lg:hidden fixed top-0 bottom-0 left-0 w-[82vw] max-w-[310px] flex flex-col z-50 transition-transform duration-200 ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ background: '#0b4c45' }}
      >
        <div className="flex items-center justify-between pr-3">
          <div className="flex-1">
            <SidebarContent />
          </div>

          <button
            onClick={closeMobileMenu}
            className="absolute top-3 right-3 w-9 h-9 rounded-xl flex items-center justify-center text-white bg-white/10"
            aria-label="Cerrar menú"
          >
            ✕
          </button>
        </div>
      </aside>

      {/* Contenido */}
      <main className="lg:ml-56 pt-14 lg:pt-0 h-screen overflow-y-auto overflow-x-hidden">
        <div className="w-full min-w-0">
          <Outlet />
        </div>
      </main>
    </div>
  )
}