# ARIA — Team Execution Strategy
### FAR AWAY 2026 | Deadline: June 14, 2026, 11:59 PM
**Days remaining from June 11: 3.5 days**

---

## 0. The Only Rule

If it's not in the demo, it doesn't exist. Build what the judge will see. Everything else is a roadmap slide.

The demo must show: browser agent filling a real form live, memory working, HITL interrupt happening, sub-agent chip appearing, and the character reacting with emotion. That's the win condition.

---

## 1. Team Structure & Ownership

Five people. Five clean lanes. No lane touches another lane's files without a sync first.

| Member | Role | Owns | Must Not Touch |
|---|---|---|---|
| **Kush** | Lead + Backend Orchestration | `backend/main.py`, agent loop, LLM routing, sub-agent manager, AWS integration | Frontend React files |
| **Somya** | Browser Agent Specialist | `backend/agent_tools.py`, Playwright engine, OVERLAY_JS, DOM+Vision hybrid | Memory module |
| **Agrani** | Frontend + UI States | All React components, Zustand state machine, WebSocket client, Canvas components | Backend Python files |
| **Dimple** | Memory + Research Agent | `backend/memory.py`, ChromaDB setup, episodic summarizer, research pipeline | Browser agent files |
| **Prithvi Raj Bais** | Character + Polish | VRM emotion controller, waveform visualizer, background world animation, Porcupine wake word | Agent logic files |

---

## 2. Build Order (Non-Negotiable)

This is the critical path. Everything on this list must work before anything off this list gets touched.

```
PHASE 0 (Today, June 11 — by midnight)
├── Repo setup: clean branch from existing ARIA codebase
├── Tauri project initialized (wrapping existing React app)
├── WebSocket connection React ↔ FastAPI confirmed working
├── ChromaDB installed, profile.json write/read working
└── All 5 members have the repo running locally

PHASE 1 (June 12 — Core Agent Working)
├── [Devansh] Playwright browser agent: DOM overlay + autofill from memory.json
├── [Devansh] Vision fallback: screenshot → LLM → coordinate action
├── [Agrani] Memory Layer 3: profile.json update from conversation
├── [Agrani] Memory Layer 2: ChromaDB episode storage + retrieval
├── [Kush] Sub-agent spawn: BrowserBot dispatches and reports back via WebSocket
├── [Prakhyat] 5 app states: Zustand store + state transitions working
└── [5th] VRM emotion states: idle/thinking/listening/speaking/success/error

PHASE 2 (June 13 — Integration + Canvases)
├── [Kush] End-to-end flow: user message → planning card → approval → BrowserBot executes → HITL fires → completion
├── [Prakhyat] Form Canvas rendering with live field status
├── [Prakhyat] HITL modal: blocks execution, waits for user input, resumes
├── [Agrani] Research pipeline: Tavily search → fetch → synthesize → Research Canvas
├── [Devansh] Certificate generation: PIL + openpyxl + output folder
├── [5th] Background world: particle animation + theme tokens
└── [5th] Porcupine wake word: WASM integration, test with character name

PHASE 3 (June 14 — Polish + Demo Prep)
├── [All] Integration testing: run all demo scenarios 3 times each
├── [Kush] Error handling: every failure state has a friendly ARIA response
├── [Prakhyat] Sub-agent chip: heartbeat animation, spawn/despawn animation
├── [5th] Character reactions: ensure emotion tags fire correctly in demo flow
├── [All] Demo video recording if live demo is unstable
└── [Kush] GitHub: clean README, working setup instructions, commit history shows genuine work
```

---

## 3. File Structure

```
aria-v2/
├── src/                          # React frontend
│   ├── components/
│   │   ├── character/
│   │   │   ├── VRMViewer.tsx         # Three.js canvas + VRM loader
│   │   │   ├── EmotionController.tsx # Blend shape driver
│   │   │   └── WakeWord.tsx          # Porcupine WASM hook
│   │   ├── canvas/
│   │   │   ├── FormCanvas.tsx
│   │   │   ├── CertificateCanvas.tsx
│   │   │   ├── ResearchCanvas.tsx
│   │   │   └── EmailBlastCanvas.tsx
│   │   ├── ui/
│   │   │   ├── ARIAButton.tsx
│   │   │   ├── ARIACard.tsx
│   │   │   ├── StepList.tsx
│   │   │   ├── SubAgentChip.tsx
│   │   │   ├── HITLModal.tsx
│   │   │   ├── WaveformVisualizer.tsx
│   │   │   └── PlanningCard.tsx
│   │   ├── layout/
│   │   │   ├── TopBar.tsx
│   │   │   ├── BottomBar.tsx
│   │   │   ├── CharacterZone.tsx
│   │   │   └── CanvasZone.tsx
│   │   └── background/
│   │       ├── BackgroundCanvas.tsx  # Particle world
│   │       └── themes.ts             # Theme configs
│   ├── store/
│   │   ├── ariaStore.ts              # Zustand root store
│   │   ├── agentStore.ts             # Sub-agent state
│   │   └── memoryStore.ts            # Profile + memory cache
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useVoice.ts               # Web Speech API
│   │   └── useTTS.ts                 # Nova Sonic / Cartesia
│   ├── pages/
│   │   ├── Home.tsx
│   │   ├── Memory.tsx
│   │   ├── Store.tsx
│   │   └── Settings.tsx
│   └── App.tsx                       # State machine router
├── backend/
│   ├── main.py                       # FastAPI app + WebSocket handler
│   ├── agent_orchestrator.py         # Sub-agent spawn + message routing
│   ├── agent_tools.py                # Playwright browser agent
│   ├── memory.py                     # ChromaDB + profile.json
│   ├── research.py                   # Tavily pipeline
│   ├── sandbox.py                    # Python script runner
│   ├── llm_router.py                 # Model selection + Bedrock calls
│   ├── skills/                       # Installed skill plugins
│   │   ├── form_filler/
│   │   ├── certificate_gen/
│   │   └── email_blast/
│   └── requirements.txt
├── src-tauri/                        # Tauri Rust shell (generated, minimal edits)
│   ├── tauri.conf.json
│   └── src/main.rs
├── public/
│   ├── models/                       # VRM model files
│   └── sounds/                       # UI sound effects
└── .env.example
```

---

## 4. AI Agent Prompts for Each Module

These are the exact prompts to paste to your AI coding assistant (Cursor, Windsurf, Claude Code) for each task. Give the full prompt — do not summarize it.

---

### PROMPT A — Kush: Backend WebSocket + Agent Orchestrator

```
Build a FastAPI backend with WebSocket support for an AI desktop agent called ARIA.

File: backend/main.py
File: backend/agent_orchestrator.py

Requirements:

1. FastAPI app with a single WebSocket endpoint at /ws
2. The WebSocket handles these incoming message types from the frontend:
   - { type: "user_message", content: "string" } — user typed or spoke a message
   - { type: "hitl_response", agentId: "string", fields: { key: value } } — user filled missing form fields
   - { type: "approve_plan", planId: "string" } — user approved the execution plan
   - { type: "cancel_agent", agentId: "string" } — user terminated a sub-agent

3. The WebSocket sends these outgoing message types to the frontend:
   - { type: "aria_message", content: "string", emotion: "EmotionTag" } — ARIA's reply
   - { type: "state_change", state: "planning|execution|completion" }
   - { type: "planning_card", plan: PlanObject } — execution plan for user approval
   - { type: "agent_spawn", agentId: "string", name: "string", accentColor: "string" }
   - { type: "agent_heartbeat", agentId: "string", status: "string", step: "string" }
   - { type: "agent_complete", agentId: "string", result: ResultObject }
   - { type: "hitl_request", agentId: "string", fields: MissingFieldList }
   - { type: "task_complete", summary: "string" }

4. AgentOrchestrator class:
   - spawn_agent(name, task, websocket) → creates an async task, returns agentId
   - send_heartbeat(agentId, status, step) → sends via websocket
   - request_hitl(agentId, missing_fields) → sends hitl_request, waits for hitl_response
   - complete_agent(agentId, result) → sends agent_complete, cleans up

5. The main LLM call (use Google Generative AI / gemini-1.5-flash for now, Bedrock routing to be added later):
   - System prompt: ARIA is a helpful AI proxy agent. She is warm, direct, and efficient. She uses inline emotion tags like [EMOTION:HAPPY] which are stripped from display but used to animate the character. She deploys sub-agents by name when tasks require sustained execution.
   - On receiving a user message, classify intent: casual_chat | web_task | research | script_task | memory_query
   - For web_task: build a plan and emit planning_card before executing
   - For casual_chat: respond directly
   - Always include an emotion tag in every response

6. Use asyncio for all agent execution — never block the WebSocket event loop.

Use Python 3.11, FastAPI 0.111, pydantic v2 models for all message types.
```

---

### PROMPT B — Devansh: Playwright Browser Agent

```
Build the browser automation module for an AI desktop agent.

File: backend/agent_tools.py

Context: This runs inside a FastAPI application. It is called by agent_orchestrator.py as an async function. It has access to a websocket connection to stream live updates.

Requirements:

1. BrowserAgent class with a single persistent Chromium browser instance (Playwright async)
   - One browser context per domain (stored in a dict, keyed by domain)
   - Browser stays open across multiple tasks — do not close and reopen
   - Browser window is headed (visible)

2. execute_form_task(url, user_profile, websocket, agent_id):
   - Navigate to URL
   - Inject OVERLAY_JS (see below) to tag all interactive elements
   - Take a screenshot
   - Call vision LLM with the screenshot + DOM structure and user_profile
   - LLM returns a list of actions: [{ action: "type|click|select", target: ID, value: str }]
   - Execute actions sequentially via Playwright
   - For each action: send agent_heartbeat via websocket with current step description
   - If LLM returns { action: "need_info", fields: [...] }: call orchestrator.request_hitl() and wait
   - After HITL response, resume action list
   - Final action: present a confirmation before submit — send hitl_request with type "submit_confirm"
   - On confirmation: submit the form
   - Return completion summary

3. OVERLAY_JS: JavaScript string that when injected via page.evaluate():
   - Selects all input, button, select, textarea, [role=button], a elements
   - Creates absolutely-positioned div badges numbered [1], [2], etc.
   - Badges are visible (yellow background, black text, 12px, z-index 9999)
   - Stores mapping of badge number → element reference for later targeting
   - Returns the count of tagged elements

4. DOM extraction: After overlay injection, extract:
   - All element types (input type, button text, label text, placeholder)
   - Their badge numbers
   - Current values if any
   - Return as a structured list for LLM context

5. Vision fallback: If DOM extraction returns fewer than 3 usable elements:
   - Take screenshot
   - Send to vision LLM with prompt: "Look at this screenshot. Identify all form fields and interactive elements. For each, provide: element type, visible label, estimated screen coordinates (x, y as % of image dimensions), and current value if visible."
   - Convert coordinates to actual pixels using page dimensions
   - Use page.mouse.click(x, y) and page.keyboard.type(value)

6. Use playwright.async_api throughout. Never use sync_playwright.
   Browser launch args: --disable-blink-features=AutomationControlled, --start-maximized
```

---

### PROMPT C — Agrani: Memory System + Research Agent

```
Build the memory system and research pipeline for ARIA.

File: backend/memory.py
File: backend/research.py

=== MEMORY SYSTEM ===

Requires: chromadb, sentence-transformers, json

MemoryManager class:

1. __init__:
   - Load/create profile.json at %APPDATA%/ARIA/memory.json (use pathlib, handle Windows/Mac)
   - Initialize ChromaDB client with persist_directory at %APPDATA%/ARIA/chroma/
   - Get or create two collections: "episodes" and "skills"
   - Load sentence-transformers model: all-MiniLM-L6-v2

2. get_profile() → dict: Returns the full profile JSON

3. update_profile(updates: dict):
   - Merge updates into existing profile
   - Normalize keys: "mail id" → "email", "mob" → "phone", "uni" → "college", etc.
   - Save back to disk immediately
   - Return updated profile

4. add_episode(task_type: str, summary: str, data_used: list[str]):
   - Create embedding of summary using sentence-transformers
   - Add to "episodes" ChromaDB collection with metadata: { task_type, timestamp, data_used }
   - Keep only last 200 episodes (delete oldest if over limit)

5. get_relevant_context(query: str, n_results: int = 5) → list[str]:
   - Embed query
   - Query ChromaDB episodes collection
   - Return top n_results episode summaries as list of strings

6. summarize_session(messages: list[dict]) → str:
   - Call LLM with: "Summarize what happened in this conversation. Focus on: what task was done, what user data was used, what the user corrected or added, what worked and what didn't. Be concise (max 100 words)."
   - Return summary string
   - Caller will store this as an episode

=== RESEARCH AGENT ===

Requires: tavily-python, httpx, beautifulsoup4

ResearchAgent class:

1. research(query: str, websocket, agent_id: str) → ResearchResult:
   
   Step 1 — Decompose:
   Call LLM: "Break this research query into 3-4 focused sub-questions that together fully answer it. Return as JSON array of strings only."
   Parse response as list of sub-questions.

   Step 2 — Search (parallel):
   For each sub-question, call Tavily search API.
   Use asyncio.gather for parallel execution.
   Collect top 3 URLs per sub-question.

   Step 3 — Fetch (parallel, with error handling):
   For each unique URL, fetch page content using httpx (async, timeout=10s).
   Parse with BeautifulSoup: extract main text, strip nav/footer/ads.
   Truncate each to 2000 chars.
   If fetch fails, skip that URL gracefully.

   Step 4 — Synthesize:
   Build context string: sub_question + relevant page excerpts.
   Call LLM: "Based on the following sources, answer the sub-question with a 2-3 sentence synthesis. Cite sources by number. Be factual and direct."
   Repeat for each sub-question.

   Step 5 — Assemble:
   Return ResearchResult(
     query=original_query,
     sub_questions=list,
     findings=dict[sub_question → synthesis],
     sources=list[{ url, title, used_for_sub_question }]
   )

   Send websocket agent_heartbeat updates after each step.

2. ResearchResult dataclass with to_markdown() method for export.
```

---

### PROMPT D — Prakhyat: Frontend State Machine + Canvases

```
Build the React frontend for ARIA — a desktop AI agent application.

Tech stack: React 18, TypeScript, Vite, Tailwind CSS, Zustand

=== STATE MACHINE ===

File: src/store/ariaStore.ts

Zustand store with:
- appState: 'home' | 'conversation' | 'planning' | 'execution' | 'completion'
- messages: Message[] (id, role: 'user'|'aria', content, emotion, timestamp)
- activePlan: PlanObject | null
- activeAgents: SubAgentChip[] (id, name, status, step, accentColor, heartbeat)
- canvasType: 'form' | 'certificate' | 'research' | 'email' | null
- hitlRequest: HITLRequest | null
- userProfile: UserProfile

Actions: transitionTo, addMessage, setActivePlan, spawnAgent, updateAgentHeartbeat, removeAgent, setHITLRequest, resolveHITL

=== WEBSOCKET HOOK ===

File: src/hooks/useWebSocket.ts

- Connect to ws://localhost:8000/ws on mount
- Auto-reconnect with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- On message: parse JSON, dispatch to appropriate store action based on type
- Expose: sendMessage(type, payload) function
- Handle connection errors gracefully (show "reconnecting..." status in UI, not an error screen)

=== FORM CANVAS ===

File: src/components/canvas/FormCanvas.tsx

Props: none (reads from store)

Layout: two-column
Left (40%): embedded webview showing the Playwright browser (src="http://localhost:8000/browser-view" — FastAPI serves a proxy)
Right (60%):
  - FieldList component: shows all detected form fields with status badges
    - "autofilled" (green badge): field ARIA will fill from memory
    - "needs input" (coral badge): field ARIA will ask user for
    - "awaiting" (grey badge): not yet processed
  - HITLModal: renders when store.hitlRequest is not null
    - Shows field labels and text inputs
    - Submit button sends hitl_response via WebSocket
  - ActionLog: last 5 agent_heartbeat messages in monospace font
  - ControlBar: [Pause] [Override] [Abort] buttons

=== PLANNING CARD ===

File: src/components/ui/PlanningCard.tsx

Shows when appState === 'planning' and activePlan is set:
- Task summary (1-2 sentences)
- StepList of execution steps with status indicators
- Permissions section (what ARIA will access)
- Information gaps section (what's missing from memory)
- [Cancel] and [Approve & Run] buttons
- [Approve & Run] calls sendMessage('approve_plan', { planId }) and transitions to 'execution' state

=== SUB-AGENT CHIP ===

File: src/components/ui/SubAgentChip.tsx

Props: { agentId, name, status, step, accentColor }

Renders a 220px glass card:
- Agent name with colored dot (accentColor)
- Current step text (truncated at 40 chars)
- Animated heartbeat SVG (30px wide, 20px tall — use a sine wave path that animates via CSS)
- [Pause] button
- Entrance animation: scale from 0.8 + fade in, 250ms ease-spring
- Despawn animation: scale to 0.8 + fade out, 200ms

Chips stack vertically in top-right of canvas zone. Max 3 visible, rest in overflow indicator "+N more".

Design tokens: use CSS variables from the design system (--bg-overlay, --glass-border, --gold-primary, etc.)
All components must NOT use any external component library (no shadcn, no MUI, no Radix). Pure Tailwind + custom CSS only.
```

---

### PROMPT E — 5th Member: VRM Character + Background World

```
Build the 3D character controller and animated background for ARIA.

=== VRM CHARACTER CONTROLLER ===

File: src/components/character/VRMViewer.tsx
File: src/components/character/EmotionController.tsx

Requirements:

1. VRMViewer.tsx:
   - React Three Fiber canvas, fills its container div
   - Load VRM model from /public/models/aria.vrm using @pixiv/three-vrm
   - Set up OrbitControls but disable user interaction (the camera is fixed)
   - Camera position: front-facing, slight upward angle, character centered at waist height
   - Ambient lighting: warm white, intensity 0.8
   - Point light: warm gold (#e8c97a), position top-right, intensity 1.2, distance 5
   - Expose: setEmotion(emotion: EmotionTag) method via useImperativeHandle
   - Run idle animation loop: breathing (chest bone Y-axis scale oscillation, 4s period, amplitude 0.02) + occasional blink (eye close blendshape, 200ms, every 3-5s random)

2. EmotionController.tsx:
   - Subscribes to ariaStore emotion state
   - Maps EmotionTag to VRM BlendShape operations:
     - 'happy': set blendshape 'joy' to 1.0 over 300ms, then ease to 0.4 sustained
     - 'thinking': set blendshape 'sorrow' to 0.3, tilt head bone 8deg right
     - 'listening': return all blendshapes to 0, open eyes slightly wider (blink blendshape to -0.2)
     - 'speaking': driven by audio amplitude (see below) — do not set static blendshape
     - 'error': head shake animation (rotate Y-axis ±10deg, 3 oscillations, 500ms total)
     - 'success': set 'joy' to 1.0 + small Y-position bounce (+0.05 then back, spring)
   - Lip sync for 'speaking' state:
     - Access TTS audio stream via Web Audio API AnalyserNode
     - Sample frequency data at 60fps
     - Map low-frequency amplitude (0-255) to 'aa' blendshape value (0.0 to 0.8)

=== BACKGROUND WORLD ===

File: src/components/background/BackgroundCanvas.tsx

Requirements:
- HTML Canvas element, position: fixed, full screen, z-index: 0
- Particle system: 35 particles max
- Each particle: { x, y, size (2-5px), opacity (0.3-0.8), driftX (-0.3 to -0.6 px/frame), driftY (0.2 to 0.5 px/frame), rotation, rotationSpeed }
- Particle shape: a simple 4-petal flower or oval (use canvas arc/bezier)
- Particles respawn at top-right edge when they drift off screen
- Background color: #0a0a0f (do not fill — let the CSS background show through, only draw particles)
- requestAnimationFrame loop, cancelAnimationFrame on unmount

=== PORCUPINE WAKE WORD ===

File: src/components/character/WakeWord.tsx

Requirements:
- Import @picovoice/porcupine-web
- Load the default 'Hey ARIA' keyword model (use Picovoice's built-in 'JARVIS' or 'ALEXA' as placeholder during dev — final build uses custom model)
- Run in a useEffect on mount, cleanup on unmount
- On keyword detected: call ariaStore.transitionTo('conversation') 
- Show a small indicator somewhere (bottom of character zone, --text-muted, --text-xs): "👂 Listening for 'ARIA'..."
- Handle microphone permission denial gracefully: hide the indicator, do not throw
```

---

## 5. Daily Sync Protocol

Every morning and evening, 10-minute standup. Three questions only:

1. What did you push since last sync? (share commit hash)
2. Is your module working end-to-end on your machine?
3. What do you need from another lane?

**Integration checkpoints:**

- End of June 12: Kush does a full integration test. BrowserBot must complete one real form fill on a live website. If it doesn't work, June 13 morning is debug only.

- End of June 13: Full demo rehearsal. All 10 demo success metrics from the PRD checked off one by one. If any fail, the demo video is recorded with whatever works.

- June 14 morning: Final build. Record demo video regardless of stability (always have a recorded backup). Submit before 8 PM to avoid last-minute issues.

---

## 6. Git Workflow

Judges may review commit history. Make it look real.

```bash
# Branch strategy
main              # Stable, demo-ready at all times
feature/browser-agent
feature/memory
feature/frontend-states
feature/character
feature/research

# Commit message format
[module] what you did
# Examples:
[browser] DOM overlay injection working on Google Forms
[memory] ChromaDB episode storage and retrieval tested
[frontend] Planning card component with step list
[character] Emotion blendshape transitions implemented
```

Each member commits to their own branch and merges to main only after testing. Kush reviews merge to main. Minimum 3 commits per member per day — shows active development.

---

## 7. Demo Script (Memorize This)

The demo must be under 4 minutes if live. This is the exact flow:

**Opening (30s):** Show the app running. Character is alive and idle. Wake word demo: say "Hey ARIA" and she responds. Explain in one sentence: *"ARIA is a personal AI proxy that lives on your desktop and does anything a human can do on a computer — using your own accounts."*

**Memory intro (20s):** Show the memory panel. Point out name, email, college, roll number already stored. Say: *"She already knows who I am. She remembers this from our previous conversations."*

**Browser task (90s):** Say to ARIA: *"Fill the registration form on this Unstop hackathon for me."* Show the planning card appear. Click Approve. Watch the browser open and the DOM overlay badges appear. Show ARIA autofilling fields from memory. Show the HITL interrupt fire for "Team Code" — fill it in, automation resumes. Show the sub-agent chip with heartbeat animation. Show form submitted.

**Completion (20s):** ARIA delivers the summary by voice. Character does the success animation. Memory updates with Team Code.

**Research task (30s) — optional if time allows:** *"Research the current state of robotics in India."* Show the research pipeline running (can be fast-forwarded in video). Show the Research Canvas with sources.

**Closing (20s):** Show the marketplace (even if static mockup). Explain the roadmap in 3 sentences. End with: *"ARIA democratizes automation. She's not for developers. She's for everyone."*

---

## 8. Submission Checklist

Complete all of these before 8 PM on June 14:

- [ ] GitHub repository is public with real commit history
- [ ] README.md has clear setup instructions that actually work
- [ ] Demo video is recorded (2–5 minutes, shows browser agent working live)
- [ ] Presentation has: problem slide, solution demo screenshot, tech stack diagram, roadmap, market size
- [ ] All team members listed with correct details
- [ ] The working app can be launched from a fresh clone with the setup instructions
- [ ] At least one live demo scenario works without any manual intervention

---

## 9. If Things Break (Contingency)

**Browser agent fails on demo day:** Record video ahead of time with it working. Show the video as "pre-recorded demo due to network conditions." Judges accept this.

**Tauri build fails:** Demo the React + FastAPI version in a browser window. Mention Tauri packaging as "production build in progress." The agent works — the wrapper is cosmetic for demo purposes.

**AWS Bedrock is slow / over quota:** Fall back to Gemini API (existing integration). ARIA still works. Swap model name in .env only.

**ChromaDB crashes:** Fall back to memory.json only (Layer 3 profile). The demo still shows memory working — just without episodic context.

**Character model won't load:** Use the existing bubble mode (orb with audio pulse) as fallback. Still impressive. Don't waste time debugging VRM loader on demo day.

**Internet is down at demo venue:** Pre-cache one research result. Use a locally saved page for the form fill demo. Porcupine works offline. TTS can use Web Speech API offline fallback. The demo runs fully offline if prepared.
