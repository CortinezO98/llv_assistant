import { useEffect, useState } from 'react'
import { patientsApi, planApi } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/Toast'

// ── PATIENTS ──────────────────────────────────────────────────────────────────
export function PatientsPage() {
  const [patients, setPatients] = useState<any[]>([])
  const [loading, setLoading]   = useState(true)
  const [search, setSearch]     = useState('')

  useEffect(() => {
    patientsApi.list().then(r => setPatients(r.data)).finally(() => setLoading(false))
  }, [])

  const filtered = patients.filter(p =>
    !search ||
    (p.full_name || '').toLowerCase().includes(search.toLowerCase()) ||
    p.whatsapp_number.includes(search)
  )

  const locationLabel: Record<string, string> = {
    puerto_rico: '🇵🇷 PR',
    latam:       '🌎 LATAM',
    usa:         '🇺🇸 USA',
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-brand-800">Pacientes</h1>
          <p className="text-sm text-[#6b8a78] mt-0.5">{patients.length} registrados en total</p>
        </div>
        <input
          className="input max-w-xs"
          placeholder="🔍 Buscar nombre o número..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#e4ede8] bg-brand-50/50">
              {['Paciente', 'WhatsApp', 'Ubicación', 'Tipo', 'Última interacción'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="text-center py-12 text-sm text-[#6b8a78]">Cargando...</td></tr>
            ) : filtered.length === 0 ? (
              <tr><td colSpan={5} className="text-center py-12 text-sm text-[#6b8a78]">Sin pacientes registrados</td></tr>
            ) : filtered.map(p => (
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
        <p className="text-sm text-[#6b8a78] mt-1">
          Próximamente — vista en tiempo real de todas las conversaciones activas
        </p>
      </div>
    </div>
  )
}

// ── PLAN USAGE ────────────────────────────────────────────────────────────────
export function PlanPage() {
  const { agent }       = useAuth()
  const toast           = useToast()
  const isSuperAdmin    = agent?.role === 'superadmin'

  const [usage, setUsage]   = useState<any>(null)
  const [loading, setLoading] = useState(true)

  // ── Estados para acciones de superadmin ──────────────────────────────────
  const [showRenew, setShowRenew]       = useState(false)
  const [renewForm, setRenewForm]       = useState({ plan_limit: 1500, payment_reference: '', notes: '' })
  const [renewSaving, setRenewSaving]   = useState(false)

  const [showAddConvs, setShowAddConvs] = useState(false)
  const [addForm, setAddForm]           = useState({ extra_conversations: 500, payment_reference: '', notes: '' })
  const [addSaving, setAddSaving]       = useState(false)

  const [toggleSaving, setToggleSaving] = useState(false)

  const load = () => {
    setLoading(true)
    planApi.getUsage().then(r => setUsage(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleRenew = async () => {
    setRenewSaving(true)
    try {
      await planApi.renew({
        plan_limit:         renewForm.plan_limit,
        payment_reference:  renewForm.payment_reference || undefined,
        notes:              renewForm.notes || undefined,
      })
      toast.success('Plan renovado', `Plan mensual renovado por ${renewForm.plan_limit} conversaciones`)
      setShowRenew(false)
      load()
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'No se pudo renovar el plan')
    } finally {
      setRenewSaving(false)
    }
  }

  const handleAddConversations = async () => {
    if (addForm.extra_conversations <= 0) {
      toast.warning('Cantidad inválida', 'Debe ser mayor que 0')
      return
    }
    setAddSaving(true)
    try {
      await planApi.addConversations({
        extra_conversations: addForm.extra_conversations,
        payment_reference:   addForm.payment_reference || undefined,
        notes:               addForm.notes || undefined,
      })
      toast.success('Conversaciones agregadas', `+${addForm.extra_conversations} conversaciones adicionales`)
      setShowAddConvs(false)
      load()
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'No se pudo agregar conversaciones')
    } finally {
      setAddSaving(false)
    }
  }

  const handleToggleService = async () => {
    if (!usage) return
    const newState = !usage.service_active
    if (!confirm(`¿${newState ? 'Activar' : 'DESACTIVAR'} el servicio del bot?`)) return
    setToggleSaving(true)
    try {
      await planApi.toggleService({ service_active: newState })
      toast.success(
        newState ? 'Servicio activado' : 'Servicio desactivado',
        newState
          ? 'El bot volverá a responder mensajes.'
          : 'El bot dejará de responder mensajes.'
      )
      load()
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'No se pudo cambiar el estado')
    } finally {
      setToggleSaving(false)
    }
  }

  // ── Colores de la barra de progreso ──────────────────────────────────────
  const pct      = usage?.percentage || 0
  const barColor = pct >= 100 ? '#E24B4A' : pct >= 80 ? '#EF9F27' : '#1D9E75'

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <svg className="animate-spin w-8 h-8 text-[#0b4c45]" viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".2"/>
          <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
        </svg>
      </div>
    )
  }

  if (!usage) {
    return <div className="p-6 text-center text-[#7a6a55]">Error cargando datos del plan.</div>
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-brand-800">Plan y Uso</h1>
          <p className="text-sm text-[#6b8a78] mt-0.5">
            Control de consumo · Período: {usage.period}
            {isSuperAdmin && (
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
                ⚡ Superadmin
              </span>
            )}
          </p>
        </div>

        {/* Indicador de estado del servicio */}
        <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
          usage.service_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
        }`}>
          <span className={`w-2 h-2 rounded-full ${usage.service_active ? 'bg-green-500' : 'bg-red-500'}`} />
          {usage.service_active ? 'Bot activo' : 'Bot inactivo'}
        </div>
      </div>

      <div className="space-y-4">

        {/* ── Barra de consumo principal ────────────────────────────────── */}
        <div className="card p-6">
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Plan Profesional</div>
              <div className="font-display text-3xl font-bold text-brand-800 mt-1">
                {usage.count}{' '}
                <span className="text-lg font-normal text-[#6b8a78]">/ {usage.limit}</span>
              </div>
              <div className="text-sm text-[#6b8a78]">conversaciones este mes</div>
              {(usage.extra_conversations > 0) && (
                <div className="text-xs text-[#6b8a78] mt-0.5">
                  Base {usage.base_limit} + <span className="text-[#0b4c45] font-semibold">+{usage.extra_conversations} extra</span>
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="font-display text-3xl font-bold" style={{ color: barColor }}>{pct}%</div>
              <div className="text-xs text-[#6b8a78] mt-1">{usage.remaining ?? usage.limit - usage.count} restantes</div>
            </div>
          </div>

          <div className="h-3 bg-brand-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700"
              style={{ width: `${Math.min(pct, 100)}%`, background: barColor }}
            />
          </div>
          <div className="flex justify-between text-xs text-[#6b8a78] mt-2">
            <span>0</span>
            <span style={{ color: '#EF9F27' }} className="font-semibold">
              ⚠️ 80% = {Math.round(usage.limit * 0.8)}
            </span>
            <span>{usage.limit}</span>
          </div>

          {/* Avisos de alerta */}
          {pct >= 80 && (
            <div className="mt-3 text-xs px-3 py-2 rounded-lg border"
              style={{ background: '#FAEEDA', borderColor: '#EF9F27', color: '#633806' }}>
              {pct >= 100
                ? '🚨 Límite alcanzado — el bot no está respondiendo. Agrega conversaciones o renueva el plan.'
                : `⚠️ Estás al ${pct}% del límite mensual.`}
            </div>
          )}
          {!usage.service_active && (
            <div className="mt-3 text-xs px-3 py-2 rounded-lg border border-red-300 bg-red-50 text-red-700">
              🔴 Servicio desactivado manualmente — el bot no está respondiendo mensajes.
            </div>
          )}
        </div>

        {/* ── Estado de alertas ─────────────────────────────────────────── */}
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

        {/* ── Detalles del plan ─────────────────────────────────────────── */}
        <div className="card p-5">
          <h3 className="font-semibold text-brand-800 mb-3">Detalles del plan</h3>
          <div className="space-y-0 text-sm">
            {[
              ['Plan',                    'Profesional'],
              ['Conversaciones base',     `${usage.base_limit ?? usage.limit} / mes`],
              ['Conversaciones extra',    usage.extra_conversations > 0 ? `+${usage.extra_conversations}` : '—'],
              ['Total disponible',        `${usage.limit} / mes`],
              ['Período actual',          usage.period],
              ['Último pago',             usage.paid_at ? new Date(usage.paid_at).toLocaleDateString('es') : 'Sin registro'],
              ['Referencia de pago',      usage.last_payment_reference || '—'],
              ['Vence',                   usage.expires_at ? new Date(usage.expires_at).toLocaleDateString('es') : 'Sin fecha'],
              ['Motor IA',                'Google Gemini 2.0 Flash'],
              ['Canal',                   'WhatsApp Business API (Meta)'],
              ['SLA soporte',             '12 horas hábiles'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between py-2 border-b border-[#e4ede8] last:border-0">
                <span className="text-[#6b8a78]">{k}</span>
                <span className="font-semibold text-brand-800">{v}</span>
              </div>
            ))}
          </div>
        </div>

        {/* ── Panel de control Superadmin ───────────────────────────────── */}
        {isSuperAdmin && (
          <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5">
            <h3 className="text-sm font-bold text-purple-800 mb-1">⚡ Panel de control — Superadmin</h3>
            <p className="text-xs text-purple-600 mb-4">
              Solo tú puedes usar estas acciones. Los cambios son inmediatos.
            </p>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={() => { setShowRenew(!showRenew); setShowAddConvs(false) }}
                className="bg-[#0b4c45] hover:bg-[#0d5c54] text-white font-semibold px-4 py-2.5 rounded-xl text-sm transition-all"
              >
                🔄 Renovar plan mensual
              </button>
              <button
                onClick={() => { setShowAddConvs(!showAddConvs); setShowRenew(false) }}
                className="bg-[#C6A96B] hover:bg-[#b8943a] text-white font-semibold px-4 py-2.5 rounded-xl text-sm transition-all"
              >
                ➕ Agregar conversaciones
              </button>
              <button
                onClick={handleToggleService}
                disabled={toggleSaving}
                className={`font-semibold px-4 py-2.5 rounded-xl text-sm transition-all disabled:opacity-50 ${
                  usage.service_active
                    ? 'bg-red-600 hover:bg-red-700 text-white'
                    : 'bg-green-600 hover:bg-green-700 text-white'
                }`}
              >
                {toggleSaving
                  ? 'Actualizando...'
                  : usage.service_active
                    ? '🔴 Desactivar servicio'
                    : '🟢 Activar servicio'}
              </button>
            </div>

            {/* ── Formulario: renovar plan ─────────────────────────────── */}
            {showRenew && (
              <div className="mt-4 bg-white rounded-xl border border-purple-200 p-4 animate-fade-in">
                <h4 className="text-sm font-semibold text-[#0b4c45] mb-1">Renovar plan mensual</h4>
                <p className="text-xs text-[#7a6a55] mb-3">
                  Activa el servicio, resetea extras a 0 y registra vencimiento a 30 días.
                </p>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                      Conversaciones del plan
                    </label>
                    <input
                      type="number"
                      className="input max-w-xs"
                      value={renewForm.plan_limit}
                      onChange={e => setRenewForm({ ...renewForm, plan_limit: Number(e.target.value) })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                      Referencia de pago
                    </label>
                    <input
                      className="input"
                      placeholder="Ej: ZELLE-2025-05-01, confirmación #123..."
                      value={renewForm.payment_reference}
                      onChange={e => setRenewForm({ ...renewForm, payment_reference: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Notas</label>
                    <input
                      className="input"
                      placeholder="Ej: Pago recibido por WhatsApp el 01/05/2025..."
                      value={renewForm.notes}
                      onChange={e => setRenewForm({ ...renewForm, notes: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={handleRenew}
                    disabled={renewSaving}
                    className="bg-[#0b4c45] hover:bg-[#0d5c54] text-white font-semibold px-4 py-2 rounded-xl text-sm disabled:opacity-50 transition-all"
                  >
                    {renewSaving ? 'Renovando...' : '✅ Confirmar renovación'}
                  </button>
                  <button onClick={() => setShowRenew(false)} className="btn-ghost text-sm">
                    Cancelar
                  </button>
                </div>
              </div>
            )}

            {/* ── Formulario: agregar conversaciones ──────────────────── */}
            {showAddConvs && (
              <div className="mt-4 bg-white rounded-xl border border-purple-200 p-4 animate-fade-in">
                <h4 className="text-sm font-semibold text-[#0b4c45] mb-1">Agregar conversaciones adicionales</h4>
                <p className="text-xs text-[#7a6a55] mb-3">
                  Se suman al disponible este mes. El servicio se activa automáticamente.
                </p>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                      Cantidad a agregar
                    </label>
                    <input
                      type="number"
                      className="input max-w-xs"
                      min={1}
                      value={addForm.extra_conversations}
                      onChange={e => setAddForm({ ...addForm, extra_conversations: Number(e.target.value) })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                      Referencia de pago
                    </label>
                    <input
                      className="input"
                      placeholder="Ej: ZELLE-2025-05-15-extra..."
                      value={addForm.payment_reference}
                      onChange={e => setAddForm({ ...addForm, payment_reference: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Notas</label>
                    <input
                      className="input"
                      placeholder="Ej: Paquete adicional 500 convs..."
                      value={addForm.notes}
                      onChange={e => setAddForm({ ...addForm, notes: e.target.value })}
                    />
                  </div>
                </div>
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={handleAddConversations}
                    disabled={addSaving}
                    className="bg-[#C6A96B] hover:bg-[#b8943a] text-white font-semibold px-4 py-2 rounded-xl text-sm disabled:opacity-50 transition-all"
                  >
                    {addSaving ? 'Agregando...' : `✅ Agregar ${addForm.extra_conversations} conversaciones`}
                  </button>
                  <button onClick={() => setShowAddConvs(false)} className="btn-ghost text-sm">
                    Cancelar
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Aviso para no-superadmin cerca del límite ─────────────────── */}
        {!isSuperAdmin && pct >= 80 && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 text-sm text-amber-800">
            <p className="font-semibold mb-1">⚠️ Estás cerca del límite mensual</p>
            <p className="text-xs">
              Contacta al administrador del sistema para renovar el plan o agregar más conversaciones.
            </p>
          </div>
        )}

      </div>
    </div>
  )
}
