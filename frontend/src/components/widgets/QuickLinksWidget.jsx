import React, { useState, useEffect } from 'react'

const STORAGE_KEY = 'aria_quick_links'

const DEFAULT_LINKS = [
    { id: 1, label: 'Unstop Hackathons', url: 'https://unstop.com/hackathons', icon: '🏆' },
    { id: 2, label: 'GitHub', url: 'https://github.com', icon: '🐙' },
    { id: 3, label: 'LeetCode', url: 'https://leetcode.com', icon: '💻' },
    { id: 4, label: 'Google Scholar', url: 'https://scholar.google.com', icon: '📚' },
]

function loadLinks() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY)
        return raw ? JSON.parse(raw) : DEFAULT_LINKS
    } catch { return DEFAULT_LINKS }
}

function saveLinks(links) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(links)) } catch { }
}

export default function QuickLinksWidget() {
    const [links, setLinks] = useState(loadLinks)
    const [adding, setAdding] = useState(false)
    const [newLabel, setNewLabel] = useState('')
    const [newUrl, setNewUrl] = useState('')

    useEffect(() => { saveLinks(links) }, [links])

    const addLink = () => {
        if (!newLabel.trim() || !newUrl.trim()) return
        const url = newUrl.startsWith('http') ? newUrl : 'https://' + newUrl
        setLinks(prev => [...prev, { id: Date.now(), label: newLabel.trim(), url, icon: '🔗' }])
        setNewLabel('')
        setNewUrl('')
        setAdding(false)
    }

    const removeLink = (id) => {
        setLinks(prev => prev.filter(l => l.id !== id))
    }

    return (
        <div style={{ userSelect: 'none', height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '4px' }}>
                <button onClick={() => setAdding(!adding)} style={{
                    width: '16px', height: '16px', borderRadius: '4px', border: '1px solid rgba(255,255,255,0.1)',
                    background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '10px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>+</button>
            </div>

            {adding && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '6px', marginBottom: '6px' }}>
                    <input
                        value={newLabel}
                        onChange={e => setNewLabel(e.target.value)}
                        placeholder="Label"
                        style={{
                            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                            borderRadius: '5px', padding: '4px 7px', color: 'var(--text-primary)', fontSize: '10px',
                            outline: 'none', fontFamily: 'var(--font-body)',
                        }}
                    />
                    <input
                        value={newUrl}
                        onChange={e => setNewUrl(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && addLink()}
                        placeholder="URL"
                        style={{
                            background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                            borderRadius: '5px', padding: '4px 7px', color: 'var(--text-primary)', fontSize: '10px',
                            outline: 'none', fontFamily: 'var(--font-body)',
                        }}
                    />
                    <button onClick={addLink} style={{
                        padding: '4px', borderRadius: '5px', border: 'none', background: 'var(--gold-primary)',
                        color: '#0a0a0f', fontSize: '10px', fontWeight: 600, cursor: 'pointer',
                    }}>Add</button>
                </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', marginTop: '4px' }}>
                {links.map(l => (
                    <a
                        key={l.id}
                        href={l.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                            display: 'flex', alignItems: 'center', gap: '6px', padding: '4px 6px',
                            borderRadius: '5px', textDecoration: 'none', transition: 'background 150ms',
                            cursor: 'pointer',
                        }}
                        onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.04)'}
                        onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                        <span style={{ fontSize: '11px' }}>{l.icon}</span>
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{l.label}</span>
                        <button onClick={(e) => { e.preventDefault(); removeLink(l.id) }} style={{
                            width: '12px', height: '12px', borderRadius: '2px', border: 'none',
                            background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer',
                            fontSize: '8px', opacity: 0, transition: 'opacity 150ms', flexShrink: 0,
                        }} onMouseEnter={e => e.target.style.opacity = 1} onMouseLeave={e => e.target.style.opacity = 0}>×</button>
                    </a>
                ))}
            </div>
        </div>
    )
}