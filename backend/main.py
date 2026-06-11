import json
import asyncio
import re
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
        }
    ]

    system_prompt = SYSTEM_PROMPT + f"\nUSER CONTEXT (Memory): {json.dumps(memory)}" + "\n\nTOOLS AVAILABLE:\n" + json.dumps(tools_context, indent=2)
    client = _get_gemini_client()
    if not client:
        return {"type": "text", "content": "[EMOTION: SAD] Gemini is not configured. Please set GEMINI_API_KEY."}

    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
        history = CHAT_HISTORY[-15:]
        contents = []
        for item in history:
            parts = [genai.types.Part.from_text(text=p) for p in item["parts"]]
            contents.append(genai.types.Content(role=item["role"], parts=parts))
        contents.append(genai.types.Content(role="user", parts=[genai.types.Part.from_text(text=user_message)]))
        
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_prompt,
            )
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
                    response_data = await loop.run_in_executor(None, invoke_gemini, content, MEMORY_STORE)
                    
                    if response_data.get("type") == "tool_call":
                        tool_name = response_data.get("name")
                        tool_args = response_data.get("args")
                        
                        if tool_name == "fill_form_with_memory":
                            form_url = tool_args.get("url")
                            await websocket.send_json({
                                "type": "task_update",
                                "task": "Launching browser agent..."
                            })
                            
                            from agent_tools import fill_form_with_playwright
                            
                            # Launch the form filler in a non-blocking background task so WS loop is completely responsive!
                            asyncio.create_task(fill_form_with_playwright(form_url, MEMORY_STORE, websocket))
                            
                            # Immediately send a chat response so ARIA speaks to the user while form filling happens!
                            response_text = "[EMOTION: HAPPY] I have launched my Google Form Filling Agent! I opened a Chromium browser using a secure, persistent local profile and am matching and autofilling the fields using the details in my memory. You can watch me fill it out live in the browser window! Once completed, I will present a confirmation prompt so we can submit it automatically."
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })
                        elif tool_name == "scout_hackathons":
                            query = tool_args.get("query", "hackathon")
                            await websocket.send_json({
                                "type": "task_update",
                                "task": "Scouting Unstop..."
                            })
                            
                            from agent_tools import scout_unstop_hackathons
                            asyncio.create_task(scout_unstop_hackathons(query, websocket))
                            
                            response_text = f"[EMOTION: HAPPY] I'm launching my Unstop Scout! I'm visually navigating to Unstop's competition page to search for active '{query}' hackathons. I will compile all hackathons I find into a beautifully formatted document in your Notepad tab. You can inspect it live in a few seconds!"
                            await websocket.send_json({
                                "type": "chat_response",
                                "content": response_text,
                                "timestamp": data.get("timestamp")
                            })
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
        from agent_tools import active_sessions
        current_task = active_sessions.get("current_task")
        if current_task:
            print("[WS] Client disconnected: Cancelling active browser automation task.")
            current_task.cancel()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

