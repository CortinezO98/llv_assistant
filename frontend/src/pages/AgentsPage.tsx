import { useEffect, useState } from 'react'
import Icons from '../components/Icons'
import { agentsApi, dashboardApi } from '../api/client'
import { useToast } from '../components/Toast'
import { useAuth } from '../context/AuthContext'

interface Agent {
  id: number; name: string; email: string; role: string
  location: string; is_active: number; current_load: number; total_closed: number
}
interface AgentSat { agent_id: number; agent_name: string; avg_score: number; total_surveys: number }

const ROLE_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  admin:      { bg: '#C6A96B20', color: '#8a6d3a',  label: 'Admin' },
  supervisor: { bg: '#3b82f620', color: '#1e40af',  label: 'Supervisor' },
  agent:      { bg: '#0b4c4520', color: '#0b4c45',  label: 'Agente' },
  superadmin: { bg: '#7c3aed20', color: '#7c3aed',  label: 'Superadmin' },
}
const LOC: Record<string, string> = {
  puerto_rico: '🇵🇷 Puerto Rico', latam: '🌎 LATAM',
}

function LoadBar({ load, max = 10 }: { load: number; max?: number }) {
  const pct   = Math.min(Math.round(load / max * 100), 100)
  const color = load === 0 ? '#1D9E75' : load < 5 ? '#EF9F27' : '#E24B4A'
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono font-bold text-sm w-4" style={{ color }}>{load}</span>
      <div className="w-16 h-1.5 rounded-full bg-[#F5F1EB]">
        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

export default function AgentsPage() {
  const toast = useToast()
  const { agent: me } = useAuth()
  const canEdit = me?.role === 'admin' || me?.role === 'superadmin'

  const [agents, setAgents]   = useState<Agent[]>([])
  const [sat, setSat]         = useState<AgentSat[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'agent', location: 'latam' })
  const [saving, setSaving]   = useState(false)
  const [tab, setTab]         = useState<'agents' | 'metrics'>('agents')

  const load = () => {
    setLoading(true)
    Promise.all([
      agentsApi.list(),
      dashboardApi.getSatisfaction(30),
    ]).then(([a, s]) => {
      setAgents(a.data)
      setSat(s.data || [])
    }).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!form.name || !form.email || !form.password) { toast.warning('Completa todos los campos'); return }
    setSaving(true)
    try {
      await agentsApi.create(form)
      setShowForm(false)
      setForm({ name: '', email: '', password: '', role: 'agent', location: 'latam' })
      load()
      toast.success('Agente creado', `${form.name} fue agregado exitosamente`)
    } catch (e: any) {
      toast.error('Error', e.response?.data?.detail || 'Intenta de nuevo')
    } finally { setSaving(false) }
  }

  const toggleActive = async (a: Agent) => {
    await agentsApi.update(a.id, { is_active: a.is_active ? 0 : 1 })
    toast.info(a.is_active ? 'Agente desactivado' : 'Agente activado', a.name)
    load()
  }

  const active   = agents.filter(a => a.is_active)
  const inactive = agents.filter(a => !a.is_active)

  // Métricas calculadas
  const totalLoad    = agents.reduce((s, a) => s + (a.current_load || 0), 0)
  const totalClosed  = agents.reduce((s, a) => s + (a.total_closed || 0), 0)
  const avgSat       = sat.length ? (sat.reduce((s, a) => s + a.avg_score, 0) / sat.length).toFixed(2) : '—'

  return (
    <div className="p-6 max-w-6xl mx-auto">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-[#0b4c45]">Agentes</h1>
          <p className="text-sm text-[#7a6a55] mt-0.5">
            {active.length} activos · {inactive.length} inactivos · {totalLoad} conv. activas ahora
          </p>
        </div>
        {canEdit && (
          <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
            + Nuevo agente
          </button>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-5">
        {[
          { l: 'Agentes activos',     v: active.length,  color: '#1D9E75' },
          { l: 'Carga total activa',  v: totalLoad,      color: totalLoad > 10 ? '#E24B4A' : '#EF9F27' },
          { l: 'Total cierres',       v: totalClosed,    color: '#0b4c45' },
          { l: 'Satisfacción prom.',  v: avgSat !== '—' ? `${avgSat} ⭐` : '—', color: '#C6A96B' },
        ].map(k => (
          <div key={k.l} className="bg-white rounded-2xl border border-[#e5ddd4] p-4">
            <div className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mb-1">{k.l}</div>
            <div className="font-display text-3xl font-bold" style={{ color: k.color }}>{k.v}</div>
          </div>
        ))}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-[#F5F1EB] p-1 rounded-xl mb-5 w-fit">
        {[{ id: 'agents', l: '👥 Agentes' }, { id: 'metrics', l: '📊 Métricas en tiempo real' }].map(t => (
          <button key={t.id} onClick={() => setTab(t.id as any)}
            className="px-4 py-2 rounded-lg text-sm font-semibold transition-all"
            style={tab === t.id ? { background: '#0b4c45', color: 'white' } : { color: '#7a6a55' }}>
            {t.l}
          </button>
        ))}
      </div>

      {/* Form */}
      {showForm && canEdit && (
        <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5 mb-5 animate-fade-in">
          <h3 className="font-semibold text-[#0b4c45] mb-4 text-sm">Crear nuevo agente</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Nombre completo',    key: 'name',     type: 'text',     ph: 'Ana García' },
              { label: 'Correo electrónico', key: 'email',    type: 'email',    ph: 'ana@llvclinic.com' },
              { label: 'Contraseña inicial', key: 'password', type: 'password', ph: '••••••••' },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-xs font-semibold text-[#7a6a55] mb-1">{f.label}</label>
                <input className="input" type={f.type} placeholder={f.ph}
                  value={(form as any)[f.key]} onChange={e => setForm({...form, [f.key]: e.target.value})} />
              </div>
            ))}
            <div>
              <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Rol</label>
              <select className="input" value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
                <option value="agent">Agente</option>
                <option value="supervisor">Supervisor</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#7a6a55] mb-1">Ubicación</label>
              <select className="input" value={form.location} onChange={e => setForm({...form, location: e.target.value})}>
                <option value="puerto_rico">Puerto Rico</option>
                <option value="latam">LATAM</option>
              </select>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button className="btn-primary" onClick={handleCreate} disabled={saving}>
              {saving ? 'Guardando...' : 'Crear agente'}
            </button>
            <button className="btn-ghost" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </div>
      )}

      {/* Tab: Agentes */}
      {tab === 'agents' && (
        <div className="bg-white rounded-2xl border border-[#e5ddd4] overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-[#e5ddd4]" style={{ background: '#F5F1EB' }}>
                {['Agente', 'Rol', 'Ubicación', 'Carga activa', 'Cierres', 'Satisfacción', 'Estado'].map(h => (
                  <th key={h} className="text-left px-4 py-3 text-xs font-semibold text-[#7a6a55] uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="text-center py-12 text-sm text-[#7a6a55]">Cargando...</td></tr>
              ) : agents.map(a => {
                const rs      = ROLE_STYLE[a.role] || ROLE_STYLE.agent
                const satData = sat.find(s => s.agent_name === a.name)
                return (
                  <tr key={a.id} className="border-b border-[#f5f1eb] hover:bg-[#fafaf8] transition-colors">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                          style={{ background: '#0b4c45', color: '#C6A96B' }}>
                          {a.name.charAt(0)}
                        </div>
                        <div>
                          <div className="text-sm font-semibold text-[#0b4c45]">{a.name}</div>
                          <div className="text-xs text-[#7a6a55]">{a.email}</div>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-md"
                        style={{ background: rs.bg, color: rs.color }}>{rs.label}</span>
                    </td>
                    <td className="px-4 py-3 text-sm text-[#7a6a55]">{LOC[a.location] || a.location}</td>
                    <td className="px-4 py-3">
                      <LoadBar load={a.current_load || 0} />
                    </td>
                    <td className="px-4 py-3 text-center font-mono font-bold text-sm text-[#0b4c45]">
                      {a.total_closed}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {satData ? (
                        <div className="text-sm font-bold text-[#C6A96B]">
                          {'⭐'.repeat(Math.round(satData.avg_score))} {satData.avg_score}
                          <div className="text-xs text-[#7a6a55] font-normal">({satData.total_surveys} enc.)</div>
                        </div>
                      ) : <span className="text-xs text-[#7a6a55]">Sin datos</span>}
                    </td>
                    <td className="px-4 py-3">
                      {canEdit ? (
                        <button onClick={() => toggleActive(a)}
                          className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all"
                          style={a.is_active
                            ? { background: '#1D9E7520', color: '#0F6E56' }
                            : { background: '#E24B4A20', color: '#A32D2D' }}>
                          {a.is_active ? '● Activo' : '○ Inactivo'}
                        </button>
                      ) : (
                        <span className="text-xs font-semibold" style={{ color: a.is_active ? '#1D9E75' : '#E24B4A' }}>
                          {a.is_active ? '● Activo' : '○ Inactivo'}
                        </span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Métricas en tiempo real */}
      {tab === 'metrics' && (
        <div className="space-y-4">
          {/* Distribución de carga */}
          <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5">
            <h3 className="font-semibold text-[#0b4c45] mb-4 text-sm">📊 Carga activa por agente</h3>
            {agents.filter(a => a.is_active).length === 0 ? (
              <p className="text-sm text-[#7a6a55] text-center py-4">Sin agentes activos</p>
            ) : (
              <div className="space-y-3">
                {agents.filter(a => a.is_active).sort((a,b) => b.current_load - a.current_load).map(a => {
                  const maxLoad = Math.max(...agents.map(x => x.current_load || 0), 1)
                  const pct     = Math.round((a.current_load || 0) / maxLoad * 100)
                  const color   = (a.current_load || 0) === 0 ? '#1D9E75' : (a.current_load || 0) < 5 ? '#EF9F27' : '#E24B4A'
                  return (
                    <div key={a.id} className="flex items-center gap-3">
                      <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                        style={{ background: '#0b4c45' }}>
                        {a.name.charAt(0)}
                      </div>
                      <span className="text-sm text-[#1a1208] w-32 flex-shrink-0 truncate">{a.name}</span>
                      <div className="flex-1 h-2 rounded-full bg-[#F5F1EB]">
                        <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, background: color }} />
                      </div>
                      <span className="font-bold text-sm w-6 text-right" style={{ color }}>{a.current_load || 0}</span>
                      <span className="text-xs text-[#7a6a55] w-12">activas</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Satisfacción por agente */}
          <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5">
            <h3 className="font-semibold text-[#0b4c45] mb-4 text-sm">⭐ Satisfacción últimos 30 días</h3>
            {sat.length === 0 ? (
              <p className="text-sm text-[#7a6a55] text-center py-4">Sin encuestas registradas</p>
            ) : (
              <div className="space-y-3">
                {sat.sort((a,b) => b.avg_score - a.avg_score).map((s, i) => (
                  <div key={s.agent_id} className="flex items-center gap-3">
                    <span className="w-5 h-5 rounded-full inline-flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                      style={{ background: '#0b4c45' }}>{i+1}</span>
                    <span className="text-sm text-[#1a1208] flex-1">{s.agent_name}</span>
                    <div className="text-right">
                      <span className="font-bold text-[#C6A96B]">{'⭐'.repeat(Math.round(s.avg_score))} {s.avg_score}</span>
                      <div className="text-xs text-[#7a6a55]">{s.total_surveys} encuestas</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Ranking por cierres */}
          <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5">
            <h3 className="font-semibold text-[#0b4c45] mb-4 text-sm">🏆 Ranking de cierres totales</h3>
            {agents.filter(a => a.total_closed > 0).length === 0 ? (
              <p className="text-sm text-[#7a6a55] text-center py-4">Sin cierres registrados</p>
            ) : (
              <div className="space-y-2">
                {[...agents].sort((a,b) => b.total_closed - a.total_closed).slice(0,10).map((a, i) => {
                  const maxC = agents[0]?.total_closed || 1
                  return (
                    <div key={a.id} className="flex items-center gap-3">
                      <span className="w-5 h-5 rounded-full inline-flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
                        style={{ background: i === 0 ? '#C6A96B' : '#0b4c45' }}>{i+1}</span>
                      <div className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
                        style={{ background: '#F5F1EB', color: '#0b4c45' }}>{a.name.charAt(0)}</div>
                      <span className="text-sm text-[#1a1208] flex-1 truncate">{a.name}</span>
                      <div className="w-24 h-1.5 rounded-full bg-[#F5F1EB]">
                        <div className="h-full rounded-full" style={{ width: `${Math.round(a.total_closed/maxC*100)}%`, background: '#0b4c45' }} />
                      </div>
                      <span className="font-bold text-sm text-[#0b4c45] w-8 text-right">{a.total_closed}</span>
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
