import { useEffect, useState } from 'react'
import Icons from '../components/Icons'
import { agentsApi } from '../api/client'
import { useToast } from '../components/Toast'

interface Agent {
  id: number; name: string; email: string; role: string
  location: string; is_active: number; current_load: number; total_closed: number
}

const ROLE_STYLE: Record<string, { bg: string; color: string; label: string }> = {
  admin:      { bg: '#C6A96B20', color: '#8a6d3a',  label: 'Admin' },
  supervisor: { bg: '#3b82f620', color: '#1e40af',  label: 'Supervisor' },
  agent:      { bg: '#0b4c4520', color: '#0b4c45',  label: 'Agente' },
}
const LOC_LABEL: Record<string, string> = {
  puerto_rico: '🇵🇷 Puerto Rico', latam: '🌎 LATAM',
}

export default function AgentsPage() {
  const toast = useToast()
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'agent', location: 'latam' })
  const [saving, setSaving] = useState(false)

  const load = () => { setLoading(true); agentsApi.list().then(r => setAgents(r.data)).finally(() => setLoading(false)) }
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
      toast.error('Error al crear agente', e.response?.data?.detail || 'Intenta de nuevo')
    } finally { setSaving(false) }
  }

  const toggleActive = async (agent: Agent) => {
    await agentsApi.update(agent.id, { is_active: agent.is_active ? 0 : 1 })
    toast.info(agent.is_active ? 'Agente desactivado' : 'Agente activado', agent.name)
    load()
  }

  const active   = agents.filter(a => a.is_active)
  const inactive = agents.filter(a => !a.is_active)

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-[#0b4c45]">Agentes</h1>
          <p className="text-sm text-[#7a6a55] mt-0.5">{active.length} activos · {inactive.length} inactivos</p>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(!showForm)}>
          <Icons.X /> Nuevo agente
        </button>
      </div>

      {/* Formulario nuevo agente */}
      {showForm && (
        <div className="bg-white rounded-2xl border border-[#e5ddd4] p-5 mb-5 animate-fade-in">
          <h3 className="font-semibold text-[#0b4c45] mb-4 text-sm">Crear nuevo agente</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'Nombre completo', key: 'name', placeholder: 'Ana García', type: 'text' },
              { label: 'Correo electrónico', key: 'email', placeholder: 'ana@llvclinic.com', type: 'email' },
              { label: 'Contraseña inicial', key: 'password', placeholder: '••••••••', type: 'password' },
            ].map(f => (
              <div key={f.key}>
                <label className="block text-xs font-semibold text-[#7a6a55] mb-1">{f.label}</label>
                <input className="input" type={f.type} placeholder={f.placeholder}
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

      {/* Tabla */}
      <div className="bg-white rounded-2xl border border-[#e5ddd4] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#e5ddd4]" style={{ background: '#F5F1EB' }}>
              {['Agente', 'Rol', 'Ubicación', 'Carga', 'Cerradas', 'Estado'].map(h => (
                <th key={h} className="text-left px-5 py-3 text-xs font-semibold text-[#7a6a55] uppercase tracking-wider">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="text-center py-12 text-sm text-[#7a6a55]">Cargando...</td></tr>
            ) : agents.map(a => {
              const rs = ROLE_STYLE[a.role] || ROLE_STYLE.agent
              return (
                <tr key={a.id} className="table-row">
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
                        style={{ background: '#0b4c45', color: '#C6A96B' }}>
                        {a.name.charAt(0)}
                      </div>
                      <div>
                        <div className="text-sm font-semibold text-[#0b4c45]">{a.name}</div>
                        <div className="text-xs text-[#7a6a55]">{a.email}</div>
                      </div>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-1.5">
                      <Icons.Briefcase />
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-md" style={{ background: rs.bg, color: rs.color }}>{rs.label}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <div className="flex items-center gap-1.5 text-sm text-[#7a6a55]">
                      <Icons.MapPin />
                      {LOC_LABEL[a.location] || a.location}
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-center">
                    <div className="flex items-center gap-1 justify-center">
                      <Icons.Activity />
                      <span className="font-mono font-bold text-sm" style={{ color: a.current_load > 0 ? '#EF9F27' : '#0b4c45' }}>{a.current_load}</span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5 text-center font-mono text-sm font-semibold text-[#0b4c45]">{a.total_closed}</td>
                  <td className="px-5 py-3.5">
                    <button onClick={() => toggleActive(a)}
                      className="flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all"
                      style={a.is_active
                        ? { background: '#1D9E7520', color: '#0F6E56' }
                        : { background: '#E24B4A20', color: '#A32D2D' }}>
                      <Icons.Power />
                      {a.is_active ? 'Activo' : 'Inactivo'}
                    </button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
