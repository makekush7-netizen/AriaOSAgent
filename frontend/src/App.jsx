import React, { useState, useRef, useEffect } from 'react'
import { getCurrentWindow } from '@tauri-apps/api/window'
import AvatarZone from './components/AvatarZone'
import BackgroundCanvas from './components/BackgroundCanvas'
import ChatPanel from './components/ChatPanel'
import BottomBar from './components/BottomBar'
import BubbleMode from './components/BubbleMode'
import MemoryPanel from './components/MemoryPanel'
import StorePage from './components/StorePage'
import HITLModal from './components/HITLModal'
import NotepadPanel from './components/NotepadPanel'
import WidgetZone from './components/WidgetZone'
import PlanningCard from './components/PlanningCard'
import TaskCanvas from './components/TaskCanvas'
import CompletionCard from './components/CompletionCard'
import SettingsPanel from './components/SettingsPanel'
import { useAriaStore } from './store/ariaStore'

const API_BASE = 'http://localhost:8001'

const getGreeting = () => {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}

export default function App() {
  const {
    appState,
    messages,
    isThinking,
    agentState,
    activeTask,
    taskLog,
    activeAgents,
    activePlan,
    hitlRequest,
    memoryData,
    widgetLayout,
    completionData,
    transitionTo,
    addMessage,
    setIsThinking,
    setAgentState,
    setActiveTask,
    addTaskLog,
    clearTaskLog,
    spawnAgent,
    updateAgentHeartbeat,
    removeAgent,
    setActivePlan,
    setHitlRequest,
    clearHitlRequest,
    setMemoryData,
    setCompletionData,
    updateWidget,
    resetWidgetLayout,
    setActiveCanvas
  } = useAriaStore()

  const [currentView, setCurrentView] = useState('home')
  const [isBubbleMode, setIsBubbleMode] = useState(false)
  const [selectedModel, setSelectedModel] = useState('female')
  const [particles, setParticles] = useState([])

  const selectedModelRef = useRef('female')
  const wsRef = useRef(null)
  const audioContextRef = useRef(null)
  const rafRef = useRef(null)

  const { theme, character } = useAriaStore()

  const greeting = character.greeting || getGreeting()

  // Apply theme CSS variables dynamically
  useEffect(() => {
    if (!theme) return
    const r = document.documentElement.style
    r.setProperty('--gold-primary', theme.goldPrimary)
    r.setProperty('--gold-dim', theme.goldDim)
    r.setProperty('--accent-teal', theme.accentTeal)
    r.setProperty('--accent-purple', theme.accentPurple)
    r.setProperty('--accent-coral', theme.accentCoral)
    r.setProperty('--accent-green', theme.accentGreen)
    r.setProperty('--bg-world', theme.bgWorld)
    r.setProperty('--bg-base', theme.bgBase)
    r.setProperty('--bg-surface', theme.bgSurface)
    r.setProperty('--text-primary', theme.textPrimary)
    r.setProperty('--text-secondary', theme.textSecondary)
    r.setProperty('--text-gold', theme.goldPrimary)
    r.setProperty('--glass-border', theme.goldPrimary + '1f')
    r.setProperty('--glass-border-active', theme.goldPrimary + '4d')
  }, [theme])

  // Fullscreen support
  useEffect(() => {
    const handleKeyDown = async (e) => {
      if (e.key === 'F11') {
        e.preventDefault()
        try {
          const win = getCurrentWindow()
          const isFull = await win.isFullscreen()
          await win.setFullscreen(!isFull)
        } catch (_) { }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Sync ref + listen for model change from Settings
  useEffect(() => {
    selectedModelRef.current = selectedModel
  }, [selectedModel])

  useEffect(() => {
    const handler = (e) => { if (e.detail) { setSelectedModel(e.detail); selectedModelRef.current = e.detail } }
    window.addEventListener('aria:modelChanged', handler)
    return () => window.removeEventListener('aria:modelChanged', handler)
  }, [])

  // Load profile memory on start
  useEffect(() => {
    fetch(`${API_BASE}/api/memory`)
      .then(r => r.json())
      .then(d => setMemoryData(d))
      .catch(e => console.error('[ARIA] Error fetching memory on mount:', e))
  }, [setMemoryData])

  // Success Particles emitter
  const triggerSuccessParticles = () => {
    const newParticles = Array.from({ length: 12 }).map((_, i) => {
      const angle = Math.random() * Math.PI * 2
      const distance = 40 + Math.random() * 80
      return {
        id: i,
        tx: `${Math.cos(angle) * distance}px`,
        ty: `${Math.sin(angle) * distance}px`,
      }
    })
    setParticles(newParticles)
    setTimeout(() => setParticles([]), 600)
  }

  // Trigger particles on entering completion state
  useEffect(() => {
    if (appState === 'completion') {
      triggerSuccessParticles()
    }
  }, [appState])

  // Audio TTS player
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
        stopActiveAudio()

        const ac = new (window.AudioContext || window.webkitAudioContext)()
        audioContextRef.current = ac

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
          } catch (_) { }
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

  // WebSocket Connection
  useEffect(() => {
    const connect = () => {
      try {
        const ws = new WebSocket('ws://localhost:8001/ws')
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

              addMessage({ role: 'assistant', content: finalText })

              const cleanTTS = finalText.replace(/([\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF])/g, '').replace(/\(.*?\)/g, '').replace(/\[.*?\]/g, '').trim()

              let shortTTS = cleanTTS
              if (cleanTTS.length > 500) {
                const truncated = cleanTTS.substring(0, 500)
                const lastSentenceEnd = Math.max(
                  truncated.lastIndexOf('. '),
                  truncated.lastIndexOf('! '),
                  truncated.lastIndexOf('? ')
                )
                shortTTS = lastSentenceEnd > 100 ? truncated.substring(0, lastSentenceEnd + 1) : truncated
              }

              if (cleanTTS) speakResponse(shortTTS)
            }

            else if (data.type === 'permission_request') {
              try {
                const ac = new (window.AudioContext || window.webkitAudioContext)()
                if (ac.state === 'suspended') ac.resume()
                const osc = ac.createOscillator(); const gain = ac.createGain()
                osc.connect(gain); gain.connect(ac.destination)
                osc.type = 'sine'; osc.frequency.setValueAtTime(880, ac.currentTime)
                gain.gain.setValueAtTime(0.1, ac.currentTime)
                gain.gain.exponentialRampToValueAtTime(0.01, ac.currentTime + 0.5)
                osc.start(ac.currentTime); osc.stop(ac.currentTime + 0.5)
              } catch (_) { }
              setHitlRequest(data)
            }

            else if (data.type === 'task_update') {
              if (data.task) {
                setActiveTask(data.task)
                addTaskLog(data.task)
              } else {
                setActiveTask(null)
                clearTaskLog()
              }
            }

            else if (data.type === 'agent_thinking') {
              setIsThinking(true)
              setAgentState('thinking')
              window.dispatchEvent(new CustomEvent('aura:setEmotion', { detail: 'thinking' }))
            }

            else if (data.type === 'planning_card') {
              setActivePlan(data.plan)
              transitionTo('planning')
            }

            else if (data.type === 'agent_spawn') {
              spawnAgent({
                id: data.agentId,
                name: data.name,
                accentColor: data.accentColor,
                status: data.status,
                step: data.step
              })

              // Map agent name to appropriate canvas layout view
              const nameLower = data.name.toLowerCase()
              if (nameLower.includes('browser') || nameLower.includes('form')) {
                setActiveCanvas('form')
              } else if (nameLower.includes('research') || nameLower.includes('scout')) {
                setActiveCanvas('research')
              } else if (nameLower.includes('script') || nameLower.includes('run')) {
                setActiveCanvas('script')
              } else if (nameLower.includes('email')) {
                setActiveCanvas('email')
              } else if (nameLower.includes('certificate')) {
                setActiveCanvas('certificate')
              }

              transitionTo('execution')
            }

            else if (data.type === 'agent_heartbeat') {
              updateAgentHeartbeat(data.agentId, data.status, data.step)
            }

            else if (data.type === 'agent_complete') {
              removeAgent(data.agentId)
              setCompletionData(data.result)
              transitionTo('completion')
            }

            else if (data.type === 'note_created') {
              window.dispatchEvent(new CustomEvent('aria:note_created', { detail: data.filename }))
            }
          } catch (e) {
            console.error('[ARIA WS message parsing error]', e)
          }
        }
        ws.onclose = () => setTimeout(connect, 3000)
      } catch (_) { }
    }
    connect()
    return () => wsRef.current?.close()
  }, [addMessage, spawnAgent, updateAgentHeartbeat, removeAgent, setCompletionData, transitionTo, setActiveCanvas, setHitlRequest, setActiveTask, addTaskLog, clearTaskLog, setIsThinking, setAgentState, setActivePlan])

  const sendWS = (type, payload = {}) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...payload }))
    }
  }

  const sendMessage = (content) => {
    if (!content.trim()) return
    stopActiveAudio()
    addMessage({ role: 'user', content })
    setIsThinking(true)
    setAgentState('thinking')
    transitionTo('conversation')
    window.dispatchEvent(new CustomEvent('aura:setEmotion', { detail: 'thinking' }))
    sendWS('chat_message', { content, timestamp: new Date().toISOString() })
  }

  const sendVoiceAudio = (chunk) => {
    stopActiveAudio()
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(chunk)
    }
  }

  const handleHITL = (response) => {
    if (typeof response === 'object' && response !== null) {
      sendWS('permission_response', response)
    } else {
      sendWS('permission_response', { allowed: response })
    }
    clearHitlRequest()
  }

  const handleApprovePlan = (planId, cancelled) => {
    sendWS('approve_plan', { planId, cancelled })
  }

  const stopAgent = () => {
    sendWS('stop_task')
    transitionTo('home')
  }

  const navItems = [
    { id: 'home', label: 'Home', tooltip: 'Companion Board', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" /></svg> },
    { id: 'notepad', label: 'Tasks', tooltip: 'Task Findings & logs', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2" /><path d="m9 12 2 2 4-4" /></svg> },
    { id: 'memory', label: 'Memory', tooltip: 'Database profile', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect width="18" height="18" x="3" y="3" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" /></svg> },
    { id: 'store', label: 'Store', tooltip: 'Skills & Skins', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /></svg> },
    { id: 'settings', label: 'Settings', tooltip: 'Avatar & Widget Config', icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" /><circle cx="12" cy="12" r="3" /></svg> },
  ]

  // Compute character column width dynamically based on view and execution state
  const charWidth = currentView === 'home'
    ? (appState === 'planning' ? '34%' : appState === 'execution' ? '28%' : '40%')
    : '34%'

  return (
    <div className="app-container">
      {/* Animated Particle Background — Night Garden */}
      <BackgroundCanvas />

      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-logo">
          <div className="logo-dot" />
          <span className="logo-text">ARIA</span>
        </div>
        <div className="sidebar-nav">
          {navItems.map(item => (
            <button
              key={item.id}
              id={`nav-${item.id}`}
              className={`sidebar-btn ${currentView === item.id ? 'active' : ''}`}
              onClick={() => setCurrentView(item.id)}
              data-tooltip={item.tooltip}
            >
              {item.icon}
            </button>
          ))}
        </div>
      </aside>

      <div className="app-shell">
        {/* Top Bar — ARIA branding + nav */}
        <header className="top-bar">
          <div className="top-bar-logo">
            <div className="logo-dot" />
            <span className="logo-text">ARIA</span>
          </div>
          <nav className="top-bar-nav">
            {navItems.map(item => (
              <button
                key={item.id}
                className={`nav-btn ${currentView === item.id ? 'active' : ''}`}
                onClick={() => setCurrentView(item.id)}
                data-tooltip={item.tooltip}
              >
                {item.icon}
              </button>
            ))}
          </nav>
        </header>

        {/* Main Content Area */}
        <main className="main-area">
          {/* Left: 3D Character Zone */}
          <div className="character-zone" style={{ width: charWidth, display: 'flex', flexDirection: 'column', position: 'relative' }}>
            <AvatarZone
              greeting={greeting}
              activeTask={activeTask}
              taskLog={taskLog}
              memoryData={memoryData}
              agentState={agentState}
              modelId={selectedModel}
              onToggleBubble={() => setIsBubbleMode(true)}
              onStopAgent={stopAgent}
              isWidget={currentView !== 'home' || appState === 'execution' || appState === 'planning'}
            />

            <div className="char-ambient-glow" />

            {/* Success particles emitter container */}
            {particles.map(p => (
              <div
                key={p.id}
                className="particle"
                style={{
                  top: '52%',
                  left: '50%',
                  '--tx': p.tx,
                  '--ty': p.ty
                }}
              />
            ))}
          </div>

          {/* Right: Pages Routing / States Overlay */}
          <div className="right-zone">
            {currentView === 'home' && (
              <>
                {appState === 'home' && <WidgetZone onNavigate={setCurrentView} />}
                {appState === 'conversation' && (
                  <ChatPanel
                    messages={messages}
                    isThinking={isThinking}
                    onSendMessage={sendMessage}
                  />
                )}
                {appState === 'planning' && (
                  <PlanningCard onApprovePlan={handleApprovePlan} />
                )}
                {appState === 'execution' && (
                  <TaskCanvas onStopAgent={stopAgent} />
                )}
                {appState === 'completion' && (
                  <CompletionCard onNavigate={setCurrentView} />
                )}
              </>
            )}

            {currentView === 'memory' && (
              <MemoryPanel memoryData={memoryData} setMemoryData={setMemoryData} apiBase={API_BASE} />
            )}

            {currentView === 'notepad' && (
              <NotepadPanel apiBase={API_BASE} />
            )}

            {currentView === 'store' && (
              <StorePage defaultTab="all" />
            )}

            {currentView === 'settings' && (
              <SettingsPanel />
            )}
          </div>
        </main>

        {/* Bottom Bar Controls */}
        {!isBubbleMode && (
          <BottomBar
            onSendMessage={sendMessage}
            onVoiceAudio={sendVoiceAudio}
          />
        )}

        {/* Bubble Orb Mode Overlay */}
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

        {/* Human-in-the-Loop Interruption Requests */}
        {hitlRequest && (
          <HITLModal
            request={hitlRequest}
            onRespond={handleHITL}
          />
        )}
      </div>
    </div>
  )
}
