import React, { useState } from 'react'

const Icons = {
  User: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>,
  Sword: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="14.5 17.5 3 6 3 3 6 3 17.5 14.5"/><line x1="13" y1="19" x2="19" y2="13"/><line x1="16" y1="16" x2="20" y2="20"/><line x1="19" y1="21" x2="21" y2="19"/></svg>,
  Square: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>,
  Sparkles: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>,
  Mail: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/></svg>,
  FileText: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>,
  Box: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>,
  Image: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/></svg>,
  Gamepad: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="6" y1="12" x2="10" y2="12"/><line x1="8" y1="10" x2="8" y2="14"/><line x1="15" y1="13" x2="15.01" y2="13"/><line x1="18" y1="11" x2="18.01" y2="11"/><rect width="20" height="12" x="2" y="6" rx="2"/></svg>,
  Send: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>,
  Rocket: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 3.82-13.012cA2 2 0 0 1 15 2h3a2 2 0 0 1 2 2v3a2 2 0 0 1-.989 1.718A22 22 0 0 1 12 15z"/><path d="M9 11v-1"/><path d="M13 15h1"/></svg>,
  Briefcase: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="20" height="14" x="2" y="7" rx="2" ry="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>,
  Palette: () => <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/><circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/><circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/><circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/></svg>
}

const SKINS = [
  { id: 'default', name: 'Default ARIA', desc: 'The classic look', icon: <Icons.User />, image: null, price: null, equipped: true },
  { id: 'kirito', name: 'Kirito', desc: 'The Black Swordsman', icon: null, image: '/kirito.png', price: '₹299', equipped: false },
  { id: 'kaniko', name: 'Kaniko', desc: 'Cyberpunk hacker', icon: null, image: '/Kaniko.png', price: '₹199', equipped: false },
  { id: 'subaru', name: 'Subaru', desc: 'Return by Death', icon: null, image: '/subaru.png', price: '₹399', equipped: false },
]

const SKILLS = [
  { id: 'gmail', name: 'Gmail Reader', dev: 'ARIA Labs', icon: <Icons.Mail />, stars: 5, price: null, installed: true },
  { id: 'form', name: 'Form Filler', dev: 'ARIA Labs', icon: <Icons.FileText />, stars: 4, price: null, installed: true },
  { id: 'blender', name: 'Blender Agent', dev: 'Community', icon: <Icons.Box />, stars: 4, price: null, installed: false },
  { id: 'photoshop', name: 'Photoshop Assistant', dev: 'PixelCraft', icon: <Icons.Image />, stars: 5, price: '₹149', installed: false },
  { id: 'unity', name: 'Unity Dev Helper', dev: 'GameForge', icon: <Icons.Gamepad />, stars: 4, price: '₹199', installed: false },
  { id: 'email', name: 'Cold Email Sender', dev: 'OutreachAI', icon: <Icons.Send />, stars: 4, price: null, installed: false },
  { id: 'unreal', name: 'Unreal Engine Skill', dev: 'EpicDev', icon: <Icons.Rocket />, stars: 5, price: '₹249', installed: false },
]

function Stars({ n }) {
  return <div className="store-card-stars">{'★'.repeat(n)}{'☆'.repeat(5 - n)}</div>
}

export default function StorePage() {
  const [tab, setTab] = useState('skins')
  const [installed, setInstalled] = useState(new Set(['gmail', 'form']))

  const handleInstall = (id) => setInstalled(p => new Set([...p, id]))

  return (
    <div className="store-page">
      <h1>Store</h1>
      <p>Customize ARIA with skins and skill plugins.</p>

      <div className="store-tabs">
        <button id="tab-skins" className={`store-tab ${tab === 'skins' ? 'active' : ''}`} onClick={() => setTab('skins')}>
           🎨 Skins
        </button>
        <button id="tab-skills" className={`store-tab ${tab === 'skills' ? 'active' : ''}`} onClick={() => setTab('skills')}>
           ⚡ Skills
        </button>
      </div>

      {tab === 'skins' && (
        <div className="store-grid">
          {SKINS.map(s => (
            <div key={s.id} className="store-card">
              <div className="store-card-content">
                {s.image ? (
                  <div className="store-card-icon skin-preview">
                    <img src={s.image} alt={s.name} />
                  </div>
                ) : (
                  <div className="store-card-icon">{s.icon}</div>
                )}
                <div className="store-card-name">{s.name}</div>
                <div className="store-card-meta">{s.desc}</div>
              </div>
              <div className="store-card-footer">
                {s.equipped
                  ? <span className="equipped-badge">Equipped</span>
                  : <div className="store-card-price">{s.price}</div>
                }
              </div>
              <button id={`skin-btn-${s.id}`} className={`store-btn ${s.equipped ? 'installed' : 'locked'}`} disabled={s.equipped}>
                {s.equipped ? 'Equipped' : `Buy ${s.price}`}
              </button>
            </div>
          ))}
        </div>
      )}

      {tab === 'skills' && (
        <div className="store-grid">
          {SKILLS.map(sk => {
            const isInst = installed.has(sk.id)
            return (
              <div key={sk.id} className="store-card">
                <div className="store-card-content">
                  <div className="store-card-icon">{sk.icon}</div>
                  <div className="store-card-name">{sk.name}</div>
                  <div className="store-card-meta">by {sk.dev}</div>
                  <Stars n={sk.stars} />
                </div>
                <div className="store-card-footer">
                  {sk.price
                    ? <div className="store-card-price">{sk.price}</div>
                    : <div className="store-card-price" style={{ color: 'var(--text-sec)' }}>Free</div>
                  }
                </div>
                <button
                  id={`skill-btn-${sk.id}`}
                  className={`store-btn ${isInst ? 'installed' : sk.price ? 'buy' : 'install'}`}
                  onClick={() => !isInst && !sk.price && handleInstall(sk.id)}
                  disabled={isInst}
                >
                  {isInst ? '✓ Installed' : sk.price ? `Buy ${sk.price}` : 'Install'}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
