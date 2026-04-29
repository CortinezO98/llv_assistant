import { useEffect, useState } from 'react'
import { patientsApi, planApi } from '../api/client'

// ── PATIENTS ──────────────────────────────────────────────────────────────────
export function PatientsPage() {
  const [patients, setPatients] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    patientsApi.list().then(r => setPatients(r.data)).finally(() => setLoading(false))
  }, [])

  const filtered = patients.filter(p =>
    !search || (p.full_name || '').toLowerCase().includes(search.toLowerCase()) ||
    p.whatsapp_number.includes(search)
  )

  const locationLabel: Record<string, string> = { puerto_rico: '🇵🇷 PR', latam: '🌎 LATAM', usa: '🇺🇸 USA' }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-brand-800">Pacientes</h1>
          <p className="text-sm text-[#6b8a78] mt-0.5">{patients.length} registrados en total</p>
        </div>
        <input className="input max-w-xs" placeholder="🔍 Buscar nombre o número..." value={search} onChange={e => setSearch(e.target.value)} />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#e4ede8] bg-brand-50/50">
              {['Paciente', 'WhatsApp', 'Ubicación', 'Tipo', 'Última interacción'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="text-center py-12 text-sm text-[#6b8a78]">Cargando...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-12 text-sm text-[#6b8a78]">Sin pacientes registrados</td></tr>
            ) : filtered.map((p) => (
              <tr key={p.id} className="table-row">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center text-brand-600 text-xs font-bold">
                      {(p.full_name || '?').charAt(0)}
                    </div>
                    <div className="text-sm font-semibold text-brand-800">{p.full_name || 'Sin nombre'}</div>
                  </div>
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[#6b8a78]">{p.whatsapp_number}</td>
                <td className="px-4 py-3 text-sm text-[#6b8a78]">{locationLabel[p.location_type] || p.location_type}</td>
                <td className="px-4 py-3">
                  <span className={`badge ${p.is_recurrent ? 'bg-brand-100 text-brand-700' : 'bg-gray-100 text-gray-600'}`}>
                    {p.is_recurrent ? '⭐ Recurrente' : 'Nuevo'}
                  </span>
                </td>
                <td className="px-4 py-3 text-xs text-[#6b8a78] font-mono">
                  {p.last_interaction_at ? new Date(p.last_interaction_at).toLocaleDateString('es') : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── CONVERSATIONS PLACEHOLDER ─────────────────────────────────────────────────
export function ConversationsPage() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="font-display text-2xl font-bold text-brand-800 mb-2">Conversaciones</h1>
      <p className="text-sm text-[#6b8a78] mb-6">Historial de conversaciones del bot</p>
      <div className="card p-12 text-center">
        <div className="text-4xl mb-3">💬</div>
        <p className="text-brand-700 font-semibold">Panel de conversaciones</p>
        <p className="text-sm text-[#6b8a78] mt-1">Próximamente — vista en tiempo real de todas las conversaciones activas</p>
      </div>
    </div>
  )
}

// ── PLAN USAGE ────────────────────────────────────────────────────────────────
export function PlanPage() {
  const [usage, setUsage] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    planApi.getUsage().then(r => setUsage(r.data)).finally(() => setLoading(false))
  }, [])

  const pct = usage?.percentage || 0
  const barColor = pct >= 100 ? 'bg-red-500' : pct >= 80 ? 'bg-amber-500' : 'bg-brand-500'

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="font-display text-2xl font-bold text-brand-800 mb-2">Plan y Uso</h1>
      <p className="text-sm text-[#6b8a78] mb-6">Control de consumo del Plan Profesional</p>

      {loading ? (
        <div className="text-center py-12 text-[#6b8a78]">Cargando...</div>
      ) : usage && (
        <div className="space-y-4">
          {/* Main card */}
          <div className="card p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Plan Profesional</div>
                <div className="font-display text-3xl font-bold text-brand-800 mt-1">
                  {usage.count} <span className="text-lg font-normal text-[#6b8a78]">/ {usage.limit}</span>
                </div>
                <div className="text-sm text-[#6b8a78]">conversaciones este mes</div>
              </div>
              <div className={`font-display text-3xl font-bold ${pct >= 80 ? 'text-amber-600' : 'text-brand-600'}`}>{pct}%</div>
            </div>
            <div className="h-3 bg-brand-100 rounded-full overflow-hidden">
              <div className={`h-full ${barColor} rounded-full transition-all duration-700`} style={{ width: `${Math.min(pct, 100)}%` }} />
            </div>
            <div className="flex justify-between text-xs text-[#6b8a78] mt-2">
              <span>0</span>
              <span className="text-amber-600 font-semibold">⚠️ 80% = {Math.round(usage.limit * 0.8)}</span>
              <span>{usage.limit}</span>
            </div>
          </div>

          {/* Alerts status */}
          <div className="card p-5">
            <h3 className="font-semibold text-brand-800 mb-3">Estado de alertas</h3>
            <div className="space-y-2.5">
              <div className="flex items-center justify-between py-2 border-b border-[#e4ede8]">
                <span className="text-sm text-[#6b8a78]">Alerta al 80% ({Math.round(usage.limit * 0.8)} conv.)</span>
                <span className={`badge ${usage.alert_80_sent ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-500'}`}>
                  {usage.alert_80_sent ? '✓ Enviada' : 'Pendiente'}
                </span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-[#6b8a78]">Alerta al 100% ({usage.limit} conv.)</span>
                <span className={`badge ${usage.alert_100_sent ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'}`}>
                  {usage.alert_100_sent ? '⚠️ Enviada' : 'Pendiente'}
                </span>
              </div>
            </div>
          </div>

          {/* Plan details */}
          <div className="card p-5">
            <h3 className="font-semibold text-brand-800 mb-3">Detalles del plan</h3>
            <div className="space-y-2 text-sm">
              {[
                ['Plan', 'Profesional'],
                ['Conversaciones incluidas', `${usage.limit} / mes`],
                ['Período actual', usage.period],
                ['Precio mensual', 'COP $450.000'],
                ['Motor IA', 'Google Gemini 2.0 Flash'],
                ['Canal', 'WhatsApp Business API (Meta)'],
                ['SLA soporte', '12 horas hábiles'],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between py-1.5 border-b border-[#e4ede8] last:border-0">
                  <span className="text-[#6b8a78]">{k}</span>
                  <span className="font-semibold text-brand-800">{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
