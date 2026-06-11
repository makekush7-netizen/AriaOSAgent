import React, { useState, useEffect, useRef } from 'react'
import { useAriaStore } from '../store/ariaStore'

export default function TaskCanvas({ onStopAgent }) {
  const {
    activeCanvas,
    activeAgents,
    taskLog,
    memoryData,
    hitlRequest,
    setHitlRequest
  } = useAriaStore()

  // Form fill state simulation
  const [formFields, setFormFields] = useState([
    { id: 1, name: 'Full Name', key: 'name', status: 'pending', val: '' },
    { id: 2, name: 'Email Address', key: 'email', status: 'pending', val: '' },
    { id: 3, name: 'College Name', key: 'college', status: 'pending', val: '' },
    { id: 4, name: 'Department', key: 'department', status: 'pending', val: '' },
    { id: 5, name: 'Roll Number', key: 'rollNo', status: 'pending', val: '' },
    { id: 6, name: 'Team Code', key: 'team_code', status: 'pending', val: '' }
  ])

  // Sync memory details to the simulated fields
  useEffect(() => {
    setFormFields(prev => prev.map(f => {
      const memVal = memoryData[f.key] || ''
      return {
        ...f,
        val: memVal,
        status: memVal ? 'autofilled' : (hitlRequest?.fields?.some(hf => hf.memory_key === f.key) ? 'needs-input' : 'pending')
      }
    }))
  }, [memoryData, hitlRequest])

  // Research canvas dummy data
  const [researchPills, setResearchPills] = useState([
    'What is quantum computing?',
    'Key applications',
    'Major industry players',
    'Timeline to commercial viability'
  ])

  const [expandedSection, setExpandedSection] = useState(0)

  const researchFindings = [
    {
      q: 'What is quantum computing?',
      synth: 'Quantum computing is a multidisciplinary field comprising aspects of computer science, physics, and mathematics that utilizes quantum mechanics to solve complex problems faster than on classical computers. It leverages qubits which exist in superposition states.',
      sources: [
        { title: 'IBM Quantum Learning', url: 'https://quantum-computing.ibm.com' },
        { title: 'Nature Physics Review', url: 'https://nature.com/articles/quant-comp' }
      ]
    },
    {
      q: 'Key applications of quantum tech',
      synth: 'Key applications include cryptography (breaking RSA, quantum key distribution), optimization of complex networks (logistics, supply chains), and quantum chemistry simulations for drug discovery and advanced material science.',
      sources: [
        { title: 'MIT Technology Review', url: 'https://techreview.com/quantum-apps' }
      ]
    }
  ]

  // Email blast canvas dummy state
  const [emailSubject, setEmailSubject] = useState('Confirmation: Hackathon Registration Received!')
  const [emailBody, setEmailBody] = useState('Hi {{name}},\n\nThank you for registering. Your team code is {{team_code}}.\n\nBest regards,\nARIA Team')

  // Certificate canvas state
  const [certFont, setCertFont] = useState('Serif')
  const [certSize, setCertSize] = useState(32)

  // Scroll to bottom of log
  const logRef = useRef(null)
  useEffect(() => {
    logRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [taskLog])

  return (
    <div className="canvas-zone" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Sub-Agent Chips (floating) */}
      <div className="chip-stack">
        {activeAgents.map(agent => (
          <div key={agent.id} className="sub-agent-chip" style={{ border: `1px solid ${agent.accentColor || 'var(--glass-border)'}` }}>
            <div className="chip-header">
              <span className="chip-name" style={{ color: agent.accentColor }}>🤖 {agent.name}</span>
              <button className="chip-pause" style={{ border: `1.5px solid ${agent.accentColor}`, color: agent.accentColor }}>Pause</button>
            </div>
            <div className="chip-step">{agent.step}</div>
            
            {/* Heartbeat Wave */}
            <svg className="chip-heartbeat" viewBox="0 0 80 20">
              <path
                d="M 0 10 L 20 10 L 25 2 L 30 18 L 35 10 L 55 10 L 60 5 L 65 15 L 70 10 L 80 10"
                fill="none"
                stroke={agent.accentColor || '#10b981'}
                strokeWidth="1.5"
                strokeDasharray="100"
                style={{
                  animation: 'heartbeat-offset 2s linear infinite'
                }}
              />
            </svg>
          </div>
        ))}
      </div>

      {/* Render Canvas based on active Canvas state */}
      {activeCanvas === 'form' && (
        <div className="form-canvas">
          {/* Simulated Browser Webview */}
          <div className="browser-frame">
            <div className="browser-url-bar">
              🌐 https://unstop.com/competitions/google-girl-hackathon-2026/register
            </div>
            <div className="browser-content" style={{ padding: '20px', overflowY: 'auto' }}>
              <div style={{ width: '100%', maxWidth: '380px', margin: 'auto', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.04)', borderRadius: '8px', padding: '16px' }}>
                <h3 style={{ fontSize: '14px', marginBottom: '16px', color: 'var(--gold-primary)', textAlign: 'center' }}>Google Girl Hackathon Registration</h3>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {formFields.map(f => (
                    <div key={f.id} style={{ display: 'flex', flexDirection: 'column', gap: '4px', position: 'relative' }}>
                      <label style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                        <span style={{ background: '#facc15', color: '#000', fontSize: '9px', fontWeight: 'bold', padding: '1px 3px', borderRadius: '3px', marginRight: '6px' }}>
                          [{f.id}]
                        </span>
                        {f.name}
                      </label>
                      <input
                        type="text"
                        disabled
                        value={f.val}
                        style={{
                          background: 'rgba(0, 0, 0, 0.4)',
                          border: f.status === 'autofilled' ? '1px solid var(--accent-green)' : (f.status === 'needs-input' ? '1px solid var(--accent-coral)' : '1px solid rgba(255,255,255,0.08)'),
                          borderRadius: '5px',
                          padding: '6px 10px',
                          color: '#fff',
                          fontSize: '11px'
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Field panel and logs */}
          <div className="field-panel">
            <div className="field-panel-title">Form Fields</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '160px', overflowY: 'auto', scrollbarWidth: 'thin' }}>
              {formFields.map(f => (
                <div key={f.id} className="field-row">
                  <div className="field-badge">[{f.id}]</div>
                  <div style={{ flex: 1 }}>{f.name}</div>
                  <div className={`status-${f.status}`} style={{ fontSize: '10px' }}>
                    {f.status === 'autofilled' ? '✅ autofilled' : (f.status === 'needs-input' ? '⚠ needs input' : '⏳ pending')}
                  </div>
                  <div style={{ maxWidth: '60px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', opacity: 0.5, fontFamily: 'monospace', fontSize: '10px' }}>
                    {f.val}
                  </div>
                </div>
              ))}
            </div>

            <div className="field-panel-title" style={{ marginTop: '10px' }}>Action Log</div>
            <div className="action-log">
              {taskLog.length === 0 ? (
                <div className="log-line muted">&gt; Waiting for agent to stream status...</div>
              ) : (
                taskLog.map((log, idx) => (
                  <div key={idx} className="log-line active">
                    &gt; {log}
                  </div>
                ))
              )}
              <div ref={logRef} />
            </div>

            <div className="control-row">
              <button className="ctrl-btn gold">Pause</button>
              <button className="ctrl-btn coral">Override</button>
              <button className="ctrl-btn muted">Skip</button>
              <button className="ctrl-btn danger" onClick={onStopAgent}>Abort</button>
            </div>
          </div>
        </div>
      )}

      {activeCanvas === 'research' && (
        <div className="research-canvas">
          <div className="research-header">🔬 Research Agent Panel</div>
          <div className="research-pills">
            {researchPills.map((pill, idx) => (
              <span key={idx} className="research-pill">{pill}</span>
            ))}
          </div>

          <div className="research-body">
            {researchFindings.map((finding, idx) => (
              <div key={idx} className="research-section">
                <div className="research-section-header" onClick={() => setExpandedSection(idx === expandedSection ? -1 : idx)}>
                  {expandedSection === idx ? '▼' : '▶'} {finding.q}
                </div>
                {expandedSection === idx && (
                  <>
                    <div className="research-finding">{finding.synth}</div>
                    <div className="research-sources">
                      Sources: {finding.sources.map((s, si) => (
                        <a key={si} href={s.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent-teal)', marginRight: '8px', textDecoration: 'underline' }}>
                          {s.title}
                        </a>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ))}

            <div className="field-panel-title" style={{ marginTop: '10px' }}>Scout Log</div>
            <div className="action-log" style={{ height: '100px' }}>
              {taskLog.map((log, idx) => (
                <div key={idx} className="log-line done">&gt; {log}</div>
              ))}
              <div ref={logRef} />
            </div>
          </div>

          <div className="research-footer">
            <button className="research-btn">Export MD</button>
            <button className="research-btn">Export PDF</button>
            <input type="text" className="research-followup" placeholder="Ask follow-up details..." />
          </div>
        </div>
      )}

      {activeCanvas === 'email' && (
        <div style={{ display: 'flex', gap: '10px', flex: 1, overflow: 'hidden' }}>
          <div className="glass-card" style={{ flex: '0 0 45%', padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className="field-panel-title">Template Editor</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Subject:</label>
              <input type="text" value={emailSubject} onChange={e => setEmailSubject(e.target.value)} style={{ background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: '6px', padding: '6px', color: '#fff', fontSize: '11px' }} />
            </div>
            <div style={{ display: 'flex', flex: 1, flexDirection: 'column', gap: '4px' }}>
              <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Body:</label>
              <textarea value={emailBody} onChange={e => setEmailBody(e.target.value)} style={{ flex: 1, background: 'rgba(0,0,0,0.3)', border: '1px solid var(--border)', borderRadius: '6px', padding: '6px', color: '#fff', fontSize: '11px', resize: 'none', fontFamily: 'monospace' }} />
            </div>
            <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
              <span className="research-pill" style={{ cursor: 'pointer' }}>{"{{name}}"}</span>
              <span className="research-pill" style={{ cursor: 'pointer' }}>{"{{team_code}}"}</span>
            </div>
          </div>

          <div className="glass-card" style={{ flex: 1, padding: '10px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div className="field-panel-title">Recipient Panel</div>
            <div style={{ border: '2px dashed var(--border)', borderRadius: '10px', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)', fontSize: '11px' }}>
              Drag and drop mailing CSV Recipient sheet here
            </div>
            <div className="control-row">
              <button className="btn-approve" style={{ width: '100%' }}>Send to 47 Recipients</button>
            </div>
          </div>
        </div>
      )}

      {activeCanvas === 'certificate' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', flex: 1, overflow: 'hidden' }}>
          <div style={{ display: 'flex', gap: '12px' }}>
            <div className="glass-card" style={{ flex: 1, padding: '12px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '12px', border: '1px dashed var(--border)' }}>
              Drop Template Image (PNG/JPG)
            </div>
            <div className="glass-card" style={{ flex: 1, padding: '12px', textAlign: 'center', color: 'var(--text-secondary)', fontSize: '12px', border: '1px dashed var(--border)' }}>
              Drop Recipient CSV Data Sheet
            </div>
          </div>

          <div className="glass-card" style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
            <div style={{ width: '80%', height: '80%', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(232,201,122,0.15)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
              <span style={{ fontSize: '18px', color: 'var(--gold-primary)', fontFamily: certFont }}>Certificate of Participation</span>
              <span style={{ fontSize: '11px', marginTop: '12px', color: '#fff' }}>Proudly presented to:</span>
              <span style={{ fontSize: `${certSize}px`, color: 'var(--gold-primary)', fontWeight: 'bold', margin: '10px 0' }}>John Doe</span>
              <span style={{ fontSize: '10px', color: 'rgba(255,255,255,0.5)' }}>for Google Girl Hackathon 2026 completion</span>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <label style={{ fontSize: '11px' }}>Font:</label>
            <select value={certFont} onChange={e => setCertFont(e.target.value)} style={{ background: '#16161f', color: '#fff', border: '1px solid var(--border)', borderRadius: '6px', padding: '4px' }}>
              <option value="Serif">Serif</option>
              <option value="Sans-Serif">Sans-Serif</option>
              <option value="Monospace">Monospace</option>
            </select>
            <label style={{ fontSize: '11px' }}>Font Size:</label>
            <input type="range" min="20" max="60" value={certSize} onChange={e => setCertSize(Number(e.target.value))} />
            <button className="btn-approve" style={{ marginLeft: 'auto' }}>Generate 47 Certificates</button>
          </div>
        </div>
      )}

      {activeCanvas === 'script' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', flex: 1, overflow: 'hidden' }}>
          <div className="glass-card" style={{ flex: 1, padding: '10px', display: 'flex', flexDirection: 'column' }}>
            <div className="field-panel-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Script Preview</span>
              <span style={{ color: 'var(--accent-purple)' }}>script_runner.py</span>
            </div>
            <pre style={{ flex: 1, background: 'rgba(0,0,0,0.5)', borderRadius: '8px', padding: '10px', color: 'var(--accent-teal)', fontFamily: 'var(--font-mono)', fontSize: '10px', overflowY: 'auto' }}>
{`# Generated by ARIA ScriptRunner
import csv
import smtplib

def run_automation_loop():
    print("Initializing mail servers...")
    # Mailing script logic goes here
    print("Script execution completed successfully.")
`}
            </pre>
          </div>

          <div className="glass-card" style={{ height: '110px', padding: '10px', display: 'flex', flexDirection: 'column' }}>
            <div className="field-panel-title">Console Output Stream</div>
            <div className="action-log">
              <div className="log-line active">&gt; Executing script_runner.py...</div>
              <div className="log-line done">&gt; Mail loop initialized: sending logs...</div>
              <div className="log-line done">&gt; Complete: 47/47 emails dispatched successfully!</div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
