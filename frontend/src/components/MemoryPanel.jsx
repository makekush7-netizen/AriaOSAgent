import React, { useState, useEffect } from 'react'

const DEFAULT_FIELDS = [
  { key: 'name', label: 'Name' },
  { key: 'email', label: 'Email' },
  { key: 'phone', label: 'Phone' },
  { key: 'college', label: 'College' },
  { key: 'department', label: 'Department' },
  { key: 'rollNo', label: 'Roll No' },
]

export default function MemoryPanel({ memoryData, setMemoryData, apiBase }) {
  const [local, setLocal] = useState({})
  const [saved, setSaved] = useState(false)
  const [customKeyInput, setCustomKeyInput] = useState('')
  const [customValInput, setCustomValInput] = useState('')
  const [showAddCustom, setShowAddCustom] = useState(false)

  useEffect(() => {
    fetch(`${apiBase}/api/memory`)
      .then(r => r.json())
      .then(d => { setLocal(d); setMemoryData(d) })
      .catch(() => setLocal(memoryData))
  }, [])

  const handleChange = (key, val) => setLocal(p => ({ ...p, [key]: val }))
  
  const handleDelete = (key) => {
    setLocal(p => { 
      const n = { ...p }
      delete n[key]
      // Sync immediately to backend so it's persisted instantly!
      fetch(`${apiBase}/api/memory`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(n)
      })
        .then(r => r.json())
        .then(d => { setMemoryData(d); setLocal(d); })
        .catch(() => setMemoryData(n))
      return n 
    })
  }

  const handleAddCustomField = () => {
    if (!customKeyInput.trim() || !customValInput.trim()) return
    const cleanKey = customKeyInput.replace(/\*/g, '').toLowerCase().replace(/[\s\xa0\u200b]+/g, '_').trim()
    if (!cleanKey) return
    setLocal(p => {
      const n = { ...p, [cleanKey]: customValInput }
      // Sync immediately to backend so it's persisted instantly!
      fetch(`${apiBase}/api/memory`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(n)
      })
        .then(r => r.json())
        .then(d => { setMemoryData(d); setLocal(d); })
        .catch(() => setMemoryData(n))
      return n
    })
    setCustomKeyInput('')
    setCustomValInput('')
    setShowAddCustom(false)
  }

  const handleSave = () => {
    setMemoryData(local)
    fetch(`${apiBase}/api/memory`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(local)
    })
      .then(() => { setSaved(true); setTimeout(() => setSaved(false), 2000) })
      .catch(() => { setSaved(true); setTimeout(() => setSaved(false), 2000) })
  }

  // Find any keys in local that are not in DEFAULT_FIELDS
  const defaultKeys = DEFAULT_FIELDS.map(f => f.key)
  const customKeys = Object.keys(local).filter(k => !defaultKeys.includes(k))

  return (
    <div className="memory-panel" style={{ overflowY: 'auto', maxH: '100%', scrollbarWidth: 'thin' }}>
      <h1 className="panel-title">Memory</h1>
      <p className="panel-subtitle">ARIA remembers these details to personalize your experience and auto-fill web forms.</p>

      {/* Default/Standard Fields */}
      <h3 style={{ color: 'var(--gold)', fontSize: '15px', marginBottom: '16px', fontWeight: '500' }}>Standard Details</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
        {DEFAULT_FIELDS.map(({ key, label }) => (
          <div key={key} className="memory-row">
            <div className="memory-label">{label}</div>
            <input
              id={`memory-${key}`}
              className="memory-input"
              value={local[key] || ''}
              onChange={e => handleChange(key, e.target.value)}
              placeholder={`Enter ${label.toLowerCase()}…`}
            />
            <button className="memory-delete" onClick={() => handleDelete(key)} title="Clear">✕</button>
          </div>
        ))}
      </div>

      {/* Dynamic/Custom Fields */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h3 style={{ color: 'var(--gold)', fontSize: '15px', fontWeight: '500', margin: 0 }}>Custom Details</h3>
        <button 
          onClick={() => setShowAddCustom(!showAddCustom)}
          style={{
            background: 'var(--surface-hover)',
            border: '1px solid var(--border)',
            borderRadius: '8px',
            color: 'var(--gold)',
            fontSize: '12px',
            padding: '6px 12px',
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
        >
          {showAddCustom ? 'Cancel' : '+ Add Custom Field'}
        </button>
      </div>

      {showAddCustom && (
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--gold-dim)',
          borderRadius: '12px',
          padding: '16px',
          marginBottom: '20px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px'
        }}>
          <div style={{ display: 'flex', gap: '12px' }}>
            <input
              type="text"
              placeholder="Field Key (e.g. project_title)"
              value={customKeyInput}
              onChange={e => setCustomKeyInput(e.target.value)}
              style={{
                flex: 1,
                background: 'rgba(0,0,0,0.2)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '8px 12px',
                color: 'var(--text)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
            <input
              type="text"
              placeholder="Value"
              value={customValInput}
              onChange={e => setCustomValInput(e.target.value)}
              style={{
                flex: 1,
                background: 'rgba(0,0,0,0.2)',
                border: '1px solid var(--border)',
                borderRadius: '8px',
                padding: '8px 12px',
                color: 'var(--text)',
                fontSize: '13px',
                outline: 'none'
              }}
            />
          </div>
          <button 
            onClick={handleAddCustomField}
            style={{
              alignSelf: 'flex-end',
              background: 'var(--gold)',
              border: 'none',
              borderRadius: '8px',
              color: '#12100e',
              padding: '6px 16px',
              fontSize: '12px',
              fontWeight: '600',
              cursor: 'pointer'
            }}
          >
            Add Field
          </button>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '32px' }}>
        {customKeys.map(key => (
          <div key={key} className="memory-row">
            <div className="memory-label" style={{ textTransform: 'capitalize' }}>
              {key.replace(/_/g, ' ')}
            </div>
            <input
              id={`memory-${key}`}
              className="memory-input"
              value={local[key] || ''}
              onChange={e => handleChange(key, e.target.value)}
              placeholder={`Enter value for ${key}...`}
            />
            <button className="memory-delete" onClick={() => handleDelete(key)} title="Clear">✕</button>
          </div>
        ))}

        {customKeys.length === 0 && !showAddCustom && (
          <div style={{ color: 'var(--text-sec)', fontSize: '13px', textAlign: 'center', padding: '10px 0' }}>
            No custom fields stored yet.
          </div>
        )}
      </div>

      <button id="memory-save-btn" className="memory-save-btn" onClick={handleSave} style={{ width: '100%' }}>
        {saved ? '✓ Saved!' : 'Save Changes'}
      </button>

      <div className="memory-footer" style={{ marginTop: '24px' }}>
        🔒 Stored locally on your device only · Never sent to cloud
      </div>
    </div>
  )
}

