import React from 'react'

const STORAGE_PREFIX = 'aria_'

function loadFromStorage(key, fallback) {
  try {
    const raw = localStorage.getItem(STORAGE_PREFIX + key)
    return raw ? JSON.parse(raw) : fallback
  } catch { return fallback }
}

function saveToStorage(key, value) {
  try { localStorage.setItem(STORAGE_PREFIX + key, JSON.stringify(value)) } catch { }
}

const DEFAULT_WIDGETS = [
  { id: 'clock', visible: true, position: { x: 0, y: 0 }, size: { w: 32, h: 30 } },
  { id: 'calendar', visible: true, position: { x: 0, y: 34 }, size: { w: 32, h: 60 } },
  { id: 'active_task', visible: true, position: { x: 34, y: 0 }, size: { w: 32, h: 30 } },
  { id: 'goals', visible: true, position: { x: 68, y: 0 }, size: { w: 32, h: 30 } },
  { id: 'memory', visible: true, position: { x: 34, y: 34 }, size: { w: 32, h: 60 } },
  { id: 'todo', visible: true, position: { x: 68, y: 34 }, size: { w: 32, h: 36 } },
  { id: 'quick_actions', visible: false, position: { x: 54, y: 34 }, size: { w: 46, h: 54 } },
  { id: 'quick_links', visible: true, position: { x: 68, y: 74 }, size: { w: 32, h: 20 } },
]

const DEFAULT_THEME = {
  id: 'night_garden',
  name: 'Night Garden',
  goldPrimary: '#e8c97a',
  goldDim: '#c4a55a',
  accentTeal: '#4fd1c7',
  accentPurple: '#9b7ff4',
  accentCoral: '#f4956a',
  accentGreen: '#6bcf7f',
  bgWorld: '#0a0a0f',
  bgBase: '#0f0f16',
  bgSurface: '#16161f',
  textPrimary: '#f0ede8',
  textSecondary: '#a09a90',
}

const DEFAULT_CHARACTER = {
  scale: 1.0,
  posX: 0,
  posY: 0,
  greeting: '',
  showGreeting: true,
}

const createStore = (createState) => {
  let state
  const listeners = new Set()

  const setState = (partial) => {
    const nextState = typeof partial === 'function' ? partial(state) : partial
    if (Object.is(nextState, state)) return
    state = { ...state, ...nextState }
    listeners.forEach((listener) => listener())
  }

  const getState = () => state

  const subscribe = (listener) => {
    listeners.add(listener)
    return () => listeners.delete(listener)
  }

  state = createState(setState, getState)

  return { setState, getState, subscribe }
}

const create = (createState) => {
  const store = createStore(createState)

  const useStore = (selector = (s) => s) => {
    return React.useSyncExternalStore(
      store.subscribe,
      () => selector(store.getState()),
      () => selector(store.getState())
    )
  }

  Object.assign(useStore, store)
  return useStore
}

// appState: 'home' | 'conversation' | 'planning' | 'execution' | 'completion'
export const useAriaStore = create((set, get) => ({
  appState: 'home',
  messages: [{ id: 1, role: 'aria', content: "Hello! I'm ARIA, your AI assistant. What would you like to do today?", ts: Date.now() }],
  isThinking: false,
  agentState: 'idle',
  activeTask: null,
  taskLog: [],
  activeAgents: [],
  activePlan: null,
  activeCanvas: 'form',
  hitlRequest: null,
  memoryData: {},
  widgetLayout: loadFromStorage('widget_layout', DEFAULT_WIDGETS),
  theme: loadFromStorage('theme', DEFAULT_THEME),
  character: loadFromStorage('character', DEFAULT_CHARACTER),
  completionData: null,

  transitionTo: (state) => set({ appState: state }),

  addMessage: (msg) => set((s) => ({
    messages: [...s.messages, { id: Date.now(), ...msg }]
  })),

  setIsThinking: (v) => set({ isThinking: v }),
  setAgentState: (v) => set({ agentState: v }),
  setActiveTask: (v) => set({ activeTask: v }),

  addTaskLog: (entry) => set((s) => ({
    taskLog: [...s.taskLog, entry].slice(-20)
  })),

  clearTaskLog: () => set({ taskLog: [] }),

  spawnAgent: (agent) => set((s) => ({
    activeAgents: [...s.activeAgents, agent]
  })),

  updateAgentHeartbeat: (agentId, status, step) => set((s) => ({
    activeAgents: s.activeAgents.map((a) => a.id === agentId ? { ...a, status, step } : a)
  })),

  removeAgent: (agentId) => set((s) => ({
    activeAgents: s.activeAgents.filter((a) => a.id !== agentId)
  })),

  setActivePlan: (plan) => set({ activePlan: plan }),

  setHitlRequest: (req) => set({ hitlRequest: req }),
  clearHitlRequest: () => set({ hitlRequest: null }),

  setMemoryData: (data) => set({ memoryData: data }),

  setCompletionData: (data) => set({ completionData: data }),

  updateWidget: (id, patch) => set((s) => {
    const next = s.widgetLayout.map((w) => w.id === id ? { ...w, ...patch } : w)
    saveToStorage('widget_layout', next)
    return { widgetLayout: next }
  }),

  setWidgetLayout: (layout) => set(() => {
    saveToStorage('widget_layout', layout)
    return { widgetLayout: layout }
  }),

  resetWidgetLayout: () => set(() => {
    saveToStorage('widget_layout', DEFAULT_WIDGETS)
    return { widgetLayout: DEFAULT_WIDGETS }
  }),

  setTheme: (theme) => set(() => {
    saveToStorage('theme', theme)
    return { theme }
  }),

  resetTheme: () => set(() => {
    saveToStorage('theme', DEFAULT_THEME)
    return { theme: DEFAULT_THEME }
  }),

  setCharacter: (patch) => set((s) => {
    const next = { ...s.character, ...patch }
    saveToStorage('character', next)
    return { character: next }
  }),

  resetCharacter: () => set(() => {
    saveToStorage('character', DEFAULT_CHARACTER)
    return { character: DEFAULT_CHARACTER }
  }),

  setActiveCanvas: (type) => set({ activeCanvas: type }),
}))
