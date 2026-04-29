import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import Icons from '../components/Icons'
import { useAuth } from '../context/AuthContext'
import { LOGO_MONO_WHITE } from '../assets/logos'

const NAV_ITEMS = [
  { to: '/',              label: 'Dashboard',       Icon: Icons.Dashboard, roles: ['admin', 'supervisor'] },
  { to: '/conversations', label: 'Conversaciones',  Icon: Icons.Chat,   roles: ['admin', 'supervisor', 'agent'] },
  { to: '/appointments',  label: 'Citas',           Icon: Icons.Calendar,    roles: ['admin', 'supervisor', 'agent'] },
  { to: '/deliveries',    label: 'Entregas/Envíos', Icon: Icons.Package,         roles: ['admin', 'supervisor', 'agent'] },
  { to: '/patients',      label: 'Pacientes',       Icon: Icons.Users,           roles: ['admin', 'supervisor', 'agent'] },
  { to: '/agents',        label: 'Agentes',         Icon: Icons.Headphones,      roles: ['admin', 'supervisor'] },
  { to: '/faq',           label: 'Base FAQ',        Icon: Icons.Book,        roles: ['admin', 'supervisor'] },
  { to: '/reports',       label: 'Reportería',      Icon: Icons.BarChart,       roles: ['admin', 'supervisor'] },
  { to: '/plan',          label: 'Plan / Uso',      Icon: Icons.Zap,             roles: ['admin'] },
]

const ROLE_LABELS: Record<string, string> = {
  admin: 'Administrador', supervisor: 'Supervisor', agent: 'Agente',
}

export default function AppLayout() {
  const { agent, logout } = useAuth()
  const navigate = useNavigate()
  const role = agent?.role || 'agent'
  const visibleItems = NAV_ITEMS.filter(item => item.roles.includes(role))

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#f8f6f2' }}>
      {/* ── Sidebar ────────────────────────────────────────────────────────── */}
      <aside className="w-56 flex-shrink-0 flex flex-col" style={{ background: '#0b4c45' }}>

        {/* Logo */}
        <div className="px-5 py-5 border-b border-white/10">
          <div className="flex items-center gap-3">
            <img
              src={LOGO_MONO_WHITE}
              alt="LLV"
              className="h-7 object-contain"
              style={{ filter: 'brightness(0) invert(1) drop-shadow(0 1px 4px rgba(198,169,107,0.4))' }}
            />
            <div>
              <div className="font-display font-bold text-white text-sm leading-tight">LLV Assistant</div>
              <div className="text-[10px] text-white/40">Wellness Clinic</div>
            </div>
          </div>
        </div>

        {/* Rol */}
        <div className="px-4 py-2.5 border-b border-white/10">
          <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-1 rounded-md"
            style={{ background: 'rgba(198,169,107,0.15)', color: '#C6A96B' }}>
            {ROLE_LABELS[role] || role}
          </span>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          {visibleItems.map(({ to, label, Icon }) => (
            <NavLink key={to} to={to} end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 cursor-pointer ${
                  isActive
                    ? 'text-[#0b4c45] shadow-sm'
                    : 'text-white/60 hover:text-white hover:bg-white/10'
                }`
              }
              style={({ isActive }) => isActive ? { background: '#C6A96B' } : {}}
            >
              <Icon size={16} strokeWidth={1.75} className="flex-shrink-0" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Perfil del agente */}
        <div className="px-3 py-4 border-t border-white/10">
          <div className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl" style={{ background: 'rgba(255,255,255,0.07)' }}>
            <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
              style={{ background: '#C6A96B', color: '#0b4c45' }}>
              {agent?.name?.charAt(0) || 'A'}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-xs font-semibold text-white truncate">{agent?.name}</div>
              <div className="text-[10px] text-white/40">{ROLE_LABELS[role]}</div>
            </div>
            <button onClick={() => { logout(); navigate('/login') }}
              className="text-white/40 hover:text-white transition-colors p-1 flex-shrink-0" title="Cerrar sesión">
              <Icons.LogOut />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Contenido principal ─────────────────────────────────────────────── */}
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  )
}
