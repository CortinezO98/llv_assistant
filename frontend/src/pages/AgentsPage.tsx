import { useEffect, useState } from 'react'
import type { FC } from 'react'
import Icons from '../components/Icons'
import { agentsApi, dashboardApi } from '../api/client'
import { useToast } from '../components/Toast'
import { useAuth } from '../context/AuthContext'

interface Agent {
  id: number
  name: string
  email: string
  role: string
  location: string
  is_active: number
  current_load: number
  total_closed: number
}

interface AgentSat {
  agent_id: number
  agent_name: string
  avg_score: number
  total_surveys: number
}

const ROLE_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  admin: {
    bg: '#C6A96B20',
    color: '#8a6d3a',
    label: 'Admin',
  },
  supervisor: {
    bg: '#3b82f620',
    color: '#1e40af',
    label: 'Supervisor',
  },
  agent: {
    bg: '#0b4c4520',
    color: '#0b4c45',
    label: 'Agente',
  },
  superadmin: {
    bg: '#7c3aed20',
    color: '#7c3aed',
    label: 'Superadmin',
  },
}

const LOC: Record<string, string> = {
  puerto_rico: '🇵🇷 Puerto Rico',
  latam: '🌎 LATAM',
}

function LoadBar({ load, max = 10 }: { load: number; max?: number }) {
  const pct = Math.min(Math.round((load / max) * 100), 100)
  const color = load === 0 ? '#1D9E75' : load < 5 ? '#EF9F27' : '#E24B4A'

  return (
    <div className="flex items-center gap-2 min-w-0">
      <span
        className="font-mono font-bold text-sm w-5 flex-shrink-0"
        style={{ color }}
      >
        {load}
      </span>

      <div className="w-20 h-1.5 rounded-full bg-[#F5F1EB] overflow-hidden">
        <div
          className="h-full rounded-full transition-all"
          style={{
            width: `${pct}%`,
            background: color,
          }}
        />
      </div>
    </div>
  )
}

function MetricCard({
  label,
  value,
  color,
}: {
  label: string
  value: string | number
  color: string
}) {
  return (
    <div className="bg-white rounded-2xl border border-[#e5ddd4] p-4 min-w-0">
      <div className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-1 truncate">
        {label}
      </div>

      <div
        className="font-display text-2xl sm:text-3xl font-bold break-words"
        style={{ color }}
      >
        {value}
      </div>
    </div>
  )
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="font-semibold text-[#0b4c45] mb-4 text-sm min-w-0 truncate">
      {children}
    </h3>
  )
}

export default function AgentsPage() {
  const toast = useToast()
  const { agent: me } = useAuth()

  const canEdit = me?.role === 'admin' || me?.role === 'superadmin'

  const [agents, setAgents] = useState<Agent[]>([])
  const [sat, setSat] = useState<AgentSat[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    role: 'agent',
    location: 'latam',
  })

  const [saving, setSaving] = useState(false)
  const [tab, setTab] = useState<'agents' | 'metrics'>('agents')

  const load = () => {
    setLoading(true)

    Promise.all([
      agentsApi.list(),
      dashboardApi.getSatisfaction(30),
    ])
      .then(([agentsResponse, satisfactionResponse]) => {
        setAgents(agentsResponse.data)
        setSat(satisfactionResponse.data || [])
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const handleCreate = async () => {
    if (!form.name || !form.email || !form.password) {
      toast.warning('Completa todos los campos')
      return
    }

    setSaving(true)

    try {
      await agentsApi.create(form)

      setShowForm(false)

      setForm({
        name: '',
        email: '',
        password: '',
        role: 'agent',
        location: 'latam',
      })

      load()

      toast.success('Agente creado', `${form.name} fue agregado exitosamente`)
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'Intenta de nuevo')
    } finally {
      setSaving(false)
    }
  }

  const toggleActive = async (agent: Agent) => {
    await agentsApi.update(agent.id, {
      is_active: agent.is_active ? 0 : 1,
    })

    toast.info(
      agent.is_active ? 'Agente desactivado' : 'Agente activado',
      agent.name
    )

    load()
  }

  const active = agents.filter((agent) => agent.is_active)
  const inactive = agents.filter((agent) => !agent.is_active)

  const totalLoad = agents.reduce(
    (sum, agent) => sum + (agent.current_load || 0),
    0
  )

  const totalClosed = agents.reduce(
    (sum, agent) => sum + (agent.total_closed || 0),
    0
  )

  const avgSat = sat.length
    ? (
        sat.reduce((sum, agentSat) => sum + agentSat.avg_score, 0) / sat.length
      ).toFixed(2)
    : '—'

  const activeAgents = agents.filter((agent) => agent.is_active)

  const maxLoad = Math.max(
    ...agents.map((agent) => agent.current_load || 0),
    1
  )

  const maxClosed = Math.max(
    ...agents.map((agent) => agent.total_closed || 0),
    1
  )

  return (
    <div className="page-mobile p-4 sm:p-6 max-w-6xl mx-auto w-full min-w-0">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
            Agentes
          </h1>

          <p className="text-sm text-[#7a6a55] mt-0.5 break-words">
            {active.length} activos · {inactive.length} inactivos · {totalLoad}{' '}
            conv. activas ahora
          </p>
        </div>

        {canEdit && (
          <button
            className="btn-primary w-full sm:w-auto justify-center"
            onClick={() => setShowForm(!showForm)}
          >
            + Nuevo agente
          </button>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        <MetricCard
          label="Agentes activos"
          value={active.length}
          color="#1D9E75"
        />

        <MetricCard
          label="Carga total activa"
          value={totalLoad}
          color={totalLoad > 10 ? '#E24B4A' : '#EF9F27'}
        />

        <MetricCard
          label="Total cierres"
          value={totalClosed}
          color="#0b4c45"
        />

        <MetricCard
          label="Satisfacción prom."
          value={avgSat !== '—' ? `${avgSat} ⭐` : '—'}
          color="#C6A96B"
        />
      </div>

      {/* Tabs */}
      <div className="grid grid-cols-2 gap-1 bg-[#F5F1EB] p-1 rounded-xl mb-5 w-full sm:w-fit">
        {[
          {
            id: 'agents',
            label: '👥 Agentes',
          },
          {
            id: 'metrics',
            label: '📊 Métricas',
          },
        ].map((item) => (
          <button
            key={item.id}
            onClick={() => setTab(item.id as 'agents' | 'metrics')}
            className="px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all truncate"
            style={
              tab === item.id
                ? {
                    background: '#0b4c45',
                    color: 'white',
                  }
                : {
                    color: '#7a6a55',
                  }
            }
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Form */}
      {showForm && canEdit && (
        <div className="bg-white rounded-2xl border border-[#e5ddd4] p-4 sm:p-5 mb-5 animate-fade-in min-w-0">
          <h3 className="font-semibold text-[#0b4c45] mb-4 text-sm">
            Crear nuevo agente
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              {
                label: 'Nombre completo',
                key: 'name',
                type: 'text',
                placeholder: 'Ana García',
              },
              {
                label: 'Correo electrónico',
                key: 'email',
                type: 'email',
                placeholder: 'ana@llvclinic.com',
              },
              {
                label: 'Contraseña inicial',
                key: 'password',
                type: 'password',
                placeholder: '••••••••',
              },
            ].map((field) => (
              <div key={field.key} className="min-w-0">
                <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                  {field.label}
                </label>

                <input
                  className="input"
                  type={field.type}
                  placeholder={field.placeholder}
                  value={(form as any)[field.key]}
                  onChange={(event) =>
                    setForm({
                      ...form,
                      [field.key]: event.target.value,
                    })
                  }
                />
              </div>
            ))}

            <div className="min-w-0">
              <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                Rol
              </label>

              <select
                className="input"
                value={form.role}
                onChange={(event) =>
                  setForm({
                    ...form,
                    role: event.target.value,
                  })
                }
              >
                <option value="agent">Agente</option>
                <option value="supervisor">Supervisor</option>
                <option value="admin">Admin</option>
              </select>
            </div>

            <div className="min-w-0">
              <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                Ubicación
              </label>

              <select
                className="input"
                value={form.location}
                onChange={(event) =>
                  setForm({
                    ...form,
                    location: event.target.value,
                  })
                }
              >
                <option value="puerto_rico">Puerto Rico</option>
                <option value="latam">LATAM</option>
              </select>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 mt-4">
            <button
              className="btn-primary justify-center"
              onClick={handleCreate}
              disabled={saving}
            >
              {saving ? 'Guardando...' : 'Crear agente'}
            </button>

            <button
              className="btn-ghost justify-center"
              onClick={() => setShowForm(false)}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Tab: Agentes */}
      {tab === 'agents' && (
        <div className="bg-white rounded-2xl border border-[#e5ddd4] overflow-hidden">
          <div className="overflow-x-auto mobile-scroll-x">
            <table className="w-full min-w-[900px]">
              <thead>
                <tr
                  className="border-b border-[#e5ddd4]"
                  style={{ background: '#F5F1EB' }}
                >
                  {[
                    'Agente',
                    'Rol',
                    'Ubicación',
                    'Carga activa',
                    'Cierres',
                    'Satisfacción',
                    'Estado',
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
                    <td
                      colSpan={7}
                      className="text-center py-12 text-sm text-[#7a6a55]"
                    >
                      Cargando...
                    </td>
                  </tr>
                ) : agents.length === 0 ? (
                  <tr>
                    <td
                      colSpan={7}
                      className="text-center py-12 text-sm text-[#7a6a55]"
                    >
                      No hay agentes registrados.
                    </td>
                  </tr>
                ) : (
                  agents.map((agent) => {
                    const roleStyle =
                      ROLE_STYLE[agent.role] || ROLE_STYLE.agent

                    const satData = sat.find(
                      (item) => item.agent_name === agent.name
                    )

                    return (
                      <tr
                        key={agent.id}
                        className="border-b border-[#f5f1eb] hover:bg-[#fafaf8] transition-colors"
                      >
                        <td className="px-4 py-3 min-w-[240px]">
                          <div className="flex items-center gap-3 min-w-0">
                            <div
                              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                              style={{
                                background: '#0b4c45',
                                color: '#C6A96B',
                              }}
                            >
                              {agent.name.charAt(0)}
                            </div>

                            <div className="min-w-0">
                              <div className="text-sm font-semibold text-[#0b4c45] max-w-[180px] truncate">
                                {agent.name}
                              </div>

                              <div className="text-xs text-[#7a6a55] max-w-[220px] truncate">
                                {agent.email}
                              </div>
                            </div>
                          </div>
                        </td>

                        <td className="px-4 py-3 whitespace-nowrap">
                          <span
                            className="text-xs font-semibold px-2 py-0.5 rounded-md"
                            style={{
                              background: roleStyle.bg,
                              color: roleStyle.color,
                            }}
                          >
                            {roleStyle.label}
                          </span>
                        </td>

                        <td className="px-4 py-3 text-sm text-[#7a6a55] whitespace-nowrap">
                          {LOC[agent.location] || agent.location}
                        </td>

                        <td className="px-4 py-3 whitespace-nowrap">
                          <LoadBar load={agent.current_load || 0} />
                        </td>

                        <td className="px-4 py-3 text-center font-mono font-bold text-sm text-[#0b4c45] whitespace-nowrap">
                          {agent.total_closed}
                        </td>

                        <td className="px-4 py-3 text-center whitespace-nowrap">
                          {satData ? (
                            <div className="text-sm font-bold text-[#C6A96B]">
                              {'⭐'.repeat(Math.round(satData.avg_score))}{' '}
                              {satData.avg_score}

                              <div className="text-xs text-[#7a6a55] font-normal">
                                ({satData.total_surveys} enc.)
                              </div>
                            </div>
                          ) : (
                            <span className="text-xs text-[#7a6a55]">
                              Sin datos
                            </span>
                          )}
                        </td>

                        <td className="px-4 py-3 whitespace-nowrap">
                          {canEdit ? (
                            <button
                              onClick={() => toggleActive(agent)}
                              className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all"
                              style={
                                agent.is_active
                                  ? {
                                      background: '#1D9E7520',
                                      color: '#0F6E56',
                                    }
                                  : {
                                      background: '#E24B4A20',
                                      color: '#A32D2D',
                                    }
                              }
                            >
                              {agent.is_active ? '● Activo' : '○ Inactivo'}
                            </button>
                          ) : (
                            <span
                              className="text-xs font-semibold"
                              style={{
                                color: agent.is_active
                                  ? '#1D9E75'
                                  : '#E24B4A',
                              }}
                            >
                              {agent.is_active ? '● Activo' : '○ Inactivo'}
                            </span>
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
      )}

      {/* Tab: Métricas en tiempo real */}
      {tab === 'metrics' && (
        <div className="space-y-4">
          {/* Distribución de carga */}
          <div className="bg-white rounded-2xl border border-[#e5ddd4] p-4 sm:p-5 min-w-0">
            <SectionTitle>📊 Carga activa por agente</SectionTitle>

            {activeAgents.length === 0 ? (
              <p className="text-sm text-[#7a6a55] text-center py-4">
                Sin agentes activos
              </p>
            ) : (
              <div className="space-y-3">
                {[...activeAgents]
                  .sort((a, b) => b.current_load - a.current_load)
                  .map((agent) => {
                    const pct = Math.round(
                      ((agent.current_load || 0) / maxLoad) * 100
                    )

                    const color =
                      (agent.current_load || 0) === 0
                        ? '#1D9E75'
                        : (agent.current_load || 0) < 5
                          ? '#EF9F27'
                          : '#E24B4A'

                    return (
                      <div
                        key={agent.id}
                        className="grid grid-cols-[28px_1fr_auto] sm:grid-cols-[28px_140px_1fr_36px_60px] gap-2 sm:gap-3 items-center min-w-0"
                      >
                        <div
                          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                          style={{ background: '#0b4c45' }}
                        >
                          {agent.name.charAt(0)}
                        </div>

                        <span className="text-sm text-[#1a1208] truncate min-w-0">
                          {agent.name}
                        </span>

                        <div className="h-2 rounded-full bg-[#F5F1EB] overflow-hidden min-w-0">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${pct}%`,
                              background: color,
                            }}
                          />
                        </div>

                        <span
                          className="font-bold text-sm text-right"
                          style={{ color }}
                        >
                          {agent.current_load || 0}
                        </span>

                        <span className="hidden sm:inline text-xs text-[#7a6a55]">
                          activas
                        </span>
                      </div>
                    )
                  })}
              </div>
            )}
          </div>

          {/* Satisfacción por agente */}
          <div className="bg-white rounded-2xl border border-[#e5ddd4] p-4 sm:p-5 min-w-0">
            <SectionTitle>⭐ Satisfacción últimos 30 días</SectionTitle>

            {sat.length === 0 ? (
              <p className="text-sm text-[#7a6a55] text-center py-4">
                Sin encuestas registradas
              </p>
            ) : (
              <div className="space-y-3">
                {[...sat]
                  .sort((a, b) => b.avg_score - a.avg_score)
                  .map((item, index) => (
                    <div
                      key={item.agent_id}
                      className="grid grid-cols-[24px_1fr_auto] gap-3 items-center min-w-0"
                    >
                      <span
                        className="w-5 h-5 rounded-full inline-flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                        style={{ background: '#0b4c45' }}
                      >
                        {index + 1}
                      </span>

                      <span className="text-sm text-[#1a1208] truncate min-w-0">
                        {item.agent_name}
                      </span>

                      <div className="text-right flex-shrink-0">
                        <span className="font-bold text-[#C6A96B] text-sm">
                          {'⭐'.repeat(Math.round(item.avg_score))}{' '}
                          {item.avg_score}
                        </span>

                        <div className="text-xs text-[#7a6a55]">
                          {item.total_surveys} encuestas
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          {/* Ranking por cierres */}
          <div className="bg-white rounded-2xl border border-[#e5ddd4] p-4 sm:p-5 min-w-0">
            <SectionTitle>🏆 Ranking de cierres totales</SectionTitle>

            {agents.filter((agent) => agent.total_closed > 0).length === 0 ? (
              <p className="text-sm text-[#7a6a55] text-center py-4">
                Sin cierres registrados
              </p>
            ) : (
              <div className="space-y-2">
                {[...agents]
                  .sort((a, b) => b.total_closed - a.total_closed)
                  .slice(0, 10)
                  .map((agent, index) => {
                    const pct = Math.round(
                      (agent.total_closed / maxClosed) * 100
                    )

                    return (
                      <div
                        key={agent.id}
                        className="grid grid-cols-[24px_28px_1fr_auto] sm:grid-cols-[24px_28px_1fr_110px_42px] gap-2 sm:gap-3 items-center min-w-0"
                      >
                        <span
                          className="w-5 h-5 rounded-full inline-flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                          style={{
                            background:
                              index === 0 ? '#C6A96B' : '#0b4c45',
                          }}
                        >
                          {index + 1}
                        </span>

                        <div
                          className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                          style={{
                            background: '#F5F1EB',
                            color: '#0b4c45',
                          }}
                        >
                          {agent.name.charAt(0)}
                        </div>

                        <span className="text-sm text-[#1a1208] truncate min-w-0">
                          {agent.name}
                        </span>

                        <div className="hidden sm:block w-24 h-1.5 rounded-full bg-[#F5F1EB] overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${pct}%`,
                              background: '#0b4c45',
                            }}
                          />
                        </div>

                        <span className="font-bold text-sm text-[#0b4c45] text-right">
                          {agent.total_closed}
                        </span>
                      </div>
                    )
                  })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}