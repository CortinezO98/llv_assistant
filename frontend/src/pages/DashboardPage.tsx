import { useEffect, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart, Bar, Cell } from 'recharts'
import Icons from '../components/Icons'
import { dashboardApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

// ── Tipos ─────────────────────────────────────────────────────────────────────
interface KpiData {
  role: string
  conversations: {
    total: number; unique_users: number; completed: number
    pct_completed: number; status_distribution: Record<string, number>
  }
  agents:       { escalated: number; pct_escalated: number }
  appointments: { total_requested: number; confirmed: number; conversion_pct: number }
  sales:        { verified_payments: number; total_revenue_usd: number }
  events:       { conversation_started: number; faq_resolved: number; agent_handoffs: number; satisfaction_received: number }
  satisfaction: { avg_score: number | null; responses: number }
  plan_usage:   { count: number; limit: number; percentage: number }
  flow_metrics: {
    lead_temperature: { caliente: number; templado: number; frio: number; total: number }
    abandonment_by_step: Record<string, number>
    completion: { total_iniciaron: number; llegaron_preguntas: number; llegaron_handoff: number; pct_preguntas: number; pct_handoff: number }
  } | null
  ganancias: {
    ingreso_cop: number; costo_cop: number; ganancia_neta: number
    margen_pct: number; costo_por_conv: number
  } | null
}

const STATUS_LABELS: Record<string, string> = {
  active: 'Activas', in_agent: 'Con agente', completed: 'Completadas', closed: 'Cerradas'
}
const STATUS_COLORS: Record<string, string> = {
  active: '#0b4c45', in_agent: '#3b82f6', completed: '#1D9E75', closed: '#7a6a55'
}

// ── Componentes base ──────────────────────────────────────────────────────────
function KpiCard({ Icon, label, value, sub, accent = false, highlight }: {
  Icon: React.FC; label: string; value: string | number; sub?: string
  accent?: boolean; highlight?: string
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
        <div className="font-display text-3xl font-bold" style={{ color: highlight || '#0b4c45' }}>{value}</div>
        {sub && <div className="text-xs text-[#7a6a55] mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="font-display text-sm font-bold text-[#0b4c45] uppercase tracking-wider mb-3 flex items-center gap-2">
      {children}
    </h2>
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
            <span className="text-lg text-[#7a6a55]">/ {limit.toLocaleString('es-CO')} conversaciones</span>
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
        <span style={{ color: '#EF9F27' }}>⚠ 80% = {Math.round(limit * 0.8).toLocaleString('es-CO')}</span>
        <span>{limit.toLocaleString('es-CO')}</span>
      </div>
      {pct >= 80 && (
        <div className="mt-3 text-xs px-3 py-2 rounded-lg border"
          style={{ background: '#FAEEDA', borderColor: '#EF9F27', color: '#633806' }}>
          {pct >= 100
            ? '🚨 Límite alcanzado — contacta al proveedor para agregar conversaciones.'
            : `⚠️ Al ${pct}% del límite mensual.`}
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

// ── Panel de temperatura de leads ─────────────────────────────────────────────
function LeadTemperaturePanel({ data }: {
  data: { caliente: number; templado: number; frio: number; total: number }
}) {
  const total = data.total || 1
  const items = [
    { key: 'caliente', emoji: '🔥', label: 'Caliente',  color: '#E24B4A', bg: '#FEF2F2', value: data.caliente },
    { key: 'templado', emoji: '🌤️', label: 'Templado',  color: '#EF9F27', bg: '#FFFBEB', value: data.templado },
    { key: 'frio',     emoji: '❄️', label: 'Frío',      color: '#3b82f6', bg: '#EFF6FF', value: data.frio },
  ]
  return (
    <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5">
      <SectionTitle>🌡️ Temperatura de leads</SectionTitle>
      <div className="space-y-3">
        {items.map(item => {
          const pct = Math.round((item.value / total) * 100)
          return (
            <div key={item.key}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-base">{item.emoji}</span>
                  <span className="text-sm font-semibold text-[#1a1208]">{item.label}</span>
                </div>
                <div className="text-right">
                  <span className="font-bold text-sm" style={{ color: item.color }}>{item.value}</span>
                  <span className="text-xs text-[#7a6a55] ml-1">({pct}%)</span>
                </div>
              </div>
              <div className="h-2 rounded-full" style={{ background: item.bg }}>
                <div className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${pct}%`, background: item.color }} />
              </div>
            </div>
          )
        })}
        <div className="pt-2 border-t border-[#e5ddd4] text-xs text-[#7a6a55]">
          Total con temperatura registrada: <strong>{data.total}</strong>
        </div>
      </div>
    </div>
  )
}

// ── Embudo del flujo ──────────────────────────────────────────────────────────
function FlowFunnelPanel({ completion }: {
  completion: { total_iniciaron: number; llegaron_preguntas: number; llegaron_handoff: number; pct_preguntas: number; pct_handoff: number }
}) {
  const steps = [
    { label: 'Iniciaron conversación', value: completion.total_iniciaron, pct: 100, color: '#0b4c45' },
    { label: 'Completaron preguntas', value: completion.llegaron_preguntas, pct: completion.pct_preguntas, color: '#1D9E75' },
    { label: 'Llegaron al handoff', value: completion.llegaron_handoff, pct: completion.pct_handoff, color: '#C6A96B' },
  ]
  return (
    <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5">
      <SectionTitle>📊 Embudo del flujo</SectionTitle>
      <div className="space-y-3">
        {steps.map((step, i) => (
          <div key={i}>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs text-[#7a6a55]">{step.label}</span>
              <div className="text-right">
                <span className="font-bold text-sm" style={{ color: step.color }}>{step.value.toLocaleString('es-CO')}</span>
                <span className="text-xs text-[#7a6a55] ml-1">({step.pct}%)</span>
              </div>
            </div>
            <div className="h-2.5 rounded-full" style={{ background: '#F5F1EB' }}>
              <div className="h-full rounded-full transition-all duration-700"
                style={{ width: `${step.pct}%`, background: step.color }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Abandono por paso ─────────────────────────────────────────────────────────
function AbandonmentPanel({ data }: { data: Record<string, number> }) {
  const entries = Object.entries(data).sort((a, b) => b[1] - a[1]).slice(0, 7)
  const max = Math.max(...entries.map(e => e[1]), 1)

  const STEP_COLORS: Record<string, string> = {
    '1. Menú inicial':        '#6b8a78',
    '2. Filtro nuevo/recompra': '#3b82f6',
    '3A. Preguntas cliente nuevo': '#8b5cf6',
    '3B. Preguntas recompra': '#ec4899',
    '4. Intención de entrega': '#EF9F27',
    '5. Captura de datos':    '#f97316',
    '6. Confirmación':        '#1D9E75',
    '7. Handoff completado':  '#0b4c45',
  }

  return (
    <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5">
      <SectionTitle>📍 Dónde están los clientes en el flujo</SectionTitle>
      {entries.length === 0 ? (
        <p className="text-sm text-[#7a6a55] text-center py-4">Sin datos aún</p>
      ) : (
        <div className="space-y-2.5">
          {entries.map(([step, count]) => {
            const pct = Math.round((count / max) * 100)
            const color = STEP_COLORS[step] || '#7a6a55'
            return (
              <div key={step} className="flex items-center gap-2">
                <span className="text-xs text-[#7a6a55] w-44 flex-shrink-0 truncate" title={step}>{step}</span>
                <div className="flex-1 h-2 rounded-full" style={{ background: '#F5F1EB' }}>
                  <div className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${pct}%`, background: color }} />
                </div>
                <span className="text-xs font-bold text-[#0b4c45] w-6 text-right">{count}</span>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Panel ganancias superadmin ────────────────────────────────────────────────
function GananciasPanel({ data }: {
  data: { ingreso_cop: number; costo_cop: number; ganancia_neta: number; margen_pct: number; costo_por_conv: number }
}) {
  const fmt = (n: number) => '$' + n.toLocaleString('es-CO') + ' COP'
  return (
    <div className="rounded-2xl border-2 border-purple-200 bg-purple-50 p-5">
      <SectionTitle>⚡ Rentabilidad real — Superadmin</SectionTitle>
      <div className="grid grid-cols-2 gap-3">
        {[
          { label: 'Ingreso bruto', value: fmt(data.ingreso_cop), color: '#0b4c45' },
          { label: 'Costo real', value: fmt(data.costo_cop), color: '#E24B4A' },
          { label: 'Ganancia neta', value: fmt(data.ganancia_neta), color: '#1D9E75', big: true },
          { label: 'Margen', value: `${data.margen_pct}%`, color: '#1D9E75', big: true },
          { label: 'Costo/conversación', value: fmt(data.costo_por_conv), color: '#7a6a55' },
        ].map(item => (
          <div key={item.label} className={`bg-white rounded-xl border border-purple-200 px-4 py-3 ${item.big ? 'col-span-1' : ''}`}>
            <div className="text-xs text-[#7a6a55] mb-0.5">{item.label}</div>
            <div className={`font-bold ${item.big ? 'text-xl' : 'text-sm'}`} style={{ color: item.color }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Dashboard principal ───────────────────────────────────────────────────────
export default function DashboardPage() {
  const { agent }       = useAuth()
  const [kpis, setKpis]         = useState<KpiData | null>(null)
  const [timeline, setTimeline] = useState<any[]>([])
  const [activity, setActivity] = useState<any[]>([])
  const [loading, setLoading]   = useState(true)
  const [days, setDays]         = useState(30)

  const role       = agent?.role || 'agent'
  const isSuperAdmin = role === 'superadmin'
  const isAgent    = role === 'agent'

  useEffect(() => {
    setLoading(true)
    Promise.all([
      dashboardApi.getKpis(days),
      dashboardApi.getRecentActivity(8),
      dashboardApi.getTimeline(days),
    ]).then(([k, a, t]) => {
      setKpis(k.data)
      setActivity(a.data)
      setTimeline(Array.isArray(t.data) ? t.data.slice(-14) : [])
    }).finally(() => setLoading(false))
  }, [days])

  const now      = new Date()
  const hour     = now.getHours()
  const greeting = hour < 12 ? 'Buenos días' : hour < 18 ? 'Buenas tardes' : 'Buenas noches'
  const statusDist = kpis?.conversations.status_distribution || {}

  // KPI cards según rol
  const KPI_CARDS = [
    { Icon: Icons.Chat,          label: 'Conversaciones',     value: kpis?.conversations.total ?? 0,             sub: `${kpis?.conversations.unique_users ?? 0} usuarios únicos`, accent: true },
    { Icon: Icons.TrendingUp,    label: 'Completadas',        value: `${kpis?.conversations.pct_completed ?? 0}%`, sub: `${kpis?.conversations.completed ?? 0} sesiones` },
    { Icon: Icons.Headphones,    label: 'Escaladas a agente', value: kpis?.agents.escalated ?? 0,                sub: `${kpis?.agents.pct_escalated ?? 0}% del total` },
    { Icon: Icons.CalendarCheck, label: 'Citas confirmadas',  value: kpis?.appointments.confirmed ?? 0,           sub: `${kpis?.appointments.conversion_pct ?? 0}% conversión` },
    ...(!isAgent ? [
      { Icon: Icons.CreditCard,  label: 'Pagos verificados',  value: kpis?.sales.verified_payments ?? 0,         sub: 'pagos confirmados' },
      { Icon: Icons.DollarSign,  label: 'Ingresos canal',     value: `$${(kpis?.sales.total_revenue_usd ?? 0).toFixed(2)}`, sub: 'USD verificados' },
    ] : []),
    { Icon: Icons.Book,          label: 'FAQ resueltas',      value: kpis?.events?.faq_resolved ?? 0,            sub: 'sin escalar a agente' },
    { Icon: Icons.Star,          label: 'Satisfacción prom.', value: kpis?.satisfaction.avg_score != null ? `${kpis.satisfaction.avg_score} ⭐` : '—', sub: `${kpis?.satisfaction.responses ?? 0} respuestas` },
  ]

  return (
    <div className="page-mobile p-4 sm:p-6 max-w-7xl mx-auto w-full min-w-0">
      {/* Header */}
      <div className="flex items-start justify-between mb-7">
        <div>
          <p className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-0.5">
            {now.toLocaleDateString('es', { weekday: 'long', day: 'numeric', month: 'long' })}
          </p>
          <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
            {greeting}, {agent?.name?.split(' ')[0]} 👋
          </h1>
          {isSuperAdmin && (
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700 mt-1 inline-block">
              ⚡ Vista Superadmin
            </span>
          )}
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
        <div className="space-y-6">

          {/* ── KPI Grid ────────────────────────────────────────────────── */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {KPI_CARDS.map(card => (
              <KpiCard key={card.label} {...card} />
            ))}
          </div>

          {/* ── Plan + Distribución ─────────────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <HeroMetric
              count={kpis.plan_usage.count}
              limit={kpis.plan_usage.limit}
              pct={kpis.plan_usage.percentage}
            />
            <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5 lg:col-span-2">
              <SectionTitle>Distribución de estados</SectionTitle>
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

          {/* ── Métricas del flujo (no para agentes) ────────────────────── */}
          {kpis.flow_metrics && (
            <>
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <LeadTemperaturePanel data={kpis.flow_metrics.lead_temperature} />
                <FlowFunnelPanel      completion={kpis.flow_metrics.completion} />
                <AbandonmentPanel     data={kpis.flow_metrics.abandonment_by_step} />
              </div>
            </>
          )}

          {/* ── Ganancias (solo superadmin) ──────────────────────────────── */}
          {kpis.ganancias && (
            <GananciasPanel data={kpis.ganancias} />
          )}

          {/* ── Gráfica + Actividad reciente ─────────────────────────────── */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5 lg:col-span-2">
              <SectionTitle>Tendencia — últimos {days} días</SectionTitle>
              {timeline.length > 1 ? (
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={timeline} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                    <defs>
                      <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#0b4c45" stopOpacity={0.15}/>
                        <stop offset="95%" stopColor="#0b4c45" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="grad2" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#C6A96B" stopOpacity={0.15}/>
                        <stop offset="95%" stopColor="#C6A96B" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#7a6a55' }} tickLine={false} axisLine={false} />
                    <YAxis tick={{ fontSize: 10, fill: '#7a6a55' }} tickLine={false} axisLine={false} />
                    <Tooltip content={<CustomTooltip />} />
                    <Area type="monotone" dataKey="conversation_started" name="Conv."     stroke="#0b4c45" strokeWidth={2} fill="url(#grad1)" dot={false} />
                    <Area type="monotone" dataKey="agent_handoff"        name="Escaladas" stroke="#C6A96B" strokeWidth={2} fill="url(#grad2)" dot={false} />
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

            <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5">
              <SectionTitle>Actividad reciente</SectionTitle>
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
