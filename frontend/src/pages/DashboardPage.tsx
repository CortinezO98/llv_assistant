import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
import Icons from '../components/Icons'
import { dashboardApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

interface KpiData {
  conversations: { total: number; unique_users: number; completed: number; pct_completed: number; status_distribution: Record<string, number> }
  agents: { escalated: number; pct_escalated: number }
  appointments: { total_requested: number; confirmed: number; conversion_pct: number }
  sales: { verified_payments: number; total_revenue_usd: number }
  events: { conversation_started: number; faq_resolved: number; agent_handoffs: number }
  plan_usage: { count: number; limit: number; percentage: number }
  period_days: number
}

const STATUS_LABELS: Record<string, string> = {
  active: 'Activas', in_agent: 'Con agente', completed: 'Completadas', closed: 'Cerradas'
}
const STATUS_COLORS: Record<string, string> = {
  active: '#0b4c45', in_agent: '#3b82f6', completed: '#1D9E75', closed: '#7a6a55'
}

function KpiCard({ Icon, label, value, sub, accent = false }: {
  Icon: React.FC; label: string; value: string | number; sub?: string; accent?: boolean
}) {
  return (
    <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5 flex flex-col gap-3 hover:shadow-md transition-shadow duration-200">
      <div className="flex items-start justify-between">
        <span className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider">{label}</span>
        <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
          style={{ background: accent ? '#C6A96B' : '#0b4c4515', color: '#0b4c45' }}>
          <Icon />
        </div>
      </div>
      <div>
        <div className="font-display text-3xl font-bold" style={{ color: '#0b4c45' }}>{value}</div>
        {sub && <div className="text-xs text-[#7a6a55] mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

function HeroMetric({ count, limit, pct }: { count: number; limit: number; pct: number }) {
  const barColor = pct >= 100 ? '#E24B4A' : pct >= 80 ? '#EF9F27' : '#1D9E75'
  return (
    <div className="bg-white rounded-2xl border border-[#e5ddd4] p-6 col-span-2">
      <div className="flex items-end justify-between mb-4">
        <div>
          <p className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-1">Plan mensual</p>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-4xl font-bold" style={{ color: '#0b4c45' }}>{count}</span>
            <span className="text-lg text-[#7a6a55]">/ {limit} conversaciones</span>
          </div>
        </div>
        <div className="font-display text-3xl font-bold" style={{ color: barColor }}>{pct}%</div>
      </div>
      <div className="h-2 rounded-full overflow-hidden" style={{ background: '#F5F1EB' }}>
        <div className="h-full rounded-full transition-all duration-700"
          style={{ width: `${Math.min(pct, 100)}%`, background: barColor }} />
      </div>
      <div className="flex justify-between text-[10px] text-[#7a6a55] mt-1.5">
        <span>0</span>
        <span style={{ color: '#EF9F27' }}>⚠ 80% = {Math.round(limit * 0.8)}</span>
        <span>{limit}</span>
      </div>
      {pct >= 80 && (
        <div className="mt-3 text-xs px-3 py-2 rounded-lg border"
          style={{ background: '#FAEEDA', borderColor: '#EF9F27', color: '#633806' }}>
          {pct >= 100
            ? '🚨 Límite alcanzado — contacta a tu proveedor para adquirir conversaciones adicionales.'
            : `⚠️ Estás al ${pct}% del límite mensual del plan Profesional.`}
        </div>
      )}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-[#e5ddd4] rounded-xl px-3 py-2 shadow-sm text-xs">
      <p className="font-semibold text-[#0b4c45] mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }}>{p.name}: {p.value}</p>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const { agent } = useAuth()
  const [kpis, setKpis]         = useState<KpiData | null>(null)
  const [timeline, setTimeline] = useState<any[]>([])
  const [activity, setActivity] = useState<any[]>([])
  const [loading, setLoading]   = useState(true)
  const [days, setDays]         = useState(30)

  useEffect(() => {
    setLoading(true)
    const token = localStorage.getItem('llv_token')
    const headers = { Authorization: `Bearer ${token}` }
    Promise.all([
      dashboardApi.getKpis(days),
      dashboardApi.getRecentActivity(8),
      fetch(`http://localhost:8001/dashboard/analytics/timeline?days=${days}`, { headers })
        .then(r => r.json()).catch(() => []),
    ]).then(([k, a, t]) => {
      setKpis(k.data)
      setActivity(a.data)
      setTimeline(Array.isArray(t) ? t.slice(-14) : [])
    }).finally(() => setLoading(false))
  }, [days])

  const now  = new Date()
  const hour = now.getHours()
  const greeting = hour < 12 ? 'Buenos días' : hour < 18 ? 'Buenas tardes' : 'Buenas noches'
  const statusDist = kpis?.conversations.status_distribution || {}

  const KPI_CARDS = [
    { Icon: Icons.Chat,          label: 'Conversaciones',      value: kpis?.conversations.total ?? 0,                    sub: `${kpis?.conversations.unique_users ?? 0} usuarios únicos`, accent: true },
    { Icon: Icons.TrendingUp,    label: 'Completadas',         value: `${kpis?.conversations.pct_completed ?? 0}%`,       sub: `${kpis?.conversations.completed ?? 0} sesiones` },
    { Icon: Icons.Headphones,    label: 'Escaladas a agente',  value: kpis?.agents.escalated ?? 0,                       sub: `${kpis?.agents.pct_escalated ?? 0}% del total` },
    { Icon: Icons.CalendarCheck, label: 'Citas confirmadas',   value: kpis?.appointments.confirmed ?? 0,                  sub: `${kpis?.appointments.conversion_pct ?? 0}% conversión` },
    { Icon: Icons.CreditCard,    label: 'Pagos verificados',   value: kpis?.sales.verified_payments ?? 0,                 sub: 'pagos confirmados' },
    { Icon: Icons.DollarSign,    label: 'Ingresos canal',      value: `$${(kpis?.sales.total_revenue_usd ?? 0).toFixed(2)}`, sub: 'USD verificados' },
    { Icon: Icons.Book,          label: 'FAQ resueltas',       value: kpis?.events?.faq_resolved ?? 0,                   sub: 'sin escalar a agente' },
    { Icon: Icons.Star,          label: 'Satisfacción',        value: '—',                                               sub: 'Encuesta pendiente' },
  ]

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-start justify-between mb-7">
        <div>
          <p className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-0.5">
            {now.toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
          <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
            {greeting}, {agent?.name?.split(' ')[0]} 👋
          </h1>
        </div>
        <div className="flex gap-1.5">
          {[7, 30, 90].map(d => (
            <button key={d} onClick={() => setDays(d)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={days === d
                ? { background: '#0b4c45', color: 'white' }
                : { background: 'white', border: '1px solid #e5ddd4', color: '#7a6a55' }}>
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <svg className="animate-spin w-8 h-8" style={{ color: '#0b4c45' }} viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".2"/>
            <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
          </svg>
        </div>
      ) : kpis ? (
        <div className="space-y-5">
          {/* KPI grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 stagger">
            {KPI_CARDS.map(card => (
              <KpiCard key={card.label} {...card} />
            ))}
          </div>

          {/* Plan + Distribución */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <HeroMetric
              count={kpis.plan_usage.count}
              limit={kpis.plan_usage.limit}
              pct={kpis.plan_usage.percentage}
            />
            <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5 lg:col-span-2">
              <p className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-4">Distribución de estados</p>
              <div className="space-y-3">
                {Object.keys(statusDist).length === 0 ? (
                  <p className="text-sm text-[#7a6a55] text-center py-4">Sin conversaciones aún</p>
                ) : Object.entries(statusDist).map(([status, count]) => {
                  const total = kpis.conversations.total || 1
                  const pct   = Math.round((count / total) * 100)
                  return (
                    <div key={status} className="flex items-center gap-3">
                      <span className="text-xs text-[#7a6a55] w-24 flex-shrink-0">{STATUS_LABELS[status] || status}</span>
                      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: '#F5F1EB' }}>
                        <div className="h-full rounded-full transition-all duration-500"
                          style={{ width: `${pct}%`, background: STATUS_COLORS[status] || '#7a6a55' }} />
                      </div>
                      <span className="text-xs font-semibold text-[#0b4c45] w-6 text-right">{count}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Gráfica + Actividad reciente */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5 lg:col-span-2">
              <p className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-4">
                Tendencia — últimos {days} días
              </p>
              {timeline.length > 1 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={timeline} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <defs>
                      <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#0b4c45" stopOpacity={0.15}/>
                        <stop offset="95%" stopColor="#0b4c45" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="grad2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#C6A96B" stopOpacity={0.15}/>
                        <stop offset="95%" stopColor="#C6A96B" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#7a6a55' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: '#7a6a55' }} tickLine={false} axisLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area type="monotone" dataKey="conversation_started" name="Conv." stroke="#0b4c45" strokeWidth={2} fill="url(#grad1)" dot={false} />
                    <Area type="monotone" dataKey="agent_handoff" name="Escaladas" stroke="#C6A96B" strokeWidth={2} fill="url(#grad2)" dot={false} />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex flex-col items-center justify-center h-40 text-center">
                  <div className="mb-2 opacity-20"><Icons.TrendingUp /></div>
                  <p className="text-sm text-[#7a6a55]">Sin datos suficientes para la gráfica</p>
                  <p className="text-xs text-[#7a6a55]/60 mt-0.5">Aparecerá después de las primeras conversaciones</p>
                </div>
              )}
            </div>

            {/* Actividad reciente */}
            <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5">
              <p className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-4">Actividad reciente</p>
              <div className="space-y-2">
                {activity.length === 0 ? (
                  <p className="text-sm text-[#7a6a55] text-center py-4">Sin actividad</p>
                ) : activity.map((s: any) => (
                  <div key={s.session_id} className="flex items-center gap-2.5 py-2 border-b border-[#e5ddd4] last:border-0">
                    <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                      style={{ background: '#F5F1EB', color: '#0b4c45' }}>
                      {(s.patient_name || '?').charAt(0)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-semibold text-[#0b4c45] truncate">{s.patient_name || 'Desconocido'}</p>
                      <p className="text-[10px] text-[#7a6a55] font-mono">{s.whatsapp_number}</p>
                    </div>
                    <div className="w-2 h-2 rounded-full flex-shrink-0"
                      style={{ background: STATUS_COLORS[s.status] || '#7a6a55' }} />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-16 text-[#7a6a55]">Error cargando datos.</div>
      )}
    </div>
  )
}
