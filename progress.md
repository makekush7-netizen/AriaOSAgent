# ARIA OS Agent - Project Progress & Understanding

## 1. Product Vision & Requirements (PRD)
ARIA (Agentic RPA Interface Assistant) is a downloadable desktop application that acts as a 3D animated companion and personal AI proxy. She executes multi-step computer tasks (filling forms, bulk emails, certificate generation, deep web research) autonomously using the user's own accounts.
- **Human-in-the-Loop (HITL):** ARIA never submits sensitive forms or executes critical actions without explicit user approval.
- **Local Privacy:** Personal memory, profile data, and conversation history remain stored locally on the user's machine.
- **Sub-Agent Delegation:** The main character delegates complex execution to child processes/workers (like `BrowserBot`, `ScriptRunner`, `ResearchBot`) so she remains responsive in the chat panel.
- **Memory Layers:**
  1. *Working Memory:* Session chat context.
  2. *Episodic Memory:* Semantic summaries of completed tasks stored in a local vector database (ChromaDB).
  3. *Semantic Profile:* Structured profile data (name, email, roll number, college) stored in a local JSON file for autofilling.

## 2. Design System & UI Specs
ARIA features a dark-themed, gold-accented visual environment that is designed to stand out.
- **Color Palette:** Layered dark backgrounds (`#0a0a0f` to `#1e1e2a`), signature gold accents (`#e8c97a`), and semantic state colors (teal, purple, coral, green, red).
- **Typography:** Display header font is Space Grotesk, body font is Inter, code canvas/logs use JetBrains Mono.
- **Visual Style:** Border glows, glassmorphism (`backdrop-filter` blur), and fluid micro-animations (e.g. SVG heartbeat lines, springy scale-up/scale-down of panels).
- **Application States:**
  - *Home State:* Character centered, desktop widgets active, chat panel collapsed.
  - *Conversation State:* Chat panel slides in, character turns to listen.
  - *Planning State:* Thinking animation, planning card with execution steps shown for user approval.
  - *Execution State:* Task Canvas takes over, character shrinks to a corner widget, sub-agent status chips appear.
  - *Completion State:* Canvas scales down, success particles burst, summary is delivered.
- **Morphing Canvas Zone:** Changes layout depending on active tasks: Form Canvas (Playwright browser preview + list of fields), Certificate Canvas (CSV upload + template + drag/drop fields), Research Canvas (synthesis + source cards), Email Blast Canvas (template editor + CSV table preview), Script Canvas (code viewer + logs).

## 3. Technical Architecture
ARIA is built as a three-process desktop app:
1. **Tauri Shell (Rust):** Window manager, transparent widget overlay on top of desktop, wake-word listener (Porcupine WASM/Rust), OTA updater.
2. **React Frontend (Vite + R3F):** Renders the 3D VRM avatar, state transitions, speech visualizer, and morphed canvases.
3. **Python FastAPI Sidecar:** Handles LLM routing, Playwright browser execution, ChromaDB semantic memory, Tavily web search, and Python script sandbox.

## 4. Current Test Version Assessment (`ARIA/` folder)
The copy-pasted `ARIA/` directory contains a functional prototype of the frontend and backend. Here is what exists:

### A. Backend (`backend_gemini/`)
- **FastAPI Server (`main.py`):**
  - Handles WebSocket communication on `/ws` (chat messages, agent status updates, permissions, HITL responses).
  - Handles local memory persistence (`memory.json`) and key-cleaning logic (normalizing variation of names like "mail id" -> "email").
  - Integrates with Gemini API (model `gemini-1.5-flash`) for intent routing and conversational responses.
  - Integrates with Cartesia API for high-quality Text-To-Speech generation.
  - Serves a notepad API for managing markdown documents in the `findings/` directory.
- **Browser Automation (`agent_tools.py`):**
  - Uses Playwright headed browser session with persistent user profile directories.
  - **`OVERLAY_JS`:** JavaScript element that injects yellow numeric badges (e.g., `[1]`, `[2]`) onto page inputs, buttons, and links.
  - **Gemini Vision Integration (`query_gemini_vision`):** Sends page screenshots and labeled overlay DOM text to Gemini to map memory items to corresponding badge numbers.
  - **Autofill Mechanism:** Performs programmatic autofills using standard inputs, visual clicks, or typing.
  - **HITL Verification:** Triggers input modals on the frontend when fields are missing, and alerts the user to confirm form submission before clicking the final submit button.
  - **Unstop Hackathon Scout:** A Playwright scraper that navigates `unstop.com` to gather hackathons and save them to a markdown file in findings.

### B. Frontend (`frontend/`)
- **React App (`src/`):**
  - **3D Avatar Viewer (`AvatarModel.jsx`, `AvatarZone.jsx`):** Renders 3D VRM characters with basic animations (idle breathing, lip-sync mapping TTS audio amplitude, custom Mixamo actions).
  - **Chat Panel (`ChatPanel.jsx`):** Conversation state interface.
  - **Voice & Visualizer (`VoiceBar.jsx`):** Speech input/output with waveform canvas pulsing.
  - **Memory Panel (`MemoryPanel.jsx`):** Form-based display of local memory details.
  - **Notepad (`NotepadPanel.jsx`):** Viewer for findings and markdown files.
  - **Skill Store (`StorePage.jsx`):** Placeholders for skill plugins.
  - **HITL Modal (`HITLModal.jsx`):** Renders overlay permission/input cards.

## 5. Next Steps / Migration Strategy
To begin building the production version:
1. **Import Codebase:** Copy the entire frontend and backend from the `ARIA/` test directory to the project root (`./frontend` and `./backend`).
2. **Setup Workspace Dependencies:** Verify dependencies, configure `.env` variables, and ensure Vite and FastAPI run smoothly in parallel.
3. **Align with v2.0 Execution Strategy:** Transition backend to support Tauri-sidecar requirements, refine the state management (Zustand), and expand the canvas views according to the design specification.
