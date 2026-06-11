# ARIA — Agentic Feature Sprint Progress
**Deadline: June 14, 2026, 11:59 PM | Started: June 11, 2026**

---

> ⚠️ **CRITICAL NOTE FOR THE NEXT ANTIGRAVITY AGENT**
> Antigravity agent sessions have limited context windows. If you are a NEW agent picking this up, READ THIS FILE FIRST before touching any code.
> Then read `files/ARIA_EXECUTION_STRATEGY.md` for the full feature spec.
> Always update this file when you finish or start a feature. Mark `[x]` = done, `[/]` = in progress, `[ ]` = not started.
> The user's name is Kush. Frontend (React/UI) is handled by Agrani — **do not touch frontend files unless it's backend-driven wiring**.
> All backend work is in `backend/`. All WebSocket message types must stay compatible with `frontend/src/App.jsx`.

---

## 🏗️ Current Architecture (What Exists)

| File | Status | Notes |
|---|---|---|
| `backend/main.py` | ✅ Working | FastAPI + WebSocket `/ws`, memory CRUD, TTS via Cartesia, Gemini chat |
| `backend/agent_tools.py` | ✅ Working | Full Playwright browser agent, HITL, vision via Gemini, badge overlay, hackathon scout |
| `backend/memory.json` | ✅ Working | Flat JSON profile (name, email, phone, college, dept, rollNo) |
| `backend/requirements.txt` | ⚠️ Partial | Missing: `chromadb`, `sentence-transformers`, `tavily-python`, `httpx`, `beautifulsoup4` |
| `frontend/src/App.jsx` | ✅ Working | WS client, emotion dispatch, HITL routing, TTS playback |
| `frontend/src/components/HITLModal.jsx` | ✅ Working | Batch + single input HITL modal with countdown |
| `frontend/src/components/AvatarZone.jsx` | ✅ Working | 3D avatar zone |
| `frontend/src/components/MemoryPanel.jsx` | ✅ Working | Read/write memory UI |
| `frontend/src/components/NotepadPanel.jsx` | ✅ Working | Notes viewer (used for hackathon scout output) |
| `frontend/src/components/StorePage.jsx` | ✅ Working | Store/marketplace placeholder |

---

## 🎯 What the Demo MUST Show (Win Condition)

1. Browser agent fills a real form live (DOM badges visible)
2. Memory working (shows saved name/email/college etc.)
3. HITL interrupt firing (custom field → user input → agent resumes)
4. Sub-agent chip appearing (heartbeat animation, spawn/despawn)
5. Character reacting with emotion
6. *(Optional)* Research pipeline running

---

## 📋 Feature Checklist

### Backend Features

- [x] **WebSocket `/ws` endpoint** — `main.py` — fully working
- [x] **Gemini LLM routing** — `main.py` — working (chat intent, tool call detection)
- [x] **Memory CRUD API** — `GET/PUT /api/memory` — working
- [x] **TTS via Cartesia** — `POST /synthesize` — working
- [x] **Browser Agent (form filler)** — `agent_tools.py` — working with DOM overlay, vision, programmatic fill, HITL
- [x] **Hackathon Scout** — `agent_tools.py` — working (scrapes Unstop, saves to findings/)
- [x] **Notes CRUD API** — `GET/POST/DELETE /api/notes/:filename` — working
- [x] **HITL batch input** — sends `permission_request` with `inputType: batch_input` — working
- [x] **HITL single input** — sends `permission_request` with `inputType: input` — working
- [x] **HITL submit confirmation** — sends `permission_request` for form submission — working
- [x] **Stop task** — `stop_task` WS message cancels current asyncio task — working
- [ ] **Sub-agent orchestrator** — `agent_orchestrator.py` — **NOT BUILT** ← NEXT TO BUILD
- [ ] **Memory Layer 2 (ChromaDB episodic)** — `backend/memory.py` — **NOT BUILT** ← AFTER ORCHESTRATOR
- [ ] **Research Agent** — `backend/research.py` — **NOT BUILT** ← AFTER MEMORY
- [ ] **Planning Card backend** — emit `planning_card` WS message with structured plan — **NOT BUILT**
- [ ] **`agent_spawn` / `agent_heartbeat` / `agent_complete` WS messages** — needed for sub-agent chip UI

### Frontend Features (Agrani's Lane)

- [x] **Chat panel** — working
- [x] **Memory panel** — working
- [x] **HITL modal** — working (batch + single + boolean)
- [x] **Avatar emotion dispatch** — working via `aura:setEmotion` custom event
- [x] **TTS lip sync** — working via WebAudio analyser → `aura:setMorph` event
- [x] **Voice input (VoiceBar)** — working
- [x] **Task status log** — working (shows last 8 task_update messages)
- [ ] **Planning Card UI** — shows when `planning_card` WS message arrives ← Agrani
- [ ] **Sub-agent Chip UI** — shows agent name, step, heartbeat animation ← Agrani
- [ ] **Research Canvas** — renders ResearchResult.to_markdown() output ← Agrani
- [ ] **Form Canvas** (browser view embed) ← Agrani / not critical for demo

---

## 🔨 Build Order for Remaining Features

### PRIORITY 1: Sub-Agent Orchestrator + WS Messages (Backend)
**File:** `backend/agent_orchestrator.py` ← **CREATE NEW**
**File:** `backend/main.py` ← modify to import and route to orchestrator

Key: Emit `agent_spawn`, `agent_heartbeat`, `agent_complete` WS messages so the frontend chip can appear.
The browser agent (`fill_form_with_playwright`) already works — we just need to WRAP it in the orchestrator.

### PRIORITY 2: Planning Card Backend Emission
**File:** `backend/main.py` — when user asks for a web_task, emit `planning_card` before executing.
The frontend needs this message to show the approval flow.

### PRIORITY 3: Memory Layer 2 (ChromaDB episodic memory)
**File:** `backend/memory.py` ← **CREATE NEW**
Requires adding `chromadb` and `sentence-transformers` to requirements.txt

### PRIORITY 4: Research Agent
**File:** `backend/research.py` ← **CREATE NEW**
Requires adding `tavily-python`, `httpx`, `beautifulsoup4` to requirements.txt

---

## 🔄 WebSocket Message Protocol (Current)

### Frontend → Backend
```json
{ "type": "chat_message", "content": "string", "timestamp": "ISO" }
{ "type": "permission_response", "allowed": true/false }
{ "type": "permission_response", "allowed": true, "value": "string" }
{ "type": "permission_response", "allowed": true, "values": { key: val } }
{ "type": "stop_task" }
```

### Backend → Frontend (existing)
```json
{ "type": "chat_response", "content": "string" }
{ "type": "agent_thinking" }
{ "type": "task_update", "task": "string" }
{ "type": "permission_request", "title": "...", "description": "...", "id": "..." }
{ "type": "permission_request", "inputType": "input", "title": "...", "description": "...", "id": "..." }
{ "type": "permission_request", "inputType": "batch_input", "fields": [...], "id": "..." }
```

### Backend → Frontend (to be added for sub-agents)
```json
{ "type": "agent_spawn", "agentId": "string", "name": "string", "accentColor": "string" }
{ "type": "agent_heartbeat", "agentId": "string", "status": "string", "step": "string" }
{ "type": "agent_complete", "agentId": "string", "result": {} }
{ "type": "planning_card", "plan": { "id": "...", "summary": "...", "steps": [...] } }
```

---

## 📝 Key Implementation Notes

1. **`active_sessions` dict in `agent_tools.py`** is used for HITL synchronization. Don't change keys.
2. **`active_websockets` list in `agent_tools.py`** is shared for broadcasting. New tools must use `broadcast_status()`.
3. **`memory.json`** stores the flat user profile. Keys are sanitized by `sanitize_key_logic()` in `main.py`.
4. **Browser profile** is stored in `backend/browser_profile/` — persistent Chromium session.
5. **Gemini API key** is in `backend/.env`. Model: `gemini-1.5-flash` by default.
6. **Cartesia API key** is also in `backend/.env`.
7. **Port:** Backend runs on `8000`. Frontend Vite dev server on Tauri's embedded webserver.
8. **asyncio task pattern:** Always use `asyncio.create_task(...)` to run agent functions non-blocking.
9. **HITL pattern:** Set `active_sessions["event_name"] = asyncio.Event()`, broadcast `permission_request`, then `await event.wait()`.

---

## 🚀 Next Agent: Start Here

**Immediate next step:** Build `backend/agent_orchestrator.py` with:
- `AgentOrchestrator` class
- `spawn_agent(name, task_coro, websocket)` → sends `agent_spawn`, runs task, sends `agent_heartbeat` during, sends `agent_complete` when done
- Wrap the existing `fill_form_with_playwright` call in `main.py` to go through orchestrator
- Add `planning_card` emission for web_task intent before execution

After that: `backend/memory.py` (ChromaDB episodic), then `backend/research.py` (Tavily research pipeline).

**Do NOT rewrite existing working code.** Extend it.

---

## 📅 Timeline

| Date | Goal |
|---|---|
| June 11 (tonight) | ✅ Repo setup, browser agent, basic WS, memory working |
| June 12 | Sub-agent orchestrator + planning card + ChromaDB memory |
| June 13 | Research agent + integration test + full demo rehearsal |
| June 14 | Polish, error handling, demo recording, submission |
