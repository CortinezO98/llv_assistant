import { useEffect, useState } from 'react'
import { api } from '../api/client'

interface ReportData {
    period: { since: string; until: string }
    conversations: { total: number; unique_users: number; completed: number; pct_completed: number; status_distribution: Record<string, number> }
    agents: { escalated: number; pct_escalated: number; by_agent: { name: string; count: number }[] }
    appointments: { total_requested: number; confirmed: number; conversion_pct: number; top_services: { service: string; count: number }[] }
    sales: { verified_payments: number; total_revenue_usd: number; payment_methods: Record<string, number> }
    channels: Record<string, number>
    satisfaction: { note: string }
    patients: { new_this_period: number; total_recurrent: number }
}

const statusLabels: Record<string, string> = {
    active: 'Activas', in_agent: 'Con agente', completed: 'Completadas', closed: 'Cerradas'
}

function KpiRow({ label, value, highlight = false }: { label: string; value: string | number; highlight?: boolean }) {
    return (
        <div className={`flex justify-between items-center py-2.5 px-4 border-b border-[#e4ede8] last:border-0 ${highlight ? 'bg-brand-50' : ''}`}>
        <span className="text-sm text-[#6b8a78]">{label}</span>
        <span className={`text-sm font-bold ${highlight ? 'text-brand-700' : 'text-brand-800'}`}>{value}</span>
        </div>
    )
}

function Section({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
    return (
        <div className="card overflow-hidden animate-fade-in">
        <div className="flex items-center gap-2 px-4 py-3 bg-brand-600">
            <span>{icon}</span>
            <span className="text-sm font-bold text-white uppercase tracking-wide">{title}</span>
        </div>
        <div>{children}</div>
        </div>
    )
}

export default function ReportsPage() {
    const [data, setData] = useState<ReportData | null>(null)
    const [loading, setLoading] = useState(true)
    const [days, setDays] = useState(30)
    const [downloading, setDownloading] = useState<'excel' | 'pdf' | null>(null)

    useEffect(() => {
        setLoading(true)
        api.get(`/reports/summary?days=${days}`)
        .then(r => setData(r.data))
        .finally(() => setLoading(false))
    }, [days])

    const download = async (format: 'excel' | 'pdf') => {
        setDownloading(format)
        try {
        const res = await api.get(`/reports/export/${format}?days=${days}`, { responseType: 'blob' })
        const ext = format === 'excel' ? 'xlsx' : 'pdf'
        const url = URL.createObjectURL(res.data)
        const a = document.createElement('a')
        a.href = url
        a.download = `LLV_Reporte_${days}dias.${ext}`
        a.click()
        URL.revokeObjectURL(url)
        } finally {
        setDownloading(null)
        }
    }

    return (
        <div className="p-6 max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
            <div>
            <h1 className="font-display text-2xl font-bold text-brand-800">Reportería</h1>
            <p className="text-sm text-[#6b8a78] mt-0.5">
                {data ? `Período: ${data.period.since} → ${data.period.until}` : 'Cargando período...'}
            </p>
            </div>
            <div className="flex items-center gap-3">
            {/* Período */}
            <div className="flex gap-1.5">
                {[7, 30, 90].map(d => (
                <button key={d} onClick={() => setDays(d)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${days === d ? 'bg-brand-600 text-white' : 'bg-white border border-[#e4ede8] text-[#6b8a78] hover:border-brand-400'}`}>
                    {d}d
                </button>
                ))}
            </div>
            {/* Exportar */}
            <button onClick={() => download('excel')} disabled={!!downloading || loading}
                className="btn-primary gap-2">
                {downloading === 'excel' ? (
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".3"/>
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
                </svg>
                ) : <span>📊</span>}
                Excel
            </button>
            <button onClick={() => download('pdf')} disabled={!!downloading || loading}
                className="btn-primary gap-2 bg-rose-600 hover:bg-rose-700">
                {downloading === 'pdf' ? (
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".3"/>
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
                </svg>
                ) : <span>📄</span>}
                PDF
            </button>
            </div>
        </div>

        {loading ? (
            <div className="flex items-center justify-center h-64">
            <svg className="animate-spin w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".2"/>
                <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
            </svg>
            </div>
        ) : data ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 stagger">

            {/* 1. Conversaciones */}
            <Section title="1. Conversaciones e Usuarios" icon="💬">
                <KpiRow label="Total conversaciones" value={data.conversations.total} highlight />
                <KpiRow label="Usuarios únicos" value={data.conversations.unique_users} />
                <KpiRow label="Completadas" value={data.conversations.completed} />
                <KpiRow label="% Completadas" value={`${data.conversations.pct_completed}%`} highlight />
            </Section>

            {/* 2. Puntos de abandono */}
            <Section title="2. Puntos de Abandono" icon="📍">
                {Object.entries(data.conversations.status_distribution).map(([s, c], i) => (
                <KpiRow key={s} label={statusLabels[s] || s} value={c} highlight={i % 2 === 0} />
                ))}
                {Object.keys(data.conversations.status_distribution).length === 0 && (
                <div className="px-4 py-6 text-center text-sm text-[#6b8a78]">Sin datos</div>
                )}
            </Section>

            {/* 3. Paso a agente */}
            <Section title="3. Paso a Asesor Humano" icon="🎧">
                <KpiRow label="Total escaladas" value={data.agents.escalated} highlight />
                <KpiRow label="% del total" value={`${data.agents.pct_escalated}%`} />
                {data.agents.by_agent.map((a, i) => (
                <KpiRow key={a.name} label={`→ ${a.name}`} value={a.count} highlight={i % 2 === 0} />
                ))}
                {data.agents.by_agent.length === 0 && (
                <div className="px-4 py-4 text-center text-sm text-[#6b8a78]">Sin escaladas en este período</div>
                )}
            </Section>

            {/* 4. Citas y ventas */}
            <Section title="4. Conversión a Citas y Ventas" icon="📅">
                <KpiRow label="Citas solicitadas" value={data.appointments.total_requested} />
                <KpiRow label="Citas confirmadas" value={data.appointments.confirmed} highlight />
                <KpiRow label="% Conversión" value={`${data.appointments.conversion_pct}%`} />
                <KpiRow label="Ventas verificadas" value={data.sales.verified_payments} highlight />
            </Section>

            {/* 5. Ingresos */}
            <Section title="5. Ingresos del Canal" icon="💰">
                <KpiRow label="Total ingresos (USD)" value={`$${data.sales.total_revenue_usd.toFixed(2)}`} highlight />
                {Object.entries(data.sales.payment_methods).map(([m, c], i) => (
                <KpiRow key={m} label={`→ ${m}`} value={`${c} pagos`} highlight={i % 2 === 0} />
                ))}
                {Object.keys(data.sales.payment_methods).length === 0 && (
                <div className="px-4 py-4 text-center text-sm text-[#6b8a78]">Sin pagos registrados</div>
                )}
            </Section>

            {/* 6. Canales */}
            <Section title="6. Canales de Entrada" icon="📱">
                {Object.entries(data.channels).map(([ch, n], i) => (
                <KpiRow key={ch} label={ch.charAt(0).toUpperCase() + ch.slice(1)} value={n} highlight={i % 2 === 0} />
                ))}
                {Object.keys(data.channels).length === 0 && (
                <KpiRow label="WhatsApp" value={data.conversations.total} highlight />
                )}
            </Section>

            {/* 7. Satisfacción */}
            <Section title="7. Satisfacción / Feedback" icon="⭐">
                <div className="px-4 py-5 text-center">
                <div className="text-3xl mb-2">📋</div>
                <p className="text-sm text-[#6b8a78]">{data.satisfaction.note}</p>
                </div>
            </Section>

            {/* 8. Pacientes */}
            <Section title="8. Pacientes Nuevos y Recurrentes" icon="👤">
                <KpiRow label="Nuevos este período" value={data.patients.new_this_period} highlight />
                <KpiRow label="Total recurrentes" value={data.patients.total_recurrent} />
            </Section>

            {/* Top servicios — full width */}
            <div className="md:col-span-2">
                <Section title="Top Servicios más Solicitados" icon="🏆">
                {data.appointments.top_services.length === 0 ? (
                    <div className="px-4 py-6 text-center text-sm text-[#6b8a78]">Sin citas registradas en este período</div>
                ) : (
                    <div className="divide-y divide-[#e4ede8]">
                    {data.appointments.top_services.map((s, i) => (
                        <div key={s.service} className={`flex items-center justify-between px-4 py-3 ${i % 2 === 0 ? 'bg-brand-50' : ''}`}>
                        <div className="flex items-center gap-3">
                            <span className="w-6 h-6 rounded-full bg-brand-600 text-white text-xs font-bold flex items-center justify-center">{i + 1}</span>
                            <span className="text-sm text-brand-800">{s.service}</span>
                        </div>
                        <span className="text-sm font-bold text-brand-700">{s.count} solicitudes</span>
                        </div>
                    ))}
                    </div>
                )}
                </Section>
            </div>

            </div>
        ) : (
            <div className="text-center py-16 text-[#6b8a78]">Error cargando reporte.</div>
        )}
        </div>
    )
}
