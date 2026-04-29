import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LOGO_GOLD_FULL, LOGO_MONO_WHITE } from '../assets/logos'

// animate.css via CDN — loaded once
const ANIMATE_CSS = 'https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css'
if (!document.querySelector(`link[href="${ANIMATE_CSS}"]`)) {
  const link = document.createElement('link')
  link.rel  = 'stylesheet'
  link.href = ANIMATE_CSS
  document.head.appendChild(link)
}

export default function LoginPage() {
  const { login }   = useAuth()
  const navigate    = useNavigate()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw]     = useState(false)
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)
  const [shake, setShake]       = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch {
      setError('Credenciales inválidas. Verifica tu correo y contraseña.')
      setShake(true)
      setTimeout(() => setShake(false), 700)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ fontFamily: "'DM Sans', sans-serif" }}>

      {/* ── Panel izquierdo — identidad de marca ─────────────────────────── */}
      <div
        className="hidden lg:flex lg:w-[55%] flex-col justify-between p-14 relative overflow-hidden"
        style={{ background: '#0b4c45' }}
      >
        {/* Decoración de fondo */}
        <div
          className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: 'radial-gradient(circle at 20% 80%, #C6A96B 0%, transparent 50%), radial-gradient(circle at 80% 20%, #C6A96B 0%, transparent 50%)'
          }}
        />
        <div
          className="absolute bottom-0 right-0 w-96 h-96 rounded-full opacity-5"
          style={{ background: '#C6A96B', transform: 'translate(30%, 30%)' }}
        />

        {/* Logo top */}
        <div className="animate__animated animate__fadeInDown animate__delay-1s relative z-10">
          <img
            src={LOGO_GOLD_FULL}
            alt="LLV Aesthetic & Wellness Clinic"
            className="h-12 object-contain object-left"
            style={{ filter: 'drop-shadow(0 2px 8px rgba(198,169,107,0.3))' }}
          />
        </div>

        {/* Centro */}
        <div className="relative z-10">
          <div className="animate__animated animate__fadeInLeft">
            <p
              className="text-[11px] font-semibold tracking-[0.25em] uppercase mb-5"
              style={{ color: '#C6A96B' }}
            >
              Panel de Operaciones
            </p>
            <h1
              className="text-5xl font-bold text-white leading-[1.15] mb-6"
              style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.02em' }}
            >
              Tu bienestar<br />
              <span style={{ color: '#C6A96B' }}>es nuestra</span><br />
              prioridad.
            </h1>
            <p className="text-white/50 text-sm leading-relaxed max-w-sm">
              Gestiona conversaciones, citas, entregas y reportería
              de LLV Wellness Clinic desde un solo lugar.
            </p>
          </div>

          {/* Stats */}
          <div className="animate__animated animate__fadeInUp animate__delay-1s flex gap-10 mt-12">
            {[
              { n: '1.500', l: 'Conv. / mes' },
              { n: '6',     l: 'Agentes' },
              { n: '24/7',  l: 'Bot activo' },
            ].map((s, i) => (
              <div key={s.l} style={{ animationDelay: `${i * 0.15}s` }}>
                <div
                  className="text-3xl font-bold"
                  style={{ fontFamily: "'Syne', sans-serif", color: '#C6A96B' }}
                >
                  {s.n}
                </div>
                <div className="text-xs text-white/40 mt-1 tracking-wide">{s.l}</div>
              </div>
            ))}
          </div>

          {/* Línea decorativa */}
          <div
            className="mt-12 h-px animate__animated animate__fadeIn animate__delay-2s"
            style={{ background: 'linear-gradient(to right, #C6A96B40, transparent)' }}
          />
        </div>

        {/* Footer */}
        <p className="text-white/20 text-xs relative z-10 animate__animated animate__fadeIn animate__delay-2s">
          © 2025 LLV Aesthetic & Wellness Clinic
        </p>
      </div>

      {/* ── Panel derecho — formulario ────────────────────────────────────── */}
      <div
        className="flex-1 flex flex-col items-center justify-center px-8 py-12"
        style={{ background: '#F5F1EB' }}
      >
        {/* Logo móvil */}
        <div className="lg:hidden mb-10 animate__animated animate__fadeInDown">
          <img src={LOGO_GOLD_FULL} alt="LLV" className="h-10 object-contain" />
        </div>

        {/* Card del formulario */}
        <div
          className={`w-full max-w-sm animate__animated animate__fadeInUp ${shake ? 'animate__headShake' : ''}`}
        >
          {/* Header */}
          <div className="mb-8">
            <h2
              className="text-2xl font-bold mb-1"
              style={{ fontFamily: "'Syne', sans-serif", color: '#0b4c45', letterSpacing: '-0.01em' }}
            >
              Bienvenido de vuelta
            </h2>
            <p className="text-sm" style={{ color: '#7a6a55' }}>
              Ingresa con tus credenciales para continuar
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Email */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#7a6a55' }}>
                Correo electrónico
              </label>
              <input
                type="email"
                className="input"
                placeholder="nombre@llvclinic.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
                style={{ background: 'white', borderColor: '#e5ddd4' }}
              />
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#7a6a55' }}>
                Contraseña
              </label>
              <div className="relative">
                <input
                  type={showPw ? 'text' : 'password'}
                  className="input pr-10"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  style={{ background: 'white', borderColor: '#e5ddd4' }}
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors"
                  style={{ color: '#7a6a55' }}
                >
                  {showPw ? (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/>
                      <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/>
                      <line x1="1" y1="1" x2="23" y2="23"/>
                    </svg>
                  ) : (
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                      <circle cx="12" cy="12" r="3"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Error */}
            {error && (
              <div
                className="flex items-center gap-2 px-4 py-3 rounded-xl animate__animated animate__fadeIn"
                style={{ background: '#FCEBEB', border: '1px solid #F09595' }}
              >
                <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: '#E24B4A' }} />
                <p className="text-xs" style={{ color: '#791F1F' }}>{error}</p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-3.5 px-4 rounded-xl font-semibold text-sm transition-all duration-200 disabled:opacity-60"
              style={{ background: '#0b4c45', color: 'white', letterSpacing: '0.01em' }}
            >
              {loading ? (
                <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".3"/>
                  <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round"/>
                </svg>
              ) : (
                <>
                  Ingresar al panel
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="5" y1="12" x2="19" y2="12"/>
                    <polyline points="12,5 19,12 12,19"/>
                  </svg>
                </>
              )}
            </button>
          </form>

          {/* Soporte */}
          <div
            className="mt-6 p-4 rounded-xl animate__animated animate__fadeIn animate__delay-1s"
            style={{ background: 'white', border: '1px solid #e5ddd4' }}
          >
            <p className="text-[10px] font-semibold uppercase tracking-wider mb-1.5" style={{ color: '#7a6a55' }}>
              Soporte técnico
            </p>
            <p className="text-xs" style={{ color: '#7a6a55' }}>
              ¿Problemas para ingresar? Contacta a{' '}
              <span className="font-semibold" style={{ color: '#0b4c45' }}>José Cortinez</span>
            </p>
          </div>
        </div>

        <p className="mt-10 text-xs" style={{ color: '#7a6a5560' }}>
          LLV Assistant v1.0 · Crea con Pau × José Cortinez
        </p>
      </div>
    </div>
  )
}
