import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import json
import re
import uuid
import time
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Dict, Any
import os
import sys
import tempfile
from pathlib import Path
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from cartesia import Cartesia

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

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
    from automation_engine import (
        detect_columns,
        draft_email_with_gemini,
        build_default_email_template,
        generate_certificates_batch,
        send_emails_batch,
        UPLOADS_DIR,
        OUTPUT_DIR as AUTO_OUTPUT_DIR,
    )
    AUTOMATION_AVAILABLE = True
except Exception as _auto_err:
    print(f"[ARIA] automation_engine import failed: {_auto_err}")
    AUTOMATION_AVAILABLE = False
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

# Local persistence path
MEMORY_FILE_PATH = Path(__file__).parent / "memory.json"

def sanitize_key_logic(k: str) -> str:
    # 1. Standard keys mapping (case-insensitive checks)
    k_lower = k.lower().strip()
    if "email" in k_lower or "e-mail" in k_lower or "mail id" in k_lower:
        return "email"
    elif "phone" in k_lower or "mobile" in k_lower or "contact" in k_lower or "tel" in k_lower or "number" in k_lower:
        if "roll" not in k_lower:
            return "phone"
    elif "roll" in k_lower or "reg" in k_lower or "registration" in k_lower or "id number" in k_lower:
        return "rollNo"
    elif "college" in k_lower or "university" in k_lower or "institute" in k_lower or "school" in k_lower:
        return "college"
    elif "dept" in k_lower or "department" in k_lower or "branch" in k_lower or "course" in k_lower or "stream" in k_lower:
        return "department"
    elif "name" in k_lower or "full name" in k_lower or "first name" in k_lower or "last name" in k_lower:
        if k_lower != "name":
            # Check if this matches a custom field (like father name, project name). If it has other words, treat as custom!
            words = [w for w in re.split(r'[^a-z]+', k_lower) if w]
            if len(words) == 1 or (len(words) == 2 and words[0] in ["full", "first", "last"]):
                return "name"
                
    # 2. General custom key sanitization
    clean = re.sub(r'[\s\xa0\u200b]+', ' ', k)
    clean = clean.replace('*', '')
    clean = clean.lower().strip()
    clean = re.sub(r'[^a-z0-9]+', '_', clean).strip('_')
    return clean

# Load memory from file
def load_memory() -> Dict[str, str]:
    if MEMORY_FILE_PATH.exists():
        try:
            with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
                raw_mem = json.load(f)
            
            sanitized_mem = {}
            dirty = False
            for k, v in raw_mem.items():
                clean_k = sanitize_key_logic(k)
                if clean_k != k:
                    dirty = True
                if clean_k:
                    # If duplicate clean key, keep the longer/non-empty value
                    if clean_k in sanitized_mem:
                        old_v = sanitized_mem[clean_k]
                        if not old_v and v:
                            sanitized_mem[clean_k] = v
                        elif v and len(str(v).strip()) > len(str(old_v).strip()):
                            sanitized_mem[clean_k] = v
                    else:
                        sanitized_mem[clean_k] = v
            
            # If any key was cleaned, save the sanitized version immediately to clean up memory.json!
            if dirty:
                try:
                    with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
                        json.dump(sanitized_mem, f, indent=4, ensure_ascii=False)
                except Exception as save_err:
                    print(f"Error auto-sanitizing memory.json: {save_err}")
            return sanitized_mem
        except Exception as e:
            print(f"Error loading memory: {e}")
    return {"name": "", "email": ""}

# Save memory to file
def save_memory(data: dict):
    try:
        # Sanitize keys before saving
        sanitized_data = {}
        for k, v in data.items():
            clean_k = sanitize_key_logic(k)
            if clean_k and v:
                sanitized_data[clean_k] = v
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(sanitized_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving memory: {e}")

MEMORY_STORE = load_memory()

@app.get("/api/memory")
def get_memory():
    global MEMORY_STORE
    MEMORY_STORE = load_memory()
    return MEMORY_STORE

@app.put("/api/memory")
def update_memory(data: dict):
    global MEMORY_STORE
    # Clean keys and filter out empty values
    MEMORY_STORE = {sanitize_key_logic(k): v for k, v in data.items() if v and sanitize_key_logic(k)}
    save_memory(MEMORY_STORE)
    return MEMORY_STORE

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
1. If the user asks you to perform an action (like filling a form or browsing a website) but does not provide a URL, you CAN guess the URL for well-known websites (like https://www.irctc.co.in or https://www.amazon.com) or just use https://www.google.com as a starting point.
2. DO NOT ask the user clarifying questions BEFORE launching the `browse_web` tool. If the user asks you to book a train ticket, search for a job, or buy a product, trigger the `browse_web` tool IMMEDIATELY with whatever information you have. The browser agent is intelligent and will ask the user for any missing details *during* the web session.
3. Only call other tools when you have all the specific information required to use them correctly.

RESPONSE FORMAT:
- For tool calls, respond with a single JSON object ONLY (no markdown), like:
    {"type":"tool_call","name":"fill_form_with_memory","args":{"url":"https://example.com"}}
- NEVER use [ACTION: tool_name] for executing tools! The [ACTION: ...] tags are STRICTLY for physical 3D avatar animations (like DANCE).
- If you need to trigger a tool, you MUST use the JSON format.
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

KNOWN_TOOL_NAMES = {"browse_web", "fill_form_with_memory", "deep_research", "scout_hackathons", "open_desktop_app", "open_website"}

def _extract_json_objects(text: str) -> list:
    results = []
    start_indices = [i for i, char in enumerate(text) if char == '{']
    for start in start_indices:
        brace_count = 0
        in_string = False
        escape = False
        for i in range(start, len(text)):
            char = text[i]
            if char == '"' and not escape:
                in_string = not in_string
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
            escape = (char == '\\' and not escape)
            
            if brace_count == 0 and not in_string:
                json_str = text[start:i+1]
                try:
                    obj = json.loads(json_str)
                    if isinstance(obj, dict):
                        results.append(obj)
                except Exception:
                    pass
                break
    return results

def _is_tool_shaped(data: dict) -> bool:
    """Check if a JSON object looks like a tool call vs random code JSON."""
    if data.get("type") == "tool_call" and "name" in data:
        return True
    t = data.get("type", "")
    if t in KNOWN_TOOL_NAMES:
        return True
    if "name" in data and data.get("name") in KNOWN_TOOL_NAMES and "args" in data:
        return True
    return False

def _parse_tool_call(text: str) -> dict | None:
    # 1. Extract all JSON objects and find the one that looks like a tool call
    objects = _extract_json_objects(text)
    
    # First pass: look for explicitly tool-shaped objects
    for data in objects:
        if not _is_tool_shaped(data):
            continue
        if data.get("type") == "tool_call" and "name" in data:
            return {"type": "tool_call", "name": data["name"], "args": data.get("args", {})}
        if data.get("type") in KNOWN_TOOL_NAMES:
            return {"type": "tool_call", "name": data["type"], "args": data.get("args", {})}
        if data.get("name") in KNOWN_TOOL_NAMES and "args" in data:
            return {"type": "tool_call", "name": data["name"], "args": data.get("args", {})}

    # 2. Fallback: Try parsing the stripped clean text
    clean = _strip_code_fences(text)
    if not clean.startswith("{") or not clean.endswith("}"):
        return None
    try:
        data = json.loads(clean)
        if isinstance(data, dict) and _is_tool_shaped(data):
            if data.get("type") == "tool_call" and "name" in data:
                return {"type": "tool_call", "name": data["name"], "args": data.get("args", {})}
            if data.get("type") in KNOWN_TOOL_NAMES:
                return {"type": "tool_call", "name": data["type"], "args": data.get("args", {})}
            if data.get("name") in KNOWN_TOOL_NAMES and "args" in data:
                return {"type": "tool_call", "name": data["name"], "args": data.get("args", {})}
    except Exception:
        pass

    return None

def _get_bedrock_client():
    try:
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
        aws_secret_access_key = os.getenv("AWS_SECRET_access_key", "").strip()
        if not aws_secret_access_key:
             aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
        region_name = os.getenv("AWS_REGION", "us-east-1").strip()
        
        if not aws_access_key_id or not aws_secret_access_key:
            return None
            
        client = boto3.client(
            service_name='bedrock-runtime',
            region_name=region_name,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
        )
        return client
    except Exception as e:
        print(f"[ARIA] Bedrock client error: {e}")
        return None

def _invoke_gemini_fallback(user_message: str, memory: dict, tools_context: list) -> dict:
    """Fallback LLM call using Gemini when Bedrock is unavailable."""
    global CHAT_HISTORY
    try:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return {"type": "text", "content": "[EMOTION: SAD] No LLM configured. Please set AWS keys or GEMINI_API_KEY in .env"}

        # Try google-genai SDK
        try:
            from google import genai as _genai
            client = _genai.Client(api_key=api_key)
            model_name = "gemini-2.0-flash"

            system_prompt = SYSTEM_PROMPT + f"\nUSER CONTEXT (Memory): {json.dumps(memory)}" + "\n\nTOOLS AVAILABLE:\n" + json.dumps(tools_context, indent=2)
            history_msgs = []
            for item in CHAT_HISTORY[-15:]:
                role = item["role"]
                if role == "model":
                    role = "assistant"
                parts = item.get("parts", [])
                text = parts[0] if parts and isinstance(parts[0], str) else ""
                history_msgs.append({"role": role, "parts": [{"text": text}]})
            history_msgs.append({"role": "user", "parts": [{"text": user_message}]})

            response = client.models.generate_content(
                model=model_name,
                contents=history_msgs,
                config={"system_instruction": system_prompt, "max_output_tokens": 800, "temperature": 0.3},
            )
            text_content = (response.text or "").strip()
        except Exception:
            # Try legacy google.generativeai SDK
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=api_key)
            model = genai_legacy.GenerativeModel(
                "gemini-1.5-flash",
                system_instruction=SYSTEM_PROMPT + f"\nUSER CONTEXT: {json.dumps(memory)}" + "\n\nTOOLS:\n" + json.dumps(tools_context, indent=2)
            )
            history_for_gemini = []
            for item in CHAT_HISTORY[-15:]:
                role = "model" if item["role"] in ["model", "assistant"] else "user"
                parts = item.get("parts", [])
                text = parts[0] if parts and isinstance(parts[0], str) else ""
                history_for_gemini.append({"role": role, "parts": [text]})
            chat = model.start_chat(history=history_for_gemini)
            response = chat.send_message(user_message)
            text_content = (response.text or "").strip()

        text_content = re.sub(r'<thinking>.*?</thinking>', '', text_content, flags=re.DOTALL | re.IGNORECASE).strip()
        text_content = re.sub(r'<thought>.*?</thought>', '', text_content, flags=re.DOTALL | re.IGNORECASE).strip()

        tool_call = _parse_tool_call(text_content)
        if tool_call:
            CHAT_HISTORY.append({"role": "user", "parts": [user_message]})
            CHAT_HISTORY.append({"role": "model", "parts": [f"[tool: {tool_call.get('name')}]"]})
            return {"type": "tool_call", "name": tool_call.get("name"), "args": tool_call.get("args", {})}

        CHAT_HISTORY.append({"role": "user", "parts": [user_message]})
        CHAT_HISTORY.append({"role": "model", "parts": [text_content]})
        if len(CHAT_HISTORY) > 30:
            CHAT_HISTORY = CHAT_HISTORY[-30:]
        return {"type": "text", "content": text_content}
    except Exception as e:
        print(f"[Gemini Fallback Error]: {e}")
        return {"type": "text", "content": f"[EMOTION: SAD] I encountered an error with the Gemini fallback: {e}"}


def invoke_llm(user_message: str, memory: dict) -> dict:
    global CHAT_HISTORY
    tools_context = [
        {
            "name": "fill_form_with_memory",
            "description": "Automatically opens a browser window and fills a web form using saved memory context (name, email, phone, college, department, roll number).",
            "args": {"url": "absolute HTTP/HTTPS URL"}
        },
        {
            "name": "browse_web",
            "description": "Opens ANY website in a real browser and performs any goal: scraping data, booking tickets, navigating pages, clicking buttons, searching, reading content, filling forms, interacting with any site. Use this for: opening IRCTC, booking trains, scraping news, checking prices, searching LinkedIn, anything on any website.",
            "args": {"url": "absolute HTTP/HTTPS URL of the starting page", "goal": "exactly what to do on this site (e.g. 'book a train ticket from Delhi to Mumbai', 'scrape latest news headlines', 'search for Python jobs')"}
        },
        {
            "name": "open_desktop_app",
            "description": "Opens desktop applications on Windows (notepad, calculator, paint, calendar, clock, alarm, cmd, explorer).",
            "args": {"app_name": "one of: notepad, calculator, paint, calendar, clock, alarm, cmd, explorer"}
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
        }
    ]

    # Augment system prompt with relevant episodic context if available
    episodic_context = ""
    if memory_mgr:
        try:
            past_episodes = memory_mgr.get_relevant_context(user_message, n_results=3)
            if past_episodes:
                episodic_context = "\n\nRELEVANT PAST EXPERIENCE:\n" + "\n".join(f"- {ep}" for ep in past_episodes)
        except Exception:
            pass

    system_prompt = SYSTEM_PROMPT + f"\nUSER CONTEXT (Memory): {json.dumps(memory)}" + episodic_context + "\n\nTOOLS AVAILABLE:\n" + json.dumps(tools_context, indent=2)
    client = _get_bedrock_client()
    if not client:
        # Fallback to Gemini when Bedrock is not configured
        print("[ARIA] Bedrock not configured — falling back to Gemini")
        return _invoke_gemini_fallback(user_message, memory, tools_context)

    try:
        model_name = os.getenv("LLM_MODEL", "amazon.nova-pro-v1:0").strip()
        history = CHAT_HISTORY[-15:]
        messages = []
        for item in history:
            role = item["role"]
            if role == "model":
                role = "assistant"
            
            # Combine parts into a single text string for Bedrock standard format
            text_parts = [p for p in item.get("parts", []) if isinstance(p, str)]
            if not text_parts:
                text_parts = [""]
            messages.append({"role": role, "content": [{"text": text_parts[0]}]})
            
        messages.append({"role": "user", "content": [{"text": user_message}]})
        
        system_prompts = [{"text": system_prompt}]
        
        response = client.converse(
            modelId=model_name,
            messages=messages,
            system=system_prompts,
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.3
            }
        )
        
        text_content = ""
        output_message = response.get('output', {}).get('message', {})
        for content_block in output_message.get('content', []):
            if 'text' in content_block:
                text_content += content_block['text']
                
        text_content = text_content.strip()

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
        print(f"Gemini Error: {e}")
        return {"type": "text", "content": f"[EMOTION: SAD] I ran into an error processing your request: {e}"}

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
            msg_type = await websocket.receive()
            if "text" in msg_type:
                data = json.loads(msg_type["text"])
                msg_type_str = data.get("type")
                
                if msg_type_str == "chat_message":
                    content = data.get("content", "")
                    print(f"[WS] User says: {content}")

                    # ── HITL interception: if an agent is waiting for user input,
                    # route this chat reply directly to the agent ────────────────
                    try:
                        from agent_tools import active_sessions
                        hitl_event = active_sessions.get("hitl_input")
                        if hitl_event and isinstance(hitl_event, asyncio.Event) and not hitl_event.is_set():
                            active_sessions["hitl_input_response"] = {"value": content, "allowed": True}
                            hitl_event.set()
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": f"[EMOTION: HAPPY] Got it! Continuing with: **{content}**",
                                "timestamp": data.get("timestamp")
                            })
                            continue
                    except Exception as _hitl_err:
                        print(f"[HITL interception error]: {_hitl_err}")
                    
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
                    response_data = await loop.run_in_executor(None, invoke_llm, content, MEMORY_STORE)
                    
                    if response_data.get("type") == "tool_call":
                        tool_name = response_data.get("name")
                        tool_args = response_data.get("args")
                        print(f"[WS] Tool call detected: {tool_name} with args: {json.dumps(tool_args)[:200]}")
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
                                    if not MEMORY_STORE.get(field)
                                ],
                            }
                            await websocket.send_json({"type": "planning_card", "plan": plan})

                            # Auto-approve immediately for now until frontend UI is ready
                            approved = True

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
                                    await orchestrator.spawn_agent(
                                        name="BrowserBot",
                                        coro=fill_form_with_playwright(form_url, MEMORY_STORE, websocket),
                                        websocket=websocket,
                                        accent_color="#10b981",
                                    )
                                else:
                                    asyncio.create_task(fill_form_with_playwright(form_url, MEMORY_STORE, websocket))

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

                        elif tool_name == "browse_web":
                            # ── Universal Web Browser Agent ────────────────────
                            browse_url = tool_args.get("url", "https://www.google.com")
                            browse_goal = tool_args.get("goal", "Browse and extract relevant information from this page")

                            # Ensure URL has scheme
                            if not browse_url.startswith("http"):
                                browse_url = "https://" + browse_url

                            # Build planning card for browser task
                            plan_id = str(uuid.uuid4())[:8]
                            plan = {
                                "id": plan_id,
                                "summary": f"Open {browse_url} and: {browse_goal}",
                                "steps": [
                                    {"id": 1, "label": "Launch Chromium browser with persistent session", "status": "pending"},
                                    {"id": 2, "label": f"Navigate to {browse_url}", "status": "pending"},
                                    {"id": 3, "label": "Analyze page with Gemini Vision", "status": "pending"},
                                    {"id": 4, "label": "Execute actions (click, type, scroll, scrape)", "status": "pending"},
                                    {"id": 5, "label": "Save results to Notepad if data extracted", "status": "pending"},
                                ],
                                "permissions": ["Open browser window", "Make web requests", "Read page content"],
                                "info_gaps": [],
                            }
                            await websocket.send_json({"type": "planning_card", "plan": plan})

                            # Auto-approve immediately for now until frontend UI is ready
                            approved = True

                            if not approved:
                                await websocket.send_json({
                                    "type": "chat_response",
                                    "content": "[EMOTION: HAPPY] No problem! I've cancelled the browser task.",
                                    "timestamp": data.get("timestamp")
                                })
                            else:
                                from agent_tools import browse_and_act
                                agent_id = str(uuid.uuid4())[:8]
                                response_text = f"[EMOTION: HAPPY] I'm launching WebAgent to open {browse_url} and {browse_goal.lower()}!"
                                await websocket.send_json({
                                    "type": "chat_response",
                                    "content": response_text,
                                    "timestamp": data.get("timestamp")
                                })

                                if orchestrator:
                                    await orchestrator.spawn_agent(
                                        name="WebAgent",
                                        coro=browse_and_act(browse_url, browse_goal, MEMORY_STORE, websocket, agent_id),
                                        websocket=websocket,
                                        accent_color="#3b82f6",
                                    )
                                else:
                                    async def _run_browse():
                                        await browse_and_act(browse_url, browse_goal, MEMORY_STORE, websocket, agent_id)
                                    asyncio.create_task(_run_browse())


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
        manager.disconnect(websocket)
        print("[WS] Client disconnected")
    except RuntimeError as e:
        if "disconnect message has been received" in str(e):
            manager.disconnect(websocket)
            print("[WS] Client disconnected (RuntimeError)")
        else:
            print(f"[WS] RuntimeError: {e}")
            manager.disconnect(websocket)
    except Exception as e:
        print(f"[WS] Unexpected error: {e}")
        manager.disconnect(websocket)
    finally:
        try:
            from agent_tools import active_sessions
            current_task = active_sessions.get("current_task")
            if current_task:
                print("[WS] Client disconnected: Cancelling active browser automation task.")
                current_task.cancel()
        except Exception:
            pass

# ── Automation Studio Endpoints ───────────────────────────────────────────────

@app.post("/api/automation/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload CSV, detect column roles, return header map + 5-row preview."""
    if not AUTOMATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Automation engine not available")
    csv_bytes = await file.read()
    # Save for later use
    save_path = UPLOADS_DIR / file.filename
    save_path.write_bytes(csv_bytes)
    result = detect_columns(csv_bytes)
    result["saved_path"] = str(save_path)
    return result


@app.post("/api/automation/upload-template")
async def upload_template(file: UploadFile = File(...)):
    """Upload certificate template image, return its served URL."""
    allowed_exts = {".png", ".jpg", ".jpeg"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed_exts:
        raise HTTPException(status_code=400, detail="Only PNG/JPG templates allowed")
    save_path = UPLOADS_DIR / file.filename
    save_path.write_bytes(await file.read())
    return {"saved_path": str(save_path), "url": f"/api/automation/template/{file.filename}"}


@app.get("/api/automation/template/{filename}")
async def serve_template(filename: str):
    """Serve uploaded template image."""
    if ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = UPLOADS_DIR / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    import mimetypes
    mime, _ = mimetypes.guess_type(str(path))
    return Response(content=path.read_bytes(), media_type=mime or "image/png")


class DraftEmailRequest(BaseModel):
    detected_cols: dict
    event_name: str = "our event"
    tone: str = "professional"

@app.post("/api/automation/draft-email")
async def draft_email(req: DraftEmailRequest):
    """Use Gemini to draft an HTML email template from detected CSV columns."""
    if not AUTOMATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Automation engine not available")
    # Try to get Gemini client
    gemini_client = None
    try:
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if api_key:
            from google import genai as _genai
            gemini_client = _genai.Client(api_key=api_key)
    except Exception:
        pass
    html = await draft_email_with_gemini(
        req.detected_cols, req.event_name, req.tone, gemini_client
    )
    return {"html": html}


class GenerateCertsRequest(BaseModel):
    csv_path: str
    template_path: str
    layout: dict
    output_dir: str = ""

@app.post("/api/automation/generate-certs")
async def generate_certs(req: GenerateCertsRequest, websocket_id: str = ""):
    """Batch-generate PDF certificates from CSV + template image + layout JSON."""
    if not AUTOMATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Automation engine not available")
    csv_path = Path(req.csv_path)
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"CSV not found: {req.csv_path}")
    csv_bytes = csv_path.read_bytes()

    # Find the active websocket to stream progress (first connected client)
    ws = manager.active_connections[0] if manager.active_connections else None

    out_dir = req.output_dir or str(AUTO_OUTPUT_DIR / "certificates")
    result = await generate_certificates_batch(
        csv_bytes=csv_bytes,
        template_img_path=req.template_path,
        layout=req.layout,
        output_dir=out_dir,
        websocket=ws,
    )
    return {"result": result, "output_dir": out_dir}


class SendEmailsRequest(BaseModel):
    csv_path: str
    subject: str
    html_template: str
    certs_base_dir: str = ""
    smtp_sender: str = ""
    smtp_password: str = ""
    name_col: str = "Member Name"
    team_col: str = "Team Name"
    email_col: str = "Email"

@app.post("/api/automation/send-emails")
async def send_emails_endpoint(req: SendEmailsRequest):
    """Batch send personalised emails (with cert attachments if available)."""
    if not AUTOMATION_AVAILABLE:
        raise HTTPException(status_code=503, detail="Automation engine not available")
    csv_path = Path(req.csv_path)
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail=f"CSV not found: {req.csv_path}")
    csv_bytes = csv_path.read_bytes()

    smtp_cfg = None
    if req.smtp_sender and req.smtp_password:
        smtp_cfg = {"sender": req.smtp_sender, "password": req.smtp_password}

    ws = manager.active_connections[0] if manager.active_connections else None

    result = await send_emails_batch(
        csv_bytes=csv_bytes,
        subject=req.subject,
        html_template=req.html_template,
        certs_base_dir=req.certs_base_dir or None,
        smtp_cfg=smtp_cfg,
        name_col=req.name_col,
        team_col=req.team_col,
        email_col=req.email_col,
        websocket=ws,
    )
    return {"result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

