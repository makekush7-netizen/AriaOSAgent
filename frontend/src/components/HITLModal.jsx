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

  const handleSubmit = () => {
    clearInterval(timerRef.current)
    if (isBatch) {
      onRespond({ allowed: true, values: batchValues })
    } else if (isInput) {
      onRespond({ allowed: true, value: inputValue })
    } else {
      onRespond(true)
    }
  }

  const handleDeny = () => {
    clearInterval(timerRef.current)
    if (isBatch) {
      onRespond({ allowed: false, values: {} })
    } else if (isInput) {
      onRespond({ allowed: false, value: '' })
    } else {
      onRespond(false)
    }
  }

  return (
    <div className="hitl-overlay">
      <div className="hitl-modal" style={{ width: isBatch ? '420px' : '320px' }}>
        <div className="hitl-header">
          <div className="hitl-title">⚡ {request?.title || 'Permission Request'}</div>
          <div className="hitl-countdown">Timeout: {countdown}s</div>
        </div>
        
        <div className="hitl-desc">
          {request?.description || 'ARIA requires your confirmation or input to proceed.'}
        </div>
        
        {isInput && (
          <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
            <input 
              autoFocus
              className="hitl-input"
              value={inputValue}
              onChange={e => setInputValue(e.target.value)}
              placeholder="Type your response..."
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              style={{ marginBottom: 0 }}
            />
            <button 
              onClick={toggleMic}
              style={{
                width: '38px',
                height: '38px',
                borderRadius: '7px',
                background: isRecording ? '#ef4444' : 'rgba(255,255,255,0.05)',
                border: '1px solid var(--border)',
                color: '#fff',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 2c-1.7 0-3 1.3-3 3v7c0 1.7 1.3 3 3 3s3-1.3 3-3V5c0-1.7-1.3-3-3-3zm5 10c0 2.8-2.2 5-5 5s-5-2.2-5-5H5c0 3.5 2.6 6.4 6 6.9V22h2v-3.1c3.4-.5 6-3.4 6-6.9h-2z" />
              </svg>
            </button>
          </div>
        )}

        {isBatch && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '12px', maxHeight: '250px', overflowY: 'auto', paddingRight: '4px' }}>
            {fields.map(f => (
              <div key={f.memory_key} style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label style={{ fontSize: '11px', color: 'var(--gold-primary)', fontWeight: '500' }}>
                  {f.label}
                </label>
                <input 
                  className="hitl-input"
                  value={batchValues[f.memory_key] || ''}
                  onChange={e => {
                    const val = e.target.value
                    setBatchValues(prev => ({ ...prev, [f.memory_key]: val }))
                  }}
                  placeholder={f.question}
                  style={{ marginBottom: 0, padding: '7px 10px' }}
                />
              </div>
            ))}
          </div>
        )}

        <div className="hitl-actions">
          <button className="hitl-allow" onClick={handleSubmit}>
            {isInput || isBatch ? 'Submit' : 'Allow'}
          </button>
          <button className="hitl-deny" onClick={handleDeny}>
            {isInput || isBatch ? 'Cancel' : 'Deny'}
          </button>
        </div>
      </div>
    </div>
  )
}
