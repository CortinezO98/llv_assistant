import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import Icons from './Icons'
import { useAuth } from '../context/AuthContext'
import { conversationsApi } from '../api/client'

const NAV_ITEMS = [
  { to: '/',              label: 'Dashboard',       Icon: Icons.Dashboard,    roles: ['admin', 'supervisor', 'superadmin'] },
  { to: '/conversations', label: 'Conversaciones',  Icon: Icons.Chat,         roles: ['admin', 'supervisor', 'agent', 'superadmin'], badge: true },
  { to: '/appointments',  label: 'Citas',           Icon: Icons.Calendar,     roles: ['admin', 'supervisor', 'agent', 'superadmin'] },
  { to: '/deliveries',    label: 'Entregas/Envíos', Icon: Icons.Package,      roles: ['admin', 'supervisor', 'agent', 'superadmin'] },
  { to: '/patients',      label: 'Pacientes',       Icon: Icons.Users,        roles: ['admin', 'supervisor', 'agent', 'superadmin'] },
  { to: '/agents',        label: 'Agentes',         Icon: Icons.Headphones,   roles: ['admin', 'supervisor', 'superadmin'] },
  { to: '/faq',           label: 'Base FAQ',        Icon: Icons.Book,         roles: ['admin', 'supervisor', 'superadmin'] },
  { to: '/reports',       label: 'Reportería',      Icon: Icons.BarChart,     roles: ['admin', 'supervisor', 'superadmin'] },
  { to: '/plan',          label: 'Plan / Uso',      Icon: Icons.Zap,          roles: ['admin', 'superadmin'] },
]

const ROLE_LABELS: Record<string, string> = {
  admin:      'Administrador',
  supervisor: 'Supervisor',
  agent:      'Agente',
  superadmin: '⚡ Superadmin',
}

export default function AppLayout() {
  const { agent, logout } = useAuth()
  const navigate = useNavigate()
  const role = agent?.role || 'agent'
  const visibleItems = NAV_ITEMS.filter(item => item.roles.includes(role))

  const [pendingCount, setPendingCount] = useState(0)

  useEffect(() => {
    const check = () => {
      conversationsApi.list('in_agent')
        .then(r => setPendingCount(r.data?.length || 0))
        .catch(() => {})
    }
    check()
    const interval = setInterval(check, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#f8f6f2' }}>
      <aside className="w-56 flex-shrink-0 flex flex-col" style={{ background: '#0b4c45' }}>

        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/10">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-display font-bold text-xs flex-shrink-0"
              style={{ background: '#C6A96B', color: '#0b4c45' }}>
              LLV
            </div>
            <div>
              <div className="font-display font-bold text-white text-sm leading-tight">LLV Assistant</div>
              <div className="text-[10px] text-white/40">Wellness Clinic</div>
            </div>
          </div>
        </div>

        {/* Rol */}
        <div className="px-4 py-2.5 border-b border-white/10">
          <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-1 rounded-md"
            style={{
              background: role === 'superadmin' ? 'rgba(167,139,250,0.2)' : 'rgba(198,169,107,0.15)',
              color: role === 'superadmin' ? '#c4b5fd' : '#C6A96B',
            }}>
            {ROLE_LABELS[role] || role}
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {visibleItems.map(({ to, label, Icon, badge }) => (
            <NavLink key={to} to={to} end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 cursor-pointer ${
                  isActive ? 'text-[#0b4c45] shadow-sm' : 'text-white/60 hover:text-white hover:bg-white/10'
                }`
              }
              style={({ isActive }) => isActive ? { background: '#C6A96B' } : {}}>
              <Icon />
              <span className="flex-1">{label}</span>
              {badge && pendingCount > 0 && (
                <span className="flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-bold animate-pulse-dot"
                  style={{ background: '#E24B4A', color: 'white' }}>
                  {pendingCount}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Perfil */}
        <div className="px-3 py-4 border-t border-white/10">
          <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl" style={{ background: 'rgba(255,255,255,0.07)' }}>
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
              style={{
                background: role === 'superadmin' ? '#c4b5fd' : '#C6A96B',
                color: '#0b4c45',
              }}>
              {agent?.name?.charAt(0) || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-white truncate">{agent?.name}</div>
              <div className="text-[10px] text-white/40">{ROLE_LABELS[role]}</div>
            </div>
            <button onClick={() => { logout(); navigate('/login') }}
              className="text-white/40 hover:text-white transition-colors p-1 flex-shrink-0">
              <Icons.LogOut />
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
