import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { useToast } from '../components/Toast'

interface Payment {
    id: number
    patient_id: number
    session_id: number | null
    patient_name: string | null
    whatsapp_number: string | null
    product_service: string
    amount: number | null
    currency: string
    payment_method: string
    payment_link_url: string | null
    proof_media_id: string | null
    status: string
    verified_by_agent_id: number | null
    verified_by_agent_name: string | null
    notes: string | null
    created_at: string | null
    updated_at: string | null
}

const STATUS_LABELS: Record<string, string> = {
    link_sent: 'Link enviado',
    proof_received: 'Comprobante recibido',
    verified: 'Verificado',
    rejected: 'Rechazado',
}

const STATUS_CLASSES: Record<string, string> = {
    link_sent: 'bg-blue-100 text-blue-700',
    proof_received: 'bg-amber-100 text-amber-700',
    verified: 'bg-teal-100 text-teal-700',
    rejected: 'bg-red-100 text-red-700',
}

const METHOD_LABELS: Record<string, string> = {
    link: 'Link de pago',
    ath: 'ATH Móvil',
    credit_card: 'Tarjeta',
    zelle: 'Zelle',
    paypal: 'PayPal',
    apple_pay: 'Apple Pay',
    other: 'Otro',
}

export default function PaymentsPage() {
    const toast = useToast()

    const [payments, setPayments] = useState<Payment[]>([])
    const [loading, setLoading] = useState(true)
    const [status, setStatus] = useState('proof_received')
    const [search, setSearch] = useState('')
    const [actionLoading, setActionLoading] = useState<number | null>(null)
    const [notes, setNotes] = useState<Record<number, string>>({})

    const queryParams = useMemo(() => {
        const params = new URLSearchParams()

        if (status) params.set('status', status)
        if (search.trim()) params.set('search', search.trim())

        return params.toString()
    }, [status, search])

    const loadPayments = async () => {
        setLoading(true)

        try {
        const response = await api.get(`/payments/${queryParams ? `?${queryParams}` : ''}`)
        setPayments(response.data)
        } catch (error) {
        toast.error('Error cargando pagos', 'No fue posible consultar los pagos.')
        } finally {
        setLoading(false)
        }
    }

    useEffect(() => {
        loadPayments()
    }, [queryParams])

    const verifyPayment = async (payment: Payment) => {
        setActionLoading(payment.id)

        try {
        await api.patch(`/payments/${payment.id}/verify`, {
            notes: notes[payment.id] || undefined,
        })

        toast.success(
            'Pago verificado',
            `El pago de ${payment.patient_name || 'cliente'} fue marcado como verificado.`
        )

        setNotes((prev) => ({ ...prev, [payment.id]: '' }))
        loadPayments()
        } catch (error) {
        toast.error('Error verificando pago', 'No fue posible verificar el pago.')
        } finally {
        setActionLoading(null)
        }
    }

    const rejectPayment = async (payment: Payment) => {
        setActionLoading(payment.id)

        try {
        await api.patch(`/payments/${payment.id}/reject`, {
            notes: notes[payment.id] || 'Comprobante rechazado por validación del agente.',
        })

        toast.success(
            'Pago rechazado',
            `El pago de ${payment.patient_name || 'cliente'} fue marcado como rechazado.`
        )

        setNotes((prev) => ({ ...prev, [payment.id]: '' }))
        loadPayments()
        } catch (error) {
        toast.error('Error rechazando pago', 'No fue posible rechazar el pago.')
        } finally {
        setActionLoading(null)
        }
    }

    const filters = [
        { value: 'proof_received', label: 'Pendientes de verificar' },
        { value: 'link_sent', label: 'Link enviado' },
        { value: 'verified', label: 'Verificados' },
        { value: 'rejected', label: 'Rechazados' },
        { value: '', label: 'Todos' },
    ]

    return (
        <div className="page-mobile p-4 sm:p-6 max-w-7xl mx-auto w-full min-w-0">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-6">
            <div className="min-w-0">
            <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
                Pagos
            </h1>

            <p className="text-sm text-[#7a6a55] mt-0.5">
                Verificación operativa de comprobantes, ATH Móvil, Zelle y otros pagos.
            </p>
            </div>

            <button
            onClick={loadPayments}
            className="btn-primary w-full sm:w-auto justify-center"
            disabled={loading}
            >
            ↻ Actualizar
            </button>
        </div>

        <div className="card p-4 mb-5">
            <div className="grid grid-cols-1 sm:grid-cols-[240px_1fr] gap-3">
            <select
                className="input"
                value={status}
                onChange={(event) => setStatus(event.target.value)}
            >
                {filters.map((filter) => (
                <option key={filter.value} value={filter.value}>
                    {filter.label}
                </option>
                ))}
            </select>

            <input
                className="input"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Buscar por cliente, WhatsApp, producto o método de pago..."
            />
            </div>
        </div>

        <div className="card overflow-hidden">
            {loading ? (
            <div className="p-10 text-center text-[#7a6a55]">
                Cargando pagos...
            </div>
            ) : payments.length === 0 ? (
            <div className="p-10 text-center">
                <p className="text-[#0b4c45] font-semibold">
                No hay pagos para mostrar.
                </p>

                <p className="text-sm text-[#7a6a55] mt-1">
                Cambia los filtros o espera nuevos comprobantes.
                </p>
            </div>
            ) : (
            <div className="overflow-x-auto mobile-scroll-x">
                <table className="w-full min-w-[1150px] text-sm">
                <thead className="bg-[#F5F1EB] text-[#0b4c45]">
                    <tr>
                    <th className="px-4 py-3 text-left font-semibold whitespace-nowrap">
                        Cliente
                    </th>
                    <th className="px-4 py-3 text-left font-semibold whitespace-nowrap">
                        Producto
                    </th>
                    <th className="px-4 py-3 text-left font-semibold whitespace-nowrap">
                        Monto
                    </th>
                    <th className="px-4 py-3 text-left font-semibold whitespace-nowrap">
                        Método
                    </th>
                    <th className="px-4 py-3 text-left font-semibold whitespace-nowrap">
                        Comprobante
                    </th>
                    <th className="px-4 py-3 text-left font-semibold whitespace-nowrap">
                        Estado
                    </th>
                    <th className="px-4 py-3 text-left font-semibold whitespace-nowrap">
                        Notas
                    </th>
                    <th className="px-4 py-3 text-left font-semibold whitespace-nowrap">
                        Acciones
                    </th>
                    </tr>
                </thead>

                <tbody>
                    {payments.map((payment) => (
                    <tr key={payment.id} className="table-row align-top">
                        <td className="px-4 py-3 min-w-[190px]">
                        <p className="font-semibold text-[#1a1208] max-w-[180px] truncate">
                            {payment.patient_name || 'Cliente'}
                        </p>

                        <p className="text-xs text-[#7a6a55] whitespace-nowrap">
                            {payment.whatsapp_number || 'Sin WhatsApp'}
                        </p>

                        <p className="text-[11px] text-[#7a6a55] mt-1 whitespace-nowrap">
                            ID pago: #{payment.id}
                        </p>
                        </td>

                        <td className="px-4 py-3 min-w-[190px]">
                        <p className="font-medium text-[#1a1208] max-w-[220px] truncate">
                            {payment.product_service || '—'}
                        </p>

                        <p className="text-xs text-[#7a6a55] whitespace-nowrap">
                            {payment.created_at || 'Sin fecha'}
                        </p>
                        </td>

                        <td className="px-4 py-3 whitespace-nowrap">
                        <span className="font-bold text-[#0b4c45]">
                            {payment.amount !== null
                            ? `$${payment.amount.toFixed(2)} ${payment.currency || 'USD'}`
                            : '—'}
                        </span>
                        </td>

                        <td className="px-4 py-3 whitespace-nowrap">
                        <span className="badge bg-[#F5F1EB] text-[#0b4c45]">
                            {METHOD_LABELS[payment.payment_method] || payment.payment_method}
                        </span>
                        </td>

                        <td className="px-4 py-3 min-w-[180px]">
                        {payment.proof_media_id ? (
                            <div>
                            <p className="text-xs font-mono text-[#0b4c45] max-w-[170px] truncate">
                                {payment.proof_media_id}
                            </p>

                            <p className="text-[11px] text-[#7a6a55] mt-1 whitespace-nowrap">
                                Media ID recibido por WhatsApp
                            </p>
                            </div>
                        ) : (
                            <span className="text-[#7a6a55] whitespace-nowrap">
                            Sin comprobante
                            </span>
                        )}
                        </td>

                        <td className="px-4 py-3 whitespace-nowrap">
                        <span
                            className={`badge ${
                            STATUS_CLASSES[payment.status] || 'bg-gray-100 text-gray-700'
                            }`}
                        >
                            {STATUS_LABELS[payment.status] || payment.status}
                        </span>

                        {payment.verified_by_agent_name && (
                            <p className="text-[11px] text-[#7a6a55] mt-1 max-w-[150px] truncate">
                            Por: {payment.verified_by_agent_name}
                            </p>
                        )}
                        </td>

                        <td className="px-4 py-3 min-w-[260px]">
                        <textarea
                            className="input min-h-[72px] text-xs"
                            value={notes[payment.id] ?? ''}
                            onChange={(event) =>
                            setNotes((prev) => ({
                                ...prev,
                                [payment.id]: event.target.value,
                            }))
                            }
                            placeholder="Nota opcional para auditoría..."
                        />

                        {payment.notes && (
                            <p className="text-[11px] text-[#7a6a55] mt-2 whitespace-pre-wrap max-w-xs">
                            {payment.notes}
                            </p>
                        )}
                        </td>

                        <td className="px-4 py-3 whitespace-nowrap">
                        <div className="flex flex-col gap-2 min-w-[150px]">
                            <button
                            className="btn-primary justify-center"
                            disabled={actionLoading === payment.id || payment.status === 'verified'}
                            onClick={() => verifyPayment(payment)}
                            >
                            {actionLoading === payment.id ? 'Procesando...' : '✓ Verificar'}
                            </button>

                            <button
                            className="btn-ghost justify-center border border-[#e5ddd4] text-red-700 hover:bg-red-50"
                            disabled={actionLoading === payment.id || payment.status === 'rejected'}
                            onClick={() => rejectPayment(payment)}
                            >
                            ✕ Rechazar
                            </button>
                        </div>
                        </td>
                    </tr>
                    ))}
                </tbody>
                </table>
            </div>
            )}
        </div>
        </div>
    )
}