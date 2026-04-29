import { useEffect, useState } from 'react'
import { faqApi } from '../api/client'

interface FAQ { id: number; category: string; question: string; answer: string; is_active: number }

const CATEGORIES = ['tratamiento', 'aplicacion', 'productos', 'cuidados', 'resultados']
const catColors: Record<string, string> = {
  tratamiento: 'bg-brand-100 text-brand-700',
  aplicacion:  'bg-blue-100 text-blue-700',
  productos:   'bg-violet-100 text-violet-700',
  cuidados:    'bg-teal-100 text-teal-700',
  resultados:  'bg-amber-100 text-amber-700',
}

export default function FaqPage() {
  const [faqs, setFaqs] = useState<FAQ[]>([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<FAQ | null>(null)
  const [form, setForm] = useState({ category: 'tratamiento', question: '', answer: '' })
  const [saving, setSaving] = useState(false)
  const [search, setSearch] = useState('')

  const load = () => {
    setLoading(true)
    faqApi.list().then(r => setFaqs(r.data)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const startEdit = (faq: FAQ) => {
    setEditing(faq)
    setForm({ category: faq.category, question: faq.question, answer: faq.answer })
    setShowForm(true)
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      if (editing) {
        await faqApi.update(editing.id, form)
      } else {
        await faqApi.create(form)
      }
      setShowForm(false); setEditing(null)
      setForm({ category: 'tratamiento', question: '', answer: '' })
      load()
    } finally { setSaving(false) }
  }

  const handleToggle = async (faq: FAQ) => {
    await faqApi.update(faq.id, { is_active: faq.is_active ? 0 : 1 })
    load()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Eliminar esta pregunta?')) return
    await faqApi.delete(id)
    load()
  }

  const filtered = faqs.filter(f =>
    (!filter || f.category === filter) &&
    (!search || f.question.toLowerCase().includes(search.toLowerCase()) || f.answer.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="font-display text-2xl font-bold text-brand-800">Base de conocimiento FAQ</h1>
          <p className="text-sm text-[#6b8a78] mt-0.5">{faqs.filter(f => f.is_active).length} preguntas activas · {faqs.length} total</p>
        </div>
        <button className="btn-primary" onClick={() => { setEditing(null); setForm({ category: 'tratamiento', question: '', answer: '' }); setShowForm(true) }}>
          <span>+</span> Nueva pregunta
        </button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-5 flex-wrap">
        <input className="input max-w-xs" placeholder="🔍 Buscar pregunta..." value={search} onChange={e => setSearch(e.target.value)} />
        <div className="flex gap-1.5">
          <button onClick={() => setFilter('')} className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${!filter ? 'bg-brand-600 text-white' : 'bg-white border border-[#e4ede8] text-[#6b8a78]'}`}>
            Todas
          </button>
          {CATEGORIES.map(cat => (
            <button key={cat} onClick={() => setFilter(filter === cat ? '' : cat)} className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${filter === cat ? 'bg-brand-600 text-white' : 'bg-white border border-[#e4ede8] text-[#6b8a78]'}`}>
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Form */}
      {showForm && (
        <div className="card p-5 mb-5 animate-fade-in">
          <h3 className="font-semibold text-brand-800 mb-4">{editing ? 'Editar pregunta' : 'Nueva pregunta frecuente'}</h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-semibold text-[#6b8a78] mb-1">Categoría</label>
              <select className="input max-w-xs" value={form.category} onChange={e => setForm({...form, category: e.target.value})}>
                {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6b8a78] mb-1">Pregunta</label>
              <input className="input" value={form.question} onChange={e => setForm({...form, question: e.target.value})} placeholder="¿Cuántas veces a la semana se aplica el tratamiento?" />
            </div>
            <div>
              <label className="block text-xs font-semibold text-[#6b8a78] mb-1">Respuesta</label>
              <textarea className="input min-h-24 resize-none" value={form.answer} onChange={e => setForm({...form, answer: e.target.value})} placeholder="Una vez por semana, el mismo día cada semana..." />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <button className="btn-primary" onClick={handleSave} disabled={saving}>{saving ? 'Guardando...' : editing ? 'Actualizar' : 'Crear FAQ'}</button>
            <button className="btn-ghost" onClick={() => { setShowForm(false); setEditing(null) }}>Cancelar</button>
          </div>
        </div>
      )}

      {/* FAQ list */}
      {loading ? (
        <div className="text-center py-12 text-[#6b8a78] text-sm">Cargando FAQ...</div>
      ) : (
        <div className="space-y-3 stagger">
          {filtered.map(faq => (
            <div key={faq.id} className={`card p-4 transition-all ${!faq.is_active ? 'opacity-50' : ''}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`badge text-[10px] ${catColors[faq.category] || 'bg-gray-100 text-gray-600'}`}>{faq.category}</span>
                    {!faq.is_active && <span className="badge bg-red-100 text-red-600 text-[10px]">Inactiva</span>}
                  </div>
                  <p className="text-sm font-semibold text-brand-800">{faq.question}</p>
                  <p className="text-xs text-[#6b8a78] mt-1 line-clamp-2">{faq.answer}</p>
                </div>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <button onClick={() => startEdit(faq)} className="p-1.5 rounded-lg hover:bg-brand-50 text-[#6b8a78] hover:text-brand-600 transition-colors" title="Editar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                  </button>
                  <button onClick={() => handleToggle(faq)} className={`p-1.5 rounded-lg transition-colors ${faq.is_active ? 'hover:bg-amber-50 text-amber-500' : 'hover:bg-teal-50 text-teal-500'}`} title={faq.is_active ? 'Desactivar' : 'Activar'}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/>{faq.is_active ? <line x1="18" y1="6" x2="6" y2="18"/> : <polyline points="20,6 9,17 4,12"/>}</svg>
                  </button>
                  <button onClick={() => handleDelete(faq.id)} className="p-1.5 rounded-lg hover:bg-red-50 text-[#6b8a78] hover:text-red-500 transition-colors" title="Eliminar">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3,6 5,6 21,6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6m4-6v6"/><path d="M9 6V4h6v2"/></svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <div className="text-center py-12 text-[#6b8a78] text-sm">No hay preguntas que coincidan con el filtro.</div>
          )}
        </div>
      )}
    </div>
  )
}
