import { useEffect, useState } from 'react'
import { patientsApi, planApi } from '../api/client'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../components/Toast'

// ── TASA DE CONVERSIÓN ────────────────────────────────────────────────────────
const TRM = 4200 // COP por 1 USD

function formatCOP(n: number) {
  return '$' + n.toLocaleString('es-CO') + ' COP'
}

function formatUSD(copAmount: number) {
  return '$' + (copAmount / TRM).toFixed(2) + ' USD'
}

// ── PLANES ────────────────────────────────────────────────────────────────────
const PLANES = [
  {
    id: 'semilla',
    nombre: 'Semilla',
    emoji: '🌱',
    conversaciones: 300,
    precioMesCOP: 150000,
    precioImplCOP: 250000,
    costoRealCOP: 17600,
    contratoMin: '3 meses',
    infraestructura: 'Compartida',
    color: '#6b8a78',
    bg: '#f0f7f4',
    border: '#c8ddd6',
    destacado: false,
    massolicitado: false,
    features: [
      '300 conversaciones/mes',
      '~4.500 mensajes incluidos',
      'Bot IA 24/7 (Gemini)',
      'Dashboard básico de KPIs',
      'SLA soporte 48h',
    ],
    descripcion: 'Para emprendedores y negocios que están comenzando.',
  },
  {
    id: 'basico',
    nombre: 'Básico',
    emoji: '⚡',
    conversaciones: 700,
    precioMesCOP: 250000,
    precioImplCOP: 400000,
    costoRealCOP: 30400,
    contratoMin: '3 meses',
    infraestructura: 'Compartida',
    color: '#2563eb',
    bg: '#eff6ff',
    border: '#bfdbfe',
    destacado: false,
    massolicitado: true,
    features: [
      '700 conversaciones/mes',
      '~10.500 mensajes incluidos',
      'Bot IA 24/7 (Gemini)',
      'Paso a agente humano',
      'Dashboard completo',
      'SLA soporte 24h',
    ],
    descripcion: 'Ideal para negocios con flujo regular de clientes.',
  },
  {
    id: 'profesional',
    nombre: 'Profesional',
    emoji: '🚀',
    conversaciones: 1500,
    precioMesCOP: 450000,
    precioImplCOP: 600000,
    costoRealCOP: 56000,
    contratoMin: '6 meses',
    infraestructura: 'Compartida',
    color: '#0b4c45',
    bg: '#e8f4f1',
    border: '#0b4c45',
    destacado: true,
    massolicitado: false,
    features: [
      '1.500 conversaciones/mes',
      '~22.500 mensajes incluidos',
      'Bot IA 24/7 (Gemini)',
      'Paso a agente + gestión',
      'Embudo de ventas',
      'Links de pago integrados',
      'Exportación Excel y PDF',
      'Dominio .com incluido',
      'SLA soporte 12h',
    ],
    descripcion: 'Para clínicas y empresas con operación consolidada.',
  },
  {
    id: 'empresarial',
    nombre: 'Empresarial',
    emoji: '🏢',
    conversaciones: 3500,
    precioMesCOP: 800000,
    precioImplCOP: 800000,
    costoRealCOP: 137400,
    contratoMin: '12 meses',
    infraestructura: 'KVM 4 Dedicado',
    color: '#b45309',
    bg: '#fffbeb',
    border: '#fcd34d',
    destacado: false,
    massolicitado: false,
    features: [
      '3.500 conversaciones/mes',
      '~52.500 mensajes incluidos',
      'Servidor dedicado KVM 4',
      'Respaldo automático diario',
      'Todos los módulos activos',
      '5 módulos personalizados',
      'SLA soporte prioritario 4h',
    ],
    descripcion: 'Para operaciones de alto volumen y múltiples sucursales.',
  },
]

// ── PAQUETES EXTRA ────────────────────────────────────────────────────────────
const PAQUETES_EXTRA = [
  { conversaciones: 100,  precioCOP: 20000,  costoRealCOP: 3200,  etiqueta: 'Mini',     emoji: '🔋', tag: '' },
  { conversaciones: 300,  precioCOP: 45000,  costoRealCOP: 9600,  etiqueta: 'Estándar', emoji: '⚡', tag: 'Popular' },
  { conversaciones: 700,  precioCOP: 90000,  costoRealCOP: 22400, etiqueta: 'Popular',  emoji: '🚀', tag: '' },
  { conversaciones: 1500, precioCOP: 150000, costoRealCOP: 48000, etiqueta: 'Pro',      emoji: '💎', tag: 'Mejor valor' },
  { conversaciones: 3000, precioCOP: 270000, costoRealCOP: 96000, etiqueta: 'Máximo',   emoji: '🏢', tag: '' },
]

// ── ADD-ONS ───────────────────────────────────────────────────────────────────
const ADDONS = [
  {
    categoria: '🛠️ Módulos personalizados',
    items: [
      { nombre: 'Módulo de negocio extra',      precioCOP: 200000, tipo: 'único', desc: 'Flujo nuevo fuera del plan base' },
      { nombre: 'Flujo conversacional',         precioCOP: 150000, tipo: 'único', desc: 'Árbol de decisión personalizado' },
      { nombre: 'Integración pasarela de pago', precioCOP: 250000, tipo: 'único', desc: 'Wompi, PayU, Mercado Pago' },
      { nombre: 'Catálogo de productos',        precioCOP: 180000, tipo: 'único', desc: 'Hasta 50 productos con precios' },
    ],
  },
  {
    categoria: '📊 Soporte premium',
    items: [
      { nombre: 'Soporte prioritario',  precioCOP: 80000,  tipo: '/mes', desc: 'SLA 4h, WhatsApp directo' },
      { nombre: 'Mantenimiento activo', precioCOP: 120000, tipo: '/mes', desc: 'Ajustes mensuales de flujos y FAQ' },
    ],
  },
  {
    categoria: '🎓 Capacitación',
    items: [
      { nombre: 'Capacitación equipo',   precioCOP: 150000, tipo: 'único', desc: 'Sesión 2h con el equipo del cliente' },
      { nombre: 'Capacitación avanzada', precioCOP: 250000, tipo: 'único', desc: '2 sesiones + documentación' },
    ],
  },
  {
    categoria: '🔗 Integraciones',
    items: [
      { nombre: 'CRM (HubSpot / Zoho)',       precioCOP: 350000, tipo: 'único', desc: 'Sincronización de contactos' },
      { nombre: 'Google Calendar',            precioCOP: 200000, tipo: 'único', desc: 'Agendamiento automático' },
      { nombre: 'Sistema propio del cliente', precioCOP: 400000, tipo: 'desde', desc: 'Cotización por complejidad' },
    ],
  },
]

// ── COMPONENTES PEQUEÑOS ─────────────────────────────────────────────────────
function ReadOnlyBadge() {
  return (
    <div className="w-full text-center py-2.5 rounded-xl text-sm font-semibold bg-gray-100 text-[#7a6a55] border border-[#e5ddd4]">
      Solo informativo
    </div>
  )
}

function ReadOnlyNotice() {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4">
      <p className="text-sm font-semibold text-blue-800 mb-1">ℹ️ Vista informativa</p>
      <p className="text-xs text-blue-700">
        Puedes consultar planes, paquetes y servicios adicionales, pero las acciones de renovación,
        activación, desactivación o aplicación de paquetes solo están disponibles para el superadmin.
      </p>
    </div>
  )
}

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
    latam: '🌎 LATAM',
    usa: '🇺🇸 USA',
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
              <tr>
                <td colSpan={5} className="text-center py-12 text-sm text-[#6b8a78]">Cargando...</td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-12 text-sm text-[#6b8a78]">Sin pacientes registrados</td>
              </tr>
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

// ── PLAN PAGE ─────────────────────────────────────────────────────────────────
export function PlanPage() {
  const { agent } = useAuth()
  const toast = useToast()

  const isSuperAdmin = agent?.role === 'superadmin'
  const isReadOnlyAdmin = agent?.role === 'admin' || agent?.role === 'supervisor'

  const [usage, setUsage] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  type TabId = 'uso' | 'planes' | 'extra' | 'addons'
  const [tab, setTab] = useState<TabId>('uso')

  // Formularios superadmin
  const [showRenew, setShowRenew] = useState(false)
  const [renewForm, setRenewForm] = useState({ plan_limit: 1500, payment_reference: '', notes: '' })
  const [renewSaving, setRenewSaving] = useState(false)
  const [addForm, setAddForm] = useState({ extra_conversations: 300, payment_reference: '', notes: '' })
  const [addSaving, setAddSaving] = useState(false)
  const [toggleSaving, setToggleSaving] = useState(false)
  const [applyingPlan, setApplyingPlan] = useState<string | null>(null)
  const [applyingPack, setApplyingPack] = useState<number | null>(null)

  const load = () => {
    setLoading(true)
    planApi.getUsage().then(r => setUsage(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  // Acciones superadmin
  const handleRenew = async () => {
    if (!isSuperAdmin) return
    setRenewSaving(true)
    try {
      await planApi.renew({
        plan_limit: renewForm.plan_limit,
        payment_reference: renewForm.payment_reference || undefined,
        notes: renewForm.notes || undefined,
      })
      toast.success('Plan renovado', `${renewForm.plan_limit.toLocaleString()} conversaciones activadas`)
      setShowRenew(false)
      load()
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'No se pudo renovar')
    } finally {
      setRenewSaving(false)
    }
  }

  const handleAddConversations = async () => {
    if (!isSuperAdmin) return
    if (addForm.extra_conversations <= 0) {
      toast.warning('Cantidad inválida', 'Debe ser mayor que 0')
      return
    }
    setAddSaving(true)
    try {
      await planApi.addConversations({
        extra_conversations: addForm.extra_conversations,
        payment_reference: addForm.payment_reference || undefined,
        notes: addForm.notes || undefined,
      })
      toast.success('Conversaciones agregadas', `+${addForm.extra_conversations.toLocaleString()}`)
      load()
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'No se pudo agregar')
    } finally {
      setAddSaving(false)
    }
  }

  const handleToggleService = async () => {
    if (!isSuperAdmin || !usage) return
    const newState = !usage.service_active
    if (!confirm(`¿${newState ? 'ACTIVAR' : 'DESACTIVAR'} el servicio del bot?`)) return
    setToggleSaving(true)
    try {
      await planApi.toggleService({ service_active: newState })
      toast.success(
        newState ? 'Bot activado ✅' : 'Bot desactivado 🔴',
        newState ? 'El bot vuelve a responder.' : 'El bot dejó de responder.'
      )
      load()
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'No se pudo cambiar')
    } finally {
      setToggleSaving(false)
    }
  }

  const handleApplyPlan = async (plan: typeof PLANES[0]) => {
    if (!isSuperAdmin) return
    if (!confirm(`¿Activar el plan ${plan.nombre} (${plan.conversaciones.toLocaleString()} conv/mes)?`)) return
    setApplyingPlan(plan.id)
    try {
      await planApi.renew({
        plan_limit: plan.conversaciones,
        notes: `Plan ${plan.nombre} — ${formatCOP(plan.precioMesCOP)}/mes`,
      })
      toast.success(`Plan ${plan.nombre} activado`, `${plan.conversaciones.toLocaleString()} conv/mes`)
      load()
      setTab('uso')
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'No se pudo aplicar')
    } finally {
      setApplyingPlan(null)
    }
  }

  const handleApplyPack = async (pack: typeof PAQUETES_EXTRA[0]) => {
    if (!isSuperAdmin) return
    if (!confirm(`¿Agregar ${pack.conversaciones.toLocaleString()} conversaciones?`)) return
    setApplyingPack(pack.conversaciones)
    try {
      await planApi.addConversations({
        extra_conversations: pack.conversaciones,
        notes: `Pack ${pack.etiqueta} — ${formatCOP(pack.precioCOP)}`,
      })
      toast.success(`Pack ${pack.etiqueta} aplicado`, `+${pack.conversaciones.toLocaleString()} conv`)
      load()
      setTab('uso')
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'No se pudo aplicar')
    } finally {
      setApplyingPack(null)
    }
  }

  const pct = usage?.percentage || 0
  const barColor = pct >= 100 ? '#E24B4A' : pct >= 80 ? '#EF9F27' : '#1D9E75'

  // Admin/supervisor y superadmin ven las 4 pestañas.
  // La diferencia está en las acciones: solo superadmin puede aplicar cambios.
  const TABS: { id: TabId; label: string }[] = [
    { id: 'uso', label: '📊 Uso actual' },
    { id: 'planes', label: '📋 Planes' },
    { id: 'extra', label: '➕ Paquetes extra' },
    { id: 'addons', label: '🔧 Servicios adicionales' },
  ]

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

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-brand-800">Plan y Uso</h1>
          <p className="text-sm text-[#6b8a78] mt-0.5">
            Período: {usage?.period}
            {isSuperAdmin && (
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-purple-100 text-purple-700">
                ⚡ Superadmin · precios internos en COP
              </span>
            )}
            {isReadOnlyAdmin && (
              <span className="ml-2 text-xs font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                💵 Solo lectura · precios en USD
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
            usage?.service_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            <span className={`w-2 h-2 rounded-full ${usage?.service_active ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}/>
            {usage?.service_active ? 'Bot activo' : 'Bot inactivo'}
          </div>

          {isSuperAdmin && (
            <button
              onClick={handleToggleService}
              disabled={toggleSaving}
              className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-all disabled:opacity-50 border ${
                usage?.service_active
                  ? 'border-red-200 text-red-600 hover:bg-red-50'
                  : 'border-green-200 text-green-600 hover:bg-green-50'
              }`}
            >
              {toggleSaving ? '...' : usage?.service_active ? '🔴 Desactivar' : '🟢 Activar'}
            </button>
          )}
        </div>
      </div>

      {/* ── Tabs ───────────────────────────────────────────────────── */}
      <div className="flex gap-1 bg-[#F5F1EB] p-1 rounded-xl mb-6 flex-wrap">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              tab === t.id ? 'bg-[#0b4c45] text-white shadow-sm' : 'text-[#7a6a55] hover:text-[#0b4c45]'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* ══ TAB: USO ACTUAL ══════════════════════════════════════════ */}
      {tab === 'uso' && (
        <div className="space-y-4">
          <div className="card p-6">
            <div className="flex items-end justify-between mb-4">
              <div>
                <div className="text-xs font-semibold text-[#6b8a78] uppercase tracking-wider mb-1">
                  Conversaciones este mes
                </div>
                <div className="flex items-baseline gap-2">
                  <span className="font-display text-4xl font-bold text-[#0b4c45]">{usage?.count ?? 0}</span>
                  <span className="text-lg text-[#7a6a55]">/ {(usage?.limit ?? 0).toLocaleString()}</span>
                </div>
                <div className="text-xs text-[#7a6a55] mt-0.5">
                  Cada conversación incluye ~15 mensajes de intercambio con el bot
                </div>
                {(usage?.extra_conversations > 0) && (
                  <div className="text-xs text-[#6b8a78] mt-0.5">
                    Base {(usage?.base_limit ?? 0).toLocaleString()} +{' '}
                    <span className="text-[#0b4c45] font-semibold">
                      +{(usage?.extra_conversations ?? 0).toLocaleString()} extra
                    </span>
                  </div>
                )}
              </div>
              <div className="text-right">
                <div className="font-display text-3xl font-bold" style={{ color: barColor }}>{pct}%</div>
                <div className="text-xs text-[#7a6a55] mt-1">{(usage?.remaining ?? 0).toLocaleString()} restantes</div>
              </div>
            </div>

            <div className="h-3 bg-brand-100 rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-700"
                style={{ width: `${Math.min(pct, 100)}%`, background: barColor }}
              />
            </div>
            <div className="flex justify-between text-[10px] text-[#7a6a55] mt-1.5">
              <span>0</span>
              <span style={{ color: '#EF9F27' }} className="font-semibold">
                ⚠ 80% = {Math.round((usage?.limit ?? 0) * 0.8).toLocaleString()}
              </span>
              <span>{(usage?.limit ?? 0).toLocaleString()}</span>
            </div>

            {pct >= 80 && (
              <div
                className="mt-3 text-xs px-3 py-2 rounded-lg border"
                style={{ background: '#FAEEDA', borderColor: '#EF9F27', color: '#633806' }}
              >
                {pct >= 100
                  ? '🚨 Límite alcanzado — el bot dejó de responder. Adquiere un paquete adicional para reactivarlo.'
                  : `⚠️ Al ${pct}% del límite. Considera adquirir conversaciones adicionales.`}
              </div>
            )}

            {!usage?.service_active && (
              <div className="mt-3 text-xs px-3 py-2 rounded-lg border border-red-300 bg-red-50 text-red-700">
                🔴 Servicio desactivado — el bot no está respondiendo mensajes.
              </div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            {[
              ['Base del plan', `${(usage?.base_limit ?? 0).toLocaleString()} conv/mes`],
              ['Extras agregados', usage?.extra_conversations > 0 ? `+${(usage?.extra_conversations ?? 0).toLocaleString()}` : '—'],
              ['Total disponible', `${(usage?.limit ?? 0).toLocaleString()} conv/mes`],
              ['Período', usage?.period ?? '—'],
              ['Último pago', usage?.paid_at ? new Date(usage.paid_at).toLocaleDateString('es') : 'Sin registro'],
              ['Referencia', usage?.last_payment_reference || '—'],
              ['Vence', usage?.expires_at ? new Date(usage.expires_at).toLocaleDateString('es') : 'Sin fecha'],
              ['Excedente', isSuperAdmin ? '$80 COP/conv' : '$0.02 USD/conv'],
            ].map(([k, v]) => (
              <div key={k} className="bg-white rounded-xl border border-[#e5ddd4] px-4 py-3">
                <div className="text-xs text-[#7a6a55] mb-0.5">{k}</div>
                <div className="text-sm font-semibold text-[#0b4c45]">{v}</div>
              </div>
            ))}
          </div>

          {isSuperAdmin && (
            <div className="bg-purple-50 border border-purple-200 rounded-2xl p-5">
              <h3 className="text-sm font-bold text-purple-800 mb-1">⚡ Acciones rápidas — Superadmin</h3>
              <p className="text-xs text-purple-600 mb-4">Cambios inmediatos sobre el plan activo del cliente.</p>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => setShowRenew(!showRenew)}
                  className="bg-[#0b4c45] hover:bg-[#0d5c54] text-white font-semibold px-4 py-2.5 rounded-xl text-sm transition-all"
                >
                  🔄 Renovar plan manual
                </button>
                <button
                  onClick={() => setTab('planes')}
                  className="bg-[#C6A96B] hover:bg-[#b8943a] text-white font-semibold px-4 py-2.5 rounded-xl text-sm transition-all"
                >
                  📋 Cambiar plan
                </button>
                <button
                  onClick={() => setTab('extra')}
                  className="bg-white hover:bg-[#f0f7f4] text-[#0b4c45] font-semibold px-4 py-2.5 rounded-xl text-sm transition-all border border-[#0b4c45]"
                >
                  ➕ Agregar conversaciones
                </button>
              </div>

              {showRenew && (
                <div className="mt-4 bg-white rounded-xl border border-purple-200 p-4 animate-fade-in">
                  <h4 className="text-sm font-semibold text-[#0b4c45] mb-3">Renovar plan manualmente</h4>
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Conversaciones del plan</label>
                      <input
                        type="number"
                        className="input max-w-xs"
                        value={renewForm.plan_limit}
                        onChange={e => setRenewForm({ ...renewForm, plan_limit: Number(e.target.value) })}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Referencia de pago</label>
                      <input
                        className="input"
                        placeholder="Ej: Transferencia #123 — 01/05/2025"
                        value={renewForm.payment_reference}
                        onChange={e => setRenewForm({ ...renewForm, payment_reference: e.target.value })}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Notas</label>
                      <input
                        className="input"
                        placeholder="Ej: Plan Profesional mayo 2025"
                        value={renewForm.notes}
                        onChange={e => setRenewForm({ ...renewForm, notes: e.target.value })}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={handleRenew}
                      disabled={renewSaving}
                      className="bg-[#0b4c45] text-white font-semibold px-4 py-2 rounded-xl text-sm disabled:opacity-50"
                    >
                      {renewSaving ? 'Renovando...' : '✅ Confirmar renovación'}
                    </button>
                    <button onClick={() => setShowRenew(false)} className="btn-ghost text-sm">Cancelar</button>
                  </div>
                </div>
              )}
            </div>
          )}

          {isReadOnlyAdmin && <ReadOnlyNotice />}
        </div>
      )}

      {/* ══ TAB: PLANES ═════════════════════════════════════════════ */}
      {tab === 'planes' && (
        <div>
          <div className="mb-5">
            <h2 className="font-display text-xl font-bold text-[#0b4c45]">Planes de suscripción mensual</h2>
            <p className="text-sm text-[#7a6a55] mt-1">
              {isSuperAdmin
                ? 'Precios internos en COP. Puedes aplicar o renovar un plan.'
                : 'Catálogo informativo para administradores y supervisores. Precios visibles en USD.'}
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
            {PLANES.map(plan => (
              <div
                key={plan.id}
                className={`relative rounded-2xl border-2 p-5 transition-all ${plan.destacado ? 'shadow-lg' : 'shadow-sm hover:shadow-md'}`}
                style={{ borderColor: plan.border, background: plan.bg }}
              >
                {plan.destacado && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-[#0b4c45] text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider whitespace-nowrap">
                      ✓ Plan activo
                    </span>
                  </div>
                )}

                {plan.massolicitado && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <span className="bg-blue-600 text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wider whitespace-nowrap">
                      Más solicitado
                    </span>
                  </div>
                )}

                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xl">{plan.emoji}</span>
                      <span className="font-display font-bold text-lg" style={{ color: plan.color }}>{plan.nombre}</span>
                    </div>

                    <div className="font-display text-2xl font-bold text-[#1a1208]">
                      {isSuperAdmin ? formatCOP(plan.precioMesCOP) : formatUSD(plan.precioMesCOP)}
                      <span className="text-sm font-normal text-[#7a6a55]">/mes</span>
                    </div>

                    {isSuperAdmin && (
                      <>
                        <div className="text-xs text-blue-600 mt-0.5">
                          Cliente ve: {formatUSD(plan.precioMesCOP)}/mes
                        </div>
                        <div className="text-xs font-semibold text-green-700 mt-1">
                          💰 Tu ganancia: {formatCOP(plan.precioMesCOP - plan.costoRealCOP)}/mes
                        </div>
                      </>
                    )}

                    <div className="text-xs text-[#7a6a55] mt-0.5">
                      Implementación: {isSuperAdmin ? formatCOP(plan.precioImplCOP) : formatUSD(plan.precioImplCOP)} · Mín. {plan.contratoMin}
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="font-bold text-lg" style={{ color: plan.color }}>
                      {plan.conversaciones.toLocaleString()}
                    </div>
                    <div className="text-xs text-[#7a6a55]">conv/mes</div>
                    <div className="text-[10px] text-[#7a6a55] mt-0.5">~{(plan.conversaciones * 15).toLocaleString()} msg</div>
                    <div className="text-[10px] text-[#7a6a55]">{plan.infraestructura}</div>
                  </div>
                </div>

                <p className="text-xs text-[#7a6a55] mb-3 italic">{plan.descripcion}</p>

                <ul className="space-y-1 mb-4">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-center gap-2 text-xs text-[#1a1208]">
                      <span style={{ color: plan.color }}>✓</span>{f}
                    </li>
                  ))}
                </ul>

                {isSuperAdmin ? (
                  <button
                    onClick={() => handleApplyPlan(plan)}
                    disabled={applyingPlan === plan.id}
                    className="w-full font-semibold py-2.5 rounded-xl text-sm transition-all disabled:opacity-50"
                    style={{
                      background: plan.destacado ? plan.color : 'white',
                      color: plan.destacado ? 'white' : plan.color,
                      border: `2px solid ${plan.color}`,
                    }}
                  >
                    {applyingPlan === plan.id
                      ? 'Aplicando...'
                      : plan.destacado
                        ? '✅ Renovar plan'
                        : `Aplicar plan ${plan.nombre}`}
                  </button>
                ) : (
                  <ReadOnlyBadge />
                )}
              </div>
            ))}
          </div>

          <div className="bg-[#F5F1EB] rounded-2xl p-4 text-sm text-[#7a6a55]">
            <p className="font-semibold text-[#0b4c45] mb-1">📌 Notas</p>
            <p>• Módulo adicional: <strong>{isSuperAdmin ? formatCOP(200000) : formatUSD(200000)}</strong> c/u</p>
            <p>• Flujo conversacional extra: <strong>{isSuperAdmin ? formatCOP(150000) : formatUSD(150000)}</strong> c/u</p>
            <p>• Excedente automático: <strong>{isSuperAdmin ? '$80 COP' : '$0.02 USD'}</strong> por conversación adicional</p>
          </div>
        </div>
      )}

      {/* ══ TAB: PAQUETES EXTRA ═════════════════════════════════════ */}
      {tab === 'extra' && (
        <div>
          <div className="mb-5">
            <h2 className="font-display text-xl font-bold text-[#0b4c45]">
              {isSuperAdmin ? 'Paquetes de conversaciones extra' : 'Conversaciones adicionales'}
            </h2>
            <p className="text-sm text-[#7a6a55] mt-1">
              {isSuperAdmin
                ? 'Se suman al plan activo inmediatamente. El servicio se reactiva automáticamente.'
                : 'Catálogo informativo de paquetes adicionales. Precios visibles en USD.'}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
            {PAQUETES_EXTRA.map(pack => (
              <div key={pack.conversaciones} className="relative bg-white rounded-2xl border border-[#e5ddd4] p-5 shadow-sm hover:shadow-md transition-all">
                {pack.tag && (
                  <div className="absolute -top-2 right-4">
                    <span className="bg-[#C6A96B] text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                      {pack.tag}
                    </span>
                  </div>
                )}

                <div className="text-3xl mb-2">{pack.emoji}</div>
                <div className="font-display font-bold text-lg text-[#0b4c45]">{pack.etiqueta}</div>
                <div className="text-sm text-[#7a6a55] mb-3">
                  +{pack.conversaciones.toLocaleString()} conversaciones
                </div>

                {isSuperAdmin ? (
                  <>
                    <div className="font-bold text-lg text-[#1a1208]">{formatCOP(pack.precioCOP)}</div>
                    <div className="text-xs text-blue-600 mb-1">Cliente ve: {formatUSD(pack.precioCOP)}</div>
                    <div className="text-xs font-semibold text-green-700 mb-4">
                      💰 Tu ganancia: {formatCOP(pack.precioCOP - pack.costoRealCOP)}
                    </div>
                    <button
                      onClick={() => handleApplyPack(pack)}
                      disabled={applyingPack === pack.conversaciones}
                      className="w-full btn-primary justify-center disabled:opacity-50 text-sm"
                    >
                      {applyingPack === pack.conversaciones ? 'Aplicando...' : `Aplicar ${pack.etiqueta}`}
                    </button>
                  </>
                ) : (
                  <>
                    <div className="font-bold text-2xl text-[#0b4c45] mb-1">{formatUSD(pack.precioCOP)}</div>
                    <div className="text-xs text-[#7a6a55] mb-4">
                      ${(pack.precioCOP / TRM / pack.conversaciones).toFixed(3)} USD/conv
                    </div>
                    <ReadOnlyBadge />
                  </>
                )}
              </div>
            ))}
          </div>

          {isSuperAdmin && (
            <div className="card p-5">
              <h3 className="font-semibold text-[#0b4c45] mb-3">📝 Cantidad personalizada</h3>
              <div className="grid grid-cols-3 gap-3 mb-3">
                <div>
                  <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Conversaciones</label>
                  <input
                    type="number"
                    className="input"
                    min={1}
                    value={addForm.extra_conversations}
                    onChange={e => setAddForm({ ...addForm, extra_conversations: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Precio cliente (COP)</label>
                  <div className="input bg-[#F5F1EB] text-[#0b4c45] font-semibold text-sm">
                    {formatCOP(addForm.extra_conversations * 80)}
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Precio cliente (USD)</label>
                  <div className="input bg-[#eff6ff] text-blue-600 font-semibold text-sm">
                    {formatUSD(addForm.extra_conversations * 80)}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Referencia de pago</label>
                  <input
                    className="input"
                    placeholder="Ej: Transferencia #456"
                    value={addForm.payment_reference}
                    onChange={e => setAddForm({ ...addForm, payment_reference: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Notas</label>
                  <input
                    className="input"
                    placeholder="Ej: Paquete solicitado por campaña"
                    value={addForm.notes}
                    onChange={e => setAddForm({ ...addForm, notes: e.target.value })}
                  />
                </div>
              </div>

              <div className="flex items-center gap-4">
                <button onClick={handleAddConversations} disabled={addSaving} className="btn-primary disabled:opacity-50">
                  {addSaving ? 'Agregando...' : `✅ Agregar ${addForm.extra_conversations.toLocaleString()} conversaciones`}
                </button>
                <span className="text-xs text-green-700 font-semibold">
                  💰 Tu ganancia: {formatCOP((addForm.extra_conversations * 80) - (addForm.extra_conversations * 32))}
                </span>
              </div>
            </div>
          )}

          {isReadOnlyAdmin && (
            <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4">
              <p className="text-sm font-semibold text-blue-800 mb-1">💡 ¿Cómo adquirir conversaciones adicionales?</p>
              <p className="text-xs text-blue-700">
                Esta vista es únicamente informativa. Contacta al superadmin del sistema para aplicar el paquete requerido.
                Excedente automático: <strong>$0.02 USD por conversación</strong> adicional.
              </p>
            </div>
          )}
        </div>
      )}

      {/* ══ TAB: ADD-ONS ════════════════════════════════════════════ */}
      {tab === 'addons' && (
        <div>
          <div className="mb-5">
            <h2 className="font-display text-xl font-bold text-[#0b4c45]">Servicios adicionales</h2>
            <p className="text-sm text-[#7a6a55] mt-1">
              {isSuperAdmin
                ? 'Servicios complementarios. Ves precios internos en COP y referencia en USD.'
                : 'Catálogo informativo de servicios complementarios. Precios visibles en USD.'}
            </p>
          </div>

          <div className="space-y-6">
            {ADDONS.map(cat => (
              <div key={cat.categoria}>
                <h3 className="font-semibold text-[#0b4c45] mb-3">{cat.categoria}</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {cat.items.map(item => (
                    <div key={item.nombre} className="bg-white rounded-xl border border-[#e5ddd4] p-4 flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="font-semibold text-sm text-[#0b4c45]">{item.nombre}</div>
                        <div className="text-xs text-[#7a6a55] mt-0.5">{item.desc}</div>
                        {!isSuperAdmin && (
                          <div className="mt-2 text-[10px] text-[#7a6a55] bg-gray-100 border border-[#e5ddd4] rounded-full inline-flex px-2 py-0.5 font-semibold">
                            Solo informativo
                          </div>
                        )}
                      </div>

                      <div className="text-right flex-shrink-0">
                        <div className="font-bold text-sm text-[#1a1208]">
                          {isSuperAdmin ? formatCOP(item.precioCOP) : formatUSD(item.precioCOP)}
                        </div>
                        {isSuperAdmin && (
                          <div className="text-[10px] text-blue-600 font-medium">Cliente ve: {formatUSD(item.precioCOP)}</div>
                        )}
                        <div className="text-[10px] text-[#7a6a55]">{item.tipo}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 bg-[#F5F1EB] rounded-2xl p-4">
            <p className="text-xs text-[#7a6a55]">
              {isSuperAdmin
                ? '💡 Estos precios incluyen tu margen de ganancia sobre los costos reales de implementación. El cliente siempre ve el precio equivalente en USD.'
                : '💡 Esta información es solo visual. Para contratar o aplicar servicios adicionales, solicita la gestión al superadmin.'}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
