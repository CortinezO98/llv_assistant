import { useEffect, useState } from 'react'
import { dashboardApi, planApi } from '../api/client'

interface KpiData {
  conversations: { total: number; unique_users: number; completed: number; pct_completed: number; status_distribution: Record<string, number> }
  agents: { escalated: number; pct_escalated: number }
  appointments: { total_requested: number; confirmed: number; conversion_pct: number }
  sales: { verified_payments: number; total_revenue_usd: number }
  plan_usage: { count: number; limit: number; percentage: number }
  period_days: number
}

function StatCard({ label, value, sub, color = 'brand', icon }: { label: string; value: string | number; sub?: string; color?: string; icon: string }) {
  const colors: Record<string, string> = {
    brand: 'bg-brand-50 text-brand-600',
    blue:  'bg-blue-50 text-blue-600',
    amber: 'bg-amber-50 text-amber-600',
    rose:  'bg-rose-50 text-rose-600',
    violet:'bg-violet-50 text-violet-600',
    teal:  'bg-teal-50 text-teal-600',
  }
  return (
    <div className="stat-card animate-fade-in">
      <div className="flex items-start justify-between">
        <span className="text-xs font-semibold text-[#6b8a78] uppercase tracking-wider leading-tight">{label}</span>
        <span className={`text-lg p-1.5 rounded-lg ${colors[color] || colors.brand}`}>{icon}</span>
      </div>
      <div>
        <div className="font-display text-3xl font-bold text-brand-800">{value}</div>
        {sub && <div className="text-xs text-[#6b8a78] mt-0.5">{sub}</div>}
      </div>
    </div>
  )
}

function PlanUsageBar({ count, limit, pct }: { count: number; limit: number; pct: number }) {
  const color = pct >= 100 ? 'bg-red-500' : pct >= 80 ? 'bg-amber-500' : 'bg-brand-500'
  return (
    <div className="card p-5 animate-fade-in" style={{ animationDelay: '0.3s' }}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Uso del plan mensual</div>
          <div className="font-display text-2xl font-bold text-brand-800 mt-0.5">{count} <span className="text-sm font-normal text-[#6b8a78]">/ {limit} conversaciones</span></div>
        </div>
        <div className={`text-2xl font-display font-bold ${pct >= 80 ? 'text-amber-600' : 'text-brand-600'}`}>{pct}%</div>
      </div>
      <div className="h-2.5 bg-brand-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${Math.min(pct, 100)}%` }} />
      </div>
      {pct >= 80 && (
        <div className="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
          ⚠️ {pct >= 100 ? 'Límite alcanzado — contacta a tu proveedor para adquirir conversaciones adicionales.' : `Estás al ${pct}% del límite mensual.`}
        </div>
      )}
    </div>
  )
}

export default function DashboardPage() {
  const [kpis, setKpis] = useState<KpiData | null>(null)
  const [activity, setActivity] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      dashboardApi.getKpis(days),
      dashboardApi.getRecentActivity(10),
    ]).then(([kpiRes, actRes]) => {
      setKpis(kpiRes.data)
      setActivity(actRes.data)
    }).finally(() => setLoading(false))
  }, [days])

  const statusLabels: Record<string, string> = {
    active: 'Activa', in_agent: 'Con agente', completed: 'Completada', closed: 'Cerrada'
  }
  const statusColors: Record<string, string> = {
    active: 'bg-brand-100 text-brand-700',
    in_agent: 'bg-blue-100 text-blue-700',
    completed: 'bg-teal-100 text-teal-700',
    closed: 'bg-gray-100 text-gray-600',
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-brand-800">Dashboard</h1>
          <p className="text-sm text-[#6b8a78] mt-0.5">Resumen de operaciones LLV Assistant</p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${days === d ? 'bg-brand-600 text-white' : 'bg-white border border-[#e4ede8] text-[#6b8a78] hover:border-brand-400'}`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center gap-3">
            <svg className="animate-spin w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".2"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
            </svg>
            <span className="text-sm text-[#6b8a78]">Cargando métricas...</span>
          </div>
        </div>
      ) : kpis ? (
        <div className="space-y-6">
          {/* KPI Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 stagger">
            <StatCard icon="💬" label="Conversaciones" value={kpis.conversations.total} sub={`${kpis.conversations.unique_users} usuarios únicos`} color="brand" />
            <StatCard icon="✅" label="Completadas" value={`${kpis.conversations.pct_completed}%`} sub={`${kpis.conversations.completed} de ${kpis.conversations.total}`} color="teal" />
            <StatCard icon="🎧" label="Escaladas a agente" value={kpis.agents.escalated} sub={`${kpis.agents.pct_escalated}% del total`} color="blue" />
            <StatCard icon="📅" label="Citas confirmadas" value={kpis.appointments.confirmed} sub={`${kpis.appointments.conversion_pct}% conversión`} color="violet" />
            <StatCard icon="💰" label="Ventas verificadas" value={kpis.sales.verified_payments} sub="pagos confirmados" color="amber" />
            <StatCard icon="💵" label="Ingresos canal" value={`$${kpis.sales.total_revenue_usd.toFixed(2)}`} sub="USD verificados" color="brand" />
            <StatCard icon="📱" label="Canal WhatsApp" value="100%" sub="único canal activo" color="teal" />
            <StatCard icon="⭐" label="Satisfacción" value="—" sub="Encuesta pendiente" color="amber" />
          </div>

          {/* Plan usage */}
          <PlanUsageBar count={kpis.plan_usage.count} limit={kpis.plan_usage.limit} pct={kpis.plan_usage.percentage} />

          {/* Bottom grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Estado de conversaciones */}
            <div className="card p-5 animate-fade-in" style={{ animationDelay: '0.35s' }}>
              <h3 className="font-semibold text-brand-800 mb-4 flex items-center gap-2">
                <span>📊</span> Distribución de estados
              </h3>
              <div className="space-y-2.5">
                {Object.entries(kpis.conversations.status_distribution).map(([status, count]) => (
                  <div key={status} className="flex items-center justify-between">
                    <span className={`badge ${statusColors[status] || 'bg-gray-100 text-gray-600'}`}>
                      {statusLabels[status] || status}
                    </span>
                    <div className="flex items-center gap-3">
                      <div className="w-24 h-1.5 bg-brand-100 rounded-full overflow-hidden">
                        <div className="h-full bg-brand-500 rounded-full" style={{ width: `${kpis.conversations.total ? (count / kpis.conversations.total) * 100 : 0}%` }} />
                      </div>
                      <span className="text-sm font-semibold text-brand-800 w-6 text-right">{count}</span>
                    </div>
                  </div>
                ))}
                {Object.keys(kpis.conversations.status_distribution).length === 0 && (
                  <p className="text-sm text-[#6b8a78] text-center py-4">Sin conversaciones en este período</p>
                )}
              </div>
            </div>

            {/* Actividad reciente */}
            <div className="card p-5 animate-fade-in" style={{ animationDelay: '0.4s' }}>
              <h3 className="font-semibold text-brand-800 mb-4 flex items-center gap-2">
                <span>🕐</span> Actividad reciente
              </h3>
              <div className="space-y-2">
                {activity.length === 0 ? (
                  <p className="text-sm text-[#6b8a78] text-center py-4">Sin actividad reciente</p>
                ) : activity.slice(0, 6).map((s: any) => (
                  <div key={s.session_id} className="flex items-center justify-between py-2 border-b border-[#e4ede8] last:border-0">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-7 h-7 bg-brand-100 rounded-full flex items-center justify-center text-brand-600 text-xs font-bold flex-shrink-0">
                        {(s.patient_name || '?').charAt(0)}
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-semibold text-brand-800 truncate">{s.patient_name || 'Desconocido'}</div>
                        <div className="text-[10px] text-[#6b8a78] font-mono">{s.whatsapp_number}</div>
                      </div>
                    </div>
                    <span className={`badge text-[10px] ${statusColors[s.status] || 'bg-gray-100 text-gray-600'}`}>
                      {statusLabels[s.status] || s.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-16 text-[#6b8a78]">Error cargando datos. Verifica la conexión al backend.</div>
      )}
    </div>
  )
}
