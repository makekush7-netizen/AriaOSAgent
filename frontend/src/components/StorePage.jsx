import React, { useEffect, useMemo, useState } from 'react'

const Icon = ({ type }) => {
  const paths = {
    mail: <><rect width="20" height="16" x="2" y="4" rx="2" /><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" /></>,
    file: <><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" /><polyline points="14 2 14 8 20 8" /><line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /></>,
    box: <><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" /><polyline points="3.27 6.96 12 12.01 20.73 6.96" /></>,
    image: <><rect width="18" height="18" x="3" y="3" rx="2" /><circle cx="9" cy="9" r="2" /><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" /></>,
    code: <><path d="m18 16 4-4-4-4" /><path d="m6 8-4 4 4 4" /><path d="m14.5 4-5 16" /></>,
    send: <><line x1="22" x2="11" y1="2" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></>,
    user: <><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></>,
  }

  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {paths[type] || paths.user}
    </svg>
  )
}

const SKINS = [
  { id: 'default', name: 'Default ARIA', desc: 'Classic companion model', icon: 'user', image: null, price: null, equipped: true },
  { id: 'kirito', name: 'Kirito', desc: 'Focused black-coat skin', image: '/kirito.png', price: 'Rs 299', equipped: false },
  { id: 'kaniko', name: 'Kaniko', desc: 'Cyberpunk desk setup', image: '/Kaniko.png', price: 'Rs 199', equipped: false },
  { id: 'subaru', name: 'Subaru', desc: 'Warm casual avatar', image: '/subaru.png', price: 'Rs 399', equipped: false },
]

const SKILLS = [
  { id: 'gmail', name: 'Gmail Reader', dev: 'ARIA Labs', icon: 'mail', stars: 5, price: null, installed: true, desc: 'Summarize unread mail and draft replies.' },
  { id: 'form', name: 'Form Filler', dev: 'ARIA Labs', icon: 'file', stars: 4, price: null, installed: true, desc: 'Fill registration forms from local memory.' },
  { id: 'blender', name: 'Blender Agent', dev: 'Community', icon: 'box', stars: 4, price: null, installed: false, desc: 'Run common 3D workflow commands.' },
  { id: 'photoshop', name: 'Photoshop Assistant', dev: 'PixelCraft', icon: 'image', stars: 5, price: 'Rs 149', installed: false, desc: 'Batch-edit creative assets.' },
  { id: 'unity', name: 'Unity Dev Helper', dev: 'GameForge', icon: 'code', stars: 4, price: 'Rs 199', installed: false, desc: 'Generate scripts and scene helpers.' },
  { id: 'email', name: 'Cold Email Sender', dev: 'OutreachAI', icon: 'send', stars: 4, price: null, installed: false, desc: 'Send templated mail from a CSV.' },
]

function Stars({ n }) {
  return <div className="store-stars" aria-label={`${n} out of 5 stars`}>{n}/5 rating</div>
}

const CATALOG = [
  ...SKINS.map((item) => ({ ...item, kind: 'skin' })),
  ...SKILLS.map((item) => ({ ...item, kind: 'skill' })),
]

export default function StorePage({ defaultTab = 'all' }) {
  const [tab, setTab] = useState(defaultTab)
  const [installed, setInstalled] = useState(new Set(['gmail', 'form']))

  useEffect(() => {
    setTab(defaultTab)
  }, [defaultTab])

  const handleInstall = (id) => setInstalled((p) => new Set([...p, id]))

  const filteredCatalog = useMemo(() => {
    if (tab === 'all') return CATALOG
    if (tab === 'skins') return CATALOG.filter((item) => item.kind === 'skin')
    return CATALOG.filter((item) => item.kind === 'skill')
  }, [tab])

  return (
    <section className="panel-page store-page">
      <div className="panel-hero">
        <div>
          <p className="eyebrow">Marketplace</p>
          <h1>Companion Catalog</h1>
          <p>One place to switch ARIA's look and expand what she can do.</p>
        </div>
        <div className="segmented-tabs">
          <button id="tab-all" className={tab === 'all' ? 'active' : ''} onClick={() => setTab('all')}>All</button>
          <button id="tab-skins" className={tab === 'skins' ? 'active' : ''} onClick={() => setTab('skins')}>Appearances</button>
          <button id="tab-skills" className={tab === 'skills' ? 'active' : ''} onClick={() => setTab('skills')}>Abilities</button>
        </div>
      </div>

      <div className="store-grid unified">
        {filteredCatalog.map((item) => {
          const isSkin = item.kind === 'skin'
          const isInstalled = !isSkin && installed.has(item.id)
          const isEquipped = isSkin && item.equipped
          const titleBadge = isSkin ? 'Appearance' : 'Skill'

          return (
            <article key={item.id} className={`store-card ${isEquipped || isInstalled ? 'equipped' : ''}`}>
              <div className={isSkin ? 'skin-preview' : 'skill-icon'}>
                {isSkin ? (item.image ? <img src={item.image} alt={item.name} /> : <Icon type={item.icon} />) : <Icon type={item.icon} />}
              </div>
              <div className="store-card-body">
                <div>
                  <span className="store-pill">{titleBadge}</span>
                  <h3>{item.name}</h3>
                  <p>{item.desc}</p>
                  {!isSkin && (
                    <>
                      <small>by {item.dev}</small>
                      <Stars n={item.stars} />
                    </>
                  )}
                </div>
                <button
                  id={`${item.kind}-btn-${item.id}`}
                  className={isEquipped || isInstalled ? 'secondary-btn disabled' : item.price ? 'secondary-btn' : 'primary-btn'}
                  onClick={() => !isSkin && !isInstalled && !item.price && handleInstall(item.id)}
                  disabled={isEquipped || isInstalled}
                >
                  {isEquipped ? 'Equipped' : isInstalled ? 'Installed' : item.price ? `Buy ${item.price}` : 'Install'}
                </button>
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}
