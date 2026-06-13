import React, { Suspense, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import AvatarModel from '../AvatarModel'
import { useAriaStore } from '../store/ariaStore'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(e) {
    console.error('[ARIA] Avatar:', e)
  }

  render() {
    return this.state.hasError ? null : this.props.children
  }
}

function PlatformGlow() {
  const disc = useRef()
  const ring = useRef()

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

function ResponsiveAvatarController({ modelId, isWidget, characterScale = 1 }) {
  const { camera, size } = useThree()
  const aspect = size.width / size.height

  // Adjust camera to show more of the body — scale factor pulls camera back
  const scaleBoost = Math.max(1, characterScale)
  const baseZ = isWidget ? 2.05 : 2.55 * scaleBoost
  const baseTargetX = 0
  const baseTargetY = isWidget ? 1.62 : 1.35
  const baseCameraY = isWidget ? 1.62 : 1.45

  const femaleScale = 2.12
  const maleScale = 1.72
  const femalePosY = -0.82
  const malePosY = -0.84

  const scale = modelId === 'male' ? maleScale : femaleScale
  const posY = modelId === 'male' ? malePosY : femalePosY

  const idealAspect = 0.8
  const targetRef = useRef({ z: baseZ, tx: baseTargetX })

  if (aspect < idealAspect) {
    const ratio = idealAspect / aspect
    targetRef.current.z = Math.min(4.4, baseZ * ratio)
    targetRef.current.tx = baseTargetX * (aspect / idealAspect)
  } else {
    targetRef.current.z = baseZ
    targetRef.current.tx = baseTargetX
  }

  useFrame(() => {
    // Smooth lerp to target camera position (prevents squeeze on resize)
    const lerp = 0.08
    camera.position.z += (targetRef.current.z - camera.position.z) * lerp
    camera.position.x += (targetRef.current.tx - camera.position.x) * lerp
    camera.position.y = baseCameraY
    camera.lookAt(targetRef.current.tx, baseTargetY, 0)
    camera.updateProjectionMatrix()
  })

  return (
    <>
      <ambientLight intensity={0.7} color="#ffe6c2" />
      <directionalLight position={[2.5, 4, 2.5]} intensity={0.85} color="#ffd7a0" />
      <directionalLight position={[-2, 2, -1]} intensity={0.35} color="#8ccfd0" />
      <directionalLight position={[0, -1, 2]} intensity={0.35} color="#e8c97a" />
      <ErrorBoundary>
        <Suspense fallback={null}>
          <AvatarModel modelId={modelId} scale={scale} position={[0, posY, 0]} />
        </Suspense>
      </ErrorBoundary>
      {!isWidget && <PlatformGlow />}
    </>
  )
}

export default function AvatarZone({
  greeting,
  activeTask,
  taskLog = [],
  memoryData,
  onToggleBubble,
  onStopAgent,
  modelId = 'female',
  isWidget = false
}) {
  const { character } = useAriaStore()
  const fullName = memoryData?.name || 'Endeavour'
  const firstName = fullName.split(' ')[0]
  const taskSummary = taskLog.length > 0 ? taskLog[taskLog.length - 1] : (activeTask || 'Idle')

  const scale = character?.scale || 1
  const posX = character?.posX || 0
  const posY = character?.posY || 0
  const showGreeting = character?.showGreeting !== false

  return (
    <div className="avatar-zone" style={{ height: '100%', display: 'flex', flexDirection: 'column', overflow: 'visible' }}>
      {!isWidget && showGreeting && (
        <div className="avatar-greeting">
          <h2>
            {greeting},<br />
            {firstName}
          </h2>
          <p>How can I help you today?</p>
        </div>
      )}

      <div className="avatar-canvas-wrap" style={{
        position: 'relative', flex: 1, overflow: 'visible',
        transform: `translate(${posX}px, ${posY}px) scale(${scale})`,
        transformOrigin: 'center bottom',
      }}>
        {!isWidget && (
          <button id="bubble-toggle-btn" className="bubble-toggle" onClick={onToggleBubble} title="Bubble mode">
            o
          </button>
        )}

        <Canvas
          camera={{ position: [0, 1.68, 2.25], fov: 32 }}
          style={{ background: 'transparent' }}
        >
          <ResponsiveAvatarController modelId={modelId} isWidget={isWidget} characterScale={scale} />
        </Canvas>

        {!isWidget && (
          <div className="avatar-task-chip">
            <span className="avatar-task-label">{taskLog.length > 0 ? 'Plan' : 'State'}</span>
            <strong>{taskSummary}</strong>
            {activeTask && onStopAgent && (
              <button type="button" onClick={onStopAgent}>Stop</button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
