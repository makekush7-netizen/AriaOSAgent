import React, { useState } from 'react'

const DEFAULT_GOALS = [
    { id: 1, name: 'Research Projects', progress: 30, color: 'var(--accent-teal)' },
    { id: 2, name: 'Form Fills Completed', progress: 60, color: 'var(--gold-primary)' },
    { id: 3, name: 'Hackathons Scouted', progress: 15, color: 'var(--accent-purple)' },
]

export default function GoalsWidget() {
    const [goals, setGoals] = useState(DEFAULT_GOALS)

    const updateProgress = (id, delta) => {
        setGoals(prev => prev.map(g =>
            g.id === id ? { ...g, progress: Math.max(0, Math.min(100, g.progress + delta)) } : g
        ))
    }

    return (
        <div style={{ userSelect: 'none', height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginTop: '2px', flex: 1 }}>
                {goals.map(g => (
                    <div key={g.id}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500 }}>{g.name}</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <span style={{ fontSize: '10px', color: g.color, fontWeight: 700 }}>{g.progress}%</span>
                                <button onClick={() => updateProgress(g.id, -5)} style={{ width: '14px', height: '14px', borderRadius: '3px', border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>−</button>
                                <button onClick={() => updateProgress(g.id, 5)} style={{ width: '14px', height: '14px', borderRadius: '3px', border: '1px solid rgba(255,255,255,0.1)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '8px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>+</button>
                            </div>
                        </div>
                        <div style={{ width: '100%', height: '4px', borderRadius: '2px', background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
                            <div style={{
                                width: `${g.progress}%`,
                                height: '100%',
                                borderRadius: '2px',
                                background: g.color,
                                transition: 'width 400ms var(--ease-out-smooth)',
                                boxShadow: `0 0 8px ${g.color}40`,
                            }} />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}