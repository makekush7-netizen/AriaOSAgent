import React, { useState, useRef, useEffect, useCallback } from 'react'

const ORB_STATES = {
  idle: { bg: 'radial-gradient(circle at 35% 35%, #6b93cc, #4a6fa5)', shadow: 'rgba(74,111,165,0.6)', label: 'Idle' },
  listening: { bg: 'radial-gradient(circle at 35% 35%, #38d5e8, #06b6d4)', shadow: 'rgba(6,182,212,0.65)', label: 'Listening…' },
  thinking: { bg: 'radial-gradient(circle at 35% 35%, #a078e8, #7c3aed)', shadow: 'rgba(124,58,237,0.65)', label: 'Thinking…' },
  speaking: { bg: 'radial-gradient(circle at 35% 35%, #e8c06a, #c9a84c)', shadow: 'rgba(201,168,76,0.7)', label: 'Speaking…' },
}

export default function BubbleMode({ messages, agentState, setAgentState, onClose, onSendMessage, onVoiceAudio }) {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [isRecording, setIsRecording] = useState(false)
  const [orbScale, setOrbScale] = useState(1)
  const recognitionRef = useRef(null)
  const analyserRef = useRef(null)
  const streamRef = useRef(null)
  const rafRef = useRef(null)
  const mediaRecRef = useRef(null)

  const state = ORB_STATES[agentState] || ORB_STATES.idle
  const recentMsgs = messages.slice(-5)

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const r = new SR()
    r.continuous = false; r.interimResults = false
    r.onresult = (e) => onSendMessage(e.results[0][0].transcript)
    r.onend = () => { setIsRecording(false); setAgentState('idle') }
    recognitionRef.current = r
  }, [])

  const startMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const ac = new AudioContext()
      const src = ac.createMediaStreamSource(stream)
      const analyser = ac.createAnalyser(); analyser.fftSize = 256
      src.connect(analyser); analyserRef.current = analyser
      const data = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteFrequencyData(data)
        const avg = data.reduce((a, b) => a + b, 0) / data.length
        setOrbScale(1 + (avg / 255) * 0.5)
        rafRef.current = requestAnimationFrame(tick)
      }
      tick()
      const mr = new MediaRecorder(stream)
      mr.ondataavailable = (e) => { if (e.data.size > 0) onVoiceAudio(e.data) }
      mr.start(250); mediaRecRef.current = mr
    } catch (_) {}
  }

  const stopMic = () => {
    cancelAnimationFrame(rafRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())
    mediaRecRef.current?.stop()
    setOrbScale(1)
  }

  const handleOrbClick = useCallback(() => {
    if (isRecording) {
      recognitionRef.current?.stop(); stopMic()
      setIsRecording(false); setAgentState('idle')
    } else {
      recognitionRef.current?.start(); startMic()
      setIsRecording(true); setAgentState('listening')
    }
  }, [isRecording])

  useEffect(() => () => { cancelAnimationFrame(rafRef.current); streamRef.current?.getTracks().forEach(t => t.stop()) }, [])

  return (
    <div className="bubble-mode">
      <button id="bubble-close-btn" className="bubble-close" onClick={onClose}>✕</button>

      <div
        id="bubble-orb"
        className={`bubble-orb ${agentState}`}
        style={{
          background: state.bg,
          boxShadow: `0 0 50px ${state.shadow}, 0 0 100px ${state.shadow}40`,
          transform: `scale(${orbScale})`,
        }}
        onClick={handleOrbClick}
        title="Click to speak"
      />

      <div className="bubble-state-label">{state.label}</div>

      <button className="drawer-toggle" onClick={() => setDrawerOpen(v => !v)}>
        {drawerOpen ? '▼ Hide chat' : '▲ Show recent messages'}
      </button>

      <div className={`bubble-drawer ${drawerOpen ? 'open' : ''}`}>
        <div className="drawer-handle" />
        {recentMsgs.map((m, i) => (
          <div key={i} style={{
            marginBottom: 10, padding: '8px 12px',
            background: m.role === 'user' ? 'var(--gold-dim)' : 'rgba(255,255,255,0.05)',
            borderRadius: 10, fontSize: 13, color: 'var(--text)'
          }}>
            <span style={{ color: 'var(--text-sec)', fontSize: 11, marginRight: 8 }}>
              {m.role === 'user' ? 'You' : 'ARIA'}
            </span>
            {m.content}
          </div>
        ))}
      </div>
    </div>
  )
}
