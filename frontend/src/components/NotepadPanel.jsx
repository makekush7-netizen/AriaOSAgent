import React, { useEffect, useState } from 'react'

const slugify = (title) => title.toLowerCase().trim().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')

export default function NotepadPanel({ apiBase }) {
  const [notes, setNotes] = useState([])
  const [selectedNote, setSelectedNote] = useState(null)
  const [editorContent, setEditorContent] = useState('')
  const [editorTitle, setEditorTitle] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const [notification, setNotification] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [newTitle, setNewTitle] = useState('')

  const fetchNotes = async () => {
    try {
      const res = await fetch(`${apiBase}/api/notes`)
      if (res.ok) {
        const data = await res.json()
        setNotes(data)

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

  const showNotification = (msg) => {
    setNotification(msg)
    setTimeout(() => setNotification(''), 2500)
  }

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
        showNotification('Saved')
        fetchNotes()
      }
    } catch (e) {
      showNotification('Save failed')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!selectedNote) return
    try {
      const res = await fetch(`${apiBase}/api/notes/${selectedNote}`, { method: 'DELETE' })
      if (res.ok) {
        showNotification('Deleted')
        setSelectedNote(null)
        setEditorContent('')
        setEditorTitle('')
        setDeleteOpen(false)
        fetchNotes()
      }
    } catch (e) {
      showNotification('Delete failed')
    }
  }

  const handleCreate = async () => {
    const cleanTitle = newTitle.trim()
    const filename = `${slugify(cleanTitle)}.md`
    if (!cleanTitle || filename === '.md') return

    try {
      const res = await fetch(`${apiBase}/api/notes/${filename}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: `# ${cleanTitle}\n\nStart typing findings here...` })
      })
      if (res.ok) {
        showNotification('Created')
        setCreateOpen(false)
        setNewTitle('')
        await fetchNotes()
        await loadNoteContent(filename)
      }
    } catch (e) {
      showNotification('Create failed')
    }
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(editorContent)
    showNotification('Copied')
  }

  return (
    <section className="panel-page notepad-page">
      <div className="panel-hero compact">
        <div>
          <p className="eyebrow">Findings</p>
          <h1>Notepad</h1>
          <p>Research notes, task logs, and generated summaries.</p>
        </div>
        <button type="button" className="primary-btn" onClick={() => setCreateOpen(true)}>New Note</button>
      </div>

      <div className="notepad-shell">
        <aside className="glass-panel note-list-panel">
          <div className="section-heading compact">
            <span>Documents</span>
            <small>{notes.length} saved</small>
          </div>

          <div className="note-list">
            {notes.map((note) => (
              <button
                key={note.filename}
                className={`note-list-item ${selectedNote === note.filename ? 'active' : ''}`}
                onClick={() => loadNoteContent(note.filename)}
              >
                <span className="note-file-icon" />
                <span>{note.title}</span>
              </button>
            ))}

            {notes.length === 0 && (
              <div className="empty-note">No findings yet.</div>
            )}
          </div>
        </aside>

        <article className="glass-panel note-editor-panel">
          {selectedNote ? (
            <>
              <div className="note-editor-header">
                <div>
                  <p className="eyebrow">Editing</p>
                  <h2>{editorTitle}</h2>
                </div>
                <div className="note-actions">
                  <button type="button" className="secondary-btn" onClick={handleCopy}>Copy</button>
                  <button type="button" className="primary-btn" onClick={handleSave}>{isSaving ? 'Saving' : 'Save'}</button>
                  <button type="button" className="danger-btn" onClick={() => setDeleteOpen(true)}>Delete</button>
                </div>
              </div>

              <textarea
                value={editorContent}
                onChange={(e) => setEditorContent(e.target.value)}
                className="note-textarea"
                placeholder="Type markdown content here..."
              />
            </>
          ) : (
            <div className="empty-editor">
              <div className="empty-mark" />
              <h2>Select a note</h2>
              <p>Open a document or create a new one to start capturing findings.</p>
            </div>
          )}

          {notification && <div className="toast">{notification}</div>}
        </article>
      </div>

      {createOpen && (
        <div className="dialog-backdrop">
          <div className="glass-panel modal-card">
            <h2>Create Note</h2>
            <input value={newTitle} onChange={(e) => setNewTitle(e.target.value)} placeholder="Document title" autoFocus />
            <div className="modal-actions">
              <button type="button" className="secondary-btn" onClick={() => setCreateOpen(false)}>Cancel</button>
              <button type="button" className="primary-btn" onClick={handleCreate}>Create</button>
            </div>
          </div>
        </div>
      )}

      {deleteOpen && (
        <div className="dialog-backdrop">
          <div className="glass-panel modal-card">
            <h2>Delete Note</h2>
            <p>This removes "{editorTitle}" from local notes.</p>
            <div className="modal-actions">
              <button type="button" className="secondary-btn" onClick={() => setDeleteOpen(false)}>Cancel</button>
              <button type="button" className="danger-btn" onClick={handleDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
