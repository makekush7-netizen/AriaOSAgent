import React, { Suspense, useRef, useEffect } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import AvatarModel from '../AvatarModel'

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false } }
  static getDerivedStateFromError() { return { hasError: true } }
  componentDidCatch(e) { console.error('[ARIA] Avatar:', e) }
  render() { return this.state.hasError ? null : this.props.children }
}

function PlatformGlow() {
  const disc = useRef(); const ring = useRef()
  useFrame(({ clock }) => {
    const t = clock.elapsedTime
    if (disc.current) disc.current.material.opacity = 0.22 + Math.sin(t * 2) * 0.1
    if (ring.current) ring.current.material.opacity = 0.55 + Math.sin(t * 2) * 0.2
  })
  return (
    <group position={[0, -0.01, 0]}>
      <mesh ref={disc} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[0.7, 64]} />
        <meshBasicMaterial color="#e8c97a" transparent opacity={0.3} />
      </mesh>
      <mesh ref={ring} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[0.68, 0.8, 64]} />
        <meshBasicMaterial color="#e8c97a" transparent opacity={0.4} />
      </mesh>
    </group>
  )
}

function ResponsiveAvatarController({ modelId, isWidget }) {
  const { camera, size } = useThree()

  // Calculate aspect ratio of the canvas
  const aspect = size.width / size.height

  // Base parameters for landscape / wide layouts (known working config)
  const baseZ = 2.6
  const baseTargetX = -0.28
  const baseTargetY = 1.25
  const baseCameraY = 1.35

  const femaleScale = 2.1
  const maleScale = 1.75
  const femalePosY = -1.25
  const malePosY = -1.35

  const scale = modelId === 'male' ? maleScale : femaleScale
  const posY = modelId === 'male' ? malePosY : femalePosY

  // Dynamic adjustments based on aspect ratio
  const idealAspect = 0.8
  let dynamicZ = baseZ
  let dynamicTargetX = baseTargetX

  if (aspect < idealAspect) {
    const ratio = idealAspect / aspect
    dynamicZ = Math.min(4.8, baseZ * ratio) // Zoom out smoothly
    dynamicTargetX = baseTargetX * (aspect / idealAspect) // Shift leftwards
  }

  // Force camera position and lookAt target on every frame to bypass controls/target overrides
  useFrame(() => {
    camera.position.set(0, baseCameraY, dynamicZ)
    camera.lookAt(dynamicTargetX, baseTargetY, 0)
    camera.updateProjectionMatrix()
  })

  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[3, 4, 3]} intensity={0.7} color="#fffcf5" />
      <directionalLight position={[-2, 2, -1]} intensity={0.5} color="#e5cc9f" />
      <directionalLight position={[0, -1, 2]} intensity={0.4} color="#e6ceaa" />
      <ErrorBoundary>
        <Suspense fallback={null}>
          <AvatarModel modelId={modelId} scale={scale} position={[0, posY, 0]} />
        </Suspense>
      </ErrorBoundary>
      {!isWidget && <PlatformGlow />}
    </>
  )
}

export default function AvatarZone({ greeting, activeTask, taskLog = [], memoryData, agentState, onToggleBubble, onStopAgent, modelId = 'female', isWidget = false }) {
  const fullName = memoryData?.name || 'Endeavour'
  const firstName = fullName.split(' ')[0]
  const memCount = Object.keys(memoryData).filter(k => memoryData[k]).length

  return (
    <div className="avatar-zone" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {!isWidget && (
        <div className="avatar-greeting">
          <h2>
            {greeting},<br />
            {firstName}✨
          </h2>
          <p>How can I help you today?</p>
        </div>
      )}

      <div className="avatar-canvas-wrap" style={{ position: 'relative', flex: 1 }}>
        {!isWidget && (
          <button id="bubble-toggle-btn" className="bubble-toggle" onClick={onToggleBubble} title="Bubble mode">⊙</button>
        )}
        
        {/* Agent Workflow Planner HUD */}
        {activeTask && !isWidget && (
          <div style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            background: 'rgba(21, 19, 17, 0.85)',
            backdropFilter: 'blur(20px)',
            border: '1px solid var(--border)',
            borderRadius: '16px',
            padding: '16px',
            width: '280px',
            pointerEvents: 'auto',
            zIndex: 10,
            boxShadow: '0 8px 30px rgba(0,0,0,0.5)'
          }}>
            <h4 style={{ color: 'var(--gold-primary)', margin: '0 0 12px 0', fontSize: '13px', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
              {taskLog.length > 0 ? 'EXECUTION PLAN' : 'ACTIVE TASK'}
            </h4>
            
            {taskLog.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {taskLog.map((task, i) => {
                  const isLast = i === taskLog.length - 1;
                  return (
                    <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: '10px', position: 'relative' }}>
                      {i !== taskLog.length - 1 && (
                        <div style={{ position: 'absolute', left: '5px', top: '15px', width: '1px', height: '100%', background: 'var(--border)' }} />
                      )}
                      <div style={{ 
                        width: '10px', height: '10px', 
                        borderRadius: '50%', 
                        background: isLast ? 'var(--gold-primary)' : 'transparent',
                        border: isLast ? 'none' : '2px solid var(--border)',
                        marginTop: '4px',
                        flexShrink: 0,
                        zIndex: 2,
                        boxShadow: isLast ? '0 0 8px var(--gold-glow)' : 'none'
                      }} />
                      <span style={{ 
                        fontSize: '12px', 
                        color: isLast ? 'var(--text-primary)' : 'var(--text-secondary)',
                        fontWeight: isLast ? '500' : '400',
                        lineHeight: '1.4'
                      }}>
                        {task}
                      </span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: '1.4' }}>
                {activeTask}
              </div>
            )}

            {activeTask && onStopAgent && (
              <button 
                onClick={onStopAgent}
                style={{
                  marginTop: '16px',
                  width: '100%',
                  padding: '8px 12px',
                  background: 'rgba(239, 68, 68, 0.15)',
                  border: '1px solid rgba(239, 68, 68, 0.4)',
                  color: '#ef4444',
                  borderRadius: '8px',
                  fontSize: '12px',
                  fontWeight: '600',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: '6px',
                  transition: 'all 0.2s ease',
                }}
              >
                <span style={{ fontSize: '14px', lineHeight: 1 }}>■</span> Terminate Active Agent
              </button>
            )}
          </div>
        )}

        <Canvas
          camera={{ position: [0, 1.35, 2.6], fov: 32 }}
          style={{ background: 'transparent' }}
        >
          <ResponsiveAvatarController modelId={modelId} isWidget={isWidget} />
        </Canvas>
      </div>

      {!isWidget && (
        <>
          <div className="status-cards">
            <div className="status-card">
              <div className="status-card-icon">✓</div>
              <div className="status-card-info">
                <div className="status-card-label">Focus Mode</div>
                <div className="status-card-value">On</div>
              </div>
            </div>
            <div className="status-card">
              <div className="status-card-icon">▶</div>
              <div className="status-card-info">
                <div className="status-card-label">Active Task</div>
                <div className="status-card-value">{activeTask || 'Idle'}</div>
              </div>
            </div>
            <div className="status-card">
              <div className="status-card-icon">◈</div>
              <div className="status-card-info">
                <div className="status-card-label">Memory</div>
                <div className="status-card-value">{memCount} stored</div>
              </div>
            </div>
          </div>

          {/* Lo-fi / Music player widget */}
          <div className="lofi-player" style={{
            position: 'absolute',
            left: '60px',
            bottom: '30px',
            background: 'rgba(28, 28, 40, 0.65)',
            backdropFilter: 'blur(20px)',
            border: '1px solid var(--glass-border)',
            borderRadius: '12px',
            padding: '10px 14px',
            width: '180px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '10px',
            zIndex: 3,
            pointerEvents: 'auto'
          }}>
            <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, flex: 1 }}>
              <span style={{ fontSize: '9px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Now Playing</span>
              <span style={{ fontSize: '11px', color: 'var(--gold-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontWeight: '500' }}>🎵 Lofi Chill Beats</span>
            </div>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
              <button style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '12px', padding: '2px' }} title="Play/Pause">⏸</button>
              <button style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer', fontSize: '12px', padding: '2px' }} title="Skip">⏭</button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
