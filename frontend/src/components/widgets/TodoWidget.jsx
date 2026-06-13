import React, { useState, useEffect } from 'react'

const STORAGE_KEY = 'aria_todos'

function loadTodos() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY)
        return raw ? JSON.parse(raw) : [
            { id: 1, text: 'Research binary search in C++', done: false },
            { id: 2, text: 'Fill hackathon registration form', done: false },
            { id: 3, text: 'Scout upcoming hackathons on Unstop', done: true },
        ]
    } catch { return [] }
}

function saveTodos(todos) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(todos)) } catch { }
}

export default function TodoWidget() {
    const [todos, setTodos] = useState(loadTodos)
    const [input, setInput] = useState('')

    useEffect(() => { saveTodos(todos) }, [todos])

    const addTodo = () => {
        if (!input.trim()) return
        setTodos(prev => [...prev, { id: Date.now(), text: input.trim(), done: false }])
        setInput('')
    }

    const toggleTodo = (id) => {
        setTodos(prev => prev.map(t => t.id === id ? { ...t, done: !t.done } : t))
    }

    const removeTodo = (id) => {
        setTodos(prev => prev.filter(t => t.id !== id))
    }

    const pending = todos.filter(t => !t.done)
    const completed = todos.filter(t => t.done)

    return (
        <div style={{ userSelect: 'none', height: '100%', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', gap: '4px', marginTop: '2px', marginBottom: '6px' }}>
                <input
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && addTodo()}
                    placeholder="Add a task..."
                    style={{
                        flex: 1, background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)',
                        borderRadius: '6px', padding: '5px 8px', color: 'var(--text-primary)', fontSize: '10px',
                        outline: 'none', fontFamily: 'var(--font-body)',
                    }}
                />
                <button onClick={addTodo} style={{
                    width: '24px', height: '24px', borderRadius: '6px', border: 'none',
                    background: 'var(--gold-primary)', color: '#0a0a0f', cursor: 'pointer',
                    fontSize: '14px', fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>+</button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', maxHeight: '120px', overflowY: 'auto' }}>
                {pending.map(t => (
                    <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 0' }}>
                        <button onClick={() => toggleTodo(t.id)} style={{
                            width: '14px', height: '14px', borderRadius: '3px', border: '1.5px solid rgba(255,255,255,0.15)',
                            background: 'transparent', cursor: 'pointer', flexShrink: 0,
                        }} />
                        <span style={{ fontSize: '10px', color: 'var(--text-secondary)', flex: 1 }}>{t.text}</span>
                    </div>
                ))}
                {completed.length > 0 && (
                    <div style={{ fontSize: '9px', color: 'var(--text-muted)', marginTop: '4px', fontWeight: 600, letterSpacing: '0.05em' }}>
                        COMPLETED ({completed.length})
                    </div>
                )}
                {completed.map(t => (
                    <div key={t.id} style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '3px 0' }}>
                        <button onClick={() => toggleTodo(t.id)} style={{
                            width: '14px', height: '14px', borderRadius: '3px', border: 'none',
                            background: 'var(--accent-green)', cursor: 'pointer', flexShrink: 0,
                            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '8px', color: '#fff',
                        }}>✓</button>
                        <span style={{ fontSize: '10px', color: 'var(--text-muted)', textDecoration: 'line-through', flex: 1 }}>{t.text}</span>
                        <button onClick={() => removeTodo(t.id)} style={{
                            width: '14px', height: '14px', borderRadius: '3px', border: 'none',
                            background: 'transparent', cursor: 'pointer', fontSize: '9px', color: 'var(--text-muted)',
                        }}>×</button>
                    </div>
                ))}
            </div>
        </div>
    )
}