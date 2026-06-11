import React, { useState, useEffect, useRef } from 'react'

const TIMEOUT = 120

export default function HITLModal({ request, onRespond }) {
  const [countdown, setCountdown] = useState(TIMEOUT)
  const [inputValue, setInputValue] = useState('')
  const [batchValues, setBatchValues] = useState({})
  const [isRecording, setIsRecording] = useState(false)
  const timerRef = useRef(null)
  const recognitionRef = useRef(null)

  const isInput = request?.inputType === 'input'
  const isBatch = request?.inputType === 'batch_input'
  const fields = request?.fields || []

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SR && isInput) {
      const r = new SR()
      r.continuous = false; r.interimResults = false; r.lang = 'en-US'
      r.onresult = (e) => {
        setInputValue(e.results[0][0].transcript)
      }
      r.onend = () => setIsRecording(false)
      recognitionRef.current = r
    }
  }, [isInput])

  useEffect(() => {
    setCountdown(TIMEOUT)
    
    if (isBatch && fields.length > 0) {
      const init = {}
      fields.forEach(f => {
        init[f.memory_key] = ''
      })
      setBatchValues(init)
    }

    timerRef.current = setInterval(() => {
      setCountdown(p => {
        if (p <= 1) {
          clearInterval(timerRef.current)
          if (isBatch) {
            onRespond({ allowed: false, values: {} })
          } else {
            onRespond(isInput ? { allowed: false, value: '' } : false)
          }
          return 0
        }
        return p - 1
      })
    }, 1000)
    
    return () => {
      clearInterval(timerRef.current)
      if (isRecording) recognitionRef.current?.stop()
    }
  }, [request])

  const toggleMic = () => {
    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
    } else {
      setInputValue('')
      recognitionRef.current?.start()
      setIsRecording(true)
    }
  }

  return (
    <div id="hitl-modal" className="hitl-overlay" style={{ width: isBatch ? '420px' : '360px', maxHeight: '90vh', display: 'flex', flexDirection: 'column' }}>
      <div className="hitl-header">
        <div className="hitl-title">⚡ {request?.title || 'Permission Request'}</div>
        <div className="hitl-countdown">Timeout in {countdown}s</div>
      </div>
      <div className="hitl-desc" style={{ marginBottom: '16px' }}>
        {request?.description || 'ARIA requires your input.'}
      </div>
      
      {isInput && (
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <input 
            autoFocus
            style={{ flex: 1, background: 'var(--surface-hover)', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px', color: 'var(--text)', outline: 'none' }}
            value={inputValue}
            onChange={e => setInputValue(e.target.value)}
            placeholder="Type your answer..."
            onKeyDown={e => {
              if (e.key === 'Enter') {
                clearInterval(timerRef.current);
                onRespond({ allowed: true, value: inputValue })
              }
            }}
          />
          <button 
            onClick={toggleMic}
            style={{ width: '40px', height: '40px', borderRadius: '8px', background: isRecording ? '#ef4444' : 'var(--surface-hover)', border: '1px solid var(--border)', color: isRecording ? '#fff' : 'var(--text)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s' }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c-1.7 0-3 1.3-3 3v7c0 1.7 1.3 3 3 3s3-1.3 3-3V5c0-1.7-1.3-3-3-3zm5 10c0 2.8-2.2 5-5 5s-5-2.2-5-5H5c0 3.5 2.6 6.4 6 6.9V22h2v-3.1c3.4-.5 6-3.4 6-6.9h-2z" /></svg>
          </button>
        </div>
      )}

      {isBatch && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '16px', maxHeight: '350px', overflowY: 'auto', paddingRight: '6px', scrollbarWidth: 'thin' }}>
          {fields.map(f => (
            <div key={f.memory_key} style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '13px', color: 'var(--gold)', fontWeight: '500', textAlign: 'left' }}>
                {f.label}
              </label>
              <input 
                style={{ background: 'var(--surface-hover)', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px', color: 'var(--text)', outline: 'none', fontSize: '13px' }}
                value={batchValues[f.memory_key] || ''}
                onChange={e => {
                  const val = e.target.value
                  setBatchValues(prev => ({ ...prev, [f.memory_key]: val }))
                }}
                placeholder={f.question}
              />
            </div>
          ))}
        </div>
      )}

      <div className="hitl-actions" style={{ marginTop: 'auto' }}>
        {isInput || isBatch ? (
          <>
            <button className="hitl-allow" onClick={() => { 
              clearInterval(timerRef.current); 
              if (isBatch) {
                onRespond({ allowed: true, values: batchValues })
              } else {
                onRespond({ allowed: true, value: inputValue }) 
              }
            }}>
              Submit
            </button>
            <button className="hitl-deny" onClick={() => { 
              clearInterval(timerRef.current); 
              if (isBatch) {
                onRespond({ allowed: false, values: {} })
              } else {
                onRespond({ allowed: false, value: '' }) 
              }
            }}>
              Cancel
            </button>
          </>
        ) : (
          <>
            <button className="hitl-allow" onClick={() => { clearInterval(timerRef.current); onRespond(true) }}>
              Allow
            </button>
            <button className="hitl-deny" onClick={() => { clearInterval(timerRef.current); onRespond(false) }}>
              Deny
            </button>
          </>
        )}
      </div>
    </div>
  )
}
