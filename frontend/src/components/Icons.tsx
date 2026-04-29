import React from "react"


// ── Inline SVG icons (no external dependency) ────────────────────────────────
const I = ({ d, size=16, sw=1.75 }: { d: string|string[]; size?: number; sw?: number }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
        {Array.isArray(d) ? d.map((p,i) => <path key={i} d={p}/>) : <path d={d}/>}
    </svg>
)

// Icon library
const Icons = {
    Dashboard:    () => <I d={["M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z","M9 22V12h6v10"]} />,
    Chat:         () => <I d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
    Calendar:     () => <I d={["M8 2v4M16 2v4M3 10h18","rect x='3' y='4' width='18' height='18' rx='2'"]} />,
    Package:      () => <I d={["M12 2L2 7l10 5 10-5-10-5","M2 17l10 5 10-5","M2 12l10 5 10-5"]} />,
    Users:        () => <I d={["M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2","M23 21v-2a4 4 0 0 0-3-3.87","M16 3.13a4 4 0 0 1 0 7.75"]} size={16}/>,
    Headphones:   () => <I d={["M3 18v-6a9 9 0 0 1 18 0v6","M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"]} />,
    Book:         () => <I d={["M4 19.5A2.5 2.5 0 0 1 6.5 17H20","M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"]} />,
    BarChart:     () => <I d={["M12 20V10","M18 20V4","M6 20v-4"]} />,
    Zap:          () => <I d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" />,
    LogOut:       () => <I d={["M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4","M16 17l5-5-5-5","M21 12H9"]} />,
    Check:        () => <I d="M20 6L9 17l-5-5" />,
    Clock:        () => <I d={["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20","M12 6v6l4 2"]} />,
    MapPin:       () => <I d={["M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z","M12 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6"]} size={13}/>,
    Stethoscope:  () => <I d={["M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3","M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4"]} />,
    TrendingUp:   () => <I d={["M23 6l-9.5 9.5-5-5L1 18","M17 6h6v6"]} />,
    Activity:     () => <I d="M22 12h-4l-3 9L9 3l-3 9H2" />,
    Power:        () => <I d={["M18.36 6.64a9 9 0 1 1-12.73 0","M12 2v10"]} />,
    Star:         () => <I d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />,
    DollarSign:   () => <I d={["M12 1v22","M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"]} />,
    CreditCard:   () => <I d={["rect x='1' y='4' width='22' height='16' rx='2'","L1 10h22"]} />,
    CalendarCheck:() => <I d={["M8 2v4M16 2v4M3 10h18","rect x='3' y='4' width='18' height='18' rx='2'","M9 16l2 2 4-4"]} />,
    MessageSq:    () => <I d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />,
    CheckCircle:  () => <I d={["M22 11.08V12a10 10 0 1 1-5.93-9.14","M22 4 12 14.01l-3-3"]} />,
    XCircle:      () => <I d={["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20","M15 9l-6 6M9 9l6 6"]} />,
    AlertTriangle:() => <I d={["M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z","M12 9v4M12 17h.01"]} />,
    Info:         () => <I d={["M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20","M12 16v-4M12 8h.01"]} />,
    X:            () => <I d={["M18 6 6 18","M6 6l12 12"]} />,
    Briefcase:    () => <I d={["rect x='2' y='7' width='20' height='14' rx='2'","M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"]} />,
    Eye:          (props?: any) => <I d={["M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z","M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6"]} size={props?.size||16} />,
    EyeOff:       () => <I d={["M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94","M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19","M1 1l22 22"]} />,
    ArrowRight:   () => <I d={["M5 12h14","M12 5l7 7-7 7"]} />,
}

export default Icons
