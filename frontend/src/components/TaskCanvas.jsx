import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useAriaStore } from '../store/ariaStore'

const API_BASE = 'http://localhost:8001'

// ── Drag-to-place label on canvas image ────────────────────────────────────────
function CertificateOverlay({ imgUrl, fields, onFieldMove, previewRow }) {
  const containerRef = useRef(null)
  const [dragging, setDragging] = useState(null) // { fieldKey, startX, startY, origX, origY }

  const onMouseDown = (e, key) => {
    e.preventDefault()
    const r = containerRef.current.getBoundingClientRect()
    setDragging({ key, startX: e.clientX, startY: e.clientY, origX: fields[key]?.x || 0.5, origY: fields[key]?.y || 0.5, rect: r })
  }

  useEffect(() => {
    if (!dragging) return
    const onMove = (e) => {
      const r = dragging.rect
      const dx = (e.clientX - dragging.startX) / r.width
      const dy = (e.clientY - dragging.startY) / r.height
      onFieldMove(dragging.key, Math.max(0, Math.min(1, dragging.origX + dx)), Math.max(0, Math.min(1, dragging.origY + dy)))
    }
    const onUp = () => setDragging(null)
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => { window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [dragging, onFieldMove])

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height: '100%', cursor: 'crosshair' }}>
      {imgUrl && <img src={imgUrl} alt="template" style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block' }} draggable={false} />}
      {Object.entries(fields).map(([key, cfg]) => (
        <div
          key={key}
          onMouseDown={e => onMouseDown(e, key)}
          style={{
            position: 'absolute',
            left: `${cfg.x * 100}%`,
            top: `${cfg.y * 100}%`,
            transform: 'translate(-50%, -50%)',
            fontFamily: cfg.fontFamily || 'serif',
            fontSize: `${cfg.fontSize || 32}px`,
            color: cfg.color || '#000000',
            fontWeight: 'bold',
            cursor: 'grab',
            userSelect: 'none',
            textShadow: '1px 1px 3px rgba(255,255,255,0.8), -1px -1px 3px rgba(255,255,255,0.8)',
            whiteSpace: 'nowrap',
            background: 'rgba(232,201,122,0.15)',
            borderRadius: '4px',
            padding: '2px 6px',
            border: '1.5px dashed rgba(232,201,122,0.6)',
          }}
          title={`Drag to reposition ${key}`}
        >
          {previewRow?.[key] || `[${key}]`}
        </div>
      ))}
    </div>
  )
}

// ── Drag-drop file zone ────────────────────────────────────────────────────────
function DropZone({ label, accept, onFile, fileName, icon }) {
  const [over, setOver] = useState(false)
  const inputRef = useRef(null)
  const onDrop = (e) => {
    e.preventDefault(); setOver(false)
    const f = e.dataTransfer.files[0]
    if (f) onFile(f)
  }
  return (
    <div
      onClick={() => inputRef.current.click()}
      onDragOver={e => { e.preventDefault(); setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={onDrop}
      style={{
        border: `2px dashed ${over ? 'var(--gold-primary)' : 'var(--glass-border)'}`,
        borderRadius: '10px', padding: '14px 10px', textAlign: 'center',
        cursor: 'pointer', transition: 'all 0.2s', flex: 1,
        background: over ? 'rgba(232,201,122,0.07)' : 'transparent',
        fontSize: '11px', color: fileName ? 'var(--accent-green)' : 'var(--text-secondary)',
      }}
    >
      <div style={{ fontSize: '22px', marginBottom: '4px' }}>{icon}</div>
      {fileName || label}
      <input ref={inputRef} type="file" accept={accept} style={{ display: 'none' }} onChange={e => e.target.files[0] && onFile(e.target.files[0])} />
    </div>
  )
}

export default function TaskCanvas({ onStopAgent }) {
  const {
    activeCanvas,
    activeAgents,
    taskLog,
    memoryData,
    hitlRequest,
  } = useAriaStore()

  // ── Form fill state ──────────────────────────────────────────────────────────
  const [formFields, setFormFields] = useState([
    { id: 1, name: 'Full Name', key: 'name', status: 'pending', val: '' },
    { id: 2, name: 'Email Address', key: 'email', status: 'pending', val: '' },
    { id: 3, name: 'College Name', key: 'college', status: 'pending', val: '' },
    { id: 4, name: 'Department', key: 'department', status: 'pending', val: '' },
    { id: 5, name: 'Roll Number', key: 'rollNo', status: 'pending', val: '' },
    { id: 6, name: 'Team Code', key: 'team_code', status: 'pending', val: '' },
  ])
  useEffect(() => {
    setFormFields(prev => prev.map(f => {
      const memVal = memoryData[f.key] || ''
      return { ...f, val: memVal, status: memVal ? 'autofilled' : (hitlRequest?.fields?.some(hf => hf.memory_key === f.key) ? 'needs-input' : 'pending') }
    }))
  }, [memoryData, hitlRequest])

  // ── Research canvas state ────────────────────────────────────────────────────
  const [expandedSection, setExpandedSection] = useState(0)
  const researchFindings = [
    { q: 'What is quantum computing?', synth: 'Quantum computing leverages qubits in superposition states, solving complex problems exponentially faster than classical computers.', sources: [{ title: 'IBM Quantum', url: 'https://quantum-computing.ibm.com' }] },
    { q: 'Key applications', synth: 'Cryptography, optimization, drug discovery, and supply chain logistics.', sources: [{ title: 'MIT Tech Review', url: 'https://techreview.com' }] },
  ]

  // ── Shared log ref ───────────────────────────────────────────────────────────
  const logRef = useRef(null)
  useEffect(() => { logRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [taskLog])

  // ════════════════════════════════════════════════════════════════════════════
  // EMAIL CANVAS STATE
  // ════════════════════════════════════════════════════════════════════════════
  const [emailCsvFile, setEmailCsvFile] = useState(null)
  const [emailCsvPath, setEmailCsvPath] = useState('')
  const [emailCsvCols, setEmailCsvCols] = useState({})  // detected roles
  const [emailHeaders, setEmailHeaders] = useState([])
  const [emailPreview, setEmailPreview] = useState([])
  const [emailSubject, setEmailSubject] = useState('🎓 Your Certificate — [Event Name]')
  const [emailBody, setEmailBody] = useState('')
  const [emailLoading, setEmailLoading] = useState('')
  const [emailSending, setEmailSending] = useState(false)
  const [emailEventName, setEmailEventName] = useState('')
  const [smtpSender, setSmtpSender] = useState('')
  const [smtpPass, setSmtpPass] = useState('')
  const [emailResult, setEmailResult] = useState('')
  const [emailTab, setEmailTab] = useState('editor') // 'editor' | 'preview'

  const uploadEmailCsv = async (file) => {
    setEmailCsvFile(file)
    setEmailLoading('Detecting columns…')
    const fd = new FormData(); fd.append('file', file)
    try {
      const res = await fetch(`${API_BASE}/api/automation/upload-csv`, { method: 'POST', body: fd })
      const data = await res.json()
      setEmailCsvPath(data.saved_path || '')
      setEmailCsvCols(data.detected || {})
      setEmailHeaders(data.headers || [])
      setEmailPreview(data.preview || [])
      setEmailLoading('Drafting HTML template with Aria…')
      // Auto-draft
      const draftRes = await fetch(`${API_BASE}/api/automation/draft-email`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ detected_cols: data.detected, event_name: emailEventName || 'Our Event', tone: 'professional' })
      })
      const draft = await draftRes.json()
      setEmailBody(draft.html || '')
      setEmailLoading('')
    } catch (e) {
      setEmailLoading(`Error: ${e.message}`)
    }
  }

  const insertPlaceholder = (ph) => {
    setEmailBody(prev => prev + ph)
  }

  const sendEmails = async () => {
    if (!emailCsvPath || !emailBody) return
    setEmailSending(true); setEmailResult('')
    try {
      const res = await fetch(`${API_BASE}/api/automation/send-emails`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          csv_path: emailCsvPath,
          subject: emailSubject,
          html_template: emailBody,
          smtp_sender: smtpSender,
          smtp_password: smtpPass,
          name_col: emailCsvCols.name || 'Member Name',
          team_col: emailCsvCols.team || 'Team Name',
          email_col: emailCsvCols.email || 'Email',
        })
      })
      const data = await res.json()
      setEmailResult(data.result || 'Done')
    } catch (e) { setEmailResult(`Error: ${e.message}`) }
    setEmailSending(false)
  }

  // ════════════════════════════════════════════════════════════════════════════
  // CERTIFICATE CANVAS STATE
  // ════════════════════════════════════════════════════════════════════════════
  const [certTemplateFile, setCertTemplateFile] = useState(null)
  const [certTemplateUrl, setCertTemplateUrl] = useState('')
  const [certTemplatePath, setCertTemplatePath] = useState('')
  const [certCsvFile, setCertCsvFile] = useState(null)
  const [certCsvPath, setCertCsvPath] = useState('')
  const [certCsvCols, setCertCsvCols] = useState({})
  const [certHeaders, setCertHeaders] = useState([])
  const [certPreview, setCertPreview] = useState([])
  const [certLoading, setCertLoading] = useState('')
  const [certResult, setCertResult] = useState('')
  const [certGenerating, setCertGenerating] = useState(false)
  const [groupCol, setGroupCol] = useState('')

  // Draggable text fields on template: { name: {x, y, fontSize, fontFamily, color} }
  const [certFields, setCertFields] = useState({
    name: { x: 0.5, y: 0.5, fontSize: 70, fontFamily: 'Times New Roman, serif', color: '#000000' }
  })
  const [activeField, setActiveField] = useState('name')

  const uploadCertTemplate = async (file) => {
    setCertTemplateFile(file)
    const localUrl = URL.createObjectURL(file)
    setCertTemplateUrl(localUrl)
    const fd = new FormData(); fd.append('file', file)
    try {
      const res = await fetch(`${API_BASE}/api/automation/upload-template`, { method: 'POST', body: fd })
      const data = await res.json()
      setCertTemplatePath(data.saved_path || '')
    } catch (e) { console.error(e) }
  }

  const uploadCertCsv = async (file) => {
    setCertCsvFile(file)
    const fd = new FormData(); fd.append('file', file)
    setCertLoading('Detecting columns…')
    try {
      const res = await fetch(`${API_BASE}/api/automation/upload-csv`, { method: 'POST', body: fd })
      const data = await res.json()
      setCertCsvPath(data.saved_path || '')
      setCertCsvCols(data.detected || {})
      setCertHeaders(data.headers || [])
      setCertPreview(data.preview || [])
      // Auto-set group col to first 'team' detection
      if (data.detected?.team) setGroupCol(data.detected.team)
      else if (data.headers?.length > 1) setGroupCol(data.headers[1])
      setCertLoading('')
    } catch (e) { setCertLoading(`Error: ${e.message}`) }
  }

  const addCertField = (header) => {
    setCertFields(prev => ({
      ...prev,
      [header]: { x: 0.5, y: 0.6 + Object.keys(prev).length * 0.08, fontSize: 40, fontFamily: 'Arial, sans-serif', color: '#333333' }
    }))
    setActiveField(header)
  }

  const onFieldMove = useCallback((key, x, y) => {
    setCertFields(prev => ({ ...prev, [key]: { ...prev[key], x, y } }))
  }, [])

  const updateActiveField = (prop, val) => {
    if (!activeField) return
    setCertFields(prev => ({ ...prev, [activeField]: { ...prev[activeField], [prop]: val } }))
  }

  const generateCerts = async () => {
    if (!certCsvPath || !certTemplatePath) return
    setCertGenerating(true); setCertResult('')
    // Build layout for the primary name field (first field = name)
    const nameField = certFields[certCsvCols.name || 'Member Name'] || certFields['name'] || Object.values(certFields)[0]
    try {
      const res = await fetch(`${API_BASE}/api/automation/generate-certs`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          csv_path: certCsvPath,
          template_path: certTemplatePath,
          layout: {
            text_x: nameField?.x || 0.5,
            text_y: nameField?.y || 0.5,
            font_size: nameField?.fontSize || 70,
            font_path: null,
            text_color: hexToRgb(nameField?.color || '#000000'),
            name_col: certCsvCols.name || 'Member Name',
            group_col: groupCol || certCsvCols.team || 'Team Name',
          }
        })
      })
      const data = await res.json()
      setCertResult(data.result || 'Done')
    } catch (e) { setCertResult(`Error: ${e.message}`) }
    setCertGenerating(false)
  }

  const hexToRgb = (hex) => {
    const r = parseInt(hex.slice(1, 3), 16)
    const g = parseInt(hex.slice(3, 5), 16)
    const b = parseInt(hex.slice(5, 7), 16)
    return [r, g, b]
  }

  // Preview row for overlay (first CSV row)
  const previewRow = certPreview[0] ? Object.fromEntries(
    Object.entries(certCsvCols).map(([role, col]) => [col, certPreview[0][col]])
  ) : {}

  const fontFamilies = [
    { label: 'Times New Roman', value: 'Times New Roman, serif' },
    { label: 'Arial', value: 'Arial, sans-serif' },
    { label: 'Georgia', value: 'Georgia, serif' },
    { label: 'Courier New', value: 'Courier New, monospace' },
    { label: 'Palatino', value: 'Palatino Linotype, serif' },
  ]

  return (
    <div className="canvas-zone" style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '8px' }}>

      {/* Sub-Agent Chips */}
      <div className="chip-stack">
        {activeAgents.map(agent => (
          <div key={agent.id} className="sub-agent-chip" style={{ border: `1px solid ${agent.accentColor || 'var(--glass-border)'}` }}>
            <div className="chip-header">
              <span className="chip-name" style={{ color: agent.accentColor }}>🤖 {agent.name}</span>
              <button className="chip-pause" style={{ border: `1.5px solid ${agent.accentColor}`, color: agent.accentColor }}>Pause</button>
            </div>
            <div className="chip-step">{agent.step}</div>
            <svg className="chip-heartbeat" viewBox="0 0 80 20">
              <path d="M 0 10 L 20 10 L 25 2 L 30 18 L 35 10 L 55 10 L 60 5 L 65 15 L 70 10 L 80 10" fill="none" stroke={agent.accentColor || '#10b981'} strokeWidth="1.5" strokeDasharray="100" style={{ animation: 'heartbeat-offset 2s linear infinite' }} />
            </svg>
          </div>
        ))}
      </div>

      {/* ── FORM CANVAS ── */}
      {activeCanvas === 'form' && (
        <div className="form-canvas">
          <div className="browser-frame">
            <div className="browser-url-bar">🌐 https://unstop.com/competitions/register</div>
            <div className="browser-content" style={{ padding: '20px', overflowY: 'auto' }}>
              <div style={{ width: '100%', maxWidth: '380px', margin: 'auto', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '8px', padding: '16px' }}>
                <h3 style={{ fontSize: '14px', marginBottom: '16px', color: 'var(--gold-primary)', textAlign: 'center' }}>Registration Form</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {formFields.map(f => (
                    <div key={f.id} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                        <span style={{ background: '#facc15', color: '#000', fontSize: '9px', fontWeight: 'bold', padding: '1px 3px', borderRadius: '3px', marginRight: '6px' }}>[{f.id}]</span>
                        {f.name}
                      </label>
                      <input type="text" disabled value={f.val} style={{ background: 'rgba(0,0,0,0.4)', border: f.status === 'autofilled' ? '1px solid var(--accent-green)' : f.status === 'needs-input' ? '1px solid var(--accent-coral)' : '1px solid rgba(255,255,255,0.08)', borderRadius: '5px', padding: '6px 10px', color: '#fff', fontSize: '11px' }} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          <div className="field-panel">
            <div className="field-panel-title">Form Fields</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '160px', overflowY: 'auto', scrollbarWidth: 'thin' }}>
              {formFields.map(f => (
                <div key={f.id} className="field-row">
                  <div className="field-badge">[{f.id}]</div>
                  <div style={{ flex: 1 }}>{f.name}</div>
                  <div className={`status-${f.status}`} style={{ fontSize: '10px' }}>{f.status === 'autofilled' ? '✅' : f.status === 'needs-input' ? '⚠' : '⏳'} {f.status}</div>
                </div>
              ))}
            </div>
            <div className="field-panel-title" style={{ marginTop: '10px' }}>Action Log</div>
            <div className="action-log">
              {taskLog.length === 0 ? <div className="log-line muted">&gt; Waiting for agent…</div> : taskLog.map((log, idx) => <div key={idx} className="log-line active">&gt; {log}</div>)}
              <div ref={logRef} />
            </div>
            <div className="control-row">
              <button className="ctrl-btn gold">Pause</button>
              <button className="ctrl-btn coral">Override</button>
              <button className="ctrl-btn danger" onClick={onStopAgent}>Abort</button>
            </div>
          </div>
        </div>
      )}

      {/* ── RESEARCH CANVAS ── */}
      {activeCanvas === 'research' && (
        <div className="research-canvas">
          <div className="research-header">🔬 Research Agent Panel</div>
          <div className="research-body">
            {researchFindings.map((finding, idx) => (
              <div key={idx} className="research-section">
                <div className="research-section-header" onClick={() => setExpandedSection(idx === expandedSection ? -1 : idx)}>
                  {expandedSection === idx ? '▼' : '▶'} {finding.q}
                </div>
                {expandedSection === idx && (
                  <>
                    <div className="research-finding">{finding.synth}</div>
                    <div className="research-sources">Sources: {finding.sources.map((s, si) => <a key={si} href={s.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-teal)', marginRight: '8px', textDecoration: 'underline' }}>{s.title}</a>)}</div>
                  </>
                )}
              </div>
            ))}
            <div className="field-panel-title" style={{ marginTop: '10px' }}>Scout Log</div>
            <div className="action-log" style={{ height: '100px' }}>
              {taskLog.map((log, idx) => <div key={idx} className="log-line done">&gt; {log}</div>)}
              <div ref={logRef} />
            </div>
          </div>
        </div>
      )}

      {/* ── EMAIL CANVAS ── */}
      {activeCanvas === 'email' && (
        <div style={{ display: 'flex', gap: '10px', flex: 1, overflow: 'hidden', flexDirection: 'column' }}>

          {/* Row 1: Drop zones + event name */}
          <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
            <DropZone label="Drop Recipient CSV" accept=".csv" icon="📋" onFile={uploadEmailCsv} fileName={emailCsvFile?.name} />
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <input
                type="text"
                placeholder="Event name (e.g. IntelliAI Arena 2026)"
                value={emailEventName}
                onChange={e => setEmailEventName(e.target.value)}
                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)', borderRadius: '6px', padding: '6px 10px', color: '#fff', fontSize: '11px', width: '100%' }}
              />
              <input
                type="text"
                placeholder="Email Subject"
                value={emailSubject}
                onChange={e => setEmailSubject(e.target.value)}
                style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)', borderRadius: '6px', padding: '6px 10px', color: '#fff', fontSize: '11px', width: '100%' }}
              />
            </div>
          </div>

          {/* Detected columns chips */}
          {Object.keys(emailCsvCols).length > 0 && (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Detected:</span>
              {Object.entries(emailCsvCols).map(([role, col]) => (
                <span key={role} className="research-pill" style={{ cursor: 'pointer', fontSize: '10px' }} onClick={() => insertPlaceholder(`[${col}]`)}>
                  {role}: <strong>{col}</strong>
                </span>
              ))}
            </div>
          )}

          {/* Status bar */}
          {emailLoading && <div style={{ fontSize: '11px', color: 'var(--accent-teal)', padding: '4px 0' }}>⏳ {emailLoading}</div>}

          {/* Editor / Preview tabs */}
          <div style={{ display: 'flex', gap: '6px', marginBottom: '2px' }}>
            {['editor', 'preview'].map(tab => (
              <button key={tab} onClick={() => setEmailTab(tab)} style={{ background: emailTab === tab ? 'var(--gold-primary)' : 'transparent', color: emailTab === tab ? '#000' : 'var(--text-secondary)', border: '1px solid var(--glass-border)', borderRadius: '6px', padding: '4px 12px', fontSize: '11px', cursor: 'pointer' }}>
                {tab === 'editor' ? '✏️ Editor' : '👁 Preview'}
              </button>
            ))}
          </div>

          {/* Main editor/preview area */}
          <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {emailTab === 'editor' ? (
              <textarea
                value={emailBody}
                onChange={e => setEmailBody(e.target.value)}
                placeholder="HTML template will appear here after dropping a CSV…"
                style={{ flex: 1, background: 'rgba(0,0,0,0.35)', border: '1px solid var(--glass-border)', borderRadius: '8px', padding: '10px', color: 'var(--accent-teal)', fontSize: '11px', resize: 'none', fontFamily: 'monospace', outline: 'none' }}
              />
            ) : (
              <iframe
                srcDoc={emailBody || '<p style="color:#888;text-align:center;margin-top:40px">No template yet — drop a CSV first</p>'}
                style={{ flex: 1, border: '1px solid var(--glass-border)', borderRadius: '8px', background: '#fff' }}
                title="email-preview"
                sandbox="allow-same-origin"
              />
            )}
          </div>

          {/* SMTP + Send */}
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
            <input type="email" placeholder="Gmail sender (optional)" value={smtpSender} onChange={e => setSmtpSender(e.target.value)} style={{ flex: 1, minWidth: '160px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)', borderRadius: '6px', padding: '5px 8px', color: '#fff', fontSize: '10px' }} />
            <input type="password" placeholder="App password (optional)" value={smtpPass} onChange={e => setSmtpPass(e.target.value)} style={{ flex: 1, minWidth: '140px', background: 'rgba(0,0,0,0.3)', border: '1px solid var(--glass-border)', borderRadius: '6px', padding: '5px 8px', color: '#fff', fontSize: '10px' }} />
            <button
              onClick={sendEmails}
              disabled={emailSending || !emailCsvPath || !emailBody}
              className="btn-approve"
              style={{ minWidth: '140px', opacity: (emailSending || !emailCsvPath || !emailBody) ? 0.5 : 1 }}
            >
              {emailSending ? '⏳ Sending…' : `📧 Send to ${emailPreview.length > 0 ? `${emailPreview.length}+ recipients` : 'recipients'}`}
            </button>
          </div>

          {emailResult && <div style={{ fontSize: '11px', color: emailResult.startsWith('✅') ? 'var(--accent-green)' : 'var(--accent-coral)', padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>{emailResult}</div>}

          {/* Task log */}
          {taskLog.length > 0 && (
            <div className="action-log" style={{ height: '70px' }}>
              {taskLog.map((log, idx) => <div key={idx} className="log-line active">&gt; {log}</div>)}
              <div ref={logRef} />
            </div>
          )}
        </div>
      )}

      {/* ── CERTIFICATE CANVAS ── */}
      {activeCanvas === 'certificate' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1, overflow: 'hidden' }}>

          {/* Row 1: Drop zones */}
          <div style={{ display: 'flex', gap: '10px' }}>
            <DropZone label="Drop Template Image (PNG/JPG)" accept=".png,.jpg,.jpeg" icon="🖼️" onFile={uploadCertTemplate} fileName={certTemplateFile?.name} />
            <DropZone label="Drop Recipient CSV" accept=".csv" icon="📋" onFile={uploadCertCsv} fileName={certCsvFile?.name} />
          </div>

          {/* Detected columns + add field buttons */}
          {certHeaders.length > 0 && (
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center' }}>
              <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Add to canvas:</span>
              {certHeaders.map(h => (
                <span
                  key={h}
                  className="research-pill"
                  style={{ cursor: 'pointer', fontSize: '10px', background: certFields[h] ? 'rgba(232,201,122,0.2)' : undefined, border: certFields[h] ? '1px solid var(--gold-primary)' : undefined }}
                  onClick={() => !certFields[h] && addCertField(h)}
                  title={certFields[h] ? 'Already on canvas' : `Place "${h}" on certificate`}
                >
                  {certFields[h] ? '✓' : '+'} {h}
                </span>
              ))}
            </div>
          )}

          {certLoading && <div style={{ fontSize: '11px', color: 'var(--accent-teal)' }}>⏳ {certLoading}</div>}

          {/* Main canvas with overlay */}
          <div className="glass-card" style={{ flex: 1, position: 'relative', overflow: 'hidden', minHeight: '200px' }}>
            {certTemplateUrl ? (
              <CertificateOverlay
                imgUrl={certTemplateUrl}
                fields={certFields}
                onFieldMove={onFieldMove}
                previewRow={previewRow}
              />
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-secondary)', fontSize: '12px', flexDirection: 'column', gap: '8px' }}>
                <div style={{ fontSize: '36px' }}>🖼️</div>
                <div>Drop a template image above to begin</div>
              </div>
            )}
          </div>

          {/* Font controls for active field */}
          {certTemplateUrl && Object.keys(certFields).length > 0 && (
            <div className="glass-card" style={{ padding: '10px', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
              {/* Field selector */}
              <select
                value={activeField || ''}
                onChange={e => setActiveField(e.target.value)}
                style={{ background: '#16161f', color: '#fff', border: '1px solid var(--glass-border)', borderRadius: '6px', padding: '4px 8px', fontSize: '11px' }}
              >
                {Object.keys(certFields).map(k => <option key={k} value={k}>{k}</option>)}
              </select>

              {/* Font family */}
              <select
                value={certFields[activeField]?.fontFamily || 'Times New Roman, serif'}
                onChange={e => updateActiveField('fontFamily', e.target.value)}
                style={{ background: '#16161f', color: '#fff', border: '1px solid var(--glass-border)', borderRadius: '6px', padding: '4px 8px', fontSize: '11px' }}
              >
                {fontFamilies.map(f => <option key={f.value} value={f.value}>{f.label}</option>)}
              </select>

              {/* Font size */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Size: {certFields[activeField]?.fontSize || 70}px</span>
                <input type="range" min="20" max="120" value={certFields[activeField]?.fontSize || 70} onChange={e => updateActiveField('fontSize', Number(e.target.value))} style={{ width: '80px' }} />
              </div>

              {/* Color */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Color:</span>
                <input type="color" value={certFields[activeField]?.color || '#000000'} onChange={e => updateActiveField('color', e.target.value)} style={{ width: '32px', height: '24px', border: 'none', borderRadius: '4px', cursor: 'pointer', background: 'none' }} />
              </div>

              {/* Group by */}
              {certHeaders.length > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>Folder by:</span>
                  <select value={groupCol} onChange={e => setGroupCol(e.target.value)} style={{ background: '#16161f', color: '#fff', border: '1px solid var(--glass-border)', borderRadius: '6px', padding: '4px 8px', fontSize: '11px' }}>
                    {certHeaders.map(h => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
              )}

              <button
                onClick={generateCerts}
                disabled={certGenerating || !certCsvPath || !certTemplatePath}
                className="btn-approve"
                style={{ marginLeft: 'auto', opacity: (certGenerating || !certCsvPath || !certTemplatePath) ? 0.5 : 1 }}
              >
                {certGenerating ? '⏳ Generating…' : `🎓 Generate ${certPreview.length > 0 ? `${certPreview.length}+ PDFs` : 'PDFs'}`}
              </button>
            </div>
          )}

          {certResult && <div style={{ fontSize: '11px', color: certResult.startsWith('✅') ? 'var(--accent-green)' : 'var(--accent-coral)', padding: '6px', background: 'rgba(0,0,0,0.2)', borderRadius: '6px' }}>{certResult}</div>}

          {/* Task log stream */}
          {taskLog.length > 0 && (
            <div className="action-log" style={{ height: '70px' }}>
              {taskLog.map((log, idx) => <div key={idx} className="log-line active">&gt; {log}</div>)}
              <div ref={logRef} />
            </div>
          )}
        </div>
      )}

      {/* ── SCRIPT CANVAS ── */}
      {activeCanvas === 'script' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', flex: 1, overflow: 'hidden' }}>
          <div className="glass-card" style={{ flex: 1, padding: '10px', display: 'flex', flexDirection: 'column' }}>
            <div className="field-panel-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Script Preview</span><span style={{ color: 'var(--accent-purple)' }}>script_runner.py</span>
            </div>
            <pre style={{ flex: 1, background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '10px', color: 'var(--accent-teal)', fontFamily: 'var(--font-mono)', fontSize: '10px', overflowY: 'auto' }}>
              {`# Generated by ARIA Automation Studio
import csv, smtplib

def run_automation_loop():
    print("Initializing mail servers...")
    print("Script execution completed successfully.")
`}
            </pre>
          </div>
          <div className="glass-card" style={{ height: '110px', padding: '10px', display: 'flex', flexDirection: 'column' }}>
            <div className="field-panel-title">Console Output Stream</div>
            <div className="action-log">
              {taskLog.length === 0 ? (
                <><div className="log-line active">&gt; Executing script_runner.py...</div>
                  <div className="log-line done">&gt; Script complete.</div></>
              ) : taskLog.map((log, idx) => <div key={idx} className="log-line done">&gt; {log}</div>)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}



