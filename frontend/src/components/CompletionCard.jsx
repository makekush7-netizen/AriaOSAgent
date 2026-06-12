import React, { useEffect, useState } from 'react'
import { useAriaStore } from '../store/ariaStore'

export default function CompletionCard({ onNavigate }) {
  const { completionData, transitionTo } = useAriaStore()
  const [progressWidth, setProgressWidth] = useState(100)

  useEffect(() => {
    // 8-second auto-dismiss timer
    const totalTime = 8000
    const intervalTime = 100
    const step = (intervalTime / totalTime) * 100

    const timer = setInterval(() => {
      setProgressWidth(prev => {
        if (prev <= step) {
          clearInterval(timer)
          transitionTo('home')
          return 0
        }
        return prev - step
      })
    }, intervalTime)

    return () => clearInterval(timer)
  }, [transitionTo])

  const handleDismiss = () => {
    transitionTo('home')
  }

  const handleViewNotepad = () => {
    onNavigate('notepad')
  }

  return (
    <div className="completion-card">
      <div className="completion-title">
        <span>✅ Task Complete</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '10px' }}>
        <div className="completion-row">
          <span style={{ color: 'var(--accent-green)', fontWeight: 'bold' }}>✓</span>
          <span>{completionData?.summary || 'Form submitted successfully to the portal.'}</span>
        </div>

        <div className="completion-row">
          <span style={{ color: 'var(--gold-primary)', fontWeight: 'bold' }}>🧠</span>
          <span>Fields populated using Profile Memory database.</span>
        </div>

        <div className="completion-row">
          <span style={{ color: 'var(--accent-teal)', fontWeight: 'bold' }}>💾</span>
          <span>Notepad logs updated. Any missing information has been synced.</span>
        </div>
      </div>

      <div className="completion-actions">
        <button className="btn-cancel" onClick={handleViewNotepad}>View Notepad</button>
        <button className="btn-approve" style={{ background: 'var(--accent-green)' }} onClick={handleDismiss}>Done</button>
      </div>

      {/* Completion Countdown Progress Line */}
      <div 
        className="completion-progress"
        style={{ width: `${progressWidth}%` }}
      />
    </div>
  )
}
