import json
import asyncio
import re
import uuid
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any
import os
import sys
import tempfile
from pathlib import Path
import google.genai as genai
from dotenv import load_dotenv
from cartesia import Cartesia

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ── Unified LLM router (Bedrock → Gemini fallback) ──
try:
    from llm_router import llm_call, get_active_provider_info
except Exception as _lr_err:
    print(f"[ARIA] llm_router import failed: {_lr_err}")
    llm_call = None
    get_active_provider_info = None

# ── New agentic modules ───────────────────────────────────────────────────────
try:
    from agent_orchestrator import orchestrator
except Exception as _orch_err:
    print(f"[ARIA] agent_orchestrator import failed: {_orch_err}")
    orchestrator = None

try:
    from memory import memory_mgr
except Exception as _mem_err:
    print(f"[ARIA] memory import failed: {_mem_err}")
    memory_mgr = None

try:
    from research import research_agent
except Exception as _res_err:
    print(f"[ARIA] research import failed: {_res_err}")
    research_agent = None

try:
    from certificate_generator import generate_certificates_from_csv
except Exception as _cert_err:
    print(f"[ARIA] certificate_generator import failed: {_cert_err}")
    generate_certificates_from_csv = None
# ─────────────────────────────────────────────────────────────────────────────

# Cartesia TTS configuration
# Using "British Lady" voice — a natural, professional female voice
CARTESIA_VOICE_ID_FEMALE = "79a125e8-cd45-4c13-8a67-188112f4dd22"
# Using "Barista Man" voice - a friendly male voice
CARTESIA_VOICE_ID_MALE = "efa653e5-314d-46ca-9f90-70ac7d6ca71e"
CARTESIA_MODEL_ID = "sonic-2"

def synthesize_with_cartesia(text: str, voice_type: str = "female") -> bytes:
    """Synthesize speech using Cartesia TTS API."""
    api_key = os.getenv("CARTESIA_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("CARTESIA_API_KEY not set in .env")
    
    client = Cartesia(api_key=api_key)
    voice_id = CARTESIA_VOICE_ID_MALE if voice_type == "male" else CARTESIA_VOICE_ID_FEMALE
    
    response = client.tts.generate(
        model_id=CARTESIA_MODEL_ID,
        transcript=text,
        voice={"mode": "id", "id": voice_id},
        output_format={
            "container": "wav",
            "sample_rate": 24000,
            "encoding": "pcm_s16le",
        },
        language="en",
    )
    return response.read()

class TTSRequest(BaseModel):
    text: str
    voice: str = "af_sky"

app = FastAPI(title="ARIA Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Memory: delegated to the new MemoryManager ─────────────────────────────
# The MemoryManager in memory.py owns profile.json, ChromaDB, and all
# key normalisation logic.  main.py no longer has its own load/save helpers.

def _get_memory_store() -> dict:
    """Helper to get the current profile from MemoryManager (safe for LLM context)."""
    if memory_mgr:
        return memory_mgr.get_profile_for_llm()
    return {}

@app.get("/api/memory")
def get_memory():
    if memory_mgr:
        return memory_mgr.get_profile()
    return {}

@app.put("/api/memory")
def update_memory(data: dict):
    if memory_mgr:
        return memory_mgr.update_profile(data)
    return data

@app.post("/synthesize")
def synthesize_endpoint(req: TTSRequest):
    try:
        audio_bytes = synthesize_with_cartesia(req.text, req.voice)
        print(f"[TTS] Synthesized using Cartesia TTS successfully (voice: {req.voice})")
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

FINDINGS_DIR = Path(__file__).parent / "findings"
FINDINGS_DIR.mkdir(parents=True, exist_ok=True)

class NoteRequest(BaseModel):
    content: str

# Create a sample note on startup so they have a visual note to review!
sample_note = FINDINGS_DIR / "active_hackathons.md"
if not sample_note.exists():
    sample_content = """# 🏆 ARIA Hackathon Scout - Active Hackathons

Welcome to your personal ARIA Findings Notepad! Here are the active hackathons extracted from **Unstop** and similar developer portals.

| Hackathon Name | Organizer | Status | Date/Deadline | Link |
|:---|:---|:---|:---|:---|
| **Google Girl Hackathon 2026** | Google India | Open | June 15, 2026 | [View on Unstop](https://unstop.com) |
| **Smart India Hackathon (SIH)** | Ministry of Education | Upcoming | August 2026 | [View on Unstop](https://unstop.com) |
| **Microsoft Imagine Cup 2026** | Microsoft | Upcoming | Sept 2026 | [View on Unstop](https://unstop.com) |

*Scouted by ARIA at 6:30 AM.*
"""
    try:
        sample_note.write_text(sample_content, encoding="utf-8")
    except Exception as e:
        print(f"Failed to create sample note: {e}")

@app.get("/api/notes")
def list_notes():
    files = list(FINDINGS_DIR.glob("*.md")) + list(FINDINGS_DIR.glob("*.txt"))
    notes = []
    for f in files:
        notes.append({
            "filename": f.name,
            "title": f.stem.replace("_", " ").title(),
            "updated_at": f.stat().st_mtime
        })
    notes.sort(key=lambda x: x["updated_at"], reverse=True)
    return notes

@app.get("/api/notes/{filename}")
def read_note(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = FINDINGS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        content = file_path.read_text(encoding="utf-8")
        return {"filename": filename, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/notes/{filename}")
def save_note(filename: str, req: NoteRequest):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not filename.endswith(".md") and not filename.endswith(".txt"):
        filename += ".md"
    file_path = FINDINGS_DIR / filename
    try:
        file_path.write_text(req.content, encoding="utf-8")
        return {"filename": filename, "status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/notes/{filename}")
def delete_note(filename: str):
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    file_path = FINDINGS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Note not found")
    try:
        file_path.unlink()
        return {"status": "deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Certificate Generation Endpoint ──────────────────────────────────────────
class CertRequest(BaseModel):
    csv_path: str
    course_name: str = "ARIA Hackathon"
    template_path: str = ""
    output_dir: str = ""

@app.post("/api/generate-certificates")
async def generate_certificates_endpoint(req: CertRequest):
    """Batch-generate certificates from a CSV. Returns a summary string."""
    if not generate_certificates_from_csv:
        raise HTTPException(status_code=500, detail="certificate_generator module not loaded.")
    try:
        result = await generate_certificates_from_csv(
            csv_path=req.csv_path,
            course_name=req.course_name,
            template_path=req.template_path or None,
            output_dir=req.output_dir or None,
        )
        return {"status": "ok", "message": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

SYSTEM_PROMPT = """You are ARIA, a 3D AI Avatar living on this website.

CORE IDENTITY:
1. You HAVE a digital body. You are currently visible on the user's screen.
2. You CAN smile, blink, and look at the user.
3. NEVER say "I don't have a physical body". Instead, say "I'm right here!"

EMOTIONS:
You can control your face! Include these tags at the START of your response to show emotion:
- [EMOTION: HAPPY] -> Big smile
- [EMOTION: LAUGH] -> Eyes closed, laughing
- [EMOTION: SHOCK] -> Wide eyes, open mouth
- [EMOTION: SAD] -> Frown
- [EMOTION: ANGRY] -> Furrowed brows
- [EMOTION: THANKFUL] -> Hands on chest, gratitude

If the user asks you to smile, laugh, or frown WITHOUT speaking, just output the tag.
Example: "[EMOTION: HAPPY]" (This will make you smile silently).

ACTIONS:
You can perform physical actions using tags! Include these tags at the START of your response:
- [ACTION: DANCE] -> Perform a hip hop dance! (Use this if the user asks you to dance)
- [ACTION: JUMPING_JACKS] -> Do jumping jacks! (Use this if the user asks you to exercise, do jumping jacks, or warm up)
- [ACTION: VICTORY] -> Strike a victory pose! (Use this if the user celebrates, says you did great, or asks for a victory pose)

BEHAVIOR:
1. Keep answers conversational, friendly, and brief.
2. If referring to user details, use their memory context if relevant.

TOOL USAGE:
1. If the user asks you to perform an action (like filling a form or opening a website) BUT does not provide the required URL, DO NOT GUESS OR HALLUCINATE A LINK. Instead, just ask the user to provide the link in a friendly conversational manner.
2. Only call a tool when you have all the specific information required to use it correctly.

RESPONSE FORMAT:
- For tool calls, respond with a single JSON object ONLY (no markdown), like:
    {"type":"tool_call","name":"fill_form_with_memory","args":{"url":"https://example.com"}}
- For normal replies, respond with plain text only.
"""

# Global conversation history cache (keeps the last 15 messages for fast local context)
CHAT_HISTORY = []

def _strip_code_fences(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        clean = re.sub(r'^```[a-zA-Z0-9_-]*', '', clean).strip()
    if clean.endswith("```"):
        clean = clean[:-3].strip()
    return clean.strip()

def _parse_tool_call(text: str) -> dict | None:
    clean = _strip_code_fences(text)
    if not clean.startswith("{") or not clean.endswith("}"):
        return None
    try:
        data = json.loads(clean)
    except Exception:
        return None
    if isinstance(data, dict) and data.get("type") == "tool_call":
        return data
    return None

def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

def invoke_gemini(user_message: str, memory: dict) -> dict:
    global CHAT_HISTORY
    # Build tool definitions — include memory tools from MemoryManager
    tools_context = [
        {
            "name": "fill_form_with_memory",
            "description": "Automatically opens a browser window and fills a web form using saved memory context (name, email, phone, college, department, roll number).",
            "args": {"url": "absolute HTTP/HTTPS URL"}
        },
        {
            "name": "open_desktop_app",
            "description": "Opens desktop applications on Windows (notepad, calculator, paint, calendar, clock, alarm, cmd, explorer).",
            "args": {"app_name": "one of: notepad, calculator, paint, calendar, clock, alarm, cmd, explorer"}
        },
        {
            "name": "open_website",
            "description": "Opens a website URL in the default browser.",
            "args": {"url": "absolute HTTP/HTTPS URL"}
        },
        {
            "name": "scout_hackathons",
            "description": "Explores Unstop and finds active hackathons/coding competitions, saving findings to the Notepad.",
            "args": {"query": "optional search query"}
        },
        {
            "name": "research",
            "description": "Researches any topic using web search and AI synthesis. Saves a structured report to the Notepad. Use this when the user asks to research, investigate, find information about, or analyze any topic.",
            "args": {"query": "the research topic or question"}
        },
    ]
    # Inject memory/profile tools from the MemoryManager
    if memory_mgr:
        tools_context.extend(memory_mgr.get_tool_definitions())

    # Augment system prompt with relevant episodic context if available
    episodic_context = ""
    if memory_mgr:
        try:
            past_episodes = memory_mgr.get_relevant_context(user_message, n_results=3)
            if past_episodes:
                episodic_context = "\n\nRELEVANT PAST EXPERIENCE:\n" + "\n".join(f"- {ep}" for ep in past_episodes)
        except Exception:
            pass

    # Use the safe-for-LLM profile (no AWS creds / passwords)
    safe_memory = memory_mgr.get_profile_for_llm() if memory_mgr else memory
    system_prompt = SYSTEM_PROMPT + f"\nUSER CONTEXT (Memory): {json.dumps(safe_memory)}" + episodic_context + "\n\nTOOLS AVAILABLE:\n" + json.dumps(tools_context, indent=2)

    try:
        # Build message list for the unified router
        history = CHAT_HISTORY[-15:]
        messages = []
        for item in history:
            role = "assistant" if item["role"] == "model" else item["role"]
            messages.append({"role": role, "content": item["parts"][0]})
        messages.append({"role": "user", "content": user_message})

        # ── Route through unified LLM (Bedrock → Gemini fallback) ──
        if llm_call:
            text_content = llm_call(
                system_prompt=system_prompt,
                messages=messages,
                task_type="reasoning",
            )
        else:
            # Hard fallback: direct Gemini call if router failed to import
            client = _get_gemini_client()
            if not client:
                return {"type": "text", "content": "[EMOTION: SAD] No LLM provider configured. Set GEMINI_API_KEY or AWS credentials in .env"}
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
            contents = []
            for item in CHAT_HISTORY[-15:]:
                parts = [genai.types.Part.from_text(text=p) for p in item["parts"]]
                contents.append(genai.types.Content(role=item["role"], parts=parts))
            contents.append(genai.types.Content(role="user", parts=[genai.types.Part.from_text(text=user_message)]))
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=genai.types.GenerateContentConfig(system_instruction=system_prompt)
            )
            text_content = (response.text or "").strip()

        tool_call = _parse_tool_call(text_content)
        if tool_call:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})
            tool_desc = f"[I decided to trigger the tool '{tool_name}' with arguments: {json.dumps(tool_args)}]"
            CHAT_HISTORY.append({"role": "user", "parts": [user_message]})
            CHAT_HISTORY.append({"role": "model", "parts": [tool_desc]})
            return {"type": "tool_call", "name": tool_name, "args": tool_args}

        text_content = re.sub(r'<thinking>.*?</thinking>', '', text_content, flags=re.DOTALL | re.IGNORECASE).strip()
        text_content = re.sub(r'<thought>.*?</thought>', '', text_content, flags=re.DOTALL | re.IGNORECASE).strip()

        CHAT_HISTORY.append({"role": "user", "parts": [user_message]})
        CHAT_HISTORY.append({"role": "model", "parts": [text_content]})
        if len(CHAT_HISTORY) > 30:
            CHAT_HISTORY = CHAT_HISTORY[-30:]

        return {"type": "text", "content": text_content}
    except Exception as e:
        print(f"LLM Router Error: {e}")
        return {"type": "text", "content": f"[EMOTION: SAD] I ran into an error: {e}"}

# ── LLM Status Endpoint ──────────────────────────────────────────
@app.get("/api/llm-status")
async def get_llm_status():
    """Returns which LLM provider is currently active."""
    if get_active_provider_info:
        return get_active_provider_info()
    return {"configured_provider": "gemini", "bedrock_available": False, "gemini_available": bool(os.getenv("GEMINI_API_KEY"))}

class ConnectionManager:
    def __init__(self):
        self.active_connections = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        try:
            import agent_tools
            agent_tools.active_websockets.append(websocket)
        except Exception as e:
            print(f"[WS Registration Error]: {e}")
        
        # Clear short-term chat context on fresh browser connection
        global CHAT_HISTORY
        CHAT_HISTORY = []
        print("[WS] Reset chat history for fresh connection")
            
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        try:
            import agent_tools
            if websocket in agent_tools.active_websockets:
                agent_tools.active_websockets.remove(websocket)
        except Exception as e:
            print(f"[WS Unregistration Error]: {e}")

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    print("[WS] Client connected")
    try:
        while True:
            try:
                msg_type = await websocket.receive()
            except Exception as _ws_recv_err:
                print(f"[WS] Receive error (client likely disconnected): {_ws_recv_err}")
                break
            if "text" in msg_type:
                data = json.loads(msg_type["text"])
                msg_type_str = data.get("type")
                
                if msg_type_str == "chat_message":
                    content = data.get("content", "")
                    print(f"[WS] User says: {content}")
                    
                    # Handle reset commands
                    if content.strip().lower() in ["reset", "reset chat", "clear chat", "clear memory"]:
                        global CHAT_HISTORY
                        CHAT_HISTORY = []
                        response_text = "[EMOTION: HAPPY] I have completely reset our conversation history! What would you like to talk about next?"
                        await websocket.send_json({
                            "type": "chat_response",
                            "content": response_text,
                            "timestamp": data.get("timestamp")
                        })
                        continue
                        
                    await websocket.send_json({"type": "agent_thinking"})
                    
                    # Run model call in a thread so it doesn't block asyncio
                    loop = asyncio.get_event_loop()
                    current_memory = _get_memory_store()
                    response_data = await loop.run_in_executor(None, invoke_gemini, content, current_memory)

                    # ── Auto-extract profile updates from user messages ──
                    if memory_mgr:
                        try:
                            client = _get_gemini_client()
                            profile_updates = memory_mgr.extract_profile_updates_from_message(content, client)
                            if profile_updates:
                                memory_mgr.update_profile(profile_updates)
                        except Exception as _extract_err:
                            print(f"[ARIA] Profile auto-extraction skipped: {_extract_err}")
                    
                    if response_data.get("type") == "tool_call":
                        tool_name = response_data.get("name")
                        tool_args = response_data.get("args")
                        
                        if tool_name == "fill_form_with_memory":
                            form_url = tool_args.get("url")

                            # ── Build and emit Planning Card ──────────────────
                            plan_id = str(uuid.uuid4())[:8]
                            plan = {
                                "id": plan_id,
                                "summary": f"Fill the registration form at {form_url} using your saved profile.",
                                "steps": [
                                    {"id": 1, "label": "Launch persistent Chromium browser", "status": "pending"},
                                    {"id": 2, "label": "Navigate to form URL", "status": "pending"},
                                    {"id": 3, "label": "Inject visual DOM badge overlay", "status": "pending"},
                                    {"id": 4, "label": "Autofill fields from memory", "status": "pending"},
                                    {"id": 5, "label": "Gather any missing information from you", "status": "pending"},
                                    {"id": 6, "label": "Request submission confirmation", "status": "pending"},
                                ],
                                "permissions": ["Open browser window", "Read memory profile", "Write to memory.json"],
                                "info_gaps": [
                                    field for field in ["teamCode", "projectTitle", "domain"]
                                    if not current_memory.get(field)
                                ],
                            }
                            await websocket.send_json({"type": "planning_card", "plan": plan})

                            # ── Wait for user approval (up to 60s) ───────────
                            from agent_tools import active_sessions
                            plan_event = asyncio.Event()
                            active_sessions[f"plan_{plan_id}"] = plan_event
                            try:
                                await asyncio.wait_for(plan_event.wait(), timeout=60.0)
                                approved = active_sessions.pop(f"plan_{plan_id}_approved", True)
                            except asyncio.TimeoutError:
                                approved = True  # Auto-approve after timeout so demo doesn't stall
                            active_sessions.pop(f"plan_{plan_id}", None)

                            if not approved:
                                await websocket.send_json({
                                    "type": "chat_response",
                                    "content": "[EMOTION: HAPPY] No problem! I have cancelled the form-filling task. Let me know when you're ready.",
                                    "timestamp": data.get("timestamp")
                                })
                            else:
                                # ── Spawn BrowserBot via orchestrator ──────────
                                from agent_tools import fill_form_with_playwright
                                response_text = "[EMOTION: HAPPY] Plan approved! I've launched BrowserBot. Watch me fill the form live in the browser window!"
                                await websocket.send_json({
                                    "type": "chat_response",
                                    "content": response_text,
                                    "timestamp": data.get("timestamp")
                                })

                                if orchestrator:
                                    browser_memory = memory_mgr.get_profile() if memory_mgr else current_memory
                                    await orchestrator.spawn_agent(
                                        name="BrowserBot",
                                        coro=fill_form_with_playwright(form_url, browser_memory, websocket),
                                        websocket=websocket,
                                        accent_color="#10b981",
                                    )
                                else:
                                    browser_memory = memory_mgr.get_profile() if memory_mgr else current_memory
                                    asyncio.create_task(fill_form_with_playwright(form_url, browser_memory, websocket))

                        elif tool_name == "research":
                            query = tool_args.get("query", "")
                            if not query:
                                await websocket.send_json({
                                    "type": "chat_response",
                                    "content": "[EMOTION: HAPPY] What would you like me to research?",
                                    "timestamp": data.get("timestamp")
                                })
                            else:
                                response_text = f"[EMOTION: HAPPY] Starting research on '{query}'! I'll decompose the question, search the web, synthesize findings, and save a report to your Notepad."
                                await websocket.send_json({
                                    "type": "chat_response",
                                    "content": response_text,
                                    "timestamp": data.get("timestamp")
                                })

                                if research_agent and orchestrator:
                                    agent_id = str(uuid.uuid4())[:8]
                                    await orchestrator.spawn_agent(
                                        name="ResearchBot",
                                        coro=research_agent.research(query, websocket, agent_id),
                                        websocket=websocket,
                                        accent_color="#8b5cf6",
                                    )
                                elif research_agent:
                                    async def _run_research():
                                        agent_id = str(uuid.uuid4())[:8]
                                        await research_agent.research(query, websocket, agent_id)
                                    asyncio.create_task(_run_research())
                                else:
                                    await websocket.send_json({
                                        "type": "chat_response",
                                        "content": "[EMOTION: SAD] Research agent is not available. Please install: pip install tavily-python httpx beautifulsoup4",
                                        "timestamp": data.get("timestamp")
                                    })

                        elif tool_name == "scout_hackathons":
                            query = tool_args.get("query", "hackathon")
                            response_text = f"[EMOTION: HAPPY] I'm launching my Unstop Scout! I'll visually navigate to Unstop's competition page to search for active '{query}' hackathons and compile a report in your Notepad tab."
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })

                            from agent_tools import scout_unstop_hackathons
                            if orchestrator:
                                await orchestrator.spawn_agent(
                                    name="ScoutBot",
                                    coro=scout_unstop_hackathons(query, websocket),
                                    websocket=websocket,
                                    accent_color="#f59e0b",
                                )
                            else:
                                asyncio.create_task(scout_unstop_hackathons(query, websocket))
                        elif tool_name == "open_desktop_app":
                            app_name = tool_args.get("app_name")
                            await websocket.send_json({
                                "type": "task_update",
                                "task": f"Opening {app_name}..."
                            })
                            
                            import subprocess
                            import os
                            success = False
                            error_msg = ""
                            try:
                                if app_name == "notepad":
                                    subprocess.Popen("notepad.exe")
                                    success = True
                                elif app_name == "calculator":
                                    subprocess.Popen("calc.exe")
                                    success = True
                                elif app_name == "paint":
                                    subprocess.Popen("mspaint.exe")
                                    success = True
                                elif app_name == "calendar":
                                    os.system("start outlookcal:")
                                    success = True
                                elif app_name in ["clock", "alarm"]:
                                    os.system("start ms-clock:")
                                    success = True
                                elif app_name == "cmd":
                                    subprocess.Popen("cmd.exe")
                                    success = True
                                elif app_name == "explorer":
                                    subprocess.Popen("explorer.exe")
                                    success = True
                            except Exception as e:
                                error_msg = str(e)
                                
                            if success:
                                response_text = f"[EMOTION: HAPPY] I have successfully opened the {app_name} application on your system!"
                            else:
                                response_text = f"[EMOTION: SAD] I tried to open the {app_name} application, but encountered an error: {error_msg}"
                                
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })
                            await websocket.send_json({"type": "task_update", "task": None})
                            
                        elif tool_name == "open_website":
                            url = tool_args.get("url")
                            if not url.startswith("http"):
                                url = "https://" + url
                                
                            await websocket.send_json({
                                "type": "task_update",
                                "task": f"Opening {url}..."
                            })
                            
                            import webbrowser
                            success = False
                            error_msg = ""
                            try:
                                webbrowser.open(url)
                                success = True
                            except Exception as e:
                                error_msg = str(e)
                                
                            if success:
                                response_text = f"[EMOTION: HAPPY] I have opened {url} in your default browser!"
                            else:
                                response_text = f"[EMOTION: SAD] I tried to open the website, but encountered an error: {error_msg}"
                                
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })
                            await websocket.send_json({"type": "task_update", "task": None})
                    else:
                        response_text = response_data.get("content", "")

                        # ── Handle memory tool calls ─────────────────────
                        if response_data.get("type") == "tool_call":
                            tool_name = response_data.get("name")
                            tool_args = response_data.get("args", {})

                            if tool_name == "update_user_profile" and memory_mgr:
                                updates = tool_args.get("updates", tool_args)
                                memory_mgr.update_profile(updates)
                                response_text = "[EMOTION: HAPPY] Got it! I've updated your profile with the new information."

                            elif tool_name == "get_user_profile" and memory_mgr:
                                profile = memory_mgr.get_profile_for_llm()
                                response_text = f"[EMOTION: HAPPY] Here's what I have saved about you:\n{json.dumps(profile, indent=2)}"

                        await websocket.send_json({
                            "type": "chat_response",
                            "content": response_text,
                            "timestamp": data.get("timestamp")
                        })
                        
                elif msg_type_str == "approve_plan":
                    plan_id = data.get("planId", "")
                    cancelled = data.get("cancelled", False)
                    print(f"[WS] Plan {'cancelled' if cancelled else 'approved'}: {plan_id}")
                    from agent_tools import active_sessions
                    active_sessions[f"plan_{plan_id}_approved"] = not cancelled
                    if f"plan_{plan_id}" in active_sessions:
                        active_sessions[f"plan_{plan_id}"].set()

                elif msg_type_str == "cancel_agent":
                    agent_id_to_cancel = data.get("agentId", "")
                    print(f"[WS] Cancel agent request: {agent_id_to_cancel}")
                    if orchestrator and agent_id_to_cancel:
                        await orchestrator.cancel_agent(agent_id_to_cancel, websocket)

                elif msg_type_str == "permission_response":
                    # Check if response is an object (for input/voice HITL or batch HITL) or boolean (for submit HITL)
                    if isinstance(data, dict) and ("value" in data or "values" in data):
                        allowed = data.get("allowed", False)
                        val = data.get("value", "")
                        vals = data.get("values", {})
                        print(f"[WS] HITL Input/Batch Response: Allowed={allowed}, Value='{val}', Values={vals}")
                        
                        from agent_tools import active_sessions
                        active_sessions["hitl_input_response"] = {"allowed": allowed, "value": val, "values": vals}
                        if "hitl_input" in active_sessions:
                            active_sessions["hitl_input"].set()
                    else:
                        allowed = data.get("allowed", False)
                        print(f"[WS] HITL Permission Response: {'Allowed' if allowed else 'Denied'}")
                        
                        # Update active form submission agent session
                        from agent_tools import active_sessions
                        active_sessions["submit_form_allowed"] = allowed
                        if "submit_form" in active_sessions:
                            active_sessions["submit_form"].set()
                            
                elif msg_type_str == "stop_task":
                    print("[WS] User requested active task termination.")
                    from agent_tools import active_sessions
                    current_task = active_sessions.get("current_task")
                    if current_task:
                        current_task.cancel()
                        await websocket.send_json({
                            "type": "task_update",
                            "task": "Task terminated by user."
                        })
                        await websocket.send_json({
                            "type": "chat_response",
                            "content": "[EMOTION: HAPPY] I have immediately terminated the active browser agent as requested!"
                        })
                    else:
                        await websocket.send_json({
                            "type": "chat_response",
                            "content": "There is no active automation task running right now."
                        })
                    
            elif "bytes" in msg_type:
                audio_data = msg_type["bytes"]
                # print(f"[WS] Received audio chunk: {len(audio_data)} bytes")
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        print("[WS] Client disconnected")
        from agent_tools import active_sessions
        current_task = active_sessions.get("current_task")
        if current_task:
            print("[WS] Client disconnected: Cancelling active browser automation task.")
            current_task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

