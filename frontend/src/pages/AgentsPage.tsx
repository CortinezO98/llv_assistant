import { useEffect, useState } from 'react'
import { agentsApi } from '../api/client'

interface Agent {
  id: number; name: string; email: string; role: string
  location: string; is_active: number; current_load: number; total_closed: number
}

const roleColors: Record<string, string> = {
  admin: 'bg-violet-100 text-violet-700',
  supervisor: 'bg-blue-100 text-blue-700',
  agent: 'bg-brand-100 text-brand-700',
}
const locationLabels: Record<string, string> = {
  puerto_rico: '🇵🇷 Puerto Rico',
  latam: '🌎 LATAM',
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'agent', location: 'latam' })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const load = () => {
    setLoading(true)
    agentsApi.list().then(r => setAgents(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    setSaving(true); setError('')
    try {
      await agentsApi.create(form)
      setShowForm(false)
      setForm({ name: '', email: '', password: '', role: 'agent', location: 'latam' })
      load()
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Error al crear agente')
    } finally { setSaving(false) }
  }

  const toggleActive = async (agent: Agent) => {
    await agentsApi.update(agent.id, { is_active: agent.is_active ? 0 : 1 })
    load()
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-brand-800">Agentes</h1>
          <p className="text-sm text-[#6b8a78] mt-0.5">Gestión del equipo operativo ({agents.filter(a => a.is_active).length} activos)</p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          <span>+</span> Nuevo agente
        </button>
      </div>

      {/* Form */}
      {showForm && (
        <div className="card p-5 mb-5 animate-fade-in">
          <h3 className="font-semibold text-brand-800 mb-4">Crear nuevo agente</h3>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-[#6b8a78] mb-1">Nombre completo</label>
              <input className="input" value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="Ana García" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6b8a78] mb-1">Correo electrónico</label>
              <input className="input" type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} placeholder="ana@llvclinic.com" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6b8a78] mb-1">Contraseña inicial</label>
              <input className="input" type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} placeholder="••••••••" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6b8a78] mb-1">Rol</label>
              <select className="input" value={form.role} onChange={e => setForm({...form, role: e.target.value})}>
                <option value="agent">Agente</option>
                <option value="supervisor">Supervisor</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6b8a78] mb-1">Ubicación</label>
              <select className="input" value={form.location} onChange={e => setForm({...form, location: e.target.value})}>
                <option value="puerto_rico">Puerto Rico</option>
                <option value="latam">LATAM</option>
              </select>
            </div>
          </div>
          {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
          <div className="flex gap-2 mt-4">
            <button className="btn-primary" onClick={handleCreate} disabled={saving}>
              {saving ? 'Guardando...' : 'Crear agente'}
            </button>
            <button className="btn-ghost" onClick={() => setShowForm(false)}>Cancelar</button>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#e4ede8] bg-brand-50/50">
              <th className="text-left px-5 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Agente</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Rol</th>
              <th className="text-left px-5 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Ubicación</th>
              <th className="text-center px-5 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Carga activa</th>
              <th className="text-center px-5 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Cerradas</th>
              <th className="text-center px-5 py-3 text-xs font-semibold text-[#6b8a78] uppercase tracking-wider">Estado</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-12 text-[#6b8a78] text-sm">Cargando...</td></tr>
            ) : agents.map((a) => (
              <tr key={a.id} className="table-row">
                <td className="px-5 py-3.5">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-brand-600 rounded-full flex items-center justify-center text-white text-xs font-bold">
                      {a.name.charAt(0)}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-brand-800">{a.name}</div>
                      <div className="text-xs text-[#6b8a78]">{a.email}</div>
                    </div>
                  </div>
                </td>
                <td className="px-5 py-3.5">
                  <span className={`badge ${roleColors[a.role] || 'bg-gray-100 text-gray-600'}`}>{a.role}</span>
                </td>
                <td className="px-5 py-3.5 text-sm text-[#6b8a78]">{locationLabels[a.location] || a.location}</td>
                <td className="px-5 py-3.5 text-center">
                  <span className={`font-mono font-bold text-sm ${a.current_load > 0 ? 'text-amber-600' : 'text-brand-600'}`}>
                    {a.current_load}
                  </span>
                </td>
                <td className="px-5 py-3.5 text-center font-mono text-sm font-semibold text-brand-700">{a.total_closed}</td>
                <td className="px-5 py-3.5 text-center">
                  <button
                    onClick={() => toggleActive(a)}
                    className={`badge cursor-pointer transition-all hover:opacity-80 ${a.is_active ? 'bg-teal-100 text-teal-700' : 'bg-red-100 text-red-600'}`}
                  >
                    <span className={`w-1.5 h-1.5 rounded-full ${a.is_active ? 'bg-teal-500 animate-pulse-dot' : 'bg-red-400'}`} />
                    {a.is_active ? 'Activo' : 'Inactivo'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
