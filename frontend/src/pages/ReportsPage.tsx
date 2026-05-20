import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api/client'
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from 'recharts'

// ── Tipos ──────────────────────────────────────────────────────────────────────

interface FlowIntelligence {
    servicios_ranking: {
        opcion: string
        servicio: string
        total: number
        convertidos: number
        pct_conversion: number
    }[]
    abandono_por_paso: Record<string, number>
    lead_temperature: Record<string, { count: number; pct: number }>
    tipos_entrega: Record<string, number>
    tipo_cliente: Record<string, number>
    objetivos: { objetivo: string; count: number }[]
    condiciones: { condicion: string; count: number }[]
    horarios_pico: { hora: string; conversaciones: number }[]
}

interface ReportData {
    period: {
        since: string
        until: string
    }
    conversations: {
        total: number
        unique_users: number
        completed: number
        pct_completed: number
        status_distribution: Record<string, number>
    }
    agents: {
        escalated: number
        pct_escalated: number
        by_agent: { name: string; count: number }[]
        satisfaction: Record<string, { avg: number; total: number }>
    }
    appointments: {
        total_requested: number
        confirmed: number
        conversion_pct: number
        top_services: { service: string; count: number }[]
    }
    sales: {
        verified_payments: number
        total_revenue_usd: number
        total_revenue_cop: number
        total_cost_cop: number
        net_profit_cop: number
        margin_pct: number
        payment_methods: Record<string, number>
    }
    channels: Record<string, number>
    patients: {
        new_this_period: number
        total_recurrent: number
    }
    flow_intelligence: FlowIntelligence
    insights: {
        top_interests: { interest: string; count: number }[]
        top_unconverted_products: { product: string; attempts: number }[]
    }
}

const STATUS_LABELS: Record<string, string> = {
    active: 'Activas',
    in_agent: 'Con agente',
    completed: 'Completadas',
    closed: 'Cerradas',
}

const SERVICIOS = [
    { value: '', label: 'Todos los servicios' },
    { value: '1', label: '1. Pérdida de peso' },
    { value: '2', label: '2. Quemadores de grasa' },
    { value: '3', label: '3. Péptidos' },
    { value: '4', label: '4. NAD+' },
    { value: '5', label: '5. Estética' },
    { value: '6', label: '6. Limpiezas faciales' },
    { value: '7', label: '7. Sueros de vitaminas' },
    { value: '8', label: '8. Rejuvenecimiento vaginal' },
    { value: '9', label: '9. Morpheus' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtCOP(n: number) {
    return '$' + Math.round(n).toLocaleString('es-CO') + ' COP'
}

function Bar2({
    label,
    value,
    max,
    color = '#0b4c45',
    }: {
    label: string
    value: number
    max: number
    color?: string
    }) {
    const pct = max > 0 ? Math.round((value / max) * 100) : 0

    return (
        <div className="mb-2.5 min-w-0">
        <div className="flex justify-between items-center mb-1 gap-2 min-w-0">
            <span
            className="text-xs text-[#6b8a78] truncate flex-1 min-w-0"
            title={label}
            >
            {label}
            </span>

            <span
            className="text-xs font-bold flex-shrink-0"
            style={{ color }}
            >
            {value.toLocaleString('es-CO')}
            </span>
        </div>

        <div className="h-1.5 rounded-full bg-[#F5F1EB] overflow-hidden">
            <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${pct}%`, background: color }}
            />
        </div>
        </div>
    )
}

function KpiRow({
    label,
    value,
    hl,
    }: {
    label: string
    value: string | number
    hl?: boolean
    }) {
    return (
        <div
        className={`flex justify-between items-center gap-3 py-2 px-3 border-b border-[#f0ebe3] last:border-0 min-w-0 ${
            hl ? 'bg-[#f0f7f4] rounded-lg' : ''
        }`}
        >
        <span className="text-sm text-[#6b8a78] truncate min-w-0">
            {label}
        </span>

        <span
            className={`text-sm font-bold text-right flex-shrink-0 ${
            hl ? 'text-[#0b4c45]' : 'text-[#1a1208]'
            }`}
        >
            {value}
        </span>
        </div>
    )
}

function Card({
    icon,
    title,
    children,
    color = '#0b4c45',
    }: {
    icon: string
    title: string
    children: ReactNode
    color?: string
    }) {
    return (
        <div className="bg-white rounded-2xl border border-[#e5ddd4] overflow-hidden shadow-sm min-w-0">
        <div
            className="flex items-center gap-2 px-4 py-3 min-w-0"
            style={{ background: color }}
        >
            <span className="flex-shrink-0">{icon}</span>
            <span className="text-sm font-bold text-white uppercase tracking-wide truncate min-w-0">
            {title}
            </span>
        </div>

        <div className="p-4 min-w-0">
            {children}
        </div>
        </div>
    )
}

// ── Página ───────────────────────────────────────────────────────────────────

export default function ReportsPage() {
    const [data, setData] = useState<ReportData | null>(null)
    const [loading, setLoading] = useState(true)
    const [downloading, setDl] = useState<'excel' | 'pdf' | null>(null)

    // Filtros
    const [days, setDays] = useState(30)
    const [dateFrom, setDateFrom] = useState('')
    const [dateTo, setDateTo] = useState('')
    const [channel, setChannel] = useState('')
    const [sessionStatus, setSessStatus] = useState('')
    const [menuOpcion, setMenuOpcion] = useState('')
    const [location, setLocation] = useState('')
    const [paymentStatus, setPayStatus] = useState('')

    const qs = () => {
        const p = new URLSearchParams({ days: String(days) })

        if (dateFrom) p.set('date_from', dateFrom)
        if (dateTo) p.set('date_to', dateTo)
        if (channel) p.set('channel', channel)
        if (sessionStatus) p.set('session_status', sessionStatus)
        if (menuOpcion) p.set('menu_opcion', menuOpcion)
        if (location) p.set('location', location)
        if (paymentStatus) p.set('payment_status', paymentStatus)

        return p.toString()
    }

    useEffect(() => {
        setLoading(true)

        api
        .get(`/reports/summary?${qs()}`)
        .then((response) => setData(response.data))
        .finally(() => setLoading(false))
    }, [
        days,
        dateFrom,
        dateTo,
        channel,
        sessionStatus,
        menuOpcion,
        location,
        paymentStatus,
    ])

    const download = async (fmt: 'excel' | 'pdf') => {
        setDl(fmt)

        try {
        const response = await api.get(`/reports/export/${fmt}?${qs()}`, {
            responseType: 'blob',
        })

        const ext = fmt === 'excel' ? 'xlsx' : 'pdf'
        const url = URL.createObjectURL(response.data)
        const link = document.createElement('a')

        link.href = url
        link.download = `LLV_BI.${ext}`
        link.click()

        URL.revokeObjectURL(url)
        } finally {
        setDl(null)
        }
    }

    const fi = data?.flow_intelligence

    const maxSvc = Math.max(...(fi?.servicios_ranking.map((s) => s.total) || [1]), 1)
    const maxStep = Math.max(...Object.values(fi?.abandono_por_paso || {}), 1)
    const maxObj = Math.max(...(fi?.objetivos.map((o) => o.count) || [1]), 1)
    const maxCond = Math.max(...(fi?.condiciones.map((c) => c.count) || [1]), 1)

    const hasFilters = !!(
        dateFrom ||
        dateTo ||
        channel ||
        sessionStatus ||
        menuOpcion ||
        location ||
        paymentStatus
    )

    return (
        <div className="page-mobile p-4 sm:p-6 max-w-7xl mx-auto w-full min-w-0">
        {/* Header */}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-5">
            <div className="min-w-0">
            <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
                Reportería
            </h1>

            <p className="text-sm text-[#6b8a78] mt-0.5 flex flex-wrap items-center gap-2">
                <span>
                {data ? `${data.period.since} → ${data.period.until}` : 'Cargando...'}
                </span>

                {menuOpcion && (
                <span className="px-2 py-0.5 bg-[#e8f4f1] text-[#0b4c45] rounded-full text-xs font-semibold">
                    {SERVICIOS.find((s) => s.value === menuOpcion)?.label}
                </span>
                )}
            </p>
            </div>

            <div className="grid grid-cols-2 gap-2 w-full sm:w-auto">
            <button
                onClick={() => download('excel')}
                disabled={!!downloading || loading}
                className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50"
                style={{ background: '#1D9E75' }}
            >
                {downloading === 'excel' ? '⏳' : '📊'} Excel
            </button>

            <button
                onClick={() => download('pdf')}
                disabled={!!downloading || loading}
                className="flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold text-white disabled:opacity-50"
                style={{ background: '#E24B4A' }}
            >
                {downloading === 'pdf' ? '⏳' : '📄'} PDF
            </button>
            </div>
        </div>

        {/* Filtros */}
        <div className="bg-white rounded-2xl border border-[#e5ddd4] p-4 mb-5">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8 gap-3 items-end">
            <div className="min-w-0">
                <div className="text-xs font-semibold text-[#7a6a55] mb-1">
                Período rápido
                </div>

                <div className="grid grid-cols-3 gap-1">
                {[7, 30, 90].map((d) => (
                    <button
                    key={d}
                    onClick={() => {
                        setDays(d)
                        setDateFrom('')
                        setDateTo('')
                    }}
                    className="px-3 py-2 rounded-lg text-xs font-semibold transition-all"
                    style={
                        days === d && !dateFrom
                        ? { background: '#0b4c45', color: 'white' }
                        : { background: '#F5F1EB', color: '#7a6a55' }
                    }
                    >
                    {d}d
                    </button>
                ))}
                </div>
            </div>

            <div className="min-w-0">
                <div className="text-xs font-semibold text-[#7a6a55] mb-1">
                Desde
                </div>
                <input
                type="date"
                className="input text-xs py-2 w-full"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                />
            </div>

            <div className="min-w-0">
                <div className="text-xs font-semibold text-[#7a6a55] mb-1">
                Hasta
                </div>
                <input
                type="date"
                className="input text-xs py-2 w-full"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                />
            </div>

            <div className="min-w-0 sm:col-span-2 lg:col-span-1">
                <div className="text-xs font-semibold text-[#7a6a55] mb-1">
                Servicio del menú
                </div>
                <select
                className="input text-xs py-2 w-full"
                value={menuOpcion}
                onChange={(e) => setMenuOpcion(e.target.value)}
                >
                {SERVICIOS.map((servicio) => (
                    <option key={servicio.value} value={servicio.value}>
                    {servicio.label}
                    </option>
                ))}
                </select>
            </div>

            <div className="min-w-0">
                <div className="text-xs font-semibold text-[#7a6a55] mb-1">
                Canal
                </div>
                <select
                className="input text-xs py-2 w-full"
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                >
                <option value="">Todos</option>
                <option value="whatsapp">WhatsApp</option>
                <option value="instagram">Instagram</option>
                <option value="web">Web</option>
                </select>
            </div>

            <div className="min-w-0">
                <div className="text-xs font-semibold text-[#7a6a55] mb-1">
                Estado sesión
                </div>
                <select
                className="input text-xs py-2 w-full"
                value={sessionStatus}
                onChange={(e) => setSessStatus(e.target.value)}
                >
                <option value="">Todos</option>
                <option value="active">Activa</option>
                <option value="in_agent">Con agente</option>
                <option value="completed">Completada</option>
                <option value="closed">Cerrada</option>
                </select>
            </div>

            <div className="min-w-0">
                <div className="text-xs font-semibold text-[#7a6a55] mb-1">
                Ubicación
                </div>
                <select
                className="input text-xs py-2 w-full"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                >
                <option value="">Todas</option>
                <option value="arecibo">Arecibo</option>
                <option value="bayamon">Bayamón</option>
                <option value="latam">LATAM</option>
                </select>
            </div>

            <div className="min-w-0">
                <div className="text-xs font-semibold text-[#7a6a55] mb-1">
                Estado pago
                </div>
                <select
                className="input text-xs py-2 w-full"
                value={paymentStatus}
                onChange={(e) => setPayStatus(e.target.value)}
                >
                <option value="">Todos</option>
                <option value="link_sent">Link enviado</option>
                <option value="proof_received">Comprobante</option>
                <option value="verified">Verificado</option>
                <option value="rejected">Rechazado</option>
                </select>
            </div>

            {hasFilters && (
                <button
                onClick={() => {
                    setDateFrom('')
                    setDateTo('')
                    setChannel('')
                    setSessStatus('')
                    setMenuOpcion('')
                    setLocation('')
                    setPayStatus('')
                }}
                className="text-xs font-semibold text-[#E24B4A] border border-[#E24B4A] px-3 py-2 rounded-lg hover:bg-red-50 transition-all w-full"
                >
                ✕ Limpiar
                </button>
            )}
            </div>
        </div>

        {loading ? (
            <div className="flex justify-center py-20">
            <svg
                className="animate-spin w-8 h-8 text-[#0b4c45]"
                viewBox="0 0 24 24"
                fill="none"
            >
                <circle
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="3"
                strokeOpacity=".2"
                />
                <path
                d="M12 2a10 10 0 0 1 10 10"
                stroke="currentColor"
                strokeWidth="3"
                strokeLinecap="round"
                />
            </svg>
            </div>
        ) : data ? (
            <div className="space-y-5 min-w-0">
            {/* KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {[
                {
                    l: 'Conversaciones',
                    v: data.conversations.total,
                    s: `${data.conversations.unique_users} únicos`,
                },
                {
                    l: 'Completadas',
                    v: `${data.conversations.pct_completed}%`,
                    s: `${data.conversations.completed} sesiones`,
                },
                {
                    l: 'Escaladas',
                    v: data.agents.escalated,
                    s: `${data.agents.pct_escalated}% del total`,
                },
                {
                    l: 'Ingresos USD',
                    v: `$${data.sales.total_revenue_usd.toFixed(2)}`,
                    s: 'pagos verificados',
                },
                ].map((kpi) => (
                <div
                    key={kpi.l}
                    className="bg-white rounded-2xl border border-[#e5ddd4] p-4 min-w-0"
                >
                    <div className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-2 truncate">
                    {kpi.l}
                    </div>

                    <div className="font-display text-2xl sm:text-3xl font-bold text-[#0b4c45] break-words">
                    {kpi.v}
                    </div>

                    <div className="text-xs text-[#7a6a55] mt-1 truncate">
                    {kpi.s}
                    </div>
                </div>
                ))}
            </div>

            {/* SECCIÓN: FLUJO CONVERSACIONAL */}
            {fi && (
                <>
                {/* Temperatura de leads + tipo cliente */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <Card icon="🌡️" title="Temperatura de leads">
                    <div className="space-y-2">
                        {(['caliente', 'templado', 'frio'] as const).map((t) => {
                        const cfg = {
                            caliente: { e: '🔥', c: '#E24B4A', bg: '#FEF2F2' },
                            templado: { e: '🌤️', c: '#EF9F27', bg: '#FFFBEB' },
                            frio: { e: '❄️', c: '#3b82f6', bg: '#EFF6FF' },
                        }[t]

                        const d2 = fi.lead_temperature[t] || { count: 0, pct: 0 }

                        return (
                            <div
                            key={t}
                            className="flex items-center gap-3 p-2.5 rounded-xl"
                            style={{ background: cfg.bg }}
                            >
                            <span className="text-xl flex-shrink-0">
                                {cfg.e}
                            </span>

                            <div className="flex-1 min-w-0">
                                <div className="text-xs text-[#7a6a55] capitalize">
                                {t}
                                </div>

                                <div
                                className="font-bold text-base"
                                style={{ color: cfg.c }}
                                >
                                {d2.count}
                                </div>
                            </div>

                            <span
                                className="font-bold text-sm flex-shrink-0"
                                style={{ color: cfg.c }}
                            >
                                {d2.pct}%
                            </span>
                            </div>
                        )
                        })}
                    </div>
                    </Card>

                    <Card icon="👤" title="Tipo de cliente">
                    <div className="space-y-2 mb-3">
                        {(() => {
                        const total = Object.values(fi.tipo_cliente).reduce(
                            (a, b) => a + b,
                            0
                        )

                        const lbl: Record<string, string> = {
                            nuevo: '👤 Nuevo',
                            recompra: '🔄 Recompra',
                        }

                        const col: Record<string, string> = {
                            nuevo: '#0b4c45',
                            recompra: '#C6A96B',
                        }

                        return Object.entries(fi.tipo_cliente).map(([tipo, cnt]) => (
                            <Bar2
                            key={tipo}
                            label={lbl[tipo] || tipo}
                            value={cnt}
                            max={total}
                            color={col[tipo] || '#7a6a55'}
                            />
                        ))
                        })()}

                        {Object.keys(fi.tipo_cliente).length === 0 && (
                        <p className="text-sm text-[#6b8a78] text-center py-2">
                            Sin datos
                        </p>
                        )}
                    </div>

                    <KpiRow
                        label="Pacientes nuevos"
                        value={data.patients.new_this_period}
                    />

                    <KpiRow
                        label="Total recurrentes"
                        value={data.patients.total_recurrent}
                        hl
                    />
                    </Card>
                </div>

                {/* Ranking de servicios */}
                <Card icon="🏆" title="Ranking de servicios — consultas y conversión">
                    {fi.servicios_ranking.length === 0 ? (
                    <p className="text-sm text-[#6b8a78] text-center py-6">
                        Sin datos en este período
                    </p>
                    ) : (
                    <div className="overflow-x-auto mobile-scroll-x">
                        <table className="w-full min-w-[760px] text-sm">
                        <thead>
                            <tr className="border-b border-[#e5ddd4]">
                            {['#', 'Servicio', 'Consultas', 'Convertidos', '% Conv.', 'Volumen'].map(
                                (header) => (
                                <th
                                    key={header}
                                    className="text-left py-2 px-2 text-xs font-semibold text-[#7a6a55] uppercase whitespace-nowrap"
                                >
                                    {header}
                                </th>
                                )
                            )}
                            </tr>
                        </thead>

                        <tbody>
                            {fi.servicios_ranking.map((svc, i) => {
                            const pct = svc.pct_conversion
                            const bc =
                                pct >= 50
                                ? '#1D9E75'
                                : pct >= 25
                                    ? '#EF9F27'
                                    : '#E24B4A'

                            return (
                                <tr
                                key={svc.opcion}
                                className={`border-b border-[#f5f1eb] ${
                                    i % 2 === 0 ? 'bg-[#fafaf8]' : ''
                                }`}
                                >
                                <td className="py-2 px-2 whitespace-nowrap">
                                    <span
                                    className="w-5 h-5 rounded-full inline-flex items-center justify-center text-xs font-bold text-white"
                                    style={{ background: '#0b4c45' }}
                                    >
                                    {i + 1}
                                    </span>
                                </td>

                                <td className="py-2 px-2 text-sm font-medium text-[#1a1208] min-w-[240px]">
                                    {svc.servicio}
                                </td>

                                <td className="py-2 px-2 text-center font-bold text-[#0b4c45] whitespace-nowrap">
                                    {svc.total}
                                </td>

                                <td className="py-2 px-2 text-center font-bold text-[#1D9E75] whitespace-nowrap">
                                    {svc.convertidos}
                                </td>

                                <td className="py-2 px-2 text-center whitespace-nowrap">
                                    <span
                                    className="px-2 py-0.5 rounded-full text-xs font-bold"
                                    style={{
                                        background: bc + '20',
                                        color: bc,
                                    }}
                                    >
                                    {pct}%
                                    </span>
                                </td>

                                <td className="py-2 px-2">
                                    <div className="w-24 h-1.5 rounded-full bg-[#F5F1EB] ml-auto overflow-hidden">
                                    <div
                                        className="h-full rounded-full"
                                        style={{
                                        width: `${Math.round((svc.total / maxSvc) * 100)}%`,
                                        background: '#0b4c45',
                                        }}
                                    />
                                    </div>
                                </td>
                                </tr>
                            )
                            })}
                        </tbody>
                        </table>
                    </div>
                    )}
                </Card>

                {/* Abandono + tipos entrega */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <Card icon="📍" title="Dónde están los clientes en el flujo">
                    {Object.keys(fi.abandono_por_paso).length === 0 ? (
                        <p className="text-sm text-[#6b8a78] text-center py-4">
                        Sin datos
                        </p>
                    ) : (
                        Object.entries(fi.abandono_por_paso).map(([paso, cnt]) => (
                        <Bar2
                            key={paso}
                            label={paso}
                            value={cnt}
                            max={maxStep}
                            color="#0b4c45"
                        />
                        ))
                    )}
                    </Card>

                    <Card icon="🚚" title="Tipo de entrega preferido">
                    {Object.keys(fi.tipos_entrega).length === 0 ? (
                        <p className="text-sm text-[#6b8a78] text-center py-4">
                        Sin datos
                        </p>
                    ) : (
                        (() => {
                        const maxE = Math.max(...Object.values(fi.tipos_entrega), 1)

                        const cols: Record<string, string> = {
                            '🚚 Entrega a domicilio': '#0b4c45',
                            '🏥 Recoger en clínica': '#C6A96B',
                            '💉 Cita en clínica': '#3b82f6',
                        }

                        return Object.entries(fi.tipos_entrega).map(([tipo, cnt]) => (
                            <Bar2
                            key={tipo}
                            label={tipo}
                            value={cnt}
                            max={maxE}
                            color={cols[tipo] || '#7a6a55'}
                            />
                        ))
                        })()
                    )}
                    </Card>
                </div>

                {/* Perfil del cliente */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <Card icon="🎯" title="Objetivos principales">
                    {fi.objetivos.length === 0 ? (
                        <p className="text-sm text-[#6b8a78] text-center py-4">
                        Sin datos
                        </p>
                    ) : (
                        fi.objetivos.map((objetivo, i) => {
                        const colors = [
                            '#0b4c45',
                            '#1D9E75',
                            '#C6A96B',
                            '#3b82f6',
                            '#7c3aed',
                        ]

                        return (
                            <Bar2
                            key={objetivo.objetivo}
                            label={objetivo.objetivo}
                            value={objetivo.count}
                            max={maxObj}
                            color={colors[i % colors.length]}
                            />
                        )
                        })
                    )}
                    </Card>

                    <Card icon="🏥" title="Condiciones médicas mencionadas">
                    {fi.condiciones.length === 0 ? (
                        <p className="text-sm text-[#6b8a78] text-center py-4">
                        Sin condiciones reportadas
                        </p>
                    ) : (
                        fi.condiciones.map((condicion) => (
                        <Bar2
                            key={condicion.condicion}
                            label={condicion.condicion}
                            value={condicion.count}
                            max={maxCond}
                            color="#E24B4A"
                        />
                        ))
                    )}
                    </Card>
                </div>

                {/* Horarios pico */}
                {fi.horarios_pico.length > 0 && (
                    <Card icon="⏰" title="Horarios de mayor actividad">
                    <div className="h-[220px] sm:h-[260px] w-full min-w-0">
                        <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            data={fi.horarios_pico}
                            margin={{ top: 8, right: 8, bottom: 0, left: -20 }}
                        >
                            <XAxis
                            dataKey="hora"
                            tick={{ fontSize: 11, fill: '#7a6a55' }}
                            tickLine={false}
                            axisLine={false}
                            />

                            <YAxis
                            tick={{ fontSize: 10, fill: '#7a6a55' }}
                            tickLine={false}
                            axisLine={false}
                            />

                            <Tooltip
                            contentStyle={{
                                borderRadius: 10,
                                border: '1px solid #e5ddd4',
                                fontSize: 12,
                            }}
                            />

                            <Bar
                            dataKey="conversaciones"
                            name="Conv."
                            radius={[4, 4, 0, 0]}
                            >
                            {fi.horarios_pico.map((_, i) => (
                                <Cell
                                key={i}
                                fill={i === 0 ? '#C6A96B' : '#0b4c45'}
                                />
                            ))}
                            </Bar>
                        </BarChart>
                        </ResponsiveContainer>
                    </div>
                    </Card>
                )}
                </>
            )}

            {/* SECCIÓN: AGENTES */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card icon="🎧" title="Paso a asesor humano">
                <KpiRow label="Total escaladas" value={data.agents.escalated} hl />
                <KpiRow label="% del total" value={`${data.agents.pct_escalated}%`} />

                {data.agents.by_agent.map((agentItem, i) => (
                    <KpiRow
                    key={agentItem.name}
                    label={`→ ${agentItem.name}`}
                    value={agentItem.count}
                    hl={i % 2 === 0}
                    />
                ))}

                {data.agents.by_agent.length === 0 && (
                    <p className="text-sm text-[#6b8a78] text-center py-3">
                    Sin escaladas
                    </p>
                )}
                </Card>

                <Card icon="⭐" title="Satisfacción por agente">
                {Object.keys(data.agents.satisfaction || {}).length === 0 ? (
                    <p className="text-sm text-[#6b8a78] text-center py-4">
                    Sin encuestas en este período
                    </p>
                ) : (
                    Object.entries(data.agents.satisfaction).map(([nombre, sat]) => (
                    <div
                        key={nombre}
                        className="flex items-center justify-between gap-3 py-2 border-b border-[#f5f1eb] last:border-0 min-w-0"
                    >
                        <span className="text-sm text-[#1a1208] truncate min-w-0">
                        {nombre}
                        </span>

                        <div className="text-right flex-shrink-0">
                        <span className="font-bold text-[#C6A96B]">
                            {'⭐'.repeat(Math.round(sat.avg))} {sat.avg}
                        </span>

                        <span className="text-xs text-[#7a6a55] ml-1">
                            ({sat.total})
                        </span>
                        </div>
                    </div>
                    ))
                )}
                </Card>
            </div>

            {/* SECCIÓN: VENTAS Y CITAS */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card icon="📅" title="Citas y ventas">
                <KpiRow
                    label="Citas solicitadas"
                    value={data.appointments.total_requested}
                />
                <KpiRow
                    label="Citas confirmadas"
                    value={data.appointments.confirmed}
                    hl
                />
                <KpiRow
                    label="% Conversión"
                    value={`${data.appointments.conversion_pct}%`}
                />
                <KpiRow
                    label="Pagos verificados"
                    value={data.sales.verified_payments}
                    hl
                />
                <KpiRow
                    label="Ingresos (USD)"
                    value={`$${data.sales.total_revenue_usd.toFixed(2)}`}
                />

                {Object.entries(data.sales.payment_methods).map(([method, count]) => (
                    <KpiRow
                    key={method}
                    label={`→ ${method}`}
                    value={`${count} pagos`}
                    />
                ))}
                </Card>

                <Card icon="🏆" title="Top servicios confirmados">
                {data.appointments.top_services.length === 0 ? (
                    <p className="text-sm text-[#6b8a78] text-center py-4">
                    Sin citas en este período
                    </p>
                ) : (
                    data.appointments.top_services.map((service, i) => (
                    <div
                        key={service.service}
                        className={`flex items-center gap-2 py-2 border-b border-[#f5f1eb] last:border-0 min-w-0 ${
                        i % 2 === 0 ? 'bg-[#fafaf8] rounded-lg px-1' : ''
                        }`}
                    >
                        <span
                        className="w-5 h-5 rounded-full inline-flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                        style={{ background: '#0b4c45' }}
                        >
                        {i + 1}
                        </span>

                        <span className="text-sm text-[#1a1208] flex-1 truncate min-w-0">
                        {service.service}
                        </span>

                        <span className="text-sm font-bold text-[#0b4c45] flex-shrink-0">
                        {service.count}
                        </span>
                    </div>
                    ))
                )}
                </Card>
            </div>

            {/* SECCIÓN: RENTABILIDAD */}
            <Card icon="💰" title="Rentabilidad del canal" color="#7c3aed">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                    {
                    l: 'Ingresos (USD)',
                    v: `$${data.sales.total_revenue_usd.toFixed(2)}`,
                    c: '#0b4c45',
                    },
                    {
                    l: 'Ingreso bruto COP',
                    v: fmtCOP(data.sales.total_revenue_cop),
                    c: '#0b4c45',
                    },
                    {
                    l: 'Costo real COP',
                    v: fmtCOP(data.sales.total_cost_cop),
                    c: '#E24B4A',
                    },
                    {
                    l: 'Ganancia neta COP',
                    v: fmtCOP(data.sales.net_profit_cop),
                    c: '#1D9E75',
                    },
                ].map((metric) => (
                    <div
                    key={metric.l}
                    className="bg-purple-50 border border-purple-200 rounded-xl p-3 text-center min-w-0"
                    >
                    <div className="text-xs text-[#7a6a55] mb-1 truncate">
                        {metric.l}
                    </div>

                    <div
                        className="font-bold text-sm break-words"
                        style={{ color: metric.c }}
                    >
                        {metric.v}
                    </div>
                    </div>
                ))}
                </div>

                <div className="mt-2 text-center text-xs text-[#7a6a55]">
                Margen:{' '}
                <span className="font-bold text-[#1D9E75]">
                    {data.sales.margin_pct}%
                </span>
                </div>
            </Card>

            {/* SECCIÓN: INSIGHTS */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <Card icon="🔎" title="Intereses más buscados">
                {data.insights.top_interests.length === 0 ? (
                    <p className="text-sm text-[#6b8a78] text-center py-4">
                    Sin datos
                    </p>
                ) : (
                    data.insights.top_interests.map((interest, i) => (
                    <KpiRow
                        key={interest.interest + i}
                        label={interest.interest}
                        value={interest.count}
                        hl={i % 2 === 0}
                    />
                    ))
                )}
                </Card>

                <Card icon="📉" title="Productos con baja conversión">
                {data.insights.top_unconverted_products.length === 0 ? (
                    <p className="text-sm text-[#6b8a78] text-center py-4">
                    Sin datos
                    </p>
                ) : (
                    data.insights.top_unconverted_products.map((product, i) => (
                    <KpiRow
                        key={product.product + i}
                        label={product.product}
                        value={product.attempts}
                        hl={i % 2 === 0}
                    />
                    ))
                )}
                </Card>
            </div>

            {/* Distribución de estados */}
            <Card icon="📊" title="Distribución de estados de conversación">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {Object.entries(data.conversations.status_distribution).map(
                    ([status, count]) => {
                    const pct =
                        data.conversations.total > 0
                        ? Math.round((count / data.conversations.total) * 100)
                        : 0

                    const cols: Record<string, string> = {
                        active: '#0b4c45',
                        in_agent: '#3b82f6',
                        completed: '#1D9E75',
                        closed: '#7a6a55',
                    }

                    return (
                        <div
                        key={status}
                        className="bg-[#F5F1EB] rounded-xl p-3 text-center min-w-0"
                        >
                        <div className="text-xs text-[#7a6a55] mb-1 truncate">
                            {STATUS_LABELS[status] || status}
                        </div>

                        <div
                            className="font-bold text-xl"
                            style={{ color: cols[status] || '#7a6a55' }}
                        >
                            {count}
                        </div>

                        <div className="text-xs text-[#7a6a55]">
                            {pct}%
                        </div>
                        </div>
                    )
                    }
                )}
                </div>
            </Card>
            </div>
        ) : (
            <div className="text-center py-16 text-[#6b8a78]">
            Error cargando reporte.
            </div>
        )}
        </div>
    )
}