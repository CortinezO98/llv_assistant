import { useEffect, useState } from 'react'
import { api } from '../api/client'

// ── Types ──────────────────────────────────────────────────────────────────────
interface Delivery {
    id: number; patient_name: string; phone: string
    service_treatment: string; amount_to_pay: number | null
    delivery_town: string; assigned_carrier: string | null
    delivery_date: string | null; status: string; notes: string | null
    created_at: string
}
interface Shipment {
    id: number; patient_name: string; phone: string; email: string | null
    postal_address: string; city: string | null; state_province: string | null
    country: string; zip_code: string | null; service_treatment: string
    amount_paid: number | null; shipment_date: string | null
    tracking_number: string | null; carrier: string | null
    status: string; notes: string | null; created_at: string
}

const deliveryStatusColors: Record<string, string> = {
    pending:    'bg-amber-100 text-amber-700',
    assigned:   'bg-blue-100 text-blue-700',
    in_transit: 'bg-purple-100 text-purple-700',
    delivered:  'bg-teal-100 text-teal-700',
    cancelled:  'bg-red-100 text-red-600',
}
const deliveryStatusLabels: Record<string, string> = {
    pending: 'Pendiente', assigned: 'Asignado', in_transit: 'En camino',
    delivered: 'Entregado', cancelled: 'Cancelado',
}
const shipmentStatusColors: Record<string, string> = {
    pending:    'bg-amber-100 text-amber-700',
    processing: 'bg-blue-100 text-blue-700',
    shipped:    'bg-purple-100 text-purple-700',
    in_transit: 'bg-indigo-100 text-indigo-700',
    delivered:  'bg-teal-100 text-teal-700',
    returned:   'bg-red-100 text-red-600',
}
const shipmentStatusLabels: Record<string, string> = {
    pending: 'Pendiente', processing: 'Procesando', shipped: 'Despachado',
    in_transit: 'En tránsito', delivered: 'Entregado', returned: 'Devuelto',
}

// ── DELIVERY TABLE ─────────────────────────────────────────────────────────────
function DeliveryTable() {
    const [items, setItems]         = useState<Delivery[]>([])
    const [loading, setLoading]     = useState(true)
    const [filter, setFilter]       = useState('')
    const [editing, setEditing]     = useState<number | null>(null)
    const [editData, setEditData]   = useState<Record<string, string>>({})

    const load = () => {
        setLoading(true)
        api.get(`/deliveries/${filter ? `?status=${filter}` : ''}`)
        .then(r => setItems(r.data))
        .finally(() => setLoading(false))
    }
    useEffect(() => { load() }, [filter])

    const save = async (id: number) => {
        await api.patch(`/deliveries/${id}`, editData)
        setEditing(null)
        load()
    }

    return (
        <div>
        {/* Filtros */}
        <div className="flex gap-1.5 mb-4 flex-wrap">
            {['', 'pending', 'assigned', 'in_transit', 'delivered'].map(s => (
            <button key={s} onClick={() => setFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${filter === s ? 'bg-[#0b4c45] text-white' : 'bg-white border border-[#e5ddd4] text-[#7a6a55]'}`}>
                {s === '' ? 'Todas' : deliveryStatusLabels[s]}
            </button>
            ))}
        </div>

        <div className="card overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full">
                <thead>
                <tr className="border-b border-[#e5ddd4] bg-[#F5F1EB]/50">
                    {['Paciente', 'Teléfono', 'Tratamiento', 'Monto', 'Pueblo', 'Carrero', 'Fecha', 'Estado', 'Acción'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-[#7a6a55] uppercase tracking-wider whitespace-nowrap">{h}</th>
                    ))}
                </tr>
                </thead>
                <tbody>
                {loading ? (
                    <tr><td colSpan={9} className="text-center py-12 text-sm text-[#7a6a55]">Cargando...</td></tr>
                ) : items.length === 0 ? (
                    <tr><td colSpan={9} className="text-center py-12 text-sm text-[#7a6a55]">Sin entregas</td></tr>
                ) : items.map(d => (
                    <tr key={d.id} className="table-row">
                    <td className="px-4 py-3 text-sm font-semibold text-[#1a1208]">{d.patient_name}</td>
                    <td className="px-4 py-3 text-xs font-mono text-[#7a6a55]">{d.phone}</td>
                    <td className="px-4 py-3 text-xs text-[#0b4c45] max-w-[180px] truncate">{d.service_treatment}</td>
                    <td className="px-4 py-3 text-sm font-bold text-[#0b4c45]">{d.amount_to_pay ? `$${d.amount_to_pay}` : '—'}</td>
                    <td className="px-4 py-3 text-sm text-[#7a6a55]">{d.delivery_town}</td>
                    <td className="px-4 py-3">
                        {editing === d.id ? (
                        <input className="input text-xs w-28" value={editData.assigned_carrier || ''} onChange={e => setEditData({...editData, assigned_carrier: e.target.value})} placeholder="Nombre carrero" />
                        ) : (
                        <span className="text-xs text-[#7a6a55]">{d.assigned_carrier || '—'}</span>
                        )}
                    </td>
                    <td className="px-4 py-3">
                        {editing === d.id ? (
                        <input type="date" className="input text-xs w-32" value={editData.delivery_date || ''} onChange={e => setEditData({...editData, delivery_date: e.target.value})} />
                        ) : (
                        <span className="text-xs font-mono text-[#7a6a55]">{d.delivery_date || '—'}</span>
                        )}
                    </td>
                    <td className="px-4 py-3">
                        {editing === d.id ? (
                        <select className="input text-xs w-28" value={editData.status || d.status} onChange={e => setEditData({...editData, status: e.target.value})}>
                            {Object.entries(deliveryStatusLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                        </select>
                        ) : (
                        <span className={`badge ${deliveryStatusColors[d.status]}`}>{deliveryStatusLabels[d.status]}</span>
                        )}
                    </td>
                    <td className="px-4 py-3">
                        {editing === d.id ? (
                        <div className="flex gap-1">
                            <button onClick={() => save(d.id)} className="btn-primary py-1 px-2 text-xs">✓</button>
                            <button onClick={() => setEditing(null)} className="btn-ghost py-1 px-2 text-xs">✕</button>
                        </div>
                        ) : (
                        <button onClick={() => { setEditing(d.id); setEditData({ assigned_carrier: d.assigned_carrier || '', delivery_date: d.delivery_date || '', status: d.status }) }}
                            className="btn-ghost py-1 px-2 text-xs border border-[#e5ddd4]">
                            ✏️ Editar
                        </button>
                        )}
                    </td>
                    </tr>
                ))}
                </tbody>
            </table>
            </div>
        </div>
        </div>
    )
}

// ── SHIPMENT TABLE ─────────────────────────────────────────────────────────────
function ShipmentTable() {
    const [items, setItems]       = useState<Shipment[]>([])
    const [loading, setLoading]   = useState(true)
    const [filter, setFilter]     = useState('')
    const [editing, setEditing]   = useState<number | null>(null)
    const [editData, setEditData] = useState<Record<string, string>>({})

    const load = () => {
        setLoading(true)
        api.get(`/deliveries/shipments${filter ? `?status=${filter}` : ''}`)
        .then(r => setItems(r.data))
        .finally(() => setLoading(false))
    }
    useEffect(() => { load() }, [filter])

    const save = async (id: number) => {
        await api.patch(`/deliveries/shipments/${id}`, editData)
        setEditing(null)
        load()
    }

    return (
        <div>
        <div className="flex gap-1.5 mb-4 flex-wrap">
            {['', 'pending', 'processing', 'shipped', 'in_transit', 'delivered'].map(s => (
            <button key={s} onClick={() => setFilter(s)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${filter === s ? 'bg-[#0b4c45] text-white' : 'bg-white border border-[#e5ddd4] text-[#7a6a55]'}`}>
                {s === '' ? 'Todos' : shipmentStatusLabels[s]}
            </button>
            ))}
        </div>

        <div className="card overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full">
                <thead>
                <tr className="border-b border-[#e5ddd4] bg-[#F5F1EB]/50">
                    {['Paciente', 'Teléfono', 'Correo', 'Dirección', 'Tratamiento', 'Monto', 'Rastreo', 'Estado', 'Acción'].map(h => (
                    <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-[#7a6a55] uppercase tracking-wider whitespace-nowrap">{h}</th>
                    ))}
                </tr>
                </thead>
                <tbody>
                {loading ? (
                    <tr><td colSpan={9} className="text-center py-12 text-sm text-[#7a6a55]">Cargando...</td></tr>
                ) : items.length === 0 ? (
                    <tr><td colSpan={9} className="text-center py-12 text-sm text-[#7a6a55]">Sin envíos</td></tr>
                ) : items.map(s => (
                    <tr key={s.id} className="table-row">
                    <td className="px-4 py-3 text-sm font-semibold text-[#1a1208] whitespace-nowrap">{s.patient_name}</td>
                    <td className="px-4 py-3 text-xs font-mono text-[#7a6a55]">{s.phone}</td>
                    <td className="px-4 py-3 text-xs text-[#7a6a55] max-w-[120px] truncate">{s.email || '—'}</td>
                    <td className="px-4 py-3 text-xs text-[#7a6a55] max-w-[160px]">
                        <div className="truncate">{s.postal_address}</div>
                        {s.city && <div className="text-[10px] text-[#7a6a55]">{s.city}, {s.country}</div>}
                    </td>
                    <td className="px-4 py-3 text-xs text-[#0b4c45] max-w-[150px] truncate">{s.service_treatment}</td>
                    <td className="px-4 py-3 text-sm font-bold text-[#0b4c45]">{s.amount_paid ? `$${s.amount_paid}` : '—'}</td>
                    <td className="px-4 py-3">
                        {editing === s.id ? (
                        <input className="input text-xs w-28" value={editData.tracking_number || ''} onChange={e => setEditData({...editData, tracking_number: e.target.value})} placeholder="# Rastreo" />
                        ) : (
                        <span className={`text-xs font-mono ${s.tracking_number ? 'text-[#0b4c45] font-semibold' : 'text-[#7a6a55]'}`}>{s.tracking_number || '—'}</span>
                        )}
                    </td>
                    <td className="px-4 py-3">
                        {editing === s.id ? (
                        <select className="input text-xs w-28" value={editData.status || s.status} onChange={e => setEditData({...editData, status: e.target.value})}>
                            {Object.entries(shipmentStatusLabels).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                        </select>
                        ) : (
                        <span className={`badge ${shipmentStatusColors[s.status]}`}>{shipmentStatusLabels[s.status]}</span>
                        )}
                    </td>
                    <td className="px-4 py-3">
                        {editing === s.id ? (
                        <div className="flex gap-1">
                            <button onClick={() => save(s.id)} className="btn-primary py-1 px-2 text-xs">✓</button>
                            <button onClick={() => setEditing(null)} className="btn-ghost py-1 px-2 text-xs">✕</button>
                        </div>
                        ) : (
                        <button onClick={() => { setEditing(s.id); setEditData({ tracking_number: s.tracking_number || '', status: s.status }) }}
                            className="btn-ghost py-1 px-2 text-xs border border-[#e5ddd4]">
                            ✏️ Editar
                        </button>
                        )}
                    </td>
                    </tr>
                ))}
                </tbody>
            </table>
            </div>
        </div>
        </div>
    )
}

// ── PAGE ───────────────────────────────────────────────────────────────────────
export default function DeliveriesPage() {
    const [tab, setTab] = useState<'deliveries' | 'shipments'>('deliveries')

    return (
        <div className="p-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-6">
            <div>
            <h1 className="font-display text-2xl font-bold text-[#0b4c45]">Entregas y Envíos</h1>
            <p className="text-sm text-[#7a6a55] mt-0.5">Gestión de pedidos registrados por el bot</p>
            </div>
            {/* Tabs */}
            <div className="flex gap-1 bg-[#F5F1EB] p-1 rounded-xl">
            <button onClick={() => setTab('deliveries')}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${tab === 'deliveries' ? 'bg-[#0b4c45] text-white shadow-sm' : 'text-[#7a6a55] hover:text-[#0b4c45]'}`}>
                🛵 Entregas PR
            </button>
            <button onClick={() => setTab('shipments')}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${tab === 'shipments' ? 'bg-[#0b4c45] text-white shadow-sm' : 'text-[#7a6a55] hover:text-[#0b4c45]'}`}>
                📦 Envíos Postales
            </button>
            </div>
        </div>

        {tab === 'deliveries' ? <DeliveryTable /> : <ShipmentTable />}
        </div>
    )
}
