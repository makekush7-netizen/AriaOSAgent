import React, { useState, useRef, useEffect, useCallback } from 'react'
import ReactDOM from 'react-dom/client'
import { getCurrentWindow } from '@tauri-apps/api/window'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { Suspense } from 'react'
import AvatarModel from './AvatarModel'
import './index.css'

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false } }
  static getDerivedStateFromError() { return { hasError: true } }
  render() { return this.state.hasError ? null : this.props.children }
}

function WidgetApp() {
  const [contextMenu, setContextMenu] = useState(null)

  // Make body truly transparent
  useEffect(() => {
    document.body.style.background = 'transparent'
    document.body.style.backgroundColor = 'transparent'
    document.documentElement.style.background = 'transparent'
  }, [])

  // Close context menu on any click
  useEffect(() => {
    const close = () => setContextMenu(null)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [])

  const handleContextMenu = useCallback((e) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY })
  }, [])

  const handleMinimize = async (e) => {
    e.stopPropagation()
    try { await getCurrentWindow().minimize() } catch(err) { console.error(err) }
    setContextMenu(null)
  }

  const handleClose = async (e) => {
    e.stopPropagation()
    try { await getCurrentWindow().close() } catch(err) { console.error(err) }
    setContextMenu(null)
  }

  return (
    <div
      onContextMenu={handleContextMenu}
      style={{ width: '100vw', height: '100vh', position: 'relative', background: 'transparent', overflow: 'hidden' }}
    >
      {/* Drag handle at the top */}
      <div
        data-tauri-drag-region
        style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: '50px',
          zIndex: 100, cursor: 'grab',
          background: 'linear-gradient(to bottom, rgba(0,0,0,0.3), transparent)'
        }}
      />

      {/* Close button */}
      <button
        onClick={handleClose}
        style={{
          position: 'absolute', top: '8px', right: '8px', zIndex: 200,
          width: '26px', height: '26px', borderRadius: '50%',
          background: 'rgba(10,10,10,0.7)', border: '1px solid rgba(255,255,255,0.15)',
          color: '#fff', fontSize: '13px', cursor: 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          transition: 'background 0.2s', fontFamily: 'sans-serif'
        }}
        onMouseEnter={e => e.currentTarget.style.background = 'rgba(220,50,50,0.8)'}
        onMouseLeave={e => e.currentTarget.style.background = 'rgba(10,10,10,0.7)'}
        title="Close"
      >✕</button>

      {/* 3D Avatar */}
      <Canvas
        camera={{ position: [0, 1.35, 2.6], fov: 32 }}
        onCreated={({ camera }) => camera.lookAt(0, 1.25, 0)}
        style={{ background: 'transparent', width: '100%', height: '100%' }}
        gl={{ alpha: true, antialias: true }}
      >
        <OrbitControls
          target={[0, 1.25, 0]}
          enableDamping
          dampingFactor={0.05}
          enablePan={false}
          enableZoom={false}
          minPolarAngle={Math.PI / 2}
          maxPolarAngle={Math.PI / 2}
        />
        <ambientLight intensity={0.7} />
        <directionalLight position={[3, 4, 3]} intensity={0.8} color="#fffcf5" />
        <directionalLight position={[-2, 2, -1]} intensity={0.5} color="#e5cc9f" />
        <directionalLight position={[0, -1, 2]} intensity={0.4} color="#e6ceaa" />
        <ErrorBoundary>
          <Suspense fallback={null}>
            <AvatarModel modelId="female" scale={2.1} position={[0, -1.25, 0]} />
          </Suspense>
        </ErrorBoundary>
      </Canvas>

      {/* Right-click Context Menu */}
      {contextMenu && (
        <div
          style={{
            position: 'fixed', top: contextMenu.y, left: contextMenu.x, zIndex: 9999,
            background: '#1a1714', border: '1px solid rgba(255,248,235,0.08)',
            borderRadius: '10px', padding: '6px 0', minWidth: '140px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.7)',
            fontFamily: 'Inter, sans-serif', overflow: 'hidden'
          }}
        >
          <button
            onClick={handleMinimize}
            style={{
              width: '100%', padding: '10px 16px', background: 'transparent',
              border: 'none', color: '#f5f0e6', textAlign: 'left',
              cursor: 'pointer', fontSize: '13px', display: 'flex',
              alignItems: 'center', gap: '10px'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,248,235,0.07)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <span>⬇</span> Minimize
          </button>
          <div style={{ height: '1px', background: 'rgba(255,248,235,0.06)', margin: '2px 0' }} />
          <button
            onClick={handleClose}
            style={{
              width: '100%', padding: '10px 16px', background: 'transparent',
              border: 'none', color: '#ef4444', textAlign: 'left',
              cursor: 'pointer', fontSize: '13px', display: 'flex',
              alignItems: 'center', gap: '10px'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(239,68,68,0.1)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <span>✕</span> Close Widget
          </button>
        </div>
      )}
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('widget-root')).render(<WidgetApp />)
