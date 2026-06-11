# ARIA — Technical Architecture & Stack
### FAR AWAY 2026 | Version 2.0

---

## 1. Architecture Overview

ARIA is a three-process desktop application. Each process has a single responsibility and communicates over well-defined interfaces. No process blocks another.

```
┌─────────────────────────────────────────────────────────┐
│                    TAURI SHELL (Rust)                   │
│  Transparent window manager, system tray, wake word     │
│  OTA updater, IPC bridge, always-on-top widget mode     │
└──────────────┬──────────────────────┬───────────────────┘
               │                      │
               ▼                      ▼
┌──────────────────────┐   ┌─────────────────────────────┐
│   REACT FRONTEND     │   │   PYTHON FASTAPI SIDECAR    │
│   (Vite + R3F)       │◄──►   (Launched by Tauri)       │
│                      │   │                             │
│  - VRM Character     │   │  - Agent orchestration      │
│  - 5 UI States       │   │  - Playwright browser agent │
│  - Task Canvases     │   │  - ChromaDB memory          │
│  - WebSocket client  │   │  - Python sandbox           │
│  - Porcupine wake    │   │  - Research pipeline        │
│    word (WASM)       │   │  - LLM API calls            │
└──────────────────────┘   │  - Skill plugin loader      │
                           └─────────────┬───────────────┘
                                         │
                           ┌─────────────▼───────────────┐
                           │       AWS BACKEND           │
                           │  (Only when needed)         │
                           │                             │
                           │  - Bedrock Nova/Nova Pro    │
                           │  - OTA manifest.json        │
                           │  - Skill marketplace API    │
                           │  - User auth (if cloud plan)│
                           └─────────────────────────────┘
```

**Communication:**
- Tauri ↔ React: Tauri IPC commands (invoke/emit) for system-level operations
- React ↔ FastAPI: WebSocket for real-time streaming, REST for discrete requests
- FastAPI ↔ AWS: HTTPS with AWS SDK (boto3) or direct Bedrock API calls
- FastAPI ↔ ChromaDB: Local library call (in-process, no network)
- FastAPI ↔ Playwright: Async subprocess with event callbacks

---

## 2. Frontend Stack

### Core Framework
```
React 18 + Vite 5
Tailwind CSS (utility-first, no component libraries)
TypeScript (strict mode — no any types)
```

### 3D Avatar
```
@pixiv/three-vrm          # VRM model loading and bone control
Three.js (r155+)          # 3D rendering engine
@react-three/fiber        # React bindings for Three.js
@react-three/drei         # Helpers (environment, cameras)
```

The VRM model renders in a dedicated Three.js canvas. Emotion states are driven by VRM BlendShape proxies. The character's mouth opens/closes based on TTS audio amplitude sampled at 60fps using the Web Audio API's AnalyserNode.

**Emotion trigger map:**
```typescript
type EmotionState = 
  | 'idle'        // breathing, occasional blink, subtle sway
  | 'listening'   // slight head tilt, attentive expression
  | 'thinking'    // eyes slightly squinted, hand to chin anim
  | 'speaking'    // lip sync active, matching TTS waveform
  | 'executing'   // focused expression, slight lean forward
  | 'happy'       // smile blend shape, eye curve
  | 'error'       // concerned expression, head shake
  | 'success'     // full smile, small bounce animation
```

LLM responses contain inline emotion tags `[EMOTION:HAPPY]` that the frontend strips from display text and routes to the avatar controller.

### Wake Word
```
@picovoice/porcupine-web   # Runs as WASM in browser context
```
Porcupine runs in a Web Worker so it never blocks the main thread. On keyword detection, it fires a custom event that the React state machine catches and transitions to Conversation State. The wake word model file (`.ppn`) is bundled with the app and trained on the character's name.

### State Machine
The 5 application states are managed by a single Zustand store. State transitions are explicit — no implicit state leaks.

```typescript
type AppState = 'home' | 'conversation' | 'planning' | 'execution' | 'completion'

interface ARIAStore {
  appState: AppState
  activeCanvas: CanvasType | null
  activeAgents: SubAgentChip[]
  messages: Message[]
  userProfile: UserProfile
  transitionTo: (state: AppState, payload?: StatePayload) => void
}
```

### WebSocket Client
A single persistent WebSocket connection to FastAPI. All real-time updates (agent action stream, HITL interrupts, task progress, TTS audio chunks) come through this connection. The client auto-reconnects with exponential backoff.

```typescript
// Message types flowing over WebSocket
type WSMessage =
  | { type: 'agent_action'; payload: AgentAction }
  | { type: 'hitl_request'; payload: HITLRequest }
  | { type: 'tts_chunk'; payload: AudioChunk }
  | { type: 'state_change'; payload: { state: AppState } }
  | { type: 'task_complete'; payload: TaskResult }
  | { type: 'agent_spawn'; payload: SubAgentInfo }
  | { type: 'agent_heartbeat'; payload: { agentId: string; status: string } }
```

---

## 3. Backend Stack

### Runtime
```
Python 3.11+
FastAPI 0.111+          # Async web framework
Uvicorn                 # ASGI server
WebSockets (built-in)   # Real-time comms with frontend
```

### Browser Automation
```
playwright 1.44+        # Async Playwright for Chromium control
```

**Playwright architecture:**
- One persistent Chromium browser instance per session (not spawned per task)
- One browser context per site (maintains cookies, localStorage, session)
- Each task gets a fresh page within the existing context
- Browser window is embedded as a Tauri webview (on Windows: via WebView2) positioned in the Canvas area

**The OVERLAY_JS system (from existing ARIA — keep and extend):**
```javascript
// Injected into every page before LLM reads DOM
const OVERLAY_JS = `
  let counter = 1;
  const elements = document.querySelectorAll(
    'input, button, select, textarea, [role="button"], a[href]'
  );
  elements.forEach(el => {
    const badge = document.createElement('div');
    badge.setAttribute('data-aria-id', counter);
    badge.style.cssText = '...'; // absolute positioned badge
    badge.textContent = counter;
    el.parentNode.insertBefore(badge, el.nextSibling);
    el.setAttribute('data-aria-target', counter);
    counter++;
  });
`;
```

The LLM receives the DOM structure with `[data-aria-target]` labels and outputs actions like:
```json
{ "action": "type", "target": 3, "value": "{{email}}" }
{ "action": "click", "target": 7 }
{ "action": "select", "target": 12, "value": "Computer Science" }
```

### Memory — ChromaDB
```
chromadb 0.5+           # Local vector store, no server process needed
sentence-transformers   # Embedding model (all-MiniLM-L6-v2, 22MB, fast)
```

**Collection structure:**
```
chroma/
  episodes/     # Episodic memory - compressed task summaries
  profile/      # Semantic profile chunks
  skills/       # Skill descriptions for intent matching
```

**Profile JSON (Layer 3) — separate from ChromaDB, plain JSON:**
```json
{
  "name": "Kush Yadav",
  "email": "makewatch7@gmail.com",
  "phone": "7415074741",
  "college": "Acropolis Institute of Technology and Research",
  "department": "AIML",
  "roll_no": "0827AL241072",
  "frequent_sites": ["unstop.com", "devfolio.co"],
  "preferences": {
    "communication_style": "casual",
    "tts_voice": "nova_sonic_female",
    "character_skin": "default_girl"
  },
  "task_patterns": [],
  "last_updated": "ISO8601"
}
```

### Python Sandbox
```python
# Execution model — restricted subprocess
import subprocess
import sys

ALLOWED_IMPORTS = [
    'os', 'json', 'csv', 'datetime', 'pathlib',
    'requests', 'pandas', 'openpyxl', 'PIL',
    'smtplib', 'email', 'jinja2'
]

def execute_sandboxed_script(script_path: str, timeout: int = 60):
    result = subprocess.run(
        [sys.executable, '-u', script_path],
        capture_output=True,
        text=True,
        timeout=timeout,
        # Restrict network in future via iptables/firewall rule
    )
    return result.stdout, result.stderr
```

ARIA generates the script, writes it to a temp file, previews it in the Script Canvas, waits for user approval, then calls `execute_sandboxed_script`. Output streams line by line via the WebSocket.

### Research Agent
```
tavily-python           # Search API (free tier: 1000 calls/month)
httpx                   # Async HTTP client for page fetching
beautifulsoup4          # HTML parsing and content extraction
```

**Pipeline (async, parallel where possible):**
```python
async def research_pipeline(query: str) -> ResearchResult:
    # 1. Decompose query into 3-5 sub-questions (LLM call)
    sub_questions = await decompose_query(query)
    
    # 2. Run searches in parallel
    search_tasks = [tavily_search(q) for q in sub_questions]
    search_results = await asyncio.gather(*search_tasks)
    
    # 3. Fetch and extract top URLs in parallel
    fetch_tasks = [fetch_and_extract(url) for result in search_results 
                   for url in result.top_urls[:3]]
    page_contents = await asyncio.gather(*fetch_tasks, return_exceptions=True)
    
    # 4. Synthesize (single LLM call with all content)
    synthesis = await synthesize_findings(sub_questions, page_contents)
    
    # 5. Return structured result with citations
    return ResearchResult(synthesis=synthesis, sources=citations)
```

### AI Inference Layer
```
boto3                   # AWS SDK for Bedrock
anthropic               # Fallback / alternative
google-generativeai     # Gemini fallback (existing integration)
ollama                  # Local model runner
```

**Routing logic:**
```python
async def llm_call(prompt: str, task_type: LLMTaskType) -> str:
    if user_settings.privacy_mode or task_type.is_sensitive:
        return await call_ollama(prompt, model='qwen2.5:3b')
    
    if user_settings.own_api_key:
        return await call_bedrock_direct(prompt, user_settings.api_key)
    
    # Default: route through ARIA's AWS backend
    return await call_aria_cloud(prompt, task_type)
```

**Model assignment by task:**
- Intent classification, memory summarization → Ollama Qwen2.5 3B (local, fast)
- Vision/screenshot analysis → AWS Bedrock Nova Lite (cheap, fast) or Gemma 3 2B local
- Complex reasoning, planning, multi-step tasks → AWS Bedrock Nova Pro
- TTS → AWS Nova Sonic via Bedrock
- Embeddings → all-MiniLM-L6-v2 local (sentence-transformers, 22MB)

---

## 4. Desktop Shell — Tauri

```
Tauri 2.0
Rust (backend shell only — no Rust written by team, Tauri CLI handles it)
WebView2 (Windows built-in)
```

**Why Tauri over Electron:**
- Installer: ~8MB vs Electron's ~150MB
- RAM at idle: ~80MB vs ~300MB
- Built-in updater with code signing
- Native transparent frameless windows for floating widget mode
- System tray integration
- Tauri IPC allows the Rust shell to call Python sidecar and vice versa

**Key Tauri configurations:**

*Window modes:*
```json
{
  "windows": [
    {
      "label": "main",
      "title": "ARIA",
      "decorations": false,
      "transparent": false,
      "width": 1280,
      "height": 800
    },
    {
      "label": "widget",
      "title": "",
      "decorations": false,
      "transparent": true,
      "alwaysOnTop": true,
      "width": 300,
      "height": 400,
      "skipTaskbar": true
    }
  ]
}
```

*Sidecar (Python FastAPI):*
```json
{
  "bundle": {
    "externalBin": ["binaries/aria-backend"]
  }
}
```
The Python backend is compiled to a single executable via PyInstaller and bundled inside the Tauri app. It launches automatically on app start and terminates on app close.

**User data path (never touched by updates):**
```
Windows: %APPDATA%\ARIA\
  ├── memory.json           # Profile (Layer 3)
  ├── chroma/               # ChromaDB (Layer 2)
  ├── browser_profiles/     # Playwright session data per site
  ├── skills/               # Installed skill plugins
  ├── characters/           # Downloaded VRM skins
  └── settings.json         # App preferences
```

---

## 5. AWS Backend

Minimal surface area. Does two things: AI inference routing and content delivery.

**Services used:**
```
AWS Bedrock          # Nova Lite, Nova Pro, Nova Sonic
AWS Lambda           # Serverless inference proxy (no EC2 for Round 1)
AWS API Gateway      # HTTPS endpoint the local app calls
AWS S3               # Skill manifests, character packs, OTA update files
AWS CloudFront       # CDN for S3 assets
AWS Cognito          # User auth for cloud plan subscribers
```

**Inference proxy (Lambda):**
```python
# lambda_handler.py — receives from local app, calls Bedrock, returns result
def lambda_handler(event, context):
    user_id = verify_token(event['headers']['Authorization'])
    check_rate_limit(user_id)
    
    response = bedrock_client.invoke_model(
        modelId=event['body']['model'],
        body=json.dumps(event['body']['payload'])
    )
    
    return {
        'statusCode': 200,
        'body': response['body'].read()
    }
```

**OTA update manifest (S3):**
```json
{
  "version": "2.1.0",
  "platforms": {
    "windows-x86_64": {
      "url": "https://cdn.aria.app/releases/aria-2.1.0-windows.msi",
      "signature": "...",
      "sha256": "..."
    }
  },
  "skills_manifest_url": "https://cdn.aria.app/skills/manifest.json",
  "system_prompt_version": "42"
}
```

---

## 6. Skill Plugin Architecture

A skill is a self-contained module with three files:

```
skills/
  form_filler/
    manifest.json     # Metadata, version, permissions required
    tool_def.json     # Tool definition injected into LLM context
    handler.py        # Actual execution logic
```

**manifest.json:**
```json
{
  "id": "form_filler",
  "name": "Form Filler",
  "version": "1.2.0",
  "author": "ARIA Labs",
  "description": "Fills any web form using your profile memory.",
  "permissions": ["browser", "memory_read"],
  "canvas": "form_canvas",
  "price": 0
}
```

**tool_def.json** (injected into LLM's tool list at runtime):
```json
{
  "name": "fill_web_form",
  "description": "Navigate to a URL and fill all form fields using the user's memory profile. Use when user asks to register, apply, sign up, or submit any form.",
  "parameters": {
    "url": { "type": "string", "description": "The form URL" },
    "additional_context": { "type": "string", "description": "Any extra info user provided" }
  }
}
```

The `handler.py` is dynamically imported by the skill loader at runtime. Skills are sandboxed — they can only call the ARIA Agent API (a defined set of safe methods), not arbitrary Python.

---

## 7. Security Model

**What never leaves the device:**
- profile memory.json
- ChromaDB vector store
- Playwright browser session cookies/tokens
- Conversation history
- Any data the user marks as Private

**What can go to AWS (only on non-private tasks):**
- Task intent and prompt text (for LLM inference)
- Screenshot thumbnails (for vision tasks, if cloud vision is enabled)

**What the app never does:**
- Store or transmit passwords
- Run unreviewed code (all scripts shown to user before execution)
- Execute sensitive browser actions without explicit HITL approval
- Call any external API not declared in a skill's manifest.json

---

## 8. Performance Targets

| Metric | Target |
|---|---|
| App startup to ready | < 4 seconds |
| Wake word to listening state | < 200ms |
| DOM overlay injection | < 500ms |
| Form field autofill (known fields) | < 2 seconds |
| Memory retrieval (ChromaDB query) | < 100ms |
| LLM response start (streaming) | < 1.5 seconds |
| TTS first audio chunk | < 800ms |
| App idle RAM usage | < 120MB |
| App active RAM usage | < 400MB |
| Installer size | < 60MB |

---

## 9. Development Environment

```bash
# Prerequisites
Node.js 20+
Python 3.11+
Rust (stable) + Tauri CLI 2.0
Git

# Frontend
npm install
npm run dev          # Vite dev server on :5173

# Backend
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows
pip install -r requirements.txt
python main.py       # FastAPI on :8000

# Tauri (development mode — wraps the Vite dev server)
npm run tauri dev

# Tauri (production build)
npm run tauri build  # Outputs installer to src-tauri/target/release/bundle/
```

**Environment variables (.env, never committed):**
```
BEDROCK_API_KEY=           # Own-key mode
GEMINI_API_KEY=            # Fallback
ARIA_CLOUD_ENDPOINT=       # AWS API Gateway URL
TAVILY_API_KEY=            # Research agent
PORCUPINE_ACCESS_KEY=      # Wake word
```

---

## 10. Dependency Reference (requirements.txt)

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
websockets==12.0
playwright==1.44.0
chromadb==0.5.0
sentence-transformers==3.0.0
boto3==1.34.0
google-generativeai==0.7.0
httpx==0.27.0
beautifulsoup4==4.12.3
tavily-python==0.3.3
pandas==2.2.0
openpyxl==3.1.2
Pillow==10.3.0
jinja2==3.1.4
python-multipart==0.0.9
pydantic==2.7.0
python-dotenv==1.0.1
aiofiles==23.2.1
```
