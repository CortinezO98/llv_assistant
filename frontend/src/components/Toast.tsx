import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import Icons from './Icons'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
    id: string
    type: ToastType
    title: string
    message?: string
}

interface ToastContextType {
    success: (title: string, message?: string) => void
    error:   (title: string, message?: string) => void
    warning: (title: string, message?: string) => void
    info:    (title: string, message?: string) => void
}

const ToastContext = createContext<ToastContextType | null>(null)

const ICONS = {
    success: Icons.CheckCircle,
    error:   Icons.XCircle,
    warning: Icons.AlertTriangle,
    info:    Icons.Info,
}

const STYLES = {
    success: { border: 'border-l-[#1D9E75]', icon: 'text-[#1D9E75]', bg: 'bg-white' },
    error:   { border: 'border-l-[#E24B4A]', icon: 'text-[#E24B4A]', bg: 'bg-white' },
    warning: { border: 'border-l-[#EF9F27]', icon: 'text-[#EF9F27]', bg: 'bg-white' },
    info:    { border: 'border-l-[#0b4c45]', icon: 'text-[#0b4c45]', bg: 'bg-white' },
}

export function ToastProvider({ children }: { children: ReactNode }) {
    const [toasts, setToasts] = useState<Toast[]>([])

    const push = useCallback((type: ToastType, title: string, message?: string) => {
        const id = Math.random().toString(36).slice(2)
        setToasts(prev => [...prev, { id, type, title, message }])
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
    }, [])

    const remove = (id: string) => setToasts(prev => prev.filter(t => t.id !== id))

    const ctx: ToastContextType = {
        success: (t, m) => push('success', t, m),
        error:   (t, m) => push('error',   t, m),
        warning: (t, m) => push('warning', t, m),
        info:    (t, m) => push('info',    t, m),
    }

    return (
        <ToastContext.Provider value={ctx}>
        {children}
        {/* Toast container */}
        <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
            {toasts.map(toast => {
            const Icon = ICONS[toast.type]
            const s    = STYLES[toast.type]
            return (
                <div
                key={toast.id}
                className={`
                    flex items-start gap-3 px-4 py-3 rounded-xl shadow-lg border border-[#e5ddd4]
                    border-l-4 ${s.border} ${s.bg}
                    pointer-events-auto animate-slide-in
                    min-w-[280px] max-w-[360px]
                `}
                >
                <Icon />
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[#1a1208]">{toast.title}</p>
                    {toast.message && <p className="text-xs text-[#7a6a55] mt-0.5">{toast.message}</p>}
                </div>
                <button onClick={() => remove(toast.id)} className="text-[#7a6a55] hover:text-[#1a1208] flex-shrink-0">
                    <Icons.X />
                </button>
                </div>
            )
            })}
        </div>
        </ToastContext.Provider>
    )
}

export function useToast(): ToastContextType {
    const ctx = useContext(ToastContext)
    if (!ctx) throw new Error('useToast must be used within ToastProvider')
    return ctx
}
