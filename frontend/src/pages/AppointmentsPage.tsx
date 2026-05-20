import { useEffect, useState } from 'react'
import { Clock, CheckCircle, Download } from 'lucide-react'
import Icons from '../components/Icons'
import { appointmentsApi, api } from '../api/client'
import { useToast } from '../components/Toast'

const STATUS_STYLE: Record<string, { bg: string; color: string; label: string; Icon: any }> = {
  pending_confirm: { bg: '#FAEEDA', color: '#633806', label: 'Pendiente', Icon: Clock },
  confirmed: { bg: '#E1F5EE', color: '#0F6E56', label: 'Confirmada', Icon: CheckCircle },
  cancelled: { bg: '#FCEBEB', color: '#791F1F', label: 'Cancelada', Icon: Clock },
  completed: { bg: '#0b4c4515', color: '#0b4c45', label: 'Completada', Icon: CheckCircle },
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
  const [exporting, setExporting] = useState(false)

  const load = () => {
    setLoading(true)

    appointmentsApi
      .list(filter || undefined)
      .then((response) => setAppointments(response.data))
      .catch(() => {
        toast.error('Error cargando citas', 'No fue posible cargar las citas.')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [filter])

  const confirm = async (id: number, name: string) => {
    try {
      await appointmentsApi.confirm(id)

      toast.success('Cita confirmada', `Se confirmó la cita de ${name}`)

      load()
    } catch {
      toast.error('Error confirmando cita', 'No fue posible confirmar la cita.')
    }
  }

  const exportExcel = async () => {
    setExporting(true)

    try {
      const params = new URLSearchParams()

      if (filter) {
        params.set('status', filter)
      }

      const url = `/appointments/export/excel${
        params.toString() ? `?${params.toString()}` : ''
      }`

      const response = await api.get(url, {
        responseType: 'blob',
      })

      const blob = new Blob([response.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })

      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')

      link.href = downloadUrl
      link.download = `Citas_Vagaro_${new Date().toISOString().slice(0, 10)}.xlsx`

      document.body.appendChild(link)
      link.click()
      link.remove()

      window.URL.revokeObjectURL(downloadUrl)

      toast.success('Excel generado', 'El archivo de citas fue descargado correctamente.')
    } catch {
      toast.error('Error exportando Excel', 'No fue posible descargar el archivo.')
    } finally {
      setExporting(false)
    }
  }

  const FILTERS = ['', 'pending_confirm', 'confirmed', 'completed', 'cancelled']

  return (
    <div className="page-mobile p-4 sm:p-6 max-w-5xl mx-auto w-full min-w-0">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
            Citas
          </h1>

          <p className="text-sm text-[#7a6a55] mt-0.5">
            {appointments.length} citas registradas por el bot
          </p>
        </div>

        <div className="flex flex-col gap-2 w-full sm:w-auto">
          <button
            onClick={exportExcel}
            disabled={exporting}
            className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-all hover:opacity-90 disabled:opacity-60"
            style={{ background: '#0b4c45', color: 'white' }}
          >
            <Download size={14} />
            {exporting ? 'Exportando...' : 'Exportar Excel Vagaro'}
          </button>

          <div className="flex flex-wrap gap-1.5">
            {FILTERS.map((status) => (
              <button
                key={status || 'all'}
                onClick={() => setFilter(status)}
                className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                style={
                  filter === status
                    ? { background: '#0b4c45', color: 'white' }
                    : {
                        background: 'white',
                        border: '1px solid #e5ddd4',
                        color: '#7a6a55',
                      }
                }
              >
                {status === '' ? 'Todas' : STATUS_STYLE[status]?.label || status}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-2xl border border-[#e5ddd4] overflow-hidden">
        <div className="overflow-x-auto mobile-scroll-x">
          <table className="w-full min-w-[850px]">
            <thead>
              <tr
                className="border-b border-[#e5ddd4]"
                style={{ background: '#F5F1EB' }}
              >
                {['Paciente', 'Servicio', 'Fecha', 'Clínica', 'Estado', 'Acción'].map(
                  (header) => (
                    <th
                      key={header}
                      className="text-left px-4 py-3 text-xs font-semibold text-[#7a6a55] uppercase tracking-wider whitespace-nowrap"
                    >
                      {header}
                    </th>
                  )
                )}
              </tr>
            </thead>

            <tbody>
              {loading ? (
                <tr>
                  <td
                    colSpan={6}
                    className="text-center py-12 text-sm text-[#7a6a55]"
                  >
                    Cargando...
                  </td>
                </tr>
              ) : appointments.length === 0 ? (
                <tr>
                  <td colSpan={6}>
                    <div className="flex flex-col items-center py-12 text-center px-4">
                      <Icons.Stethoscope />

                      <p className="text-sm font-semibold text-[#7a6a55] mt-2">
                        Sin citas
                        {filter ? ` con estado "${STATUS_STYLE[filter]?.label}"` : ''}
                      </p>

                      <p className="text-xs text-[#7a6a55]/60 mt-0.5">
                        Las citas registradas por el bot aparecerán aquí.
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                appointments.map((appointment) => {
                  const statusStyle =
                    STATUS_STYLE[appointment.status] || STATUS_STYLE.pending_confirm

                  const StatusIcon = statusStyle.Icon

                  return (
                    <tr key={appointment.id} className="table-row">
                      <td className="px-4 py-3.5 min-w-[210px]">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div
                            className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                            style={{ background: '#F5F1EB', color: '#0b4c45' }}
                          >
                            {appointment.full_name?.charAt(0) || '?'}
                          </div>

                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-[#0b4c45] max-w-[180px] truncate">
                              {appointment.full_name || 'Paciente'}
                            </div>

                            <div className="text-xs font-mono text-[#7a6a55] whitespace-nowrap">
                              {appointment.phone || '—'}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="px-4 py-3.5 min-w-[230px]">
                        <div className="flex items-center gap-1.5 text-sm text-[#0b4c45] max-w-[220px] min-w-0">
                          <Icons.MapPin />
                          <span className="truncate">
                            {appointment.service || '—'}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3.5 text-sm font-mono text-[#7a6a55] whitespace-nowrap">
                        {appointment.preferred_date || '—'}
                      </td>

                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <div className="flex items-center gap-1 text-xs text-[#7a6a55] whitespace-nowrap">
                          <Icons.MapPin />
                          {CLINIC_LABEL[appointment.clinic] || appointment.clinic || '—'}
                        </div>
                      </td>

                      <td className="px-4 py-3.5 whitespace-nowrap">
                        <span
                          className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-lg whitespace-nowrap"
                          style={{
                            background: statusStyle.bg,
                            color: statusStyle.color,
                          }}
                        >
                          <StatusIcon size={11} />
                          {statusStyle.label}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 whitespace-nowrap">
                        {appointment.status === 'pending_confirm' ? (
                          <button
                            onClick={() =>
                              confirm(appointment.id, appointment.full_name || 'paciente')
                            }
                            className="inline-flex items-center justify-center gap-1 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all hover:opacity-80 whitespace-nowrap"
                            style={{ background: '#0b4c45', color: 'white' }}
                          >
                            <Icons.Check />
                            Confirmar
                          </button>
                        ) : (
                          <span className="text-xs text-[#7a6a55]">—</span>
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
    </div>
  )
}