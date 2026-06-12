import React, { useEffect, useState } from 'react'

const DEFAULT_FIELDS = [
  { key: 'name', label: 'Name', hint: 'Used for greetings and form autofill' },
  { key: 'email', label: 'Email', hint: 'Primary contact for registrations' },
  { key: 'phone', label: 'Phone', hint: 'Phone number for portals' },
  { key: 'college', label: 'College', hint: 'Institution or organization' },
  { key: 'department', label: 'Department', hint: 'Course, branch, or team' },
  { key: 'rollNo', label: 'Roll No', hint: 'Student or employee ID' },
]

const cleanKey = (value) =>
  value.replace(/\*/g, '').toLowerCase().replace(/[\s\xa0\u200b]+/g, '_').trim()

export default function MemoryPanel({ memoryData, setMemoryData, apiBase }) {
  const [local, setLocal] = useState({})
  const [saved, setSaved] = useState(false)
  const [customKeyInput, setCustomKeyInput] = useState('')
  const [customValInput, setCustomValInput] = useState('')
  const [showAddCustom, setShowAddCustom] = useState(false)

  useEffect(() => {
    fetch(`${apiBase}/api/memory`)
      .then((r) => r.json())
      .then((d) => { setLocal(d); setMemoryData(d) })
      .catch(() => setLocal(memoryData))
  }, [])

  const persist = (next) => {
    fetch(`${apiBase}/api/memory`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(next)
    })
      .then((r) => r.json())
      .then((d) => { setMemoryData(d); setLocal(d) })
      .catch(() => setMemoryData(next))
  }

  const handleChange = (key, val) => setLocal((p) => ({ ...p, [key]: val }))

  const handleDelete = (key) => {
    setLocal((p) => {
      const next = { ...p }
      delete next[key]
      persist(next)
      return next
    })
  }

  const handleAddCustomField = () => {
    const key = cleanKey(customKeyInput)
    if (!key || !customValInput.trim()) return

    setLocal((p) => {
      const next = { ...p, [key]: customValInput.trim() }
      persist(next)
      return next
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
      .then(() => { setSaved(true); setTimeout(() => setSaved(false), 1800) })
      .catch(() => { setSaved(true); setTimeout(() => setSaved(false), 1800) })
  }

  const defaultKeys = DEFAULT_FIELDS.map((f) => f.key)
  const customKeys = Object.keys(local).filter((k) => !defaultKeys.includes(k))
  const filledCount = Object.values(local).filter(Boolean).length

  return (
    <section className="panel-page memory-panel">
      <div className="panel-hero">
        <div>
          <p className="eyebrow">Local profile</p>
          <h1>Memory</h1>
          <p>Details ARIA can use for personalization, form filling, and repeat tasks.</p>
        </div>
        <div className="memory-score-card">
          <span>{filledCount}</span>
          <small>stored fields</small>
        </div>
      </div>

      <div className="memory-layout">
        <div className="glass-panel memory-form-card">
          <div className="section-heading">
            <span>Standard Details</span>
            <small>Used by BrowserBot during autofill</small>
          </div>

          <div className="memory-field-grid">
            {DEFAULT_FIELDS.map(({ key, label, hint }) => (
              <label key={key} className="memory-field">
                <span>{label}</span>
                <small>{hint}</small>
                <div className="memory-input-wrap">
                  <input
                    id={`memory-${key}`}
                    value={local[key] || ''}
                    onChange={(e) => handleChange(key, e.target.value)}
                    placeholder={`Enter ${label.toLowerCase()}`}
                  />
                  {local[key] && (
                    <button type="button" onClick={() => handleDelete(key)} aria-label={`Clear ${label}`}>
                      x
                    </button>
                  )}
                </div>
              </label>
            ))}
          </div>
        </div>

        <aside className="glass-panel memory-custom-card">
          <div className="section-heading compact">
            <span>Custom Details</span>
            <button type="button" className="ghost-link" onClick={() => setShowAddCustom((v) => !v)}>
              {showAddCustom ? 'Cancel' : 'Add field'}
            </button>
          </div>

          {showAddCustom && (
            <div className="custom-field-editor">
              <input
                value={customKeyInput}
                onChange={(e) => setCustomKeyInput(e.target.value)}
                placeholder="Field name"
              />
              <input
                value={customValInput}
                onChange={(e) => setCustomValInput(e.target.value)}
                placeholder="Value"
              />
              <button type="button" className="primary-btn" onClick={handleAddCustomField}>Add</button>
            </div>
          )}

          <div className="custom-memory-list">
            {customKeys.map((key) => (
              <div key={key} className="custom-memory-row">
                <div>
                  <span>{key.replace(/_/g, ' ')}</span>
                  <small>{local[key]}</small>
                </div>
                <button type="button" onClick={() => handleDelete(key)} aria-label={`Clear ${key}`}>x</button>
              </div>
            ))}

            {customKeys.length === 0 && !showAddCustom && (
              <div className="empty-note">No custom fields yet.</div>
            )}
          </div>
        </aside>
      </div>

      <div className="panel-footer-actions">
        <div className="privacy-note">
          <span className="lock-dot" />
          Stored locally on your device only
        </div>
        <button id="memory-save-btn" className="primary-btn wide" onClick={handleSave}>
          {saved ? 'Saved' : 'Save Changes'}
        </button>
      </div>
    </section>
  )
}
