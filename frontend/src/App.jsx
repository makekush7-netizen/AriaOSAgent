import React, { useState, useRef, useEffect } from 'react'
import { getCurrentWindow } from '@tauri-apps/api/window'
import AvatarZone from './components/AvatarZone'
import ChatPanel from './components/ChatPanel'
import VoiceBar from './components/VoiceBar'
import BubbleMode from './components/BubbleMode'
import MemoryPanel from './components/MemoryPanel'
import StorePage from './components/StorePage'
import HITLModal from './components/HITLModal'
import NotepadPanel from './components/NotepadPanel'

const API_BASE = 'http://localhost:8000'

const getGreeting = () => {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function App() {
  const [currentView, setCurrentView] = useState('home')
  const [isBubbleMode, setIsBubbleMode] = useState(false)
  const [selectedModel, setSelectedModel] = useState('female')
  const selectedModelRef = useRef('female')

  // F11 Fullscreen
  useEffect(() => {
    const handleKeyDown = async (e) => {
      if (e.key === 'F11') {
        e.preventDefault()
        try {
          const win = getCurrentWindow()
          const isFull = await win.isFullscreen()
          await win.setFullscreen(!isFull)
        } catch (err) {}
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])
  
  // Update ref when state changes
  useEffect(() => {
    selectedModelRef.current = selectedModel
  }, [selectedModel])


  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hello! I'm ARIA, your AI assistant. How can I help?", timestamp: new Date() }
  ])
  const [isThinking, setIsThinking] = useState(false)
  const [hitlRequest, setHitlRequest] = useState(null)
  const [activeTask, setActiveTask] = useState(null)
  const [taskLog, setTaskLog] = useState([])
  const [memoryData, setMemoryData] = useState({})
  const [agentState, setAgentState] = useState('idle')
  const wsRef = useRef(null)
  const greeting = getGreeting()
  const audioContextRef = useRef(null)
  const rafRef = useRef(null)

  const stopActiveAudio = () => {
    if (audioContextRef.current) {
      try {
        if (audioContextRef.current.state !== 'closed') {
          audioContextRef.current.close()
        }
      } catch (e) {
        console.error('Error closing AudioContext:', e)
      }
      audioContextRef.current = null
    }
    if (rafRef.current) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    window.dispatchEvent(new CustomEvent('aura:setMorph', { detail: { name: 'mouthOpen', value: 0 } }))
  }

  const speakResponse = async (text) => {
    stopActiveAudio()
    try {
      const res = await fetch(`${API_BASE}/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice: selectedModelRef.current })
      })
      if (res.ok) {
        const ab = await res.arrayBuffer()
        // Ensure no other fetch completed while we were waiting
        stopActiveAudio()
        
        const ac = new (window.AudioContext || window.webkitAudioContext)()
        audioContextRef.current = ac
        
        // Browsers require resuming AudioContext after creation if there wasn't a recent user gesture
        if (ac.state === 'suspended') {
          await ac.resume()
        }
        
        const buf = await ac.decodeAudioData(ab)
        const src = ac.createBufferSource()
        src.buffer = buf
        const ana = ac.createAnalyser()
        ana.fftSize = 2048
        const d = new Uint8Array(ana.frequencyBinCount)
        
        src.connect(ana)
        ana.connect(ac.destination)
        src.start()

        const tick = () => {
          ana.getByteTimeDomainData(d)
          let sum = 0
          for (let i = 0; i < d.length; i++) sum += Math.pow((d[i] - 128) / 128, 2)
          const v = Math.min(1, Math.sqrt(sum / d.length) * 4)
          window.dispatchEvent(new CustomEvent('aura:setMorph', { detail: { name: 'mouthOpen', value: v } }))
          rafRef.current = requestAnimationFrame(tick)
        }
        tick()
        
        src.onended = () => {
          if (rafRef.current) cancelAnimationFrame(rafRef.current)
          window.dispatchEvent(new CustomEvent('aura:setMorph', { detail: { name: 'mouthOpen', value: 0 } }))
          try {
            ac.close()
          } catch (_) {}
          if (audioContextRef.current === ac) {
            audioContextRef.current = null
          }
          setAgentState('idle')
        }
      } else {
        setAgentState('idle')
      }
    } catch (e) { 
      console.error('TTS Error', e)
      setAgentState('idle')
    }
  }

  // Load memory from backend on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/memory`)
      .then(r => r.json())
      .then(d => setMemoryData(d))
      .catch(e => console.error('[ARIA] Error fetching memory on mount:', e))
  }, [])

  // WebSocket
  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket('ws://localhost:8000/ws')
        wsRef.current = ws
        ws.onopen = () => console.log('[ARIA] WS connected')
        ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data)
            if (data.type === 'chat_response') {
              setIsThinking(false)
              setAgentState('speaking')
              
              stopActiveAudio()
              
              let finalText = data.content
              const emotionMatch = finalText.match(/\[EMOTION:\s*(\w+)\]/i)
              if (emotionMatch) {
                const emotion = emotionMatch[1].toLowerCase()
                window.dispatchEvent(new CustomEvent('aura:setEmotion', { detail: emotion }))
                finalText = finalText.replace(emotionMatch[0], '').trim()
              } else {
                window.dispatchEvent(new CustomEvent('aura:setEmotion', { detail: 'happy' }))
              }
              
              const actionMatch = finalText.match(/\[ACTION:\s*(\w+)\]/i)
              if (actionMatch) {
                const action = actionMatch[1].toLowerCase()
                window.dispatchEvent(new CustomEvent('aura:setAction', { detail: action }))
                finalText = finalText.replace(actionMatch[0], '').trim()
              }
              
              setMessages(p => [...p, { role: 'assistant', content: finalText, timestamp: new Date() }])
              
              const cleanTTS = finalText.replace(/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g, '').replace(/\(.*?\)/g, '').replace(/\[.*?\]/g, '').trim()
              
              // Cap at ~500 chars but break at the last sentence-ending punctuation so we never cut mid-sentence.
              let shortTTS = cleanTTS;
              if (cleanTTS.length > 500) {
                const truncated = cleanTTS.substring(0, 500);
                const lastSentenceEnd = Math.max(
                  truncated.lastIndexOf('. '),
                  truncated.lastIndexOf('! '),
                  truncated.lastIndexOf('? '),
                  truncated.lastIndexOf('.'),
                  truncated.lastIndexOf('!'),
                  truncated.lastIndexOf('?')
                );
                shortTTS = lastSentenceEnd > 100 ? truncated.substring(0, lastSentenceEnd + 1) : truncated;
              }
              
              if (cleanTTS) speakResponse(shortTTS)
            }
            if (data.type === 'permission_request') {
              // Beep sound for HITL to alert the user!
              try {
                const ac = new (window.AudioContext || window.webkitAudioContext)();
                if (ac.state === 'suspended') ac.resume();
                const osc = ac.createOscillator(); const gain = ac.createGain();
                osc.connect(gain); gain.connect(ac.destination);
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, ac.currentTime);
                gain.gain.setValueAtTime(0.1, ac.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ac.currentTime + 0.5);
                osc.start(ac.currentTime); osc.stop(ac.currentTime + 0.5);
              } catch (_) {}
              setHitlRequest(data)
            }
            if (data.type === 'task_update') {
              setActiveTask(data.task)
              if (!data.task) {
                setTaskLog([])
              } else {
                setTaskLog(prev => {
                  if (prev.length === 0 || prev[prev.length - 1] !== data.task) {
                     return [...prev, data.task].slice(-8)
                  }
                  return prev
                })
              }
            }
            if (data.type === 'agent_thinking') {
              setIsThinking(true); setAgentState('thinking')
              window.dispatchEvent(new CustomEvent('aura:setEmotion', { detail: 'thinking' }))
            }
          } catch (_) {}
        }
        ws.onclose = () => setTimeout(connect, 3000)
        ws.onerror = () => {}
      } catch (_) {}
    }
    connect()
    return () => wsRef.current?.close()
  }, [])

  const sendWS = (type, payload = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN)
      wsRef.current.send(JSON.stringify({ type, ...payload }))
  }

  const sendMessage = (content) => {
    if (!content.trim()) return
    stopActiveAudio()
    setMessages(p => [...p, { role: 'user', content, timestamp: new Date() }])
    setIsThinking(true); setAgentState('thinking')
    window.dispatchEvent(new CustomEvent('aura:setEmotion', { detail: 'thinking' }))
    sendWS('chat_message', { content, timestamp: new Date().toISOString() })
  }

  const sendVoiceAudio = (chunk) => {
    stopActiveAudio()
    if (wsRef.current?.readyState === WebSocket.OPEN) wsRef.current.send(chunk)
  }

  const handleHITL = (response) => {
    if (typeof response === 'object' && response !== null) {
      sendWS('permission_response', response)
    } else {
      sendWS('permission_response', { allowed: response })
    }
    setHitlRequest(null)
  }

  const stopAgent = () => {
    sendWS('stop_task')
  }

  const navItems = [
    { id: 'home', label: 'Home', icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg> },
    { id: 'memory', label: 'Memory', icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg> },
    { id: 'notepad', label: 'Notepad', icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg> },
    { id: 'store', label: 'Store', icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M6 2 3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4Z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg> },
    { id: 'settings', label: 'Settings', icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg> },
  ]

  return (
    <div className="app" style={{ display:'flex', flexDirection:'column', height:'100vh' }}>
      <nav className="navbar">
        <div className="navbar-logo">
          <div className="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M12 2v20M2 12h20M4.9 4.9l14.2 14.2M4.9 19.1 19.1 4.9M8 4l8 16M4 8l16 8M4 16l16-8M8 20 16 4"/>
            </svg>
          </div>
          <span className="logo-text">ARIA</span>
        </div>
        <div className="navbar-nav">
          {navItems.map(item => (
            <button key={item.id} id={`nav-${item.id}`}
              className={`nav-item ${currentView === item.id ? 'active' : ''}`}
              onClick={() => setCurrentView(item.id)}>
              <span className="nav-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </div>
      </nav>

      <main className="main-content">
        {currentView === 'home' && (
          <div className="home-layout">
            <AvatarZone
              greeting={greeting}
              activeTask={activeTask}
              taskLog={taskLog}
              memoryData={memoryData}
              agentState={agentState}
              modelId={selectedModel}
              onToggleBubble={() => setIsBubbleMode(true)}
              onStopAgent={stopAgent}
            />
            <ChatPanel
              messages={messages}
              isThinking={isThinking}
              onSendMessage={sendMessage}
            />
          </div>
        )}
        {currentView === 'memory' && (
          <MemoryPanel memoryData={memoryData} setMemoryData={setMemoryData} apiBase={API_BASE} />
        )}
        {currentView === 'notepad' && (
          <NotepadPanel apiBase={API_BASE} />
        )}
        {currentView === 'store' && <StorePage />}
        {currentView === 'settings' && (
          <div className="settings-panel" style={{ padding: '40px', maxWidth: '800px', margin: '0 auto', color: 'var(--text)' }}>
            <h2 style={{ fontSize: '28px', marginBottom: '24px', fontWeight: '600' }}>Settings</h2>
            
            <div className="settings-section" style={{ background: 'var(--bg-sec)', padding: '24px', borderRadius: '16px', border: '1px solid var(--border)' }}>
              <h3 style={{ fontSize: '18px', marginBottom: '16px', color: 'var(--gold)' }}>Appearance & Voice</h3>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <div style={{ fontWeight: '500', marginBottom: '4px' }}>Avatar Model</div>
                    <div style={{ fontSize: '13px', color: 'var(--text-sec)' }}>Choose the visual representation and voice of your assistant</div>
                  </div>
                  
                  <div style={{ display: 'flex', background: 'var(--bg)', borderRadius: '8px', padding: '4px', border: '1px solid var(--border)' }}>
                    <button 
                      onClick={() => setSelectedModel('female')}
                      style={{ 
                        padding: '8px 16px', 
                        borderRadius: '6px', 
                        background: selectedModel === 'female' ? 'var(--gold)' : 'transparent',
                        color: selectedModel === 'female' ? '#000' : 'var(--text)',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: '500',
                        transition: 'all 0.2s'
                      }}>
                      Female (Default)
                    </button>
                    <button 
                      onClick={() => setSelectedModel('male')}
                      style={{ 
                        padding: '8px 16px', 
                        borderRadius: '6px', 
                        background: selectedModel === 'male' ? 'var(--gold)' : 'transparent',
                        color: selectedModel === 'male' ? '#000' : 'var(--text)',
                        border: 'none',
                        cursor: 'pointer',
                        fontWeight: '500',
                        transition: 'all 0.2s'
                      }}>
                      Male
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {!isBubbleMode && (
        <VoiceBar
          onSendMessage={sendMessage}
          onVoiceAudio={sendVoiceAudio}
          agentState={agentState}
          setAgentState={setAgentState}
        />
      )}

      {isBubbleMode && (
        <BubbleMode
          messages={messages}
          agentState={agentState}
          setAgentState={setAgentState}
          onClose={() => setIsBubbleMode(false)}
          onSendMessage={sendMessage}
          onVoiceAudio={sendVoiceAudio}
        />
      )}

      {hitlRequest && <HITLModal request={hitlRequest} onRespond={handleHITL} />}
    </div>
  )
}
