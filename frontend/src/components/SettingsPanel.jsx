import React, { useState, useRef } from 'react'
import { useAriaStore } from '../store/ariaStore'

const PRESET_THEMES = [
    {
        id: 'night_garden', name: 'Night Garden',
        goldPrimary: '#e8c97a', goldDim: '#c4a55a', accentTeal: '#4fd1c7',
        accentPurple: '#9b7ff4', accentCoral: '#f4956a', accentGreen: '#6bcf7f',
        bgWorld: '#0a0a0f', bgBase: '#0f0f16', bgSurface: '#16161f',
        textPrimary: '#f0ede8', textSecondary: '#a09a90',
    },
    {
        id: 'cherry_blossom', name: 'Cherry Blossom',
        goldPrimary: '#f0a0b0', goldDim: '#c08090', accentTeal: '#80d0d0',
        accentPurple: '#c090e0', accentCoral: '#f08080', accentGreen: '#90d090',
        bgWorld: '#1a0a10', bgBase: '#150a12', bgSurface: '#201018',
        textPrimary: '#f0e8e8', textSecondary: '#a09090',
    },
    {
        id: 'deep_space', name: 'Deep Space',
        goldPrimary: '#8090e0', goldDim: '#6070b0', accentTeal: '#60c0e0',
        accentPurple: '#a080f0', accentCoral: '#e08080', accentGreen: '#80d0a0',
        bgWorld: '#050510', bgBase: '#08081a', bgSurface: '#0c0c24',
        textPrimary: '#e0e0f0', textSecondary: '#8080a0',
    },
    {
        id: 'warm_amber', name: 'Warm Amber',
        goldPrimary: '#f0c060', goldDim: '#c09040', accentTeal: '#60c0a0',
        accentPurple: '#c080d0', accentCoral: '#e07050', accentGreen: '#80c060',
        bgWorld: '#0f0a05', bgBase: '#120e08', bgSurface: '#1a1510',
        textPrimary: '#f0e8d8', textSecondary: '#a09080',
    },
]

const WIDGET_LABELS = {
    clock: { icon: '🕐', name: 'Time' },
    calendar: { icon: '📅', name: 'Calendar' },
    active_task: { icon: '⚡', name: 'Active Task' },
    goals: { icon: '🎯', name: 'Goals' },
    memory: { icon: '🧠', name: 'Memory' },
    todo: { icon: '✅', name: 'To Do' },
    quick_actions: { icon: '✦', name: 'Quick Actions' },
    quick_links: { icon: '🔗', name: 'Quick Links' },
}

function ColorInput({ label, value, onChange }) {
    return (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-secondary)', minWidth: '100px' }}>{label}</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                    type="color"
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    style={{ width: '32px', height: '24px', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '4px', cursor: 'pointer', background: 'transparent', padding: 0 }}
                />
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', minWidth: '60px' }}>{value}</span>
            </div>
        </div>
    )
}

export default function SettingsPanel() {
    const { theme, setTheme, resetTheme, character, setCharacter, resetCharacter, widgetLayout, updateWidget, resetWidgetLayout } = useAriaStore()
    const [selectedModel, setSelectedModel] = useState(() => localStorage.getItem('aria_model') || 'female')
    const handleModelChange = (m) => { setSelectedModel(m); localStorage.setItem('aria_model', m); window.dispatchEvent(new CustomEvent('aria:modelChanged', { detail: m })) }
    const [tab, setTab] = useState('dashboard')
    const fileInputRef = useRef(null)

    const tabs = [
        { id: 'dashboard', label: 'Dashboard', icon: '📊' },
        { id: 'character', label: 'Character', icon: '🧑' },
        { id: 'theme', label: 'Theme', icon: '🎨' },
    ]

    const handleBgUpload = (e) => {
        const file = e.target.files?.[0]
        if (!file) return
        const reader = new FileReader()
        reader.onload = (ev) => {
            const dataUrl = ev.target.result
            document.querySelector('.app-bg-image img')?.setAttribute('src', dataUrl)
            localStorage.setItem('aria_custom_bg', dataUrl)
        }
        reader.readAsDataURL(file)
    }

    return (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '0', color: 'var(--text-primary)', overflow: 'hidden' }}>
            {/* Header */}
            <div style={{ padding: '20px 24px 0', flexShrink: 0 }}>
                <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '28px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
                    Customize ARIA
                </h1>
                <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                    Personalize your dashboard, character, and color theme.
                </p>

                {/* Tab bar */}
                <div style={{ display: 'flex', gap: '4px', background: 'rgba(10,10,15,0.4)', padding: '4px', borderRadius: '12px', border: '1px solid rgba(232,201,122,0.12)', width: 'fit-content' }}>
                    {tabs.map(t => (
                        <button
                            key={t.id}
                            onClick={() => setTab(t.id)}
                            style={{
                                padding: '7px 16px', borderRadius: '8px', border: 'none', fontSize: '12px', fontWeight: 600,
                                fontFamily: 'var(--font-body)', cursor: 'pointer', transition: 'all 150ms',
                                background: tab === t.id ? 'var(--gold-primary)' : 'transparent',
                                color: tab === t.id ? '#0a0a0f' : 'var(--text-secondary)',
                            }}
                        >
                            {t.icon} {t.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* Content */}
            <div style={{ flex: 1, overflow: 'auto', padding: '16px 24px 24px' }}>

                {/* ─── DASHBOARD TAB ─── */}
                {tab === 'dashboard' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '600px' }}>
                        <div className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 style={{ color: 'var(--gold-primary)', fontSize: '14px', fontWeight: 600 }}>Widget Manager</h3>
                                <button onClick={resetWidgetLayout} style={{
                                    background: 'transparent', border: '1px solid rgba(232,201,122,0.2)', color: 'var(--gold-primary)',
                                    fontSize: '10px', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer',
                                }}>Reset Layout</button>
                            </div>
                            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Toggle widgets on/off. Drag to reposition on the dashboard.</p>

                            {widgetLayout.map(w => {
                                const info = WIDGET_LABELS[w.id] || { icon: '📦', name: w.id }
                                return (
                                    <div key={w.id} style={{
                                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                                        padding: '10px 12px', borderRadius: '10px', background: 'rgba(255,255,255,0.03)',
                                        border: '1px solid rgba(255,255,255,0.05)',
                                    }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                            <span style={{ fontSize: '16px' }}>{info.icon}</span>
                                            <div>
                                                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{info.name}</div>
                                                <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>
                                                    {Math.round(w.position.x)}%, {Math.round(w.position.y)}% — {Math.round(w.size.w)}×{Math.round(w.size.h)}%
                                                </div>
                                            </div>
                                        </div>
                                        <button
                                            onClick={() => updateWidget(w.id, { visible: !w.visible })}
                                            style={{
                                                width: '36px', height: '20px', borderRadius: '10px', border: 'none', cursor: 'pointer',
                                                background: w.visible ? 'var(--accent-green)' : 'rgba(255,255,255,0.1)',
                                                position: 'relative', transition: 'background 200ms',
                                            }}
                                        >
                                            <div style={{
                                                width: '16px', height: '16px', borderRadius: '50%', background: '#fff',
                                                position: 'absolute', top: '2px',
                                                left: w.visible ? '18px' : '2px',
                                                transition: 'left 200ms',
                                            }} />
                                        </button>
                                    </div>
                                )
                            })}
                        </div>

                        {/* Background upload */}
                        <div className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <h3 style={{ color: 'var(--gold-primary)', fontSize: '14px', fontWeight: 600 }}>Background</h3>
                            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Upload a custom background image. It will be auto-resized and darkened to match the theme.</p>
                            <input ref={fileInputRef} type="file" accept="image/*" onChange={handleBgUpload} style={{ display: 'none' }} />
                            <button onClick={() => fileInputRef.current?.click()} style={{
                                padding: '10px', borderRadius: '8px', border: '1px dashed rgba(232,201,122,0.3)',
                                background: 'rgba(232,201,122,0.05)', color: 'var(--gold-primary)', fontSize: '12px',
                                cursor: 'pointer', fontFamily: 'var(--font-body)',
                            }}>
                                📁 Upload Image
                            </button>
                        </div>
                    </div>
                )}

                {/* ─── CHARACTER TAB ─── */}
                {tab === 'character' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '600px' }}>
                        {/* Model selector */}
                        <div className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            <h3 style={{ color: 'var(--gold-primary)', fontSize: '14px', fontWeight: 600 }}>Avatar Model</h3>
                            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Choose your digital companion's appearance and voice.</p>
                            <div style={{ display: 'flex', gap: '10px' }}>
                                {['female', 'male'].map(m => (
                                    <button key={m} onClick={() => handleModelChange(m)} style={{
                                        flex: 1, padding: '14px', borderRadius: '10px', border: `2px solid ${selectedModel === m ? 'var(--gold-primary)' : 'rgba(255,255,255,0.08)'}`,
                                        background: selectedModel === m ? 'rgba(232,201,122,0.08)' : 'rgba(255,255,255,0.02)',
                                        cursor: 'pointer', textAlign: 'center', transition: 'all 200ms',
                                    }}>
                                        <div style={{ fontSize: '24px', marginBottom: '4px' }}>{m === 'female' ? '👩' : '👨'}</div>
                                        <div style={{ fontSize: '12px', fontWeight: 600, color: selectedModel === m ? 'var(--gold-primary)' : 'var(--text-secondary)' }}>
                                            {m === 'female' ? 'Female (I)' : 'Male'}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 style={{ color: 'var(--gold-primary)', fontSize: '14px', fontWeight: 600 }}>Appearance</h3>
                                <button onClick={resetCharacter} style={{
                                    background: 'transparent', border: '1px solid rgba(232,201,122,0.2)', color: 'var(--gold-primary)',
                                    fontSize: '10px', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer',
                                }}>Reset</button>
                            </div>

                            {/* Character scale */}
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Character Size</span>
                                    <span style={{ fontSize: '11px', color: 'var(--gold-primary)', fontFamily: 'var(--font-mono)' }}>{character.scale.toFixed(1)}x</span>
                                </div>
                                <input
                                    type="range" min="0.5" max="1.5" step="0.1" value={character.scale}
                                    onChange={e => setCharacter({ scale: parseFloat(e.target.value) })}
                                    style={{ width: '100%', accentColor: 'var(--gold-primary)' }}
                                />
                            </div>

                            {/* Position X */}
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Horizontal Position</span>
                                    <span style={{ fontSize: '11px', color: 'var(--gold-primary)', fontFamily: 'var(--font-mono)' }}>{character.posX > 0 ? '+' : ''}{character.posX}</span>
                                </div>
                                <input
                                    type="range" min="-50" max="50" step="1" value={character.posX}
                                    onChange={e => setCharacter({ posX: parseInt(e.target.value) })}
                                    style={{ width: '100%', accentColor: 'var(--gold-primary)' }}
                                />
                            </div>

                            {/* Position Y */}
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Vertical Position</span>
                                    <span style={{ fontSize: '11px', color: 'var(--gold-primary)', fontFamily: 'var(--font-mono)' }}>{character.posY > 0 ? '+' : ''}{character.posY}</span>
                                </div>
                                <input
                                    type="range" min="-50" max="50" step="1" value={character.posY}
                                    onChange={e => setCharacter({ posY: parseInt(e.target.value) })}
                                    style={{ width: '100%', accentColor: 'var(--gold-primary)' }}
                                />
                            </div>
                        </div>

                        {/* Graphics Quality */}
                        <div className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <h3 style={{ color: 'var(--gold-primary)', fontSize: '14px', fontWeight: 600 }}>Graphics Quality</h3>
                            <p style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Adjust polygon count based on your system specs. Lower = better performance.</p>
                            <div style={{ display: 'flex', gap: '8px' }}>
                                {[
                                    { id: 'low', label: 'Low', desc: '~20k polys', color: 'var(--accent-coral)' },
                                    { id: 'medium', label: 'Medium', desc: '~35k polys', color: 'var(--gold-primary)' },
                                    { id: 'high', label: 'High', desc: '~50k polys', color: 'var(--accent-green)' },
                                ].map(q => (
                                    <button key={q.id} onClick={() => setCharacter({ quality: q.id })} style={{
                                        flex: 1, padding: '10px', borderRadius: '8px',
                                        border: `2px solid ${character.quality === q.id ? q.color : 'rgba(255,255,255,0.08)'}`,
                                        background: character.quality === q.id ? `${q.color}15` : 'rgba(255,255,255,0.02)',
                                        cursor: 'pointer', textAlign: 'center', transition: 'all 200ms',
                                    }}>
                                        <div style={{ fontSize: '12px', fontWeight: 600, color: character.quality === q.id ? q.color : 'var(--text-secondary)' }}>{q.label}</div>
                                        <div style={{ fontSize: '9px', color: 'var(--text-muted)', marginTop: '2px' }}>{q.desc}</div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Greeting */}
                        <div className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <h3 style={{ color: 'var(--gold-primary)', fontSize: '14px', fontWeight: 600 }}>Greeting</h3>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Show greeting text</span>
                                <button
                                    onClick={() => setCharacter({ showGreeting: !character.showGreeting })}
                                    style={{
                                        width: '36px', height: '20px', borderRadius: '10px', border: 'none', cursor: 'pointer',
                                        background: character.showGreeting ? 'var(--accent-green)' : 'rgba(255,255,255,0.1)',
                                        position: 'relative', transition: 'background 200ms',
                                    }}
                                >
                                    <div style={{
                                        width: '16px', height: '16px', borderRadius: '50%', background: '#fff',
                                        position: 'absolute', top: '2px',
                                        left: character.showGreeting ? '18px' : '2px',
                                        transition: 'left 200ms',
                                    }} />
                                </button>
                            </div>
                            <input
                                value={character.greeting}
                                onChange={e => setCharacter({ greeting: e.target.value })}
                                placeholder="Custom greeting (leave empty for default)"
                                style={{
                                    width: '100%', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                                    borderRadius: '8px', padding: '8px 12px', color: 'var(--text-primary)', fontSize: '12px',
                                    outline: 'none', fontFamily: 'var(--font-body)',
                                }}
                            />
                            <p style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Leave empty to auto-detect time-based greeting.</p>
                        </div>
                    </div>
                )}

                {/* ─── THEME TAB ─── */}
                {tab === 'theme' && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '600px' }}>
                        {/* Preset themes */}
                        <div className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <h3 style={{ color: 'var(--gold-primary)', fontSize: '14px', fontWeight: 600 }}>Preset Themes</h3>
                                <button onClick={resetTheme} style={{
                                    background: 'transparent', border: '1px solid rgba(232,201,122,0.2)', color: 'var(--gold-primary)',
                                    fontSize: '10px', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer',
                                }}>Reset</button>
                            </div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px' }}>
                                {PRESET_THEMES.map(t => (
                                    <button
                                        key={t.id}
                                        onClick={() => setTheme(t)}
                                        style={{
                                            padding: '12px', borderRadius: '10px', border: `2px solid ${theme.id === t.id ? t.goldPrimary : 'rgba(255,255,255,0.08)'}`,
                                            background: t.bgWorld, cursor: 'pointer', textAlign: 'left', transition: 'border-color 200ms',
                                        }}
                                    >
                                        <div style={{ display: 'flex', gap: '4px', marginBottom: '6px' }}>
                                            <div style={{ width: '14px', height: '14px', borderRadius: '50%', background: t.goldPrimary }} />
                                            <div style={{ width: '14px', height: '14px', borderRadius: '50%', background: t.accentTeal }} />
                                            <div style={{ width: '14px', height: '14px', borderRadius: '50%', background: t.accentPurple }} />
                                            <div style={{ width: '14px', height: '14px', borderRadius: '50%', background: t.accentCoral }} />
                                        </div>
                                        <div style={{ fontSize: '11px', fontWeight: 600, color: t.textPrimary }}>{t.name}</div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Custom colors */}
                        <div className="glass-card" style={{ padding: '18px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                            <h3 style={{ color: 'var(--gold-primary)', fontSize: '14px', fontWeight: 600 }}>Custom Colors</h3>
                            <p style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Pick your own colors. Changes apply instantly.</p>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                                <ColorInput label="Gold Primary" value={theme.goldPrimary} onChange={v => setTheme({ ...theme, id: 'custom', goldPrimary: v })} />
                                <ColorInput label="Gold Dim" value={theme.goldDim} onChange={v => setTheme({ ...theme, id: 'custom', goldDim: v })} />
                                <ColorInput label="Accent Teal" value={theme.accentTeal} onChange={v => setTheme({ ...theme, id: 'custom', accentTeal: v })} />
                                <ColorInput label="Accent Purple" value={theme.accentPurple} onChange={v => setTheme({ ...theme, id: 'custom', accentPurple: v })} />
                                <ColorInput label="Accent Coral" value={theme.accentCoral} onChange={v => setTheme({ ...theme, id: 'custom', accentCoral: v })} />
                                <ColorInput label="Accent Green" value={theme.accentGreen} onChange={v => setTheme({ ...theme, id: 'custom', accentGreen: v })} />
                                <ColorInput label="Background" value={theme.bgWorld} onChange={v => setTheme({ ...theme, id: 'custom', bgWorld: v })} />
                                <ColorInput label="Surface" value={theme.bgSurface} onChange={v => setTheme({ ...theme, id: 'custom', bgSurface: v })} />
                                <ColorInput label="Text Primary" value={theme.textPrimary} onChange={v => setTheme({ ...theme, id: 'custom', textPrimary: v })} />
                                <ColorInput label="Text Secondary" value={theme.textSecondary} onChange={v => setTheme({ ...theme, id: 'custom', textSecondary: v })} />
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}