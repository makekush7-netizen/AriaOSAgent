import React, { useState, useEffect, useRef } from 'react'
import { useAriaStore } from '../store/ariaStore'

// Helper to format date/time in HH:MM AM/PM format (e.g. 08:42 PM)
const fmtTime = (date) => {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: true })
}
const fmtDate = (date) => date.toLocaleDateString([], { weekday: 'long', month: 'short', day: 'numeric' })

export default function WidgetZone({ onNavigate }) {
  const {
    widgetLayout,
    activeTask,
    memoryData,
    updateWidget,
    transitionTo,
    setActivePlan,
    setActiveCanvas
  } = useAriaStore()

  const [time, setTime] = useState(new Date())
  const containerRef = useRef(null)
  const [dragState, setDragState] = useState(null) // { id, startX, startY, startLeft, startTop, mode: 'drag' | 'resize' }

  // Clock tick
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Memory calculations
  const memKeys = Object.keys(memoryData).filter(k => memoryData[k])
  const memCount = memKeys.length

  // Drag & Resize handlers
  const handleMouseDown = (e, id, mode) => {
    e.preventDefault()
    if (!containerRef.current) return

    const rect = containerRef.current.getBoundingClientRect()
    const widget = widgetLayout.find(w => w.id === id)
    if (!widget) return

    const startLeft = widget.position.x
    const startTop = widget.position.y
    const startWidth = widget.size.w
    const startHeight = widget.size.h

    setDragState({
      id,
      mode,
      startX: e.clientX,
      startY: e.clientY,
      startLeft,
      startTop,
      startWidth,
      startHeight,
      containerWidth: rect.width,
      containerHeight: rect.height
    })
  }

  useEffect(() => {
    if (!dragState) return

    const handleMouseMove = (e) => {
      const deltaX = e.clientX - dragState.startX
      const deltaY = e.clientY - dragState.startY

      const deltaPctX = (deltaX / dragState.containerWidth) * 100
      const deltaPctY = (deltaY / dragState.containerHeight) * 100

      if (dragState.mode === 'drag') {
        const newX = Math.max(0, Math.min(100 - dragState.startWidth, dragState.startLeft + deltaPctX))
        const newY = Math.max(0, Math.min(100 - dragState.startHeight, dragState.startTop + deltaPctY))
        updateWidget(dragState.id, { position: { x: newX, y: newY } })
      } else if (dragState.mode === 'resize') {
        const newW = Math.max(15, Math.min(100 - dragState.startLeft, dragState.startWidth + deltaPctX))
        const newH = Math.max(15, Math.min(100 - dragState.startTop, dragState.startHeight + deltaPctY))
        updateWidget(dragState.id, { size: { w: newW, h: newH } })
      }
    }

    const handleMouseUp = () => {
      setDragState(null)
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [dragState, updateWidget])

  // Click Quick Action
  const handleQuickAction = (action) => {
    if (action === 'fill_form') {
      const mockPlan = {
        id: 'mock_form_fill',
        summary: 'Autofill the Unstop Competition & Profile registration form.',
        steps: [
          { id: 1, label: 'Open browser workspace', status: 'active' },
          { id: 2, label: 'Navigate to target form', status: 'pending' },
          { id: 3, label: 'Autofill details (name, email, college, roll number)', status: 'pending' },
          { id: 4, label: 'Confirm submission', status: 'pending' }
        ],
        permissions: ['Open browser window', 'Read profile memory'],
        info_gaps: []
      }
      setActivePlan(mockPlan)
      setActiveCanvas('form')
      transitionTo('planning')
    } else if (action === 'research') {
      transitionTo('conversation')
    } else if (action === 'write_email') {
      const mockPlan = {
        id: 'mock_email_blast',
        summary: 'Send confirmation updates to all 47 registered hackathon participants.',
        steps: [
          { id: 1, label: 'Parse user-provided CSV sheet', status: 'pending' },
          { id: 2, label: 'Initialize template rendering context', status: 'pending' },
          { id: 3, label: 'Preview mail drafts', status: 'pending' },
          { id: 4, label: 'Execute mailing loops via script automation', status: 'pending' }
        ],
        permissions: ['Read memory profile', 'Execute background automation scripts'],
        info_gaps: []
      }
      setActivePlan(mockPlan)
      setActiveCanvas('email')
      transitionTo('planning')
    } else if (action === 'book_ticket') {
      const mockPlan = {
        id: 'mock_book_ticket',
        summary: 'Book developer conference passes on BookMyShow.',
        steps: [
          { id: 1, label: 'Search event page', status: 'pending' },
          { id: 2, label: 'Select ticket quantities', status: 'pending' },
          { id: 3, label: 'Secure cart checkout', status: 'pending' }
        ],
        permissions: ['Open browser window', 'Write secure cookie memory'],
        info_gaps: []
      }
      setActivePlan(mockPlan)
      setActiveCanvas('form')
      transitionTo('planning')
    }
  }

  const renderWidgetContent = (id) => {
    switch (id) {
      case 'clock':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', height: '100%' }}>
            <div className="clock-time" style={{ fontSize: '24px', fontWeight: 'bold' }}>{fmtTime(time)}</div>
            <div className="clock-date" style={{ fontSize: '11px', opacity: 0.7, marginTop: '2px' }}>{fmtDate(time)}</div>
            <div className="clock-weather" style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px', fontSize: '11px', color: 'var(--text-secondary)' }}>
              <span>⛅</span>
              <span>Rainy 24°C</span>
            </div>
          </div>
        )
      case 'active_task':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', paddingBottom: '4px' }}>
            {activeTask ? (
              <div className="task-active">
                <span className="logo-dot" style={{ animationDuration: '1s', display: 'inline-block', marginRight: '6px' }} />
                <span>{activeTask}</span>
              </div>
            ) : (
              <div className="task-idle" style={{ fontSize: '12px', opacity: 0.7 }}>No active tasks running</div>
            )}
            <div style={{ display: 'flex', gap: '8px', marginTop: '6px' }}>
              <button 
                className="new-task-btn" 
                style={{
                  background: 'rgba(232, 201, 122, 0.08)',
                  border: '1px dashed var(--gold-primary)',
                  borderRadius: '6px',
                  color: 'var(--gold-primary)',
                  padding: '4px 8px',
                  fontSize: '10px',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px'
                }} 
                onClick={() => transitionTo('conversation')}
              >
                <span>+</span> New Task
              </button>
            </div>
          </div>
        )
      case 'memory':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'space-between', height: '100%', paddingBottom: '4px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5', margin: '4px 0' }}>
              You have {memCount > 0 ? memCount : '128'} memories across {memCount > 0 ? Math.ceil(memCount / 4) : '14'} categories.
            </div>
            <button 
              className="memory-link-btn" 
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--gold-primary)',
                fontSize: '11px',
                cursor: 'pointer',
                padding: 0,
                textAlign: 'left',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                fontWeight: '500'
              }} 
              onClick={() => onNavigate('memory')}
            >
              Open Memory →
            </button>
          </div>
        )
      case 'quick_actions':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', justifyContent: 'center' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '4px' }}>
              <button className="action-pill" onClick={() => handleQuickAction('research')}>Research</button>
              <button className="action-pill" onClick={() => handleQuickAction('write_email')}>Write Email</button>
              <button className="action-pill" onClick={() => handleQuickAction('fill_form')}>Fill Form</button>
              <button className="action-pill" onClick={() => handleQuickAction('book_ticket')}>Book Ticket</button>
            </div>
          </div>
        )
      default:
        return null
    }
  }

  const widgetTitles = {
    clock: '🕐 Time',
    active_task: '⚡ Active Task',
    memory: '🧠 Memory',
    quick_actions: '✦ Quick Actions'
  }

  const visibleWidgets = widgetLayout.filter(w => w.visible)

  return (
    <div className="widget-zone" ref={containerRef}>
      {visibleWidgets.length === 0 ? (
        <div className="widget-empty-hint">No widgets visible. Restore them in Settings.</div>
      ) : (
        <div className="widget-canvas-host">
          {visibleWidgets.map(widget => (
            <div
              key={widget.id}
              className={`widget-card ${dragState?.id === widget.id ? 'dragging' : ''}`}
              style={{
                left: `${widget.position.x}%`,
                top: `${widget.position.y}%`,
                width: `${widget.size.w}%`,
                height: `${widget.size.h}%`,
              }}
            >
              <div
                className="widget-header"
                onMouseDown={(e) => handleMouseDown(e, widget.id, 'drag')}
              >
                <div className="widget-title">{widgetTitles[widget.id] || widget.id}</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <button className="widget-options-btn" onClick={(e) => e.stopPropagation()} title="Options">⋯</button>
                  <button
                    className="widget-close"
                    onClick={(e) => {
                      e.stopPropagation()
                      updateWidget(widget.id, { visible: false })
                    }}
                  >
                    ×
                  </button>
                </div>
              </div>

              <div className="widget-content" style={{ height: 'calc(100% - 25px)', overflow: 'hidden' }}>
                {renderWidgetContent(widget.id)}
              </div>

              <div
                className="widget-resize-handle"
                onMouseDown={(e) => handleMouseDown(e, widget.id, 'resize')}
              >
                ◢
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
