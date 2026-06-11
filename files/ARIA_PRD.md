# ARIA — Product Requirements Document
### FAR AWAY 2026 | Theme: Agentic & Autonomous Systems
**Version:** 2.0 | **Team:** Endeavour | **Deadline:** June 14, 2026, 11:59 PM

---

## 1. Product Vision

ARIA (Agentic RPA Interface Assistant) is a downloadable desktop application that acts as a personal AI proxy for non-technical users. She lives on your desktop as a 3D animated companion, understands natural language commands, and autonomously executes complex multi-step computer tasks — browsing websites, filling forms, sending bulk emails, generating certificates, and conducting deep research — using the user's own accounts and identity.

**The one-liner:** *ARIA is your personal AI proxy. She lives on your desktop, uses your accounts, and does anything a human can do on a computer.*

ARIA is not a chatbot. ARIA is not a script runner. ARIA is the first consumer-grade OS-level agent with a persistent personality — built for the 500 million people automation tools have left behind.

---

## 2. The Problem

Powerful automation tools exist. None of them are for normal people.

- UiPath, Selenium, and Python scripts require programming knowledge most users don't have and can't afford to learn.
- Cloud AI agents (ChatGPT, Gemini) can reason but cannot touch your screen, use your accounts, or operate your software.
- Existing "AI assistants" have zero memory — you repeat yourself every single session.
- Cloud-only agents require uploading sensitive data (Aadhaar, bank details, passwords) to third-party servers.
- Users currently juggle 5+ different apps for tasks that one intelligent agent should handle end-to-end.

**The gap:** There is no product that combines genuine screen-level computer control, persistent personal memory, and a zero-coding interface accessible to a non-technical 40-year-old government employee or a first-year college student.

---

## 3. Target Users

**Primary:** Students, college applicants, hackathon participants — people who repeatedly fill the same forms, register for the same events, and send the same emails across dozens of platforms.

**Secondary:** Small business owners, freelancers, and government employees who handle repetitive data entry, bulk communication, and web-based administrative tasks daily.

**Tertiary:** Developers and power users who want a local, privacy-respecting agent they can extend with custom skills and run on their own hardware without a cloud subscription.

---

## 4. Core Product Principles

**P1 — Human stays in control.** ARIA never executes a sensitive action without explicit user approval. Every action is transparent, permission-gated, and narrated back to the user.

**P2 — Privacy is local.** Personal memory, Aadhaar numbers, banking info, and conversation history never leave the device. Sensitive tasks run entirely on local models. Only non-sensitive reasoning routes to the cloud.

**P3 — The character is part of the interface.** The 3D VRM companion is not decoration. It provides presence, personality, and emotional feedback. It is one of ARIA's primary differentiators.

**P4 — Zero friction to start.** A user downloads one installer. They get a working agent in under 5 minutes without configuring servers, installing Python, or understanding APIs.

**P5 — Infinitely extensible.** Skills can be added from a marketplace without reinstalling the app. The core agent stays lean; capabilities are layered on top.

---

## 5. Feature Specification

### 5.1 The Browser Agent (Core Feature — Round 1 Non-Negotiable)

ARIA operates an embedded Chromium browser (Playwright headed mode) that is fully visible inside the application window. The user can watch the cursor move and actions happen in real time.

**Operation Modes:**

*DOM Mode (Primary):* ARIA injects a JavaScript overlay onto the active page that tags every interactive element (inputs, buttons, dropdowns, checkboxes) with a numbered badge `[1]`, `[2]`, etc. The LLM reads the labeled DOM structure and outputs a sequence of actions referencing badge IDs. Autofill runs against these IDs. This is fast, reliable, and the default mode.

*Vision Mode (Fallback):* When DOM mode fails (complex SPAs, canvas elements, dynamically rendered UIs), ARIA takes a screenshot, sends it to a vision-capable model, receives coordinates and actions, and executes them via Playwright's mouse and keyboard APIs. Cursor movement is real — it looks like a human operating the machine.

*Hybrid Execution:* DOM mode runs first. If confidence score from the LLM is below threshold, or if action fails, the system automatically falls back to Vision mode. The user never manually selects a mode.

**What it can do:**
- Fill any web form using profile memory without user input for known fields
- Navigate multi-page flows (registration → confirmation → submission)
- Book tickets (flight, train, tatkal) through the user's own logged-in account
- Scroll, click, hover, type, select dropdowns, upload files
- Handle dynamic content that loads asynchronously
- Pause mid-task and ask the user for missing information via HITL modal
- Stream live narration of every action back to the chat panel

**User login model:** The user logs into any website inside ARIA's Chromium window using their own credentials. ARIA never stores, reads, or transmits passwords. The browser maintains persistent session profiles per site, stored locally.

### 5.2 The Memory System

Three independent layers that work together:

**Layer 1 — Working Memory (Session Context)**
The active conversation window. Last 15 messages. Discarded at session end. Used for natural back-and-forth mid-task.

**Layer 2 — Episodic Memory (What Happened)**
After every completed task, a lightweight LLM call generates a compressed semantic summary: what was done, what data was used, what the user corrected. Stored as vector embeddings in a local ChromaDB instance. Retrieved semantically — not by keyword. When a new task starts, the top 3–5 relevant episodes are pulled and injected as context. The user never fills in the same field twice.

**Layer 3 — Semantic Profile (Who the User Is)**
A structured JSON object that actively updates as conversations happen. Contains: name, email, phone, college, roll number, frequently visited sites, common task patterns, shortcuts the user has defined, preferred communication style. This layer never grows large — it is continuously condensed. When the user says "my usual email," ARIA already knows.

**Memory retrieval:** No full dumps. On every new message, the incoming query is embedded and matched against ChromaDB. Only the top-N relevant chunks are injected into the LLM context. Fast, cheap, and accurate.

### 5.3 Sub-Agent Architecture

ARIA (the main model) stays in the conversation at all times. She does not get consumed by task execution. When a task requires sustained autonomous work, ARIA deploys a named child agent and delegates.

**How it works:**
1. User issues a command: *"Fill out 15 hackathon registration forms on Unstop for me."*
2. ARIA understands intent, builds an execution plan, presents it to the user for approval.
3. User approves. ARIA says: *"I've deployed FormRunner to handle this. I'll stay here if you need anything."*
4. A floating sub-agent chip appears in the UI showing the agent's name, status, and a live heartbeat activity line.
5. The child agent executes the task in a separate process. ARIA remains fully available for conversation.
6. Child agent completes or encounters a blocker → sends a HITL interrupt → ARIA surfaces it as a message.
7. On completion, the chip closes and ARIA delivers the summary.

**Sub-agent types (Round 1):**
- `BrowserBot` — handles all Playwright web navigation tasks
- `ScriptRunner` — executes Python scripts in the sandboxed environment
- `ResearchBot` — runs the multi-step web research pipeline

Sub-agents are named by the user on first use and remembered. The user can rename them, give them custom personalities, or replace them with marketplace versions.

### 5.4 Python Sandbox

A sandboxed Python execution environment (subprocess with restricted imports) where ARIA can write, preview, and run automation scripts for tasks that don't require a browser.

**Capabilities:**
- Bulk email sending via CSV (name + email + template variables)
- Bulk certificate generation (template image + CSV → output folder of named PDFs)
- Data transformation and spreadsheet operations (pandas, openpyxl)
- File operations (rename, move, organize, compress)
- HTTP requests and API calls (requests library)

**Safety model:**
- ARIA generates the script
- Script is shown to user in a code preview panel before execution
- User explicitly approves with one click (HITL)
- Execution runs in restricted subprocess with no network access unless explicitly granted
- Output streams back line by line to the chat panel

### 5.5 Research Agent

A multi-step autonomous research pipeline that operates differently from browser automation — it is headless, fast, and focused on information gathering rather than UI interaction.

**Pipeline:**
1. Parse research query into sub-questions
2. Run parallel searches via Tavily API (or Serper fallback)
3. Fetch top 3–5 URLs per sub-question via headless Playwright or direct HTTP
4. Extract clean text content, strip boilerplate
5. Synthesize findings across sources using LLM
6. Generate structured output with citations, source URLs, confidence levels
7. Deliver to the Research Canvas with expandable source cards

**Output:** A Research Canvas panel showing findings organized by sub-question, with collapsible source evidence for each claim. The user can export as Markdown or PDF.

### 5.6 Task Canvas System

The Canvas is the actual product interface for task execution. It is not a fixed panel — it morphs based on what task is active. The Canvas behaves like a mini application: draggable, resizable, dockable to any screen edge.

**Form Canvas:** Live browser preview + list of fields about to be filled + inline approval toggles + HITL interrupt area. User can override any individual field before ARIA proceeds.

**Certificate Canvas:** Template image upload zone + CSV/spreadsheet drop zone + font selector + position picker with live preview overlay + export settings. User sees exactly what each certificate will look like before the batch runs.

**Research Canvas:** Sub-question breakdown + source cards with expandable evidence + synthesis panel + export controls. Sources are ranked by credibility score.

**Email Blast Canvas:** Email template editor (with variable placeholders like `{{name}}`, `{{college}}`) + CSV upload for recipient list + preview of first 3 emails + send controls with rate-limit settings.

**Script Canvas:** Code preview panel + execution output stream + error highlighting + re-run button. Used when ScriptRunner is active.

### 5.7 Wake Word & Voice

Software wake word using Porcupine (Picovoice — free tier, runs locally at ~2% CPU, always listening). The user names their agent and trains the wake word to that name. When ARIA hears her name, she activates and opens the conversation interface.

Voice input: Web Speech API (browser-native, no cost, good accuracy for Indian English).

Voice output: AWS Nova Sonic (primary, via Bedrock) for high-quality realistic TTS. Cartesia TTS (secondary, existing integration) as fallback. The voice persona matches the selected character skin.

### 5.8 The Skill Marketplace

A built-in store where users browse, install, and activate skill plugins. Skills are modular capability extensions — they add new tool definitions to ARIA's agent brain and new Canvas layouts for their task types.

**On install:** The skill's tool definition JSON is downloaded, validated, and registered with the local FastAPI backend. No app restart required.

**Skill categories:** Browser automation scripts for specific websites (LinkedIn auto-apply, Swiggy bulk ordering), software integrations (Blender controller, Photoshop batch processor), workflow templates (daily briefing, meeting notes), and character skin packs.

**Marketplace architecture:** Skills are served from ARIA's AWS backend as JSON manifests + Python tool files. The app checks for updates on startup. Skills auto-update silently unless the user has pinned a version.

### 5.9 OTA Updates

The Tauri built-in updater handles binary updates. App data (ChromaDB, memory.json, installed skills, user settings, session profiles) lives in `%APPDATA%/ARIA` on Windows, completely separated from the app binary. Updates never touch user data.

Skills, system prompts, and UI config can be pushed as JSON/config-only updates without a full binary release — the app pulls a `manifest.json` from AWS on startup and hot-reloads changed configs.

### 5.10 AI Inference Model

**Cloud plan (default):** User creates an ARIA account. API calls route through ARIA's AWS backend → AWS Bedrock → Nova Pro (reasoning) / Nova Lite (fast tasks). ARIA team controls model access, rate limits, and billing. Users pay a subscription.

**Own API key (privacy mode):** User provides their own Bedrock API key or Gemini API key. All calls go directly from the local FastAPI sidecar to the model provider. Zero data touches ARIA's servers.

**Local model (offline/sensitive mode):** Ollama running Qwen2.5 3B or Phi-3 Mini handles memory summarization, simple intent classification, and any task the user marks as "private." Gemma 3 2B handles vision fallback locally. Cloud models are not called for these tasks.

---

## 6. Application States (from Design Findings)

The application does not have pages. It has states. Each state has a defined visual configuration.

**Home State:** Character centered, background world visible, widget layer active (clock, active task chip, quick actions). Chat panel collapsed. The environment feels like a personal space, not a SaaS dashboard.

**Conversation State:** Triggered by wake word, click, or voice. Chat panel slides in. Character animates responsively (listening, thinking, speaking). Does not permanently occupy half the screen.

**Planning State:** Triggered when ARIA identifies a multi-step task. Character steps aside slightly. A planning card appears showing goal understanding, execution plan, required permissions, required information gaps. User approves or modifies before anything executes.

**Execution State:** Task Canvas occupies the main area. Character shrinks to a corner widget. Sub-agent chips appear. Agent action log streams in real time. Character reacts to events (success, error, waiting).

**Completion State:** Canvas closes with a subtle animation. Character returns to center. ARIA delivers a verbal + text summary of what happened, files generated, and results. Returns to Home State.

---

## 7. What We Are NOT Building for Round 1

The following are confirmed roadmap items to mention in the pitch but not build before June 14:

- Hardware wake word dongle
- Mobile companion app
- Multi-language support
- Enterprise SSO / team memory
- Full marketplace with community-submitted skills (we ship with 5 first-party skills)
- Linux and macOS builds (Windows only for Round 1)
- Parallel multi-tab browser execution

---

## 8. Success Metrics for Demo

The Round 1 submission must demonstrate all of the following working live or in video:

1. Wake word activates ARIA by name
2. Voice command triggers browser agent on a real website
3. DOM overlay badges appear visibly on screen
4. ARIA autofills known fields from memory without asking
5. HITL modal fires for an unknown field, user fills it, automation resumes
6. Sub-agent chip appears with heartbeat during execution
7. Completion summary delivered by voice + text
8. Memory panel shows correctly updated profile after task
9. At least one Canvas (Form Canvas minimum, Certificate Canvas preferred as second)
10. The character visibly reacts with different emotion states throughout the flow

---

## 9. Competitive Positioning

| | ARIA | UiPath | Claude Computer Use | Rabbit R1 |
|---|---|---|---|---|
| No coding required | ✅ | ❌ | ❌ | ✅ |
| Persistent memory | ✅ | ❌ | ❌ | ❌ |
| Local privacy mode | ✅ | ❌ | ❌ | ❌ |
| Visible character/personality | ✅ | ❌ | ❌ | ⚠️ |
| Extensible skill marketplace | ✅ | ✅ | ❌ | ❌ |
| Works with user's existing accounts | ✅ | ⚠️ | ⚠️ | ❌ |
| Runs on consumer hardware | ✅ | ❌ | ❌ | ✅ (dedicated) |
| One-click installer | ✅ | ❌ | ❌ | N/A |

---

## 10. Roadmap

**Phase 1 (0–3 months) — MVP:** Core agent end-to-end, form fill, bulk email, certificate generation, research agent, marketplace UI with 5 first-party skills, local memory, Nova Sonic voice.

**Phase 2 (3–6 months) — Skill Ecosystem:** Developer SDK, open marketplace, Tauri desktop wrapper with true OS-level window access, mobile companion app for monitoring running agents.

**Phase 3 (6–12 months) — Enterprise:** Multi-agent orchestration across team members, white-label deployment, SAP and Salesforce integrations, government portal skills.

**Phase 4 (1–2 years) — Global Platform:** International language support, 1000+ community skills, hardware partnerships, Series A funding target.
