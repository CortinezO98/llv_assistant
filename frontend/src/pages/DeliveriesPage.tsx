import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

// ── Types ──────────────────────────────────────────────────────────────────────

interface Delivery {
    id: number
    patient_name: string
    phone: string
    service_treatment: string
    amount_to_pay: number | null
    delivery_town: string
    assigned_carrier: string | null
    delivery_date: string | null
    status: string
    notes: string | null
    created_at: string
}

interface Shipment {
    id: number
    patient_name: string
    phone: string
    email: string | null
    postal_address: string
    city: string | null
    state_province: string | null
    country: string
    zip_code: string | null
    service_treatment: string
    amount_paid: number | null
    shipment_date: string | null
    tracking_number: string | null
    carrier: string | null
    status: string
    notes: string | null
    created_at: string
}

// ── Status helpers ─────────────────────────────────────────────────────────────

const deliveryStatusColors: Record<string, string> = {
    pending: 'bg-amber-100 text-amber-700',
    assigned: 'bg-blue-100 text-blue-700',
    in_transit: 'bg-purple-100 text-purple-700',
    delivered: 'bg-teal-100 text-teal-700',
    cancelled: 'bg-red-100 text-red-600',
}

const deliveryStatusLabels: Record<string, string> = {
    pending: 'Pendiente',
    assigned: 'Asignado',
    in_transit: 'En camino',
    delivered: 'Entregado',
    cancelled: 'Cancelado',
}

const shipmentStatusColors: Record<string, string> = {
    pending: 'bg-amber-100 text-amber-700',
    processing: 'bg-blue-100 text-blue-700',
    shipped: 'bg-purple-100 text-purple-700',
    in_transit: 'bg-indigo-100 text-indigo-700',
    delivered: 'bg-teal-100 text-teal-700',
    returned: 'bg-red-100 text-red-600',
}

const shipmentStatusLabels: Record<string, string> = {
    pending: 'Pendiente',
    processing: 'Procesando',
    shipped: 'Despachado',
    in_transit: 'En tránsito',
    delivered: 'Entregado',
    returned: 'Devuelto',
}

// ── DELIVERY TABLE ─────────────────────────────────────────────────────────────

function DeliveryTable() {
    const [items, setItems] = useState<Delivery[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState('')
    const [search, setSearch] = useState('')
    const [editing, setEditing] = useState<number | null>(null)
    const [editData, setEditData] = useState<Record<string, string>>({})

    const load = () => {
        setLoading(true)

        api
        .get(`/deliveries/${filter ? `?status=${filter}` : ''}`)
        .then((response) => setItems(response.data))
        .finally(() => setLoading(false))
    }

    useEffect(() => {
        load()
    }, [filter])

    const filteredItems = useMemo(() => {
        const term = search.toLowerCase().trim()

        if (!term) return items

        return items.filter((item) =>
        [
            item.patient_name,
            item.phone,
            item.service_treatment,
            item.delivery_town,
            item.assigned_carrier || '',
            item.notes || '',
            item.status,
        ]
            .join(' ')
            .toLowerCase()
            .includes(term)
        )
    }, [items, search])

    const save = async (id: number) => {
        await api.patch(`/deliveries/${id}`, editData)

        setEditing(null)
        setEditData({})
        load()
    }

    return (
        <div>
        <div className="card p-4 mb-5">
            <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-3">
            <select
                className="input"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
            >
                <option value="">Todas las entregas</option>
                {Object.entries(deliveryStatusLabels).map(([value, label]) => (
                <option key={value} value={value}>
                    {label}
                </option>
                ))}
            </select>

            <input
                className="input"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por cliente, teléfono, tratamiento, pueblo, carrero o nota..."
            />
            </div>
        </div>

        <div className="card overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full min-w-[1000px]">
                <thead>
                <tr className="border-b border-[#e5ddd4] bg-[#F5F1EB]/50">
                    {[
                    'Paciente',
                    'Teléfono',
                    'Tratamiento',
                    'Monto',
                    'Pueblo',
                    'Carrero',
                    'Fecha',
                    'Estado',
                    'Acción',
                    ].map((header) => (
                    <th
                        key={header}
                        className="text-left px-4 py-3 text-xs font-semibold text-[#7a6a55] uppercase tracking-wider whitespace-nowrap"
                    >
                        {header}
                    </th>
                    ))}
                </tr>
                </thead>

                <tbody>
                {loading ? (
                    <tr>
                    <td colSpan={9} className="text-center py-12 text-sm text-[#7a6a55]">
                        Cargando entregas...
                    </td>
                    </tr>
                ) : filteredItems.length === 0 ? (
                    <tr>
                    <td colSpan={9} className="text-center py-12 text-sm text-[#7a6a55]">
                        Sin entregas para mostrar.
                    </td>
                    </tr>
                ) : (
                    filteredItems.map((delivery) => (
                    <tr key={delivery.id} className="table-row">
                        <td className="px-4 py-3 text-sm font-semibold text-[#1a1208] whitespace-nowrap">
                        {delivery.patient_name}
                        </td>

                        <td className="px-4 py-3 text-xs font-mono text-[#7a6a55] whitespace-nowrap">
                        {delivery.phone}
                        </td>

                        <td className="px-4 py-3 text-xs text-[#0b4c45] max-w-[180px] truncate">
                        {delivery.service_treatment}
                        </td>

                        <td className="px-4 py-3 text-sm font-bold text-[#0b4c45] whitespace-nowrap">
                        {delivery.amount_to_pay ? `$${delivery.amount_to_pay}` : '—'}
                        </td>

                        <td className="px-4 py-3 text-sm text-[#7a6a55] whitespace-nowrap">
                        {delivery.delivery_town}
                        </td>

                        <td className="px-4 py-3">
                        {editing === delivery.id ? (
                            <input
                            className="input text-xs w-36"
                            value={editData.assigned_carrier || ''}
                            onChange={(event) =>
                                setEditData({
                                ...editData,
                                assigned_carrier: event.target.value,
                                })
                            }
                            placeholder="Nombre carrero"
                            />
                        ) : (
                            <span className="text-xs text-[#7a6a55]">
                            {delivery.assigned_carrier || '—'}
                            </span>
                        )}
                        </td>

                        <td className="px-4 py-3">
                        {editing === delivery.id ? (
                            <input
                            type="date"
                            className="input text-xs w-36"
                            value={editData.delivery_date || ''}
                            onChange={(event) =>
                                setEditData({
                                ...editData,
                                delivery_date: event.target.value,
                                })
                            }
                            />
                        ) : (
                            <span className="text-xs font-mono text-[#7a6a55] whitespace-nowrap">
                            {delivery.delivery_date || '—'}
                            </span>
                        )}
                        </td>

                        <td className="px-4 py-3">
                        {editing === delivery.id ? (
                            <select
                            className="input text-xs w-32"
                            value={editData.status || delivery.status}
                            onChange={(event) =>
                                setEditData({
                                ...editData,
                                status: event.target.value,
                                })
                            }
                            >
                            {Object.entries(deliveryStatusLabels).map(([value, label]) => (
                                <option key={value} value={value}>
                                {label}
                                </option>
                            ))}
                            </select>
                        ) : (
                            <span
                            className={`badge ${
                                deliveryStatusColors[delivery.status] || 'bg-gray-100 text-gray-700'
                            }`}
                            >
                            {deliveryStatusLabels[delivery.status] || delivery.status}
                            </span>
                        )}
                        </td>

                        <td className="px-4 py-3">
                        {editing === delivery.id ? (
                            <div className="flex gap-1">
                            <button
                                onClick={() => save(delivery.id)}
                                className="btn-primary py-1 px-2 text-xs"
                            >
                                ✓
                            </button>

                            <button
                                onClick={() => {
                                setEditing(null)
                                setEditData({})
                                }}
                                className="btn-ghost py-1 px-2 text-xs"
                            >
                                ✕
                            </button>
                            </div>
                        ) : (
                            <button
                            onClick={() => {
                                setEditing(delivery.id)
                                setEditData({
                                assigned_carrier: delivery.assigned_carrier || '',
                                delivery_date: delivery.delivery_date || '',
                                status: delivery.status,
                                })
                            }}
                            className="btn-ghost py-1 px-2 text-xs border border-[#e5ddd4]"
                            >
                            ✏️ Editar
                            </button>
                        )}
                        </td>
                    </tr>
                    ))
                )}
                </tbody>
            </table>
            </div>
        </div>
        </div>
    )
}

// ── SHIPMENT TABLE ─────────────────────────────────────────────────────────────

function ShipmentTable() {
    const [items, setItems] = useState<Shipment[]>([])
    const [loading, setLoading] = useState(true)
    const [filter, setFilter] = useState('')
    const [search, setSearch] = useState('')
    const [editing, setEditing] = useState<number | null>(null)
    const [editData, setEditData] = useState<Record<string, string>>({})

    const load = () => {
        setLoading(true)

        api
        .get(`/deliveries/shipments${filter ? `?status=${filter}` : ''}`)
        .then((response) => setItems(response.data))
        .finally(() => setLoading(false))
    }

    useEffect(() => {
        load()
    }, [filter])

    const filteredItems = useMemo(() => {
        const term = search.toLowerCase().trim()

        if (!term) return items

        return items.filter((item) =>
        [
            item.patient_name,
            item.phone,
            item.email || '',
            item.postal_address,
            item.city || '',
            item.state_province || '',
            item.country,
            item.zip_code || '',
            item.service_treatment,
            item.tracking_number || '',
            item.carrier || '',
            item.notes || '',
            item.status,
        ]
            .join(' ')
            .toLowerCase()
            .includes(term)
        )
    }, [items, search])

    const save = async (id: number) => {
        await api.patch(`/deliveries/shipments/${id}`, editData)

        setEditing(null)
        setEditData({})
        load()
    }

    return (
        <div>
        <div className="card p-4 mb-5">
            <div className="grid grid-cols-1 md:grid-cols-[220px_1fr] gap-3">
            <select
                className="input"
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
            >
                <option value="">Todos los envíos</option>
                {Object.entries(shipmentStatusLabels).map(([value, label]) => (
                <option key={value} value={value}>
                    {label}
                </option>
                ))}
            </select>

            <input
                className="input"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por cliente, tracking, carrier, ciudad, país o tratamiento..."
            />
            </div>
        </div>

        <div className="card overflow-hidden">
            <div className="overflow-x-auto">
            <table className="w-full min-w-[1050px]">
                <thead>
                <tr className="border-b border-[#e5ddd4] bg-[#F5F1EB]/50">
                    {[
                    'Paciente',
                    'Teléfono',
                    'Correo',
                    'Dirección',
                    'Tratamiento',
                    'Monto',
                    'Carrier',
                    'Rastreo',
                    'Estado',
                    'Acción',
                    ].map((header) => (
                    <th
                        key={header}
                        className="text-left px-4 py-3 text-xs font-semibold text-[#7a6a55] uppercase tracking-wider whitespace-nowrap"
                    >
                        {header}
                    </th>
                    ))}
                </tr>
                </thead>

                <tbody>
                {loading ? (
                    <tr>
                    <td colSpan={10} className="text-center py-12 text-sm text-[#7a6a55]">
                        Cargando envíos...
                    </td>
                    </tr>
                ) : filteredItems.length === 0 ? (
                    <tr>
                    <td colSpan={10} className="text-center py-12 text-sm text-[#7a6a55]">
                        Sin envíos para mostrar.
                    </td>
                    </tr>
                ) : (
                    filteredItems.map((shipment) => (
                    <tr key={shipment.id} className="table-row">
                        <td className="px-4 py-3 text-sm font-semibold text-[#1a1208] whitespace-nowrap">
                        {shipment.patient_name}
                        </td>

                        <td className="px-4 py-3 text-xs font-mono text-[#7a6a55] whitespace-nowrap">
                        {shipment.phone}
                        </td>

                        <td className="px-4 py-3 text-xs text-[#7a6a55] max-w-[140px] truncate">
                        {shipment.email || '—'}
                        </td>

                        <td className="px-4 py-3 text-xs text-[#7a6a55] max-w-[190px]">
                        <div className="truncate">
                            {shipment.postal_address}
                        </div>

                        <div className="text-[10px] text-[#7a6a55] truncate">
                            {[shipment.city, shipment.state_province, shipment.country, shipment.zip_code]
                            .filter(Boolean)
                            .join(', ')}
                        </div>
                        </td>

                        <td className="px-4 py-3 text-xs text-[#0b4c45] max-w-[160px] truncate">
                        {shipment.service_treatment}
                        </td>

                        <td className="px-4 py-3 text-sm font-bold text-[#0b4c45] whitespace-nowrap">
                        {shipment.amount_paid ? `$${shipment.amount_paid}` : '—'}
                        </td>

                        <td className="px-4 py-3">
                        {editing === shipment.id ? (
                            <input
                            className="input text-xs w-28"
                            value={editData.carrier || ''}
                            onChange={(event) =>
                                setEditData({
                                ...editData,
                                carrier: event.target.value,
                                })
                            }
                            placeholder="USPS, UPS..."
                            />
                        ) : (
                            <span className="text-xs text-[#7a6a55]">
                            {shipment.carrier || '—'}
                            </span>
                        )}
                        </td>

                        <td className="px-4 py-3">
                        {editing === shipment.id ? (
                            <input
                            className="input text-xs w-32"
                            value={editData.tracking_number || ''}
                            onChange={(event) =>
                                setEditData({
                                ...editData,
                                tracking_number: event.target.value,
                                })
                            }
                            placeholder="# Rastreo"
                            />
                        ) : (
                            <span
                            className={`text-xs font-mono ${
                                shipment.tracking_number
                                ? 'text-[#0b4c45] font-semibold'
                                : 'text-[#7a6a55]'
                            }`}
                            >
                            {shipment.tracking_number || '—'}
                            </span>
                        )}
                        </td>

                        <td className="px-4 py-3">
                        {editing === shipment.id ? (
                            <select
                            className="input text-xs w-32"
                            value={editData.status || shipment.status}
                            onChange={(event) =>
                                setEditData({
                                ...editData,
                                status: event.target.value,
                                })
                            }
                            >
                            {Object.entries(shipmentStatusLabels).map(([value, label]) => (
                                <option key={value} value={value}>
                                {label}
                                </option>
                            ))}
                            </select>
                        ) : (
                            <span
                            className={`badge ${
                                shipmentStatusColors[shipment.status] || 'bg-gray-100 text-gray-700'
                            }`}
                            >
                            {shipmentStatusLabels[shipment.status] || shipment.status}
                            </span>
                        )}
                        </td>

                        <td className="px-4 py-3">
                        {editing === shipment.id ? (
                            <div className="flex gap-1">
                            <button
                                onClick={() => save(shipment.id)}
                                className="btn-primary py-1 px-2 text-xs"
                            >
                                ✓
                            </button>

                            <button
                                onClick={() => {
                                setEditing(null)
                                setEditData({})
                                }}
                                className="btn-ghost py-1 px-2 text-xs"
                            >
                                ✕
                            </button>
                            </div>
                        ) : (
                            <button
                            onClick={() => {
                                setEditing(shipment.id)
                                setEditData({
                                tracking_number: shipment.tracking_number || '',
                                carrier: shipment.carrier || '',
                                status: shipment.status,
                                })
                            }}
                            className="btn-ghost py-1 px-2 text-xs border border-[#e5ddd4]"
                            >
                            ✏️ Editar
                            </button>
                        )}
                        </td>
                    </tr>
                    ))
                )}
                </tbody>
            </table>
            </div>
        </div>
        </div>
    )
}

// ── MAIN PAGE ─────────────────────────────────────────────────────────────────

export default function DeliveriesPage() {
    const [tab, setTab] = useState<'deliveries' | 'shipments'>('deliveries')

    return (
        <div className="page-mobile p-4 sm:p-6 max-w-7xl mx-auto w-full min-w-0">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between mb-6">
            <div>
            <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
                Entregas y Envíos
            </h1>

            <p className="text-sm text-[#7a6a55] mt-0.5">
                Gestión operativa de entregas en Puerto Rico y envíos postales.
            </p>
            </div>

            <div className="flex gap-1 bg-[#F5F1EB] p-1 rounded-xl">
            <button
                onClick={() => setTab('deliveries')}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                tab === 'deliveries'
                    ? 'bg-[#0b4c45] text-white shadow-sm'
                    : 'text-[#7a6a55] hover:text-[#0b4c45]'
                }`}
            >
                🛵 Entregas PR
            </button>

            <button
                onClick={() => setTab('shipments')}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                tab === 'shipments'
                    ? 'bg-[#0b4c45] text-white shadow-sm'
                    : 'text-[#7a6a55] hover:text-[#0b4c45]'
                }`}
            >
                📦 Envíos
            </button>
            </div>
        </div>

        {tab === 'deliveries' ? <DeliveryTable /> : <ShipmentTable />}
        </div>
    )
}