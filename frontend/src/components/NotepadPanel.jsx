import React, { useState, useEffect } from 'react'

export default function NotepadPanel({ apiBase }) {
  const [notes, setNotes] = useState([])
  const [selectedNote, setSelectedNote] = useState(null)
  const [editorContent, setEditorContent] = useState('')
  const [editorTitle, setEditorTitle] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [notification, setNotification] = useState('')

  const fetchNotes = async () => {
    try {
      const res = await fetch(`${apiBase}/api/notes`)
      if (res.ok) {
        const data = await res.json()
        setNotes(data)
        
        // Auto-select first note if none selected yet
        if (data.length > 0 && !selectedNote) {
          loadNoteContent(data[0].filename)
        }
      }
    } catch (e) {
      console.error('Failed to fetch notes', e)
    }
  }

  const loadNoteContent = async (filename) => {
    try {
      const res = await fetch(`${apiBase}/api/notes/${filename}`)
      if (res.ok) {
        const data = await res.json()
        setSelectedNote(filename)
        setEditorContent(data.content)
        setEditorTitle(filename.replace('.md', '').replace('.txt', '').replace(/_/g, ' '))
      }
    } catch (e) {
      console.error('Failed to load note content', e)
    }
  }

  useEffect(() => {
    fetchNotes()
  }, [])

  const handleSave = async () => {
    if (!selectedNote) return
    setIsSaving(true)
    try {
      const res = await fetch(`${apiBase}/api/notes/${selectedNote}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: editorContent })
      })
      if (res.ok) {
        showNotification('Saved successfully!')
        fetchNotes()
      }
    } catch (e) {
      showNotification('Failed to save')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedNote) return
    if (!window.confirm(`Are you sure you want to delete "${editorTitle}"?`)) return
    try {
      const res = await fetch(`${apiBase}/api/notes/${selectedNote}`, {
        method: 'DELETE'
      })
      if (res.ok) {
        showNotification('Deleted document')
        setSelectedNote(null)
        setEditorContent('')
        setEditorTitle('')
        fetchNotes()
      }
    } catch (e) {
      showNotification('Failed to delete')
    }
  }

  const handleCreate = async () => {
    const title = prompt('Enter document title:')
    if (!title || !title.trim()) return
    const filename = title.toLowerCase().trim().replace(/\s+/g, '_') + '.md'
    try {
      const res = await fetch(`${apiBase}/api/notes/${filename}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: `# ${title}\n\nStart typing research findings or competitor details here...` })
      })
      if (res.ok) {
        showNotification('Document created!')
        await fetchNotes()
        await loadNoteContent(filename)
      }
    } catch (e) {
      showNotification('Failed to create')
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(editorContent)
    showNotification('Copied to clipboard!')
  }

  const showNotification = (msg) => {
    setNotification(msg)
    setTimeout(() => setNotification(''), 3000)
  }

  return (
    <div className="notepad-container" style={{ display: 'flex', height: '100%', padding: '24px 40px', gap: '24px' }}>
      
      {/* Sidebar List */}
      <div className="notepad-sidebar" style={{
        width: '30%',
        background: 'var(--surface)',
        backdropFilter: 'blur(24px)',
        border: '1px solid var(--border)',
        borderRadius: '20px',
        display: 'flex',
        flexDirection: 'column',
        padding: '20px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3 style={{ fontSize: '18px', fontWeight: '500', color: 'var(--gold)', letterSpacing: '0.5px' }}>Findings Notepad</h3>
          <button 
            onClick={handleCreate}
            style={{
              background: 'var(--gold-dim)',
              border: '1px solid var(--gold)',
              borderRadius: '50%',
              width: '32px',
              height: '32px',
              color: 'var(--gold)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 'bold',
              transition: 'all 0.2s',
              boxShadow: '0 0 8px var(--gold-glow)'
            }}
            title="Create New Document"
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--gold)'; e.currentTarget.style.color = '#12100e' }}
            onMouseLeave={e => { e.currentTarget.style.background = 'var(--gold-dim)'; e.currentTarget.style.color = 'var(--gold)' }}
          >
            +
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {notes.map(note => (
            <button
              key={note.filename}
              onClick={() => loadNoteContent(note.filename)}
              style={{
                width: '100%',
                padding: '14px 16px',
                textAlign: 'left',
                background: selectedNote === note.filename ? 'var(--surface-hover)' : 'transparent',
                border: selectedNote === note.filename ? '1px solid var(--gold)' : '1px solid var(--border)',
                borderRadius: '12px',
                color: selectedNote === note.filename ? 'var(--text)' : 'var(--text-sec)',
                cursor: 'pointer',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                boxShadow: selectedNote === note.filename ? '0 0 10px var(--gold-dim)' : 'none'
              }}
              onMouseEnter={e => {
                if (selectedNote !== note.filename) {
                  e.currentTarget.style.borderColor = 'var(--gold)';
                  e.currentTarget.style.color = 'var(--text)';
                }
              }}
              onMouseLeave={e => {
                if (selectedNote !== note.filename) {
                  e.currentTarget.style.borderColor = 'var(--border)';
                  e.currentTarget.style.color = 'var(--text-sec)';
                }
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, color: 'var(--gold)' }}>
                <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
                <path d="M14 2v4a2 2 0 0 0 2 2h4"/>
                <path d="M10 9H8"/>
                <path d="M16 13H8"/>
                <path d="M16 17H8"/>
              </svg>
              <span style={{ fontSize: '13px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: '500' }}>
                {note.title}
              </span>
            </button>
          ))}

          {notes.length === 0 && (
            <div style={{ color: 'var(--text-sec)', fontSize: '13px', textAlign: 'center', marginTop: '40px' }}>
              No scouted findings yet. Ask ARIA to search hackathons for you!
            </div>
          )}
        </div>
      </div>

      {/* Editor Workspace */}
      <div className="notepad-editor" style={{
        flex: 1,
        background: 'var(--surface)',
        backdropFilter: 'blur(24px)',
        border: '1px solid var(--border)',
        borderRadius: '20px',
        display: 'flex',
        flexDirection: 'column',
        padding: '24px',
        position: 'relative'
      }}>
        {selectedNote ? (
          <>
            {/* Header controls */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', gap: '16px' }}>
              <input 
                type="text"
                value={editorTitle}
                disabled
                style={{
                  background: 'transparent',
                  border: 'none',
                  fontSize: '20px',
                  fontWeight: '600',
                  color: 'var(--text)',
                  width: '60%',
                  outline: 'none'
                }}
              />
              <div style={{ display: 'flex', gap: '8px' }}>
                <button 
                  onClick={handleCopy}
                  style={{
                    background: 'var(--surface-hover)',
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    padding: '8px 14px',
                    color: 'var(--text)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor = 'var(--gold)'}
                  onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--border)'}
                >
                  📄 Copy
                </button>
                <button 
                  onClick={handleSave}
                  style={{
                    background: 'var(--gold)',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '8px 16px',
                    color: '#12100e',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: '600',
                    transition: 'all 0.2s',
                    boxShadow: '0 0 10px var(--gold-glow)'
                  }}
                  onMouseEnter={e => e.currentTarget.style.filter = 'brightness(1.1)'}
                  onMouseLeave={e => e.currentTarget.style.filter = 'none'}
                >
                  {isSaving ? 'Saving...' : '💾 Save'}
                </button>
                <button 
                  onClick={handleDelete}
                  style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid #ef4444',
                    borderRadius: '8px',
                    padding: '8px 14px',
                    color: '#ef4444',
                    cursor: 'pointer',
                    fontSize: '12px',
                    transition: 'all 0.2s'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#ef4444' + '22'}
                  onMouseLeave={e => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
                >
                  🗑️ Delete
                </button>
              </div>
            </div>

            {/* Editing field */}
            <textarea
              value={editorContent}
              onChange={e => setEditorContent(e.target.value)}
              style={{
                flex: 1,
                background: 'rgba(0,0,0,0.15)',
                border: '1px solid var(--border)',
                borderRadius: '12px',
                padding: '20px',
                color: 'var(--text)',
                fontFamily: 'monospace',
                fontSize: '14px',
                lineHeight: '1.6',
                resize: 'none',
                outline: 'none',
                transition: 'border-color 0.2s',
                scrollbarWidth: 'thin'
              }}
              onFocus={e => e.currentTarget.style.borderColor = 'var(--gold)'}
              onBlur={e => e.currentTarget.style.borderColor = 'var(--border)'}
              placeholder="Type markdown content here..."
            />
          </>
        ) : (
          <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-sec)',
            gap: '16px'
          }}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ color: 'var(--gold)', filter: 'drop-shadow(0 0 8px var(--gold-glow))', opacity: 0.6 }}>
              <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            <span style={{ fontSize: '14px' }}>Select or create a document to read and edit findings.</span>
          </div>
        )}

        {/* Notification Toast */}
        {notification && (
          <div style={{
            position: 'absolute',
            bottom: '24px',
            right: '24px',
            background: 'var(--gold)',
            color: '#12100e',
            padding: '10px 20px',
            borderRadius: '8px',
            fontSize: '13px',
            fontWeight: '600',
            boxShadow: '0 4px 15px rgba(0,0,0,0.3)',
            animation: 'fade-in 0.2s ease'
          }}>
            {notification}
          </div>
        )}
      </div>

    </div>
  )
}
