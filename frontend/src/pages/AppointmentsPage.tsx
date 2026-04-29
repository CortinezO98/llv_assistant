import { useEffect, useState } from 'react'
import { appointmentsApi } from '../api/client'

const statusColors: Record<string, string> = {
  pending_confirm: 'bg-amber-100 text-amber-700',
  confirmed: 'bg-teal-100 text-teal-700',
  cancelled: 'bg-red-100 text-red-600',
  completed: 'bg-brand-100 text-brand-700',
}
const statusLabels: Record<string, string> = {
  pending_confirm: 'Pendiente', confirmed: 'Confirmada',
  cancelled: 'Cancelada', completed: 'Completada',
}
const clinicLabels: Record<string, string> = {
  arecibo: '🏥 Arecibo', bayamon: '🏥 Bayamón',
  latam: '🌎 LATAM', virtual: '💻 Virtual',
}

export function AppointmentsPage() {
  const [appointments, setAppointments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  const load = () => {
    setLoading(true)
    appointmentsApi.list(filter || undefined).then(r => setAppointments(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filter])

  const confirm = async (id: number) => {
    await appointmentsApi.confirm(id)
    load()
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-brand-800">Citas</h1>
          <p className="text-sm text-[#6b8a78] mt-0.5">Solicitudes de agendamiento del bot</p>
        </div>
        <div className="flex gap-1.5">
          {['', 'pending_confirm', 'confirmed', 'completed'].map((s) => (
            <button key={s} onClick={() => setFilter(s)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${filter === s ? 'bg-brand-600 text-white' : 'bg-white border border-[#e4ede8] text-[#6b8a78]'}`}>
              {s === '' ? 'Todas' : statusLabels[s]}
            </button>
          ))}
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#e4ede8] bg-brand-50/50">
              {['Paciente', 'Servicio', 'Fecha preferida', 'Clínica', 'Estado', 'Acción'].map(h => (
                <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-12 text-sm text-[#6b8a78]">Cargando...</td></tr>
            ) : appointments.length === 0 ? (
              <tr><td colSpan={6} className="text-center py-12 text-sm text-[#6b8a78]">Sin citas en este período</td></tr>
            ) : appointments.map((a) => (
              <tr key={a.id} className="table-row">
                <td className="px-4 py-3">
                  <div className="text-sm font-semibold text-brand-800">{a.full_name}</div>
                  <div className="text-xs text-[#6b8a78] font-mono">{a.phone}</div>
                </td>
                <td className="px-4 py-3 text-sm text-brand-700 max-w-xs truncate">{a.service}</td>
                <td className="px-4 py-3 text-sm font-mono text-[#6b8a78]">{a.preferred_date || '—'}</td>
                <td className="px-4 py-3 text-sm text-[#6b8a78]">{clinicLabels[a.clinic] || a.clinic}</td>
                <td className="px-4 py-3">
                  <span className={`badge ${statusColors[a.status] || 'bg-gray-100 text-gray-600'}`}>{statusLabels[a.status] || a.status}</span>
                </td>
                <td className="px-4 py-3">
                  {a.status === 'pending_confirm' && (
                    <button onClick={() => confirm(a.id)} className="btn-primary py-1 px-3 text-xs">
                      ✓ Confirmar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
