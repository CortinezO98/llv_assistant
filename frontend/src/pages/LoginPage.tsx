import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LOGO_GOLD_FULL, LOGO_MONO_WHITE } from '../assets/logos'

// animate.css via CDN — loaded once
const ANIMATE_CSS = 'https://cdnjs.cloudflare.com/ajax/libs/animate.css/4.1.1/animate.min.css'
if (!document.querySelector(`link[href="${ANIMATE_CSS}"]`)) {
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = ANIMATE_CSS
  document.head.appendChild(link)
}

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [remember, setRemember] = useState(true)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()

    if (!email.trim() || !password.trim()) {
      setError('Ingresa tu correo y contraseña para continuar.')
      return
    }

    setError('')
    setLoading(true)

    try {
      await login(email.trim(), password)
      navigate('/')
    } catch {
      setError('Credenciales inválidas. Verifica tu correo y contraseña.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen w-full overflow-hidden bg-[#F5F1EB] text-[#10231f]"
      style={{ fontFamily: "'DM Sans', sans-serif" }}
    >
      <div className="min-h-screen grid lg:grid-cols-[1.08fr_0.92fr]">
        {/* Panel izquierdo – identidad de marca */}
        <section className="relative hidden lg:flex flex-col justify-between overflow-hidden bg-[#0b4c45] px-14 py-12">
          {/* Decoración de fondo */}
          <div className="absolute inset-0 opacity-[0.07]">
            <div className="absolute -top-24 -left-24 h-80 w-80 rounded-full bg-[#C6A96B] blur-3xl" />
            <div className="absolute top-1/3 right-10 h-72 w-72 rounded-full bg-white blur-3xl" />
            <div className="absolute -bottom-28 right-0 h-96 w-96 rounded-full bg-[#C6A96B] blur-3xl" />
          </div>

          <div
            className="absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage:
                'linear-gradient(rgba(255,255,255,.2) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.2) 1px, transparent 1px)',
              backgroundSize: '50px 50px',
            }}
          />

          <div className="relative z-10 animate__animated animate__fadeInDown">
            <img
              src={LOGO_GOLD_FULL}
              alt="LLV Aesthetic & Wellness Clinic"
              className="h-14 object-contain object-left"
              style={{
                filter: 'drop-shadow(0 12px 24px rgba(0,0,0,0.2))',
              }}
            />
          </div>

          <div className="relative z-10 max-w-2xl animate__animated animate__fadeInLeft">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-[#e0d0a0] backdrop-blur">
              <span className="h-2 w-2 rounded-full bg-[#C6A96B]" />
              Centro de operaciones — LLV Wellness Clinic
            </div>

            <h1
              className="max-w-xl text-5xl font-extrabold leading-[1.02] tracking-[-0.04em] text-white"
              style={{ fontFamily: "'Syne', sans-serif" }}
            >
              Conversaciones, citas y entregas en un solo lugar.
            </h1>

            <p className="mt-6 max-w-xl text-base leading-7 text-white/70">
              Bot 24/7 con IA que atiende pacientes nuevos, recompras
              y pedidos. Derivación automática a agentes, reportería
              de citas y seguimiento de entregas locales y envíos.
            </p>

            <div className="mt-10 grid max-w-xl grid-cols-3 gap-4">
              <div className="rounded-2xl border border-white/10 bg-white/10 p-5 backdrop-blur">
                <p className="text-2xl font-bold text-[#C6A96B]">24/7</p>
                <p className="mt-1 text-xs leading-5 text-white/65">
                  Chatbot activo todo el día
                </p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/10 p-5 backdrop-blur">
                <p className="text-2xl font-bold text-[#C6A96B]">⚡</p>
                <p className="mt-1 text-xs leading-5 text-white/65">
                  Evaluación y derivación automática
                </p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/10 p-5 backdrop-blur">
                <p className="text-2xl font-bold text-[#C6A96B]">📊</p>
                <p className="mt-1 text-xs leading-5 text-white/65">
                  Métricas y reportería en vivo
                </p>
              </div>
            </div>
          </div>

          <div className="relative z-10 flex items-center justify-between border-t border-white/10 pt-6 animate__animated animate__fadeIn animate__delay-1s">
            <p className="text-xs text-white/50">
              LLV Assistant · Sistema privado de gestión
            </p>

            <div className="flex items-center gap-2 text-xs text-white/50">
              <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,.9)]" />
              Servicio operativo
            </div>
          </div>
        </section>

        {/* Panel derecho – formulario */}
        <section className="relative flex min-h-screen items-center justify-center px-5 py-10 sm:px-8">
          {/* Fondo decorativo sutil */}
          <div className="absolute inset-0 pointer-events-none">
            <div className="absolute top-0 right-0 w-64 h-64 rounded-full bg-[#C6A96B]/10 blur-3xl" />
            <div className="absolute bottom-0 left-0 w-80 h-80 rounded-full bg-[#0b4c45]/5 blur-3xl" />
          </div>

          <div className="relative w-full max-w-[480px]">
            {/* Logo móvil */}
            <div className="mb-8 flex justify-center lg:hidden">
              <div className="rounded-2xl bg-[#0b4c45] px-6 py-4 shadow-xl shadow-[#0b4c45]/20">
                <img
                  src={LOGO_MONO_WHITE}
                  alt="LLV Assistant"
                  className="h-10 object-contain"
                />
              </div>
            </div>

            <div className="rounded-[2rem] border border-[#e5ddd4] bg-white/95 p-6 shadow-[0_24px_80px_rgba(11,76,69,0.12)] backdrop-blur-xl sm:p-8 animate__animated animate__fadeInUp">
              <div className="mb-7">
                <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-[#F5F1EB] px-3 py-1.5 text-[11px] font-bold uppercase tracking-[0.16em] text-[#7a6a55]">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#0b4c45]" />
                  Acceso seguro
                </div>

                <h2
                  className="text-3xl font-extrabold tracking-[-0.04em] text-[#0b4c45]"
                  style={{ fontFamily: "'Syne', sans-serif" }}
                >
                  Bienvenido de nuevo
                </h2>

                <p className="mt-2 text-sm leading-6 text-[#7a6a55]">
                  Ingresa al panel administrativo para gestionar conversaciones,
                  agentes, citas, entregas y reportes.
                </p>
              </div>

              {error && (
                <div className="mb-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 animate__animated animate__fadeIn">
                  <div className="flex items-start gap-3">
                    <span className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-red-100 text-xs font-bold">
                      !
                    </span>
                    <p>{error}</p>
                  </div>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label
                    htmlFor="email"
                    className="mb-2 block text-xs font-bold uppercase tracking-[0.13em] text-[#7a6a55]"
                  >
                    Correo electrónico
                  </label>

                  <div className="relative">
                    <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#9c8a72]">
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <rect x="3" y="5" width="18" height="14" rx="2" />
                        <path d="m3 7 9 6 9-6" />
                      </svg>
                    </span>

                    <input
                      id="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder="usuario@llvclinic.com"
                      className="w-full rounded-2xl border border-[#e5ddd4] bg-white px-12 py-3.5 text-sm text-[#10231f] outline-none transition-all placeholder:text-[#b8aa98] focus:border-[#C6A96B] focus:ring-4 focus:ring-[#C6A96B]/20"
                    />
                  </div>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label
                      htmlFor="password"
                      className="block text-xs font-bold uppercase tracking-[0.13em] text-[#7a6a55]"
                    >
                      Contraseña
                    </label>

                    <span className="text-[11px] font-medium text-[#9c8a72]">
                      Credenciales internas
                    </span>
                  </div>

                  <div className="relative">
                    <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[#9c8a72]">
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <rect x="4" y="11" width="16" height="9" rx="2" />
                        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
                      </svg>
                    </span>

                    <input
                      id="password"
                      type={showPw ? 'text' : 'password'}
                      autoComplete="current-password"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="••••••••••••"
                      className="w-full rounded-2xl border border-[#e5ddd4] bg-white px-12 py-3.5 pr-14 text-sm text-[#10231f] outline-none transition-all placeholder:text-[#b8aa98] focus:border-[#C6A96B] focus:ring-4 focus:ring-[#C6A96B]/20"
                    />

                    <button
                      type="button"
                      onClick={() => setShowPw(v => !v)}
                      className="absolute right-3 top-1/2 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-xl text-[#7a6a55] transition hover:bg-[#F5F1EB] hover:text-[#0b4c45]"
                      aria-label={showPw ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    >
                      {showPw ? (
                        <svg
                          width="18"
                          height="18"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M17.94 17.94A10.94 10.94 0 0 1 12 20C7 20 2.73 16.89 1 12a12.1 12.1 0 0 1 5.06-5.94" />
                          <path d="M10.58 10.58A2 2 0 0 0 13.42 13.42" />
                          <path d="m3 3 18 18" />
                          <path d="M14.12 5.1A10.94 10.94 0 0 1 23 12a12.2 12.2 0 0 1-2.2 3.42" />
                        </svg>
                      ) : (
                        <svg
                          width="18"
                          height="18"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z" />
                          <circle cx="12" cy="12" r="3" />
                        </svg>
                      )}
                    </button>
                  </div>
                </div>

                <div className="flex items-center justify-between gap-3">
                  <label className="flex cursor-pointer items-center gap-2 text-xs font-medium text-[#7a6a55]">
                    <input
                      type="checkbox"
                      checked={remember}
                      onChange={e => setRemember(e.target.checked)}
                      className="h-4 w-4 rounded border-[#d8cbbb] text-[#0b4c45] focus:ring-[#0b4c45]"
                    />
                    Mantener sesión activa
                  </label>

                  <span className="text-xs text-[#9c8a72]">
                    v1.0
                  </span>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="group flex w-full items-center justify-center gap-2 rounded-2xl bg-[#0b4c45] px-5 py-3.5 text-sm font-bold text-white shadow-xl shadow-[#0b4c45]/20 transition-all hover:-translate-y-0.5 hover:bg-[#093d38] hover:shadow-2xl hover:shadow-[#0b4c45]/25 disabled:cursor-not-allowed disabled:opacity-70 disabled:hover:translate-y-0"
                >
                  {loading ? (
                    <>
                      <svg
                        className="h-4 w-4 animate-spin"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <circle
                          cx="12"
                          cy="12"
                          r="10"
                          stroke="currentColor"
                          strokeWidth="3"
                          strokeOpacity=".25"
                        />
                        <path
                          d="M12 2a10 10 0 0 1 10 10"
                          stroke="currentColor"
                          strokeWidth="3"
                          strokeLinecap="round"
                        />
                      </svg>
                      Validando acceso...
                    </>
                  ) : (
                    <>
                      Ingresar al dashboard
                      <svg
                        className="transition-transform group-hover:translate-x-0.5"
                        width="17"
                        height="17"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        <line x1="5" y1="12" x2="19" y2="12" />
                        <polyline points="12,5 19,12 12,19" />
                      </svg>
                    </>
                  )}
                </button>
              </form>

              <div className="mt-6 rounded-2xl border border-[#e5ddd4] bg-[#F5F1EB] p-4">
                <div className="flex items-start gap-3">
                  <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-white text-[#0b4c45] shadow-sm">
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
                      <path d="m9 12 2 2 4-4" />
                    </svg>
                  </div>

                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-[#7a6a55]">
                      Acceso protegido
                    </p>
                    <p className="mt-1 text-xs leading-5 text-[#7a6a55]">
                      Este panel es exclusivo para personal autorizado. Toda la
                      actividad queda asociada al usuario autenticado.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <p className="mt-6 text-center text-xs text-[#7a6a55]/80">
              ¿Problemas para ingresar?{' '}
              <a
                href="mailto:jcortinezosorio@gmail.com"
                className="font-semibold text-[#0b4c45] hover:underline"
              >
                jcortinezosorio@gmail.com
              </a>
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}