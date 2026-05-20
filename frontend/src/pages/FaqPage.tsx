import { useEffect, useState } from 'react'
import { faqApi } from '../api/client'

interface FAQ {
  id: number
  category: string
  question: string
  answer: string
  is_active: number
  usage_count?: number
}

const CATEGORIES = [
  { value: 'tratamiento', label: 'Tratamiento', color: '#0b4c45', bg: '#e8f4f1' },
  { value: 'aplicacion', label: 'Aplicación', color: '#2563eb', bg: '#eff6ff' },
  { value: 'productos', label: 'Productos', color: '#7c3aed', bg: '#f5f3ff' },
  { value: 'cuidados', label: 'Cuidados', color: '#0891b2', bg: '#ecfeff' },
  { value: 'resultados', label: 'Resultados', color: '#d97706', bg: '#fffbeb' },
  { value: 'pagos', label: 'Pagos', color: '#059669', bg: '#ecfdf5' },
  { value: 'logistica', label: 'Logística', color: '#dc2626', bg: '#fef2f2' },
  { value: 'general', label: 'General', color: '#6b7280', bg: '#f9fafb' },
]

export default function FaqPage() {
  const [faqs, setFaqs] = useState<FAQ[]>([])
  const [filter, setFilter] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<FAQ | null>(null)
  const [form, setForm] = useState({
    category: 'tratamiento',
    question: '',
    answer: '',
  })
  const [saving, setSaving] = useState(false)
  const [expanded, setExpanded] = useState<number | null>(null)

  const load = () => {
    setLoading(true)

    faqApi
      .list()
      .then((response) => setFaqs(response.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  const startEdit = (faq: FAQ) => {
    setEditing(faq)
    setForm({
      category: faq.category,
      question: faq.question,
      answer: faq.answer,
    })
    setShowForm(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleSave = async () => {
    if (!form.question.trim() || !form.answer.trim()) return

    setSaving(true)

    try {
      if (editing) {
        await faqApi.update(editing.id, form)
      } else {
        await faqApi.create(form)
      }

      setShowForm(false)
      setEditing(null)
      setForm({
        category: 'tratamiento',
        question: '',
        answer: '',
      })

      load()
    } finally {
      setSaving(false)
    }
  }

  const handleToggle = async (faq: FAQ) => {
    await faqApi.update(faq.id, {
      is_active: faq.is_active ? 0 : 1,
    })

    load()
  }

  const handleDelete = async (id: number) => {
    if (!confirm('¿Eliminar esta pregunta frecuente?')) return

    await faqApi.delete(id)

    load()
  }

  const filtered = faqs.filter(
    (faq) =>
      (!filter || faq.category === filter) &&
      (!search ||
        faq.question.toLowerCase().includes(search.toLowerCase()) ||
        faq.answer.toLowerCase().includes(search.toLowerCase()))
  )

  const activeCount = faqs.filter((faq) => faq.is_active).length

  const catCounts = CATEGORIES.map((category) => ({
    ...category,
    count: faqs.filter(
      (faq) => faq.category === category.value && faq.is_active
    ).length,
  }))

  return (
    <div className="page-mobile p-4 sm:p-6 max-w-5xl mx-auto w-full min-w-0">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between mb-6">
        <div className="min-w-0">
          <h1 className="font-display text-2xl font-bold text-[#0b4c45]">
            Base de conocimiento FAQ
          </h1>

          <p className="text-sm text-[#7a6a55] mt-0.5">
            {activeCount} preguntas activas · {faqs.length} total
          </p>
        </div>

        <button
          className="btn-primary w-full sm:w-auto justify-center"
          onClick={() => {
            setEditing(null)
            setForm({
              category: 'tratamiento',
              question: '',
              answer: '',
            })
            setShowForm(true)
          }}
        >
          + Nueva pregunta
        </button>
      </div>

      {/* Categorías con contadores */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 mb-5">
        <button
          onClick={() => setFilter('')}
          className="flex flex-col items-center p-2 rounded-xl border-2 transition-all text-center min-w-0"
          style={
            !filter
              ? {
                  borderColor: '#0b4c45',
                  background: '#e8f4f1',
                }
              : {
                  borderColor: '#e5ddd4',
                  background: 'white',
                }
          }
        >
          <span className="text-lg">📚</span>

          <span className="text-[10px] font-semibold text-[#7a6a55] mt-0.5 truncate w-full">
            Todas
          </span>

          <span className="text-sm font-bold text-[#0b4c45]">
            {activeCount}
          </span>
        </button>

        {catCounts.map((category) => (
          <button
            key={category.value}
            onClick={() =>
              setFilter(filter === category.value ? '' : category.value)
            }
            className="flex flex-col items-center p-2 rounded-xl border-2 transition-all text-center min-w-0"
            style={
              filter === category.value
                ? {
                    borderColor: category.color,
                    background: category.bg,
                  }
                : {
                    borderColor: '#e5ddd4',
                    background: 'white',
                  }
            }
          >
            <span
              className="text-xs font-semibold truncate w-full"
              style={{ color: category.color }}
            >
              {category.label}
            </span>

            <span
              className="text-sm font-bold"
              style={{ color: category.color }}
            >
              {category.count}
            </span>
          </button>
        ))}
      </div>

      {/* Búsqueda */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-3 mb-5">
        <input
          className="input flex-1"
          placeholder="🔍 Buscar en preguntas y respuestas..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        {(search || filter) && (
          <button
            onClick={() => {
              setSearch('')
              setFilter('')
            }}
            className="text-xs font-semibold text-[#E24B4A] border border-[#E24B4A] px-3 py-2 rounded-lg hover:bg-red-50 w-full sm:w-auto"
          >
            ✕ Limpiar
          </button>
        )}

        <span className="text-xs text-[#7a6a55] whitespace-nowrap text-center sm:text-left">
          {filtered.length} resultados
        </span>
      </div>

      {/* Formulario */}
      {showForm && (
        <div className="bg-white rounded-2xl border-2 border-[#0b4c45] p-4 sm:p-5 mb-5 animate-fade-in min-w-0">
          <h3 className="font-semibold text-[#0b4c45] mb-4">
            {editing ? 'Editar pregunta' : 'Nueva pregunta frecuente'}
          </h3>

          <div className="space-y-4">
            <div className="min-w-0">
              <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                Categoría
              </label>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {CATEGORIES.map((category) => (
                  <button
                    key={category.value}
                    onClick={() =>
                      setForm({
                        ...form,
                        category: category.value,
                      })
                    }
                    className="px-3 py-2 rounded-lg text-xs font-semibold transition-all truncate"
                    style={
                      form.category === category.value
                        ? {
                            background: category.color,
                            color: 'white',
                          }
                        : {
                            background: category.bg,
                            color: category.color,
                          }
                    }
                  >
                    {category.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="min-w-0">
              <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                Pregunta
              </label>

              <input
                className="input"
                value={form.question}
                onChange={(event) =>
                  setForm({
                    ...form,
                    question: event.target.value,
                  })
                }
                placeholder="¿Cuántas veces a la semana se aplica el tratamiento?"
              />
            </div>

            <div className="min-w-0">
              <label className="block text-xs font-semibold text-[#7a6a55] mb-1">
                Respuesta
              </label>

              <textarea
                className="input min-h-28 resize-none"
                value={form.answer}
                onChange={(event) =>
                  setForm({
                    ...form,
                    answer: event.target.value,
                  })
                }
                placeholder="Escribe la respuesta completa que el bot enviará al cliente..."
              />

              <p className="text-xs text-[#7a6a55] mt-1">
                Puedes usar *negrita* y _cursiva_ para dar formato en WhatsApp.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-2 mt-4">
            <button
              className="btn-primary justify-center"
              onClick={handleSave}
              disabled={
                saving || !form.question.trim() || !form.answer.trim()
              }
            >
              {saving
                ? 'Guardando...'
                : editing
                  ? 'Actualizar FAQ'
                  : 'Crear FAQ'}
            </button>

            <button
              className="btn-ghost justify-center"
              onClick={() => {
                setShowForm(false)
                setEditing(null)
              }}
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* Lista FAQ */}
      {loading ? (
        <div className="text-center py-12 text-[#7a6a55] text-sm">
          Cargando...
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-[#7a6a55] text-sm">
          No hay preguntas que coincidan con el filtro.
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((faq) => {
            const category = CATEGORIES.find(
              (item) => item.value === faq.category
            )

            const isExpanded = expanded === faq.id

            return (
              <div
                key={faq.id}
                className={`bg-white rounded-xl border transition-all min-w-0 ${
                  !faq.is_active ? 'opacity-50' : 'hover:shadow-sm'
                } ${
                  isExpanded ? 'border-[#0b4c45]' : 'border-[#e5ddd4]'
                }`}
              >
                {/* Header de la FAQ */}
                <div
                  className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 p-4 cursor-pointer"
                  onClick={() =>
                    setExpanded(isExpanded ? null : faq.id)
                  }
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span
                        className="text-[10px] font-bold px-2 py-0.5 rounded-md"
                        style={{
                          background: category?.bg || '#F5F1EB',
                          color: category?.color || '#7a6a55',
                        }}
                      >
                        {category?.label || faq.category}
                      </span>

                      {!faq.is_active && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-red-100 text-red-600">
                          Inactiva
                        </span>
                      )}

                      {(faq.usage_count || 0) > 0 && (
                        <span className="text-[10px] text-[#7a6a55]">
                          🤖 Usada {faq.usage_count} veces
                        </span>
                      )}
                    </div>

                    <p className="text-sm font-semibold text-[#0b4c45] break-words">
                      {faq.question}
                    </p>

                    {!isExpanded && (
                      <p className="text-xs text-[#7a6a55] mt-1 line-clamp-1 break-words">
                        {faq.answer}
                      </p>
                    )}
                  </div>

                  <div
                    className="flex items-center justify-end gap-1 flex-shrink-0"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <button
                      onClick={() => startEdit(faq)}
                      className="p-1.5 rounded-lg hover:bg-[#e8f4f1] text-[#7a6a55] hover:text-[#0b4c45] transition-colors"
                      title="Editar"
                    >
                      ✏️
                    </button>

                    <button
                      onClick={() => handleToggle(faq)}
                      className="p-1.5 rounded-lg transition-colors text-[#7a6a55]"
                      title={faq.is_active ? 'Desactivar' : 'Activar'}
                    >
                      {faq.is_active ? '🟡' : '🟢'}
                    </button>

                    <button
                      onClick={() => handleDelete(faq.id)}
                      className="p-1.5 rounded-lg hover:bg-red-50 text-[#7a6a55] hover:text-red-500 transition-colors"
                      title="Eliminar"
                    >
                      🗑️
                    </button>

                    <span className="text-[#7a6a55] ml-1">
                      {isExpanded ? '▲' : '▼'}
                    </span>
                  </div>
                </div>

                {/* Respuesta expandida */}
                {isExpanded && (
                  <div className="px-4 pb-4 border-t border-[#f5f1eb]">
                    <p className="text-xs font-semibold text-[#7a6a55] uppercase tracking-wider mt-3 mb-2">
                      Respuesta del bot:
                    </p>

                    <div className="bg-[#F5F1EB] rounded-xl p-3 text-sm text-[#1a1208] whitespace-pre-wrap break-words">
                      {faq.answer}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}