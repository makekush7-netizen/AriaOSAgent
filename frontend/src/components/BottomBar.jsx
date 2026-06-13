import React, { useState, useRef, useEffect } from 'react'
import { useAriaStore } from '../store/ariaStore'

export default function BottomBar({ onSendMessage, onVoiceAudio }) {
  const { agentState, setAgentState, appState } = useAriaStore()
  const [input, setInput] = useState('')
  const [isRecording, setIsRecording] = useState(false)
  const recognitionRef = useRef(null)
  const mediaRecRef = useRef(null)
  const streamRef = useRef(null)
  const canvasRef = useRef(null)
  const animationRef = useRef(null)

  // Speech Recognition init
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SR) return
    const r = new SR()
    r.continuous = false
    r.interimResults = false
    r.lang = 'en-US'
    r.onresult = (e) => {
      const transcript = e.results[0][0].transcript
      if (transcript.trim()) {
        onSendMessage(transcript.trim())
      }
    }
    r.onend = () => {
      setIsRecording(false)
      if (agentState === 'listening') {
        setAgentState('idle')
      }
    }
    recognitionRef.current = r
  }, [onSendMessage, agentState, setAgentState])

  // Canvas Waveform Animation Loop — 20-bar visualizer
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const BAR_COUNT = 20
    let time = 0

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)

      const width = canvas.width
      const height = canvas.height
      const midY = height / 2
      const barWidth = Math.floor(width / BAR_COUNT) - 1
      const maxBarHeight = height * 0.7

      // Determine colors based on state
      let color = '#5a5550' // Idle: muted grey
      let intensity = 0.15

      if (isRecording || agentState === 'listening') {
        color = '#4fd1c7' // Mic active: teal
        intensity = 0.8
      } else if (agentState === 'speaking') {
        color = '#e8c97a' // TTS playing: gold
        intensity = 0.9
      } else if (agentState === 'thinking') {
        color = '#e8c97a'
        intensity = 0.4
      }

      time += 0.06

      // Draw 20 bars
      for (let i = 0; i < BAR_COUNT; i++) {
        const x = i * (barWidth + 1)
        const freq = 0.3 + (i % 3) * 0.15
        const phase = i * 0.5
        const wave = Math.sin(time * freq + phase) * 0.5 + 0.5
        const barHeight = Math.max(2, wave * maxBarHeight * intensity)
        const alpha = 0.4 + wave * 0.6

        ctx.fillStyle = color
        ctx.globalAlpha = alpha
        ctx.beginPath()
        ctx.roundRect(x, midY - barHeight / 2, barWidth, barHeight, 1.5)
        ctx.fill()
      }

      ctx.globalAlpha = 1
      animationRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(animationRef.current)
  }, [isRecording, agentState])

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      const mr = new MediaRecorder(stream)
      mr.ondataavailable = (e) => {
        if (e.data.size > 0) onVoiceAudio(e.data)
      }
      mr.start(250)
      mediaRecRef.current = mr

      recognitionRef.current?.start()
      setIsRecording(true)
      setAgentState('listening')
    } catch (err) {
      console.error('Failed to access mic:', err)
    }
  }

  const stopRecording = () => {
    recognitionRef.current?.stop()
    mediaRecRef.current?.stop()
    streamRef.current?.getTracks().forEach(t => t.stop())
    setIsRecording(false)
    setAgentState('idle')
  }

  const toggleMic = () => {
    if (isRecording) {
      stopRecording()
    } else {
      startRecording()
    }
  }

  const handleSend = () => {
    if (!input.trim()) return
    onSendMessage(input.trim())
    setInput('')
  }

  const isExecuting = appState === 'execution'

  return (
    <div className="bottom-bar">
      {/* Voice microphone button */}
      <button
        id="mic-btn"
        className={`voice-btn ${isRecording ? 'listening' : ''}`}
        onClick={toggleMic}
        title={isRecording ? 'Stop speaking' : 'Press to speak'}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" x2="12" y1="19" y2="22" />
        </svg>
      </button>

      {/* Waveform Canvas */}
      <canvas
        ref={canvasRef}
        className="waveform-canvas"
        width="80"
        height="30"
      />

      {/* Text Input Wrapper */}
      <div className="chat-input-wrap">
        {isExecuting && (
          <div className="agent-running-label">
            <span className="running-dot" />
            <span>Agent running...</span>
          </div>
        )}
        <input
          id="chat-input"
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Press to speak or type a message..."
        />
      </div>

      {/* Send Button */}
      <button id="chat-send-btn" className="send-btn" onClick={handleSend} title="Send Message">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <line x1="22" x2="11" y1="2" y2="13" />
          <polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>
  )
}
