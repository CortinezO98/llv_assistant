import { useCallback, useEffect, useRef, useState } from 'react'
import { conversationsApi, agentsApi } from '../api/client'
import { useAuth } from '../context/AuthContext'

function playNotificationSound() {
    try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
        const oscillator = ctx.createOscillator()
        const gainNode = ctx.createGain()

        oscillator.connect(gainNode)
        gainNode.connect(ctx.destination)

        oscillator.frequency.setValueAtTime(880, ctx.currentTime)
        oscillator.frequency.setValueAtTime(660, ctx.currentTime + 0.1)

        gainNode.gain.setValueAtTime(0.3, ctx.currentTime)
        gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4)

        oscillator.start(ctx.currentTime)
        oscillator.stop(ctx.currentTime + 0.4)
    } catch {
        // Algunos navegadores bloquean audio hasta que el usuario interactúa.
    }
}

// ── Interfaces ────────────────────────────────────────────────────────────────

interface Message {
    id: number
    direction: 'inbound' | 'outbound'
    content: string
    sent_by_bot: boolean
    agent_id: number | null
    created_at: string
}

interface Patient {
    id: number | null
    name: string
    whatsapp_number: string
    location_type: string
    is_recurrent: boolean
}

interface Conversation {
    session_id: number
    status: string
    channel: string
    patient: Patient
    assigned_agent: { id: number; name: string } | null
    last_message: string | null
    last_message_at: string | null
    last_message_id?: number | null
    last_message_direction?: 'inbound' | 'outbound' | null
    last_message_sent_by_bot?: boolean | null
    ai_summary: string | null
    escalation_reason: string | null
    created_at: string
    updated_at: string
}

interface ConversationDetail {
    session_id: number
    status: string
    patient: Patient
    ai_summary: string | null
    escalation_reason: string | null
    escalated_at: string | null
    messages: Message[]
}

type WsStatus = 'connecting' | 'connected' | 'disconnected'

// ── Constantes ────────────────────────────────────────────────────────────────

const statusColors: Record<string, string> = {
    active:    'bg-brand-100 text-brand-700',
    in_agent:  'bg-blue-100 text-blue-700',
    completed: 'bg-teal-100 text-teal-700',
    closed:    'bg-gray-100 text-gray-500',
}

const statusLabels: Record<string, string> = {
    active:    'Bot activo',
    in_agent:  'Con agente',
    completed: 'Completada',
    closed:    'Cerrada',
}

const locationFlag: Record<string, string> = {
    puerto_rico: '🇵🇷',
    latam:       '🌎',
    usa:         '🇺🇸',
}

// ── Modal: Agendar Cita ───────────────────────────────────────────────────────

function AppointmentModal({
    sessionId,
    onClose,
    onSuccess,
}: {
    sessionId: number
    onClose: () => void
    onSuccess: () => void
}) {
    const [form, setForm] = useState({
        full_name: '', phone: '', service: '', preferred_date: '',
        preferred_time: '', clinic: 'latam', medical_conditions: '', notes: '',
    })
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async () => {
        if (!form.service.trim()) { setError('El servicio es requerido'); return }
        setSaving(true)
        try {
            await conversationsApi.createAppointment(sessionId, {
                ...form,
                notify_customer: true,
            })
            onSuccess()
            onClose()
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Error al crear la cita')
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-md animate-fade-in">
                <div className="flex items-center justify-between px-5 py-4 border-b border-[#e4ede8]">
                    <h3 className="font-semibold text-[#0b4c45]">📅 Agendar cita</h3>
                    <button onClick={onClose} className="text-[#7a6a55] hover:text-[#0b4c45] text-lg leading-none">✕</button>
                </div>

                <div className="p-5 space-y-3 max-h-[70vh] overflow-y-auto">
                    {error && (
                        <div className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
                            {error}
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Nombre del paciente</label>
                            <input className="input" placeholder="María González" value={form.full_name}
                                onChange={e => setForm({ ...form, full_name: e.target.value })} />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Teléfono</label>
                            <input className="input" placeholder="+1787..." value={form.phone}
                                onChange={e => setForm({ ...form, phone: e.target.value })} />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                            Servicio / Tratamiento <span className="text-red-500">*</span>
                        </label>
                        <input className="input" placeholder="Ej: Semaglutide 0.5mg, Botox Full Face..."
                            value={form.service}
                            onChange={e => setForm({ ...form, service: e.target.value })} />
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Clínica</label>
                            <select className="input" value={form.clinic}
                                onChange={e => setForm({ ...form, clinic: e.target.value })}>
                                <option value="latam">LATAM</option>
                                <option value="arecibo">Arecibo</option>
                                <option value="bayamon">Bayamón</option>
                                <option value="virtual">Virtual</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Fecha preferida</label>
                            <input type="date" className="input" value={form.preferred_date}
                                onChange={e => setForm({ ...form, preferred_date: e.target.value })} />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Hora preferida</label>
                            <input type="time" className="input" value={form.preferred_time}
                                onChange={e => setForm({ ...form, preferred_time: e.target.value })} />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Condiciones médicas</label>
                        <input className="input" placeholder="Tiroides, diabetes, ninguna..."
                            value={form.medical_conditions}
                            onChange={e => setForm({ ...form, medical_conditions: e.target.value })} />
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Notas internas</label>
                        <textarea className="input resize-none" rows={2}
                            placeholder="Notas adicionales para el equipo..."
                            value={form.notes}
                            onChange={e => setForm({ ...form, notes: e.target.value })} />
                    </div>
                </div>

                <div className="flex gap-2 px-5 pb-5 pt-3 border-t border-[#e4ede8]">
                    <button onClick={handleSubmit} disabled={saving}
                        className="btn-primary flex-1 disabled:opacity-50">
                        {saving ? 'Guardando...' : '✅ Crear cita y notificar'}
                    </button>
                    <button onClick={onClose} className="btn-ghost">Cancelar</button>
                </div>
            </div>
        </div>
    )
}

// ── Modal: Crear Entrega ──────────────────────────────────────────────────────

function DeliveryModal({
    sessionId,
    onClose,
    onSuccess,
}: {
    sessionId: number
    onClose: () => void
    onSuccess: () => void
}) {
    const [form, setForm] = useState({
        patient_name: '', phone: '', service_treatment: '', amount_to_pay: '',
        delivery_town: '', assigned_carrier: '', delivery_date: '', notes: '',
    })
    const [saving, setSaving] = useState(false)
    const [error, setError] = useState('')

    const handleSubmit = async () => {
        if (!form.service_treatment.trim()) { setError('El tratamiento es requerido'); return }
        if (!form.delivery_town.trim())     { setError('El pueblo de entrega es requerido'); return }
        setSaving(true)
        try {
            await conversationsApi.createDelivery(sessionId, {
                ...form,
                amount_to_pay: form.amount_to_pay ? Number(form.amount_to_pay) : null,
                notify_customer: true,
            })
            onSuccess()
            onClose()
        } catch (e: any) {
            setError(e.response?.data?.detail || 'Error al crear la entrega')
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-md animate-fade-in">
                <div className="flex items-center justify-between px-5 py-4 border-b border-[#e4ede8]">
                    <h3 className="font-semibold text-[#0b4c45]">📦 Crear entrega</h3>
                    <button onClick={onClose} className="text-[#7a6a55] hover:text-[#0b4c45] text-lg leading-none">✕</button>
                </div>

                <div className="p-5 space-y-3 max-h-[70vh] overflow-y-auto">
                    {error && (
                        <div className="text-xs text-red-600 bg-red-50 px-3 py-2 rounded-lg border border-red-200">
                            {error}
                        </div>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Nombre del paciente</label>
                            <input className="input" placeholder="María González" value={form.patient_name}
                                onChange={e => setForm({ ...form, patient_name: e.target.value })} />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Teléfono</label>
                            <input className="input" placeholder="+1787..." value={form.phone}
                                onChange={e => setForm({ ...form, phone: e.target.value })} />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                            Tratamiento / Producto <span className="text-red-500">*</span>
                        </label>
                        <input className="input" placeholder="Ej: Semaglutide 0.5mg Kit 1 mes"
                            value={form.service_treatment}
                            onChange={e => setForm({ ...form, service_treatment: e.target.value })} />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                                Pueblo de entrega <span className="text-red-500">*</span>
                            </label>
                            <input className="input" placeholder="Ej: Arecibo, Bayamón..."
                                value={form.delivery_town}
                                onChange={e => setForm({ ...form, delivery_town: e.target.value })} />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Monto a pagar (USD)</label>
                            <input type="number" className="input" placeholder="199.00"
                                value={form.amount_to_pay}
                                onChange={e => setForm({ ...form, amount_to_pay: e.target.value })} />
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Carrero asignado</label>
                            <input className="input" placeholder="Yailo, Israel..."
                                value={form.assigned_carrier}
                                onChange={e => setForm({ ...form, assigned_carrier: e.target.value })} />
                        </div>
                        <div>
                            <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Fecha de entrega</label>
                            <input type="date" className="input" value={form.delivery_date}
                                onChange={e => setForm({ ...form, delivery_date: e.target.value })} />
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Notas internas</label>
                        <textarea className="input resize-none" rows={2}
                            placeholder="Notas para el equipo..."
                            value={form.notes}
                            onChange={e => setForm({ ...form, notes: e.target.value })} />
                    </div>
                </div>

                <div className="flex gap-2 px-5 pb-5 pt-3 border-t border-[#e4ede8]">
                    <button onClick={handleSubmit} disabled={saving}
                        className="btn-primary flex-1 disabled:opacity-50">
                        {saving ? 'Guardando...' : '✅ Crear entrega y notificar'}
                    </button>
                    <button onClick={onClose} className="btn-ghost">Cancelar</button>
                </div>
            </div>
        </div>
    )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function ConversationsPage() {
    const { agent } = useAuth()
    const isAdmin = agent?.role === 'admin' || agent?.role === 'supervisor' || agent?.role === 'superadmin'

    const [conversations, setConversations]     = useState<Conversation[]>([])
    const [selected, setSelected]               = useState<ConversationDetail | null>(null)
    const [selectedId, setSelectedId]           = useState<number | null>(null)
    const [filter, setFilter]                   = useState('')
    const [search, setSearch]                   = useState('')
    const [message, setMessage]                 = useState('')
    const [sending, setSending]                 = useState(false)
    const [loadingDetail, setLoadingDetail]     = useState(false)
    const [agents, setAgents]                   = useState<any[]>([])
    const [showTransfer, setShowTransfer]       = useState(false)
    const [newMessageAlert, setNewMessageAlert] = useState<string | null>(null)
    const [wsStatus, setWsStatus]               = useState<WsStatus>('connecting')

    // ── Nuevos estados para modales ───────────────────────────────────────────
    const [showAppointmentModal, setShowAppointmentModal] = useState(false)
    const [showDeliveryModal, setShowDeliveryModal]       = useState(false)

    const messagesEndRef        = useRef<HTMLDivElement>(null)
    const socketRef             = useRef<WebSocket | null>(null)
    const reconnectTimeoutRef   = useRef<number | null>(null)
    const reconnectAttemptRef   = useRef(0)
    const selectedIdRef         = useRef<number | null>(null)
    const alertTimeoutRef       = useRef<number | null>(null)

    useEffect(() => {
        selectedIdRef.current = selectedId
    }, [selectedId])

    const loadConversations = useCallback(() => {
        conversationsApi
            .list(filter || undefined)
            .then(r => setConversations(r.data))
            .catch(error => {
                console.warn('Error cargando conversaciones', error)
            })
    }, [filter])

    useEffect(() => {
        loadConversations()
    }, [loadConversations])

    useEffect(() => {
        if ('Notification' in window && Notification.permission === 'default') {
            Notification.requestPermission().catch(() => {})
        }
    }, [])

    // 🔥 WebSocket realtime con reconexión automática.
    useEffect(() => {
        let manuallyClosed = false

        const connectWebSocket = () => {
            const token = localStorage.getItem('llv_token')
            if (!token) {
                setWsStatus('disconnected')
                return
            }

            setWsStatus('connecting')

            const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001'
            const wsUrl  = apiUrl.replace('http://', 'ws://').replace('https://', 'wss://')
            const socket = new WebSocket(`${wsUrl}/ws/realtime?token=${token}`)
            socketRef.current = socket

            socket.onopen = () => {
                console.log('⚡ WebSocket realtime conectado')
                reconnectAttemptRef.current = 0
                setWsStatus('connected')
            }

            socket.onmessage = event => {
                try {
                    const data = JSON.parse(event.data)

                    if (data.type !== 'new_message') return
                    if (data.direction !== 'inbound') return

                    const currentAgentId = agent?.agent_id || agent?.id

                    if (
                        agent?.role === 'agent' &&
                        data.assigned_agent_id &&
                        Number(data.assigned_agent_id) !== Number(currentAgentId)
                    ) {
                        return
                    }

                    const messageId    = Number(data.message_id || Date.now())
                    const sessionId    = Number(data.session_id)
                    const customerName = data.customer_name || data.whatsapp_number || 'Cliente'

                    playNotificationSound()
                    setNewMessageAlert(`Nuevo mensaje de ${customerName}`)

                    if (alertTimeoutRef.current) window.clearTimeout(alertTimeoutRef.current)
                    alertTimeoutRef.current = window.setTimeout(() => setNewMessageAlert(null), 4000)

                    if ('Notification' in window && Notification.permission === 'granted') {
                        new Notification('LLV Assistant', { body: `Nuevo mensaje de ${customerName}` })
                    }

                    setConversations(prev => {
                        const exists = prev.some(conv => conv.session_id === sessionId)
                        if (!exists) {
                            loadConversations()
                            return prev
                        }
                        const updated = prev.map(conv =>
                            conv.session_id === sessionId
                                ? {
                                    ...conv,
                                    last_message:              data.content,
                                    last_message_at:           data.created_at,
                                    last_message_id:           messageId,
                                    last_message_direction:    data.direction,
                                    last_message_sent_by_bot:  false,
                                    updated_at:                data.created_at,
                                  }
                                : conv
                        )
                        return updated.sort((a, b) => {
                            const dateA = new Date(a.updated_at || a.last_message_at || 0).getTime()
                            const dateB = new Date(b.updated_at || b.last_message_at || 0).getTime()
                            return dateB - dateA
                        })
                    })

                    setSelected(prev => {
                        if (!prev || prev.session_id !== sessionId) return prev
                        if (prev.messages.some(msg => msg.id === messageId)) return prev
                        return {
                            ...prev,
                            messages: [
                                ...prev.messages,
                                {
                                    id: messageId, direction: data.direction, content: data.content,
                                    sent_by_bot: false, agent_id: null, created_at: data.created_at,
                                },
                            ],
                        }
                    })
                } catch (error) {
                    console.warn('Error procesando evento realtime', error)
                }
            }

            socket.onerror  = () => console.warn('WebSocket realtime error')
            socket.onclose  = () => {
                console.warn('WebSocket realtime cerrado')
                setWsStatus('disconnected')
                if (manuallyClosed) return
                reconnectAttemptRef.current += 1
                const delay = Math.min(1000 * Math.pow(2, reconnectAttemptRef.current), 15000)
                reconnectTimeoutRef.current = window.setTimeout(() => connectWebSocket(), delay)
            }
        }

        connectWebSocket()

        return () => {
            manuallyClosed = true
            if (reconnectTimeoutRef.current)  window.clearTimeout(reconnectTimeoutRef.current)
            if (alertTimeoutRef.current)       window.clearTimeout(alertTimeoutRef.current)
            if (socketRef.current)             socketRef.current.close()
        }
    }, [agent?.agent_id, agent?.id, agent?.role, loadConversations])

    useEffect(() => {
        if (isAdmin) {
            agentsApi
                .list()
                .then(r => setAgents(r.data.filter((a: any) => a.is_active)))
                .catch(error => console.warn('Error cargando agentes', error))
        }
    }, [isAdmin])

    const openConversation = async (conv: Conversation) => {
        setSelectedId(conv.session_id)
        setLoadingDetail(true)
        try {
            const r = await conversationsApi.getMessages(conv.session_id)
            setSelected(r.data)
        } finally {
            setLoadingDetail(false)
        }
    }

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [selected?.messages])

    const handleSend = async () => {
        if (!message.trim() || !selectedId) return

        setSending(true)
        const textToSend = message.trim()
        const tempId     = Date.now()
        const createdAt  = new Date().toISOString()
        setMessage('')

        try {
            await conversationsApi.send(selectedId, textToSend)

            setSelected(prev => {
                if (!prev || prev.session_id !== selectedId) return prev
                return {
                    ...prev,
                    messages: [
                        ...prev.messages,
                        {
                            id: tempId, direction: 'outbound', content: textToSend,
                            sent_by_bot: false, agent_id: agent?.agent_id || agent?.id || null,
                            created_at: createdAt,
                        },
                    ],
                }
            })

            setConversations(prev =>
                prev.map(conv =>
                    conv.session_id === selectedId
                        ? {
                            ...conv, last_message: textToSend, last_message_at: createdAt,
                            last_message_id: tempId, last_message_direction: 'outbound',
                            last_message_sent_by_bot: false, updated_at: createdAt,
                          }
                        : conv
                )
            )
        } catch (error) {
            console.warn('Error enviando mensaje', error)
            setMessage(textToSend)
        } finally {
            setSending(false)
        }
    }

    const handleTake = async () => {
        if (!selectedId) return
        await conversationsApi.take(selectedId)
        const r = await conversationsApi.getMessages(selectedId)
        setSelected(r.data)
        loadConversations()
    }

    const handleClose = async () => {
        if (!selectedId || !confirm('¿Cerrar esta conversación?')) return
        await conversationsApi.close(selectedId)
        setSelected(null)
        setSelectedId(null)
        loadConversations()
    }

    const handleTransfer = async (agentId: number) => {
        if (!selectedId) return
        await conversationsApi.transfer(selectedId, agentId)
        setShowTransfer(false)
        const r = await conversationsApi.getMessages(selectedId)
        setSelected(r.data)
        loadConversations()
    }

    const filtered = conversations.filter(c =>
        !search ||
        c.patient.name.toLowerCase().includes(search.toLowerCase()) ||
        c.patient.whatsapp_number.includes(search)
    )

    const canRespond = selected && (
        isAdmin ||
        selected.status === 'in_agent' ||
        selected.status === 'active'
    )

    // Botones de cita/entrega solo visibles cuando hay un agente asignado
    const canCreateActions = selected?.status === 'in_agent'

    return (
        <div className="flex h-full" style={{ position: 'relative' }}>

            {/* ── Alerta de nuevo mensaje ─────────────────────────────────── */}
            {newMessageAlert && (
                <div style={{
                    position: 'fixed', top: '20px', right: '20px', zIndex: 9999,
                    background: '#0b4c45', color: 'white', padding: '12px 20px',
                    borderRadius: '10px', boxShadow: '0 4px 16px rgba(0,0,0,0.2)',
                    display: 'flex', alignItems: 'center', gap: '10px',
                    fontSize: '14px', fontWeight: 500,
                }}>
                    <span style={{ fontSize: '20px' }}>💬</span>
                    <span>{newMessageAlert}</span>
                </div>
            )}

            {/* ── Modales ─────────────────────────────────────────────────── */}
            {showAppointmentModal && selectedId && (
                <AppointmentModal
                    sessionId={selectedId}
                    onClose={() => setShowAppointmentModal(false)}
                    onSuccess={loadConversations}
                />
            )}

            {showDeliveryModal && selectedId && (
                <DeliveryModal
                    sessionId={selectedId}
                    onClose={() => setShowDeliveryModal(false)}
                    onSuccess={loadConversations}
                />
            )}

            <div className="flex h-full w-full">

                {/* ── Sidebar: lista de conversaciones ────────────────────── */}
                <div className="w-80 flex-shrink-0 border-r border-[#e4ede8] bg-white flex flex-col">
                    <div className="px-4 py-4 border-b border-[#e4ede8]">
                        <div className="flex items-start justify-between mb-3">
                            <div>
                                <h2 className="font-display font-bold text-brand-800">
                                    Conversaciones
                                </h2>
                                <div className="text-[10px] mt-1">
                                    {wsStatus === 'connected' && (
                                        <span className="text-green-600">● Tiempo real activo</span>
                                    )}
                                    {wsStatus === 'connecting' && (
                                        <span className="text-amber-600">● Conectando realtime...</span>
                                    )}
                                    {wsStatus === 'disconnected' && (
                                        <span className="text-red-500">● Reconectando realtime...</span>
                                    )}
                                </div>
                            </div>
                            <span className="badge bg-brand-100 text-brand-700">
                                {filtered.length}
                            </span>
                        </div>

                        <input
                            className="input text-sm"
                            placeholder="🔍 Buscar paciente..."
                            value={search}
                            onChange={e => setSearch(e.target.value)}
                        />

                        <div className="flex gap-1 mt-2 flex-wrap">
                            {['', 'active', 'in_agent', 'completed'].map(s => (
                                <button key={s} onClick={() => setFilter(s)}
                                    className={`px-2 py-1 rounded-lg text-[10px] font-semibold transition-all ${
                                        filter === s
                                            ? 'bg-brand-600 text-white'
                                            : 'bg-gray-100 text-gray-500 hover:bg-brand-50'
                                    }`}>
                                    {s === '' ? 'Todas' : statusLabels[s]}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="flex-1 overflow-y-auto">
                        {filtered.length === 0 ? (
                            <div className="p-6 text-center text-sm text-[#6b8a78]">
                                Sin conversaciones
                                {filter ? ` con estado "${statusLabels[filter]}"` : ''}
                            </div>
                        ) : (
                            filtered.map(conv => (
                                <div key={conv.session_id} onClick={() => openConversation(conv)}
                                    className={`px-4 py-3.5 border-b border-[#e4ede8] cursor-pointer transition-colors hover:bg-brand-50/50 ${
                                        selectedId === conv.session_id
                                            ? 'bg-brand-50 border-l-2 border-l-brand-600'
                                            : ''
                                    }`}>
                                    <div className="flex items-start justify-between gap-2 mb-1">
                                        <div className="flex items-center gap-2 min-w-0">
                                            <div className="w-8 h-8 bg-brand-100 rounded-full flex items-center justify-center text-brand-600 text-xs font-bold flex-shrink-0">
                                                {conv.patient.name.charAt(0)}
                                            </div>
                                            <div className="min-w-0">
                                                <div className="text-xs font-semibold text-brand-800 truncate flex items-center gap-1">
                                                    {locationFlag[conv.patient.location_type] || '🌎'}{' '}
                                                    {conv.patient.name}
                                                    {conv.patient.is_recurrent && (
                                                        <span className="text-amber-500 text-[10px]">⭐</span>
                                                    )}
                                                </div>
                                                <div className="text-[10px] text-[#6b8a78] font-mono">
                                                    {conv.patient.whatsapp_number}
                                                </div>
                                            </div>
                                        </div>
                                        <span className={`badge text-[9px] flex-shrink-0 ${statusColors[conv.status]}`}>
                                            {statusLabels[conv.status]}
                                        </span>
                                    </div>

                                    {conv.last_message && (
                                        <p className="text-[11px] text-[#6b8a78] truncate ml-10">
                                            {conv.last_message_direction === 'inbound' ? 'Cliente: ' : 'Equipo: '}
                                            {conv.last_message}
                                        </p>
                                    )}
                                    {conv.assigned_agent && (
                                        <p className="text-[10px] text-blue-500 ml-10 mt-0.5">
                                            → {conv.assigned_agent.name}
                                        </p>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* ── Panel del chat ──────────────────────────────────────── */}
                <div className="flex-1 flex flex-col bg-[#f8faf9]">
                    {!selected ? (
                        <div className="flex-1 flex flex-col items-center justify-center text-center p-8">
                            <div className="text-5xl mb-4">💬</div>
                            <h3 className="font-display font-bold text-brand-800 text-xl mb-2">
                                Panel de conversaciones
                            </h3>
                            <p className="text-sm text-[#6b8a78] max-w-xs">
                                {isAdmin
                                    ? 'Selecciona una conversación de la lista para ver el historial y responder.'
                                    : 'Selecciona una conversación asignada a ti para responder al cliente.'}
                            </p>
                        </div>
                    ) : loadingDetail ? (
                        <div className="flex-1 flex items-center justify-center">
                            <svg className="animate-spin w-8 h-8 text-brand-500" viewBox="0 0 24 24" fill="none">
                                <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".2"/>
                                <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
                            </svg>
                        </div>
                    ) : (
                        <>
                            {/* ── Header del chat ─────────────────────────── */}
                            <div className="bg-white border-b border-[#e4ede8] px-5 py-3.5 flex items-center justify-between">
                                <div className="flex items-center gap-3">
                                    <div className="w-9 h-9 bg-brand-100 rounded-full flex items-center justify-center text-brand-600 font-bold">
                                        {selected.patient.name.charAt(0)}
                                    </div>
                                    <div>
                                        <div className="font-semibold text-brand-800 text-sm flex items-center gap-2">
                                            {locationFlag[selected.patient.location_type]}{' '}
                                            {selected.patient.name}
                                            {selected.patient.is_recurrent && (
                                                <span className="badge bg-amber-100 text-amber-700 text-[9px]">
                                                    ⭐ Recurrente
                                                </span>
                                            )}
                                        </div>
                                        <div className="text-xs text-[#6b8a78] font-mono">
                                            {selected.patient.whatsapp_number}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 flex-wrap justify-end">
                                    <span className={`badge ${statusColors[selected.status]}`}>
                                        {statusLabels[selected.status]}
                                    </span>

                                    {/* ── Botones de cita y entrega (solo en_agente) ── */}
                                    {canCreateActions && (
                                        <>
                                            <button
                                                onClick={() => setShowAppointmentModal(true)}
                                                className="btn-ghost py-1.5 px-3 text-xs border border-[#e4ede8]"
                                            >
                                                📅 Agendar cita
                                            </button>
                                            <button
                                                onClick={() => setShowDeliveryModal(true)}
                                                className="btn-ghost py-1.5 px-3 text-xs border border-[#e4ede8]"
                                            >
                                                📦 Crear entrega
                                            </button>
                                        </>
                                    )}

                                    {isAdmin && selected.status === 'active' && (
                                        <button onClick={handleTake} className="btn-primary py-1.5 px-3 text-xs">
                                            🎧 Tomar
                                        </button>
                                    )}

                                    {isAdmin && selected.status === 'in_agent' && (
                                        <div className="relative">
                                            <button
                                                onClick={() => setShowTransfer(!showTransfer)}
                                                className="btn-ghost py-1.5 px-3 text-xs border border-[#e4ede8]"
                                            >
                                                🔄 Transferir
                                            </button>
                                            {showTransfer && (
                                                <div className="absolute right-0 top-full mt-1 bg-white border border-[#e4ede8] rounded-xl shadow-lg z-10 w-48 py-1">
                                                    {agents
                                                        .filter(a => a.id !== (agent?.agent_id || agent?.id))
                                                        .map((a: any) => (
                                                            <button key={a.id} onClick={() => handleTransfer(a.id)}
                                                                className="w-full text-left px-3 py-2 text-xs hover:bg-brand-50 text-brand-800">
                                                                {a.name}{' '}
                                                                <span className="text-[#6b8a78]">({a.current_load} activas)</span>
                                                            </button>
                                                        ))}
                                                </div>
                                            )}
                                        </div>
                                    )}

                                    {selected.status !== 'completed' && selected.status !== 'closed' && (
                                        <button onClick={handleClose}
                                            className="btn-ghost py-1.5 px-3 text-xs border border-red-200 text-red-500 hover:bg-red-50">
                                            ✓ Cerrar
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* ── Resumen IA ──────────────────────────────── */}
                            {selected.ai_summary && (
                                <div className="mx-4 mt-3 p-3 bg-blue-50 border border-blue-200 rounded-xl">
                                    <div className="text-xs font-semibold text-blue-700 mb-1">
                                        🤖 Resumen IA de la conversación
                                    </div>
                                    <p className="text-xs text-blue-800 whitespace-pre-line">
                                        {selected.ai_summary}
                                    </p>
                                    {selected.escalation_reason && (
                                        <div className="mt-1.5 text-[10px] text-blue-600">
                                            <strong>Motivo escalada:</strong>{' '}
                                            {selected.escalation_reason}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* ── Mensajes ────────────────────────────────── */}
                            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-2">
                                {selected.messages.map(msg => (
                                    <div key={msg.id} className={`flex ${msg.direction === 'outbound' ? 'justify-end' : 'justify-start'}`}>
                                        <div className={`max-w-[75%] rounded-2xl px-3.5 py-2.5 text-sm ${
                                            msg.direction === 'outbound'
                                                ? msg.sent_by_bot
                                                    ? 'bg-brand-600 text-white rounded-br-sm'
                                                    : 'bg-blue-600 text-white rounded-br-sm'
                                                : 'bg-white text-brand-900 border border-[#e4ede8] rounded-bl-sm shadow-sm'
                                        }`}>
                                            {msg.direction === 'outbound' && (
                                                <div className="text-[9px] opacity-70 mb-0.5">
                                                    {msg.sent_by_bot ? '🤖 Bot' : '👤 Agente'}
                                                </div>
                                            )}
                                            <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                                            <div className="text-[9px] mt-1 opacity-60 text-right">
                                                {new Date(msg.created_at).toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' })}
                                            </div>
                                        </div>
                                    </div>
                                ))}

                                {selected.messages.length === 0 && (
                                    <div className="text-center py-8 text-sm text-[#6b8a78]">
                                        Sin mensajes aún
                                    </div>
                                )}

                                <div ref={messagesEndRef} />
                            </div>

                            {/* ── Input de respuesta ──────────────────────── */}
                            {canRespond && selected.status !== 'completed' && selected.status !== 'closed' ? (
                                <div className="bg-white border-t border-[#e4ede8] px-4 py-3">
                                    <div className="flex gap-2 items-end">
                                        <textarea
                                            className="input flex-1 resize-none min-h-[44px] max-h-32 text-sm"
                                            placeholder="Escribe tu respuesta al cliente..."
                                            value={message}
                                            onChange={e => setMessage(e.target.value)}
                                            onKeyDown={e => {
                                                if (e.key === 'Enter' && !e.shiftKey) {
                                                    e.preventDefault()
                                                    handleSend()
                                                }
                                            }}
                                            rows={1}
                                        />
                                        <button onClick={handleSend} disabled={sending || !message.trim()}
                                            className="btn-primary px-4 py-2.5 flex-shrink-0 disabled:opacity-40">
                                            {sending ? (
                                                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                                                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".3"/>
                                                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
                                                </svg>
                                            ) : (
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                    <line x1="22" y1="2" x2="11" y2="13"/>
                                                    <polygon points="22,2 15,22 11,13 2,9"/>
                                                </svg>
                                            )}
                                        </button>
                                    </div>
                                    <p className="text-[10px] text-[#6b8a78] mt-1.5">
                                        Enter para enviar · Shift+Enter para nueva línea
                                    </p>
                                </div>
                            ) : (
                                <div className="bg-gray-50 border-t border-[#e4ede8] px-4 py-3 text-center text-xs text-[#6b8a78]">
                                    {selected.status === 'completed' || selected.status === 'closed'
                                        ? '✓ Conversación cerrada'
                                        : 'Toma la conversación para poder responder'}
                                </div>
                            )}
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}
