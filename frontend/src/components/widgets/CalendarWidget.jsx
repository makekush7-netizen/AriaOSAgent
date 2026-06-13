import React, { useState, useEffect } from 'react'

const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']

export default function CalendarWidget() {
    const [now, setNow] = useState(new Date())

    useEffect(() => {
        const t = setInterval(() => setNow(new Date()), 60000)
        return () => clearInterval(t)
    }, [])

    const year = now.getFullYear()
    const month = now.getMonth()
    const today = now.getDate()
    const firstDay = new Date(year, month, 1).getDay()
    const daysInMonth = new Date(year, month + 1, 0).getDate()
    const daysInPrev = new Date(year, month, 0).getDate()

    const cells = []
    // Previous month trailing days
    for (let i = firstDay - 1; i >= 0; i--) {
        cells.push({ day: daysInPrev - i, muted: true })
    }
    // Current month
    for (let d = 1; d <= daysInMonth; d++) {
        cells.push({ day: d, muted: false, isToday: d === today })
    }
    // Next month leading days
    const remaining = 42 - cells.length
    for (let d = 1; d <= remaining; d++) {
        cells.push({ day: d, muted: true })
    }

    return (
        <div style={{ userSelect: 'none', height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontFamily: 'var(--font-display)', fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {MONTHS[month]} {year}
                </span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '2px', textAlign: 'center', flex: 1 }}>
                {DAYS.map(d => (
                    <div key={d} style={{ fontSize: '8px', color: 'var(--text-muted)', padding: '2px 0', fontWeight: 600, letterSpacing: '0.05em' }}>{d}</div>
                ))}
                {cells.map((c, i) => (
                    <div
                        key={i}
                        style={{
                            fontSize: '10px',
                            padding: '3px 0',
                            borderRadius: '6px',
                            color: c.isToday ? '#0a0a0f' : c.muted ? 'var(--text-muted)' : 'var(--text-secondary)',
                            background: c.isToday ? 'var(--gold-primary)' : 'transparent',
                            fontWeight: c.isToday ? 700 : 400,
                            cursor: c.muted ? 'default' : 'pointer',
                            transition: 'background 150ms',
                        }}
                    >
                        {c.day}
                    </div>
                ))}
            </div>
        </div>
    )
}