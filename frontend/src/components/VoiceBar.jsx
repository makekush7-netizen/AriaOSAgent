import React, { useState, useRef, useEffect, useCallback } from 'react'

const NUM_BARS = 40

export default function VoiceBar({ onSendMessage, onVoiceAudio, agentState, setAgentState }) {
  const [isRecording, setIsRecording] = useState(false)
  const [showTextInput, setShowTextInput] = useState(false)
  const [textInput, setTextInput] = useState('')
  const [bars, setBars] = useState(Array(NUM_BARS).fill(6))
  const recognitionRef = useRef(null)
  const analyserRef = useRef(null)
  const streamRef = useRef(null)
  const rafRef = useRef(null)
  const mediaRecRef = useRef(null)

  // Speech Recognition init
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const r = new SR()
    r.continuous = false; r.interimResults = false; r.lang = 'en-US'
    r.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      onSendMessage(transcript)
    }
    r.onend = () => { setIsRecording(false); setAgentState('idle') }
    recognitionRef.current = r
  }, [])

  const startWaveform = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream
      const ac = new AudioContext()
      const src = ac.createMediaStreamSource(stream)
      const analyser = ac.createAnalyser()
      analyser.fftSize = 128
      src.connect(analyser)
      analyserRef.current = analyser
      const data = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteFrequencyData(data)
        const step = Math.floor(data.length / NUM_BARS)
        setBars(Array.from({ length: NUM_BARS }, (_, i) => {
          const v = data[i * step] || 0
          return Math.max(4, (v / 255) * 34)
        }))
        rafRef.current = requestAnimationFrame(tick)
      }
      tick()
      // MediaRecorder for sending audio chunks
      const mr = new MediaRecorder(stream)
      mr.ondataavailable = (e) => { if (e.data.size > 0) onVoiceAudio(e.data) }
      mr.start(250)
      mediaRecRef.current = mr
    } catch (_) {}
  }

  const stopWaveform = () => {
    cancelAnimationFrame(rafRef.current)
    streamRef.current?.getTracks().forEach(t => t.stop())
    mediaRecRef.current?.stop()
    setBars(Array(NUM_BARS).fill(6))
  }

  const toggleMic = useCallback(() => {
    if (isRecording) {
      recognitionRef.current?.stop()
      stopWaveform()
      setIsRecording(false); setAgentState('idle')
    } else {
      recognitionRef.current?.start()
      startWaveform()
      setIsRecording(true); setAgentState('listening')
    }
  }, [isRecording])

  const handleTextSend = () => {
    if (!textInput.trim()) return
    onSendMessage(textInput.trim())
    setTextInput(''); setShowTextInput(false)
  }

  const isActive = isRecording || agentState === 'speaking'

  return (
    <div className="voice-bar">
      <div className="vb-label">
        <div className="vb-label-title">Voice Mode</div>
        <div className={`vb-label-status ${isActive ? '' : 'inactive'}`}>
          {isActive ? 'Active' : 'Inactive'}
        </div>
      </div>

      <div className="vb-center">
        <div className="waveform">
          {bars.slice(0, NUM_BARS / 2).map((h, i) => (
            <div key={i} className="wave-bar"
              style={{
                height: `${h}px`,
                animationDelay: `${i * 0.04}s`,
                animationDuration: isRecording ? '0s' : '2s'
              }}
            />
          ))}
        </div>

        <button id="mic-btn" className={`mic-btn ${isRecording ? 'recording' : ''}`} onClick={toggleMic}>
          <svg viewBox="0 0 24 24">
            <path d="M12 2c-1.7 0-3 1.3-3 3v7c0 1.7 1.3 3 3 3s3-1.3 3-3V5c0-1.7-1.3-3-3-3zm5 10c0 2.8-2.2 5-5 5s-5-2.2-5-5H5c0 3.5 2.6 6.4 6 6.9V22h2v-3.1c3.4-.5 6-3.4 6-6.9h-2z" />
          </svg>
        </button>

        <div className="waveform">
          {bars.slice(NUM_BARS / 2).map((h, i) => (
            <div key={i} className="wave-bar"
              style={{
                height: `${h}px`,
                animationDelay: `${(NUM_BARS / 2 - i) * 0.04}s`,
                animationDuration: isRecording ? '0s' : '2s'
              }}
            />
          ))}
        </div>
      </div>

      <div className="vb-hint" style={{ cursor: 'pointer' }} onClick={() => setShowTextInput(v => !v)}>
        Press to speak<br />or <span style={{ color: 'var(--gold)' }}>type a message</span>
      </div>

      {showTextInput && (
        <div className="vb-text-input-wrap">
          <input id="vb-text-input" className="vb-text-input" value={textInput}
            onChange={e => setTextInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleTextSend()}
            placeholder="Type your message…" autoFocus />
          <button className="vb-text-send" onClick={handleTextSend}>Send</button>
        </div>
      )}
    </div>
  )
}
