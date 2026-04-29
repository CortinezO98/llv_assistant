import { useEffect, useState } from 'react'
import { Clock, CheckCircle } from 'lucide-react'
import Icons from '../components/Icons'
import { appointmentsApi } from '../api/client'
import { useToast } from '../components/Toast'

const STATUS_STYLE: Record<string, { bg: string; color: string; label: string; Icon: any }> = {
  pending_confirm: { bg: '#FAEEDA', color: '#633806', label: 'Pendiente', Icon: Clock },
  confirmed:       { bg: '#E1F5EE', color: '#0F6E56', label: 'Confirmada', Icon: CheckCircle },
  cancelled:       { bg: '#FCEBEB', color: '#791F1F', label: 'Cancelada', Icon: Clock },
  completed:       { bg: '#0b4c4515', color: '#0b4c45', label: 'Completada', Icon: CheckCircle },
}

const CLINIC_LABEL: Record<string, string> = {
  arecibo: 'Arecibo',
  bayamon: 'Bayamón',
  latam: 'LATAM',
  virtual: 'Virtual',
}

export function AppointmentsPage() {
  const toast = useToast()
  const [appointments, setAppointments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  const load = () => {
    setLoading(true)

    appointmentsApi
      .list(filter || undefined)
      .then((r) => setAppointments(r.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [filter])

  const confirm = async (id: number, name: string) => {
    await appointmentsApi.confirm(id)
    toast.success('Cita confirmada', `Se confirmó la cita de ${name}`)
    load()
  }

  const FILTERS = ['', 'pending_confirm', 'confirmed', 'completed']

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
            Citas
          </h1>
          <p className="text-sm text-[#7a6a55] mt-0.5">
            {appointments.length} citas registradas por el bot
          </p>
        </div>

        <div className="flex gap-1.5">
          {FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={
                filter === s
                  ? { background: '#0b4c45', color: 'white' }
                  : {
                      background: 'white',
                      border: '1px solid #e5ddd4',
                      color: '#7a6a55',
                    }
              }
            >
              {s === '' ? 'Todas' : STATUS_STYLE[s]?.label || s}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl border border-[#e5ddd4] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr
              className="border-b border-[#e5ddd4]"
              style={{ background: '#F5F1EB' }}
            >
              {['Paciente', 'Servicio', 'Fecha', 'Clínica', 'Estado', 'Acción'].map(
                (h) => (
                  <th
                    key={h}
                    className="text-left px-4 py-3 text-xs font-semibold text-[#7a6a55] uppercase tracking-wider"
                  >
                    {h}
                  </th>
                )
              )}
            </tr>
          </thead>

          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center py-12 text-sm text-[#7a6a55]">
                  Cargando...
                </td>
              </tr>
            ) : appointments.length === 0 ? (
              <tr>
                <td colSpan={6}>
                  <div className="flex flex-col items-center py-12 text-center">
                    <Icons.Stethoscope />
                    <p className="text-sm font-semibold text-[#7a6a55]">
                      Sin citas
                      {filter ? ` con estado "${STATUS_STYLE[filter]?.label}"` : ''}
                    </p>
                    <p className="text-xs text-[#7a6a55]/60 mt-0.5">
                      Las citas registradas por el bot aparecerán aquí
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              appointments.map((a) => {
                const ss = STATUS_STYLE[a.status] || STATUS_STYLE.pending_confirm
                const StatusIcon = ss.Icon

                return (
                  <tr key={a.id} className="table-row">
                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <div
                          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                          style={{ background: '#F5F1EB', color: '#0b4c45' }}
                        >
                          {a.full_name?.charAt(0) || '?'}
                        </div>

                        <div>
                          <div className="text-sm font-semibold text-[#0b4c45]">
                            {a.full_name}
                          </div>
                          <div className="text-xs font-mono text-[#7a6a55]">
                            {a.phone}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1.5 text-sm text-[#0b4c45] max-w-[200px]">
                        <Icons.MapPin />
                        <span className="truncate">{a.service}</span>
                      </div>
                    </td>

                    <td className="px-4 py-3.5 text-sm font-mono text-[#7a6a55]">
                      {a.preferred_date || '—'}
                    </td>

                    <td className="px-4 py-3.5">
                      <div className="flex items-center gap-1 text-xs text-[#7a6a55]">
                        <Icons.MapPin />
                        {CLINIC_LABEL[a.clinic] || a.clinic}
                      </div>
                    </td>

                    <td className="px-4 py-3.5">
                      <span
                        className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg"
                        style={{ background: ss.bg, color: ss.color }}
                      >
                        <StatusIcon size={11} />
                        {ss.label}
                      </span>
                    </td>

                    <td className="px-4 py-3.5">
                      {a.status === 'pending_confirm' && (
                        <button
                          onClick={() => confirm(a.id, a.full_name)}
                          className="flex items-center gap-1 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all hover:opacity-80"
                          style={{ background: '#0b4c45', color: 'white' }}
                        >
                          <Icons.Check />
                          Confirmar
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}