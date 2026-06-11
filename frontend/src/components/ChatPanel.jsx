import React, { useState, useRef, useEffect } from 'react'

const fmt = (d) => d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

export default function ChatPanel({ messages, isThinking, onSendMessage }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, isThinking])

  const handleSend = () => {
    if (!input.trim()) return
    onSendMessage(input.trim())
    setInput('')
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <div className="chat-header-left">
          <div className="chat-header-title">ARIA</div>
          <div className="chat-online">
            <span className="online-dot" />
            <span>Online · Always here to help</span>
          </div>
        </div>
        <button id="chat-menu-btn" className="chat-menu-btn">···</button>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`msg-row ${msg.role === 'user' ? 'user' : 'agent'}`}>
            {msg.role === 'assistant' && (
              <div className="agent-avatar-icon">A</div>
            )}
            <div>
              <div className={`bubble ${msg.role === 'user' ? 'user' : 'agent'}`}>
                {msg.content}
              </div>
              <div className="bubble-time">{fmt(new Date(msg.timestamp))}</div>
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="msg-row agent">
            <div className="agent-avatar-icon">A</div>
            <div className="typing-indicator">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-area">
        <input
          id="chat-input"
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="Type a message…"
        />
        <button id="chat-send-btn" className="chat-send-btn" onClick={handleSend}>➤</button>
      </div>
    </div>
  )
}
