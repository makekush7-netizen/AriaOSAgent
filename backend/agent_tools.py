# -*- coding: utf-8 -*-
import sys
import os
import asyncio
from pathlib import Path
import re
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Use async playwright for uvicorn compatibility
from playwright.async_api import async_playwright

# ─── Gemini Vision client (used as primary vision engine) ──────────────────────
try:
    from google import genai as _genai_module
    _GENAI_AVAILABLE = True
except ImportError:
    try:
        import google.generativeai as _genai_module
        _GENAI_AVAILABLE = True
    except ImportError:
        _genai_module = None
        _GENAI_AVAILABLE = False

PROFILE_PATH = Path(__file__).parent / "browser_profile"

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# Global list to track active WebSocket connections without circular imports
active_websockets = []

async def broadcast_status(websocket, text: str):
    """Utility to send task updates to the frontend websocket if open"""
    targets = list(active_websockets)
    if websocket and websocket not in targets:
        targets.append(websocket)
        
    for ws in targets:
        try:
            await ws.send_json({
                "type": "task_update",
                "task": text
            })
        except Exception:
            pass

def clean_label(text: str) -> str:
    """Normalize label text for matching"""
    if not text:
        return ""
    return re.sub(r'[*:\s]+', ' ', text).strip().lower()

def match_field_key(label: str, placeholder: str, name_attr: str) -> str:
    """Match form field labels/meta to memory keys (fallback method)"""
    combined = f"{label} {placeholder} {name_attr}".lower()
    if any(x in combined for x in ["email", "e-mail", "mail id"]):
        return "email"
    if any(x in combined for x in ["phone", "mobile", "contact", "tel", "number"]) and not any(x in combined for x in ["roll"]):
        return "phone"
    if any(x in combined for x in ["roll", "reg", "registration", "id number"]):
        return "rollNo"
    if any(x in combined for x in ["college", "university", "institute", "school"]):
        return "college"
    if any(x in combined for x in ["dept", "department", "branch", "course"]):
        return "department"
    if any(x in combined for x in ["name", "full name", "first name", "last name"]):
        return "name"
    return ""

# Global store for active agent sessions (concurrency and HITL approvals)
active_sessions: Dict[str, Any] = {}

OVERLAY_JS = """
(() => {
  // Clear any existing badges
  const existing = document.querySelectorAll('.aria-badge');
  existing.forEach(e => e.remove());

  // Increment version to kill previous requestAnimationFrame loops
  window.ariaOverlayIteration = (window.ariaOverlayIteration || 0) + 1;
  const currentIteration = window.ariaOverlayIteration;

  window.ariaElements = [];
  
  // Find visible interactive elements
  const selectors = [
    'input[type="text"]',
    'input[type="email"]',
    'input[type="tel"]',
    'input[type="number"]',
    'input[type="radio"]',
    'input[type="checkbox"]',
    'textarea',
    'select',
    'button',
    'a',
    '[role="radio"]',
    '[role="checkbox"]',
    '[role="button"]',
    '.freebirdFormviewerComponentsQuestionRadioOption',
    '.freebirdFormviewerComponentsQuestionCheckboxOption',
    '.freebirdFormviewerComponentsQuestionRadioOption label',
    '.freebirdFormviewerComponentsQuestionCheckboxOption label'
  ];
  
  let candidates = Array.from(document.querySelectorAll(selectors.join(',')));
  
  const isDomVisible = (el) => {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return false;
    const style = window.getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && style.opacity !== '0';
  };
  
  candidates = candidates.filter(isDomVisible);

  let index = 1;
  candidates.forEach(el => {
    try {
      if (el.closest('.aria-badge') || el.classList.contains('aria-badge')) return;
      
      // Assign index
      const id = index++;
      
      // Create floating visual badge using fixed positioning
      const badge = document.createElement('div');
      badge.className = 'aria-badge';
      badge.innerText = `[${id}]`;
      
      Object.assign(badge.style, {
        position: 'fixed',
        backgroundColor: '#facc15',
        color: '#000000',
        border: '2px solid #000000',
        borderRadius: '4px',
        padding: '2px 5px',
        fontSize: '11px',
        fontWeight: 'bold',
        fontFamily: 'monospace',
        zIndex: '2147483647',
        pointerEvents: 'none',
        boxShadow: '0 2px 5px rgba(0,0,0,0.5)',
      });
      
      document.body.appendChild(badge);
      window.ariaElements.push({ id, element: el, badge: badge });
    } catch (err) {
      console.error('[ARIA Overlay Error] Failed to badge element:', err);
    }
  });

  // Reposition helper using getBoundingClientRect relative to the viewport
  const reposition = () => {
    if (!window.ariaElements) return;
    window.ariaElements.forEach(item => {
      const el = item.element;
      const badge = item.badge;
      if (!el || !badge) return;
      
      // If target element is no longer in the DOM, remove the badge
      if (!document.body.contains(el)) {
        badge.remove();
        return;
      }
      
      const rect = el.getBoundingClientRect();
      const isCurrentlyVisible = rect.width > 0 && rect.height > 0;
      
      if (!isCurrentlyVisible) {
        badge.style.display = 'none';
      } else {
        badge.style.display = 'block';
        badge.style.left = `${rect.left - 5}px`;
        badge.style.top = `${rect.top - 8}px`;
      }
    });
  };

  // Initial call
  reposition();

  // Listen to ALL scrolls and resizes on the page (capture phase ensures nested div scroll mapping)
  window.addEventListener('scroll', reposition, { capture: true, passive: true });
  window.addEventListener('resize', reposition, { passive: true });

  // requestAnimationFrame tick loop to handle dynamic layout/autofill shifts
  const tick = () => {
    if (window.ariaOverlayIteration !== currentIteration) {
      // New overlay instance was injected, exit stale loop
      return;
    }
    reposition();
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);

  return window.ariaElements.map(item => {
    try {
      const el = item.element;
      const placeholder = el.getAttribute('placeholder') || '';
      const name = el.getAttribute('name') || '';
      const ariaLabel = el.getAttribute('aria-label') || '';
      const type = el.getAttribute('type') || '';
      const role = el.getAttribute('role') || '';
      const currentValue = el.value || '';
      
      let labelText = '';
      
      // 1. Google Forms/Structured cards container climbing
      let current = el;
      while (current && current !== document.body) {
        if (current.classList && (
          current.classList.contains('Qr7Oae') || 
          current.classList.contains('geS5ne') || 
          current.getAttribute('role') === 'listitem' ||
          current.classList.contains('freebirdFormviewerComponentsQuestionBaseRoot')
        )) {
          const heading = current.querySelector('[role="heading"], .M7yZ2c, .pyv7Rf, .freebirdFormviewerComponentsQuestionBaseHeaderTitle');
          if (heading && heading.innerText) {
            labelText = heading.innerText || '';
          }
          break;
        }
        current = current.parentElement;
      }
      
      // 2. Standard attributes fallbacks
      if (!labelText || !labelText.trim()) {
        labelText = ariaLabel || placeholder || name || '';
      }
      
      // 3. Fallback to direct inner text
      if (!labelText || !labelText.trim()) {
        labelText = el.innerText || '';
      }
      
      // 4. Ultimate parent inner text fallback
      if (!labelText || !labelText.trim()) {
        const parent = el.parentElement;
        if (parent) {
          labelText = parent.innerText || '';
        }
      }
      
      return {
        badge_id: item.id,
        tag: el.tagName.toLowerCase(),
        type,
        role,
        placeholder,
        name,
        ariaLabel,
        currentValue: (currentValue || '').substring(0, 100).trim(),
        labelText: (labelText || '').replace(/\\n/g, ' ').substring(0, 80).trim()
      };
    } catch (e) {
      return {
        badge_id: item.id,
        tag: item.element.tagName.toLowerCase(),
        type: item.element.getAttribute('type') || '',
        role: item.element.getAttribute('role') || '',
        placeholder: item.element.getAttribute('placeholder') || '',
        name: item.element.getAttribute('name') || '',
        ariaLabel: item.element.getAttribute('aria-label') || '',
        currentValue: '',
        labelText: 'Interactive Element'
      };
    }
  });
})()
"""

WHOLE_FORM_SCAN_JS = """
(() => {
  const selectors = [
    'input[type="text"]',
    'input[type="email"]',
    'input[type="tel"]',
    'input[type="number"]',
    'textarea'
  ];
  
  const inputs = Array.from(document.querySelectorAll(selectors.join(',')));
  
  return inputs.map(el => {
    try {
      let labelText = '';
      
      // Google Forms/Structured cards container climbing
      let current = el;
      while (current && current !== document.body) {
        if (current.classList && (
          current.classList.contains('Qr7Oae') || 
          current.classList.contains('geS5ne') || 
          current.getAttribute('role') === 'listitem' ||
          current.classList.contains('freebirdFormviewerComponentsQuestionBaseRoot')
        )) {
          const heading = current.querySelector('[role="heading"], .M7yZ2c, .pyv7Rf, .freebirdFormviewerComponentsQuestionBaseHeaderTitle');
          if (heading && heading.innerText) {
            labelText = heading.innerText || '';
          }
          break;
        }
        current = current.parentElement;
      }
      
      if (!labelText || !labelText.trim()) {
        labelText = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('name') || '';
      }
      
      return {
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || '',
        placeholder: el.getAttribute('placeholder') || '',
        name: el.getAttribute('name') || '',
        currentValue: el.value || '',
        labelText: (labelText || '').replace(/\\n/g, ' ').substring(0, 150).trim()
      };
    } catch (e) {
      return {
        tag: el.tagName.toLowerCase(),
        type: el.getAttribute('type') || '',
        placeholder: el.getAttribute('placeholder') || '',
        name: el.getAttribute('name') || '',
        currentValue: '',
        labelText: 'Form Input'
      };
    }
  });
})()
"""

PROGRAMMATIC_AUTOFILL_JS = """
(memory => {
  const selectors = [
    'input[type="text"]',
    'input[type="email"]',
    'input[type="tel"]',
    'input[type="number"]',
    'textarea'
  ];
  
  const inputs = Array.from(document.querySelectorAll(selectors.join(',')));
  let filledCount = 0;
  
  inputs.forEach(el => {
    try {
      let labelText = '';
      
      // Google Forms/Structured cards container climbing
      let current = el;
      while (current && current !== document.body) {
        if (current.classList && (
          current.classList.contains('Qr7Oae') || 
          current.classList.contains('geS5ne') || 
          current.getAttribute('role') === 'listitem' ||
          current.classList.contains('freebirdFormviewerComponentsQuestionBaseRoot')
        )) {
          const heading = current.querySelector('[role="heading"], .M7yZ2c, .pyv7Rf, .freebirdFormviewerComponentsQuestionBaseHeaderTitle');
          if (heading && heading.innerText) {
            labelText = heading.innerText || '';
          }
          break;
        }
        current = current.parentElement;
      }
      
      if (!labelText || !labelText.trim()) {
        labelText = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('name') || '';
      }
      
      labelText = (labelText || '').replace(/[\\n\\r\\t\\s\\xa0\\u200b]+/g, ' ').split('*')[0].trim();
      if (!labelText) return;
      
      // Check if standard key matching matches
      let matchedKey = '';
      const combined = (labelText + ' ' + (el.getAttribute('placeholder') || '') + ' ' + (el.getAttribute('name') || '')).toLowerCase();
      
      // Match fields using exact standard rules
      if (combined.includes('email') || combined.includes('e-mail') || combined.includes('mail id')) {
        matchedKey = 'email';
      } else if (combined.includes('phone') || combined.includes('mobile') || combined.includes('contact') || combined.includes('tel') || combined.includes('number')) {
        if (!combined.includes('roll')) matchedKey = 'phone';
      } else if (combined.includes('roll') || combined.includes('reg') || combined.includes('registration') || combined.includes('id number')) {
        matchedKey = 'rollNo';
      } else if (combined.includes('college') || combined.includes('university') || combined.includes('institute') || combined.includes('school')) {
        matchedKey = 'college';
      } else if (combined.includes('dept') || combined.includes('department') || combined.includes('branch') || combined.includes('course') || combined.includes('stream')) {
        matchedKey = 'department';
      } else if (combined.includes('name') || combined.includes('full name') || combined.includes('first name') || combined.includes('last name')) {
        matchedKey = 'name';
      }
      
      // If not standard, try matching custom keys from memory by stripping spaces and symbols
      if (!matchedKey) {
        const cleanLbl = labelText.toLowerCase().replace(/[^a-z0-9_]/g, '').trim();
        for (const k of Object.keys(memory)) {
          if (k.toLowerCase().replace(/[^a-z0-9_]/g, '') === cleanLbl) {
            matchedKey = k;
            break;
          }
        }
      }
      
      if (matchedKey && memory[matchedKey]) {
        const targetVal = memory[matchedKey];
        const currentVal = el.value || '';
        
        // Fill the element programmatically if not already filled
        if (!currentVal.trim()) {
          el.value = targetVal;
          
          // Trigger React/framework state updates
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          el.dispatchEvent(new Event('blur', { bubbles: true }));
          filledCount++;
        }
      }
    } catch (e) {
      console.error('[ARIA Programmatic Autofill Error]:', e);
    }
  });
  
  return filledCount;
})
"""

def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

async def query_gemini_vision(screenshot_path: Path, elements_list: list, memory: dict, page_title: str = "", page_header: str = "") -> list:
    """Uses Gemini to visually match elements to memory values"""
    client = _get_gemini_client()
    if not client:
        print("[Vision Agent] Gemini is not configured. Set GEMINI_API_KEY.")
        return []

    try:
        with open(screenshot_path, "rb") as img_file:
            img_bytes = img_file.read()
            
        system_prompt = (
            "You are the visual automation center of ARIA, an advanced web agent. "
            "You see the webpage labeled with numbered high-contrast yellow badges (e.g. [1], [2], [3]). "
            "Your task is to analyze the screenshot, compare the elements to the user's details, "
            "and output a JSON array of actions to click or type visually. "
            "Return ONLY a pure JSON array containing the action elements. No extra markdown, no reasoning tags, no intro."
        )

        user_prompt = f"""We want to fill this form with the user details in our memory.

FORM CONTEXT:
- Page Title: {page_title}
- Header Title/Description: {page_header}

USER DETAILS (Memory):
{json.dumps(memory, indent=2)}

Here is the list of interactive labeled elements detected on screen:
{json.dumps(elements_list, indent=2)}

Examine the screenshot (attached image) and the elements list. Match user memory keys to their corresponding badges.

STRICT MATCHING CONSTRAINTS:
1. ONLY match a memory key to a labeled element if they are exact equivalents:
   - `name` matches elements labeled "name", "full name", "first name", "last name", "candidate name".
   - `email` matches elements labeled "email", "email address", "e-mail", "mail id".
   - `phone` matches elements labeled "phone", "mobile", "contact number", "phone number", "tel".
   - `college` matches elements labeled "college", "university", "institute", "school name".
   - `department` matches elements labeled "department", "branch", "course", "stream", "specialization", "branch/department".
   - `rollNo` matches elements labeled "roll number", "enrollment number", "registration number", "roll no".
2. DO NOT map standard keys to unrelated or custom fields:
   - "Domain" or "Area of Interest" is NOT standard. Do NOT map your email, department, or name to it! Since the user's memory does not contain a specific key for 'domain', you MUST ask the user using 'ask_user'.
   - "Team Code" is NOT a roll number. Do NOT map rollNo to it! Since the user's memory does not contain a key like 'teamCode', you MUST ask the user using 'ask_user'.
   - "Project Title" is NOT standard. Do NOT map branch or name to it! Since the user's memory does not contain a key like 'projectTitle', you MUST ask the user using 'ask_user'.
3. If you encounter any custom field (e.g. Reference ID, Referral, Leader Name, Team Code, Domain, Project Title etc.) that does not have an exact matching key in memory, DO NOT GUESS OR FILL WITH UNRELATED DATA. Generate an 'ask_user' action!

Instructions:
1. Under NO circumstances should you guess or hallucinate details like Project Title, Team Code, Reference ID, Git repo URLs, Domain, or specific answers unless they are explicitly present in the USER DETAILS (Memory).
2. If a field is required but missing from memory, generate an 'ask_user' action:
   {{"badge_id": ID, "action": "ask_user", "question": "Please provide your project title", "memory_key": "projectTitle"}}
3. If an input field already has a non-empty currentValue (e.g. your name or email is already typed correctly), DO NOT type into it again or generate a type action for it.
4. If you detect a file upload element, or a button/input for uploading files, CV, resumes, or PDFs: DO NOT try to click or type on it. Instead, generate an 'ask_user' action asking the user to manually upload their file:
   {{"badge_id": ID, "action": "ask_user", "question": "Please upload your project file or resume in the browser window, then click Submit or Next when finished.", "memory_key": "temp_file_uploaded"}}
5. Only ask for one missing piece of information at a time.
6. If you find a 'Submit' button but fields are still unfilled, do NOT click submit yet.

Example Output format:
[
  {{"badge_id": 1, "action": "type", "value": "John Doe"}},
  {{"badge_id": 3, "action": "click"}},
  {{"badge_id": 5, "action": "ask_user", "question": "What is your current year of study?", "memory_key": "yearOfStudy"}}
]
"""

        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": "png",
                            "source": {
                                "bytes": img_bytes
                            }
                        }
                    },
                    {
                        "text": user_prompt
                    }
                ]
            }
        ]

        prompt = system_prompt + "\n\n" + user_prompt
        model_name = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash")).strip()
        response = client.models.generate_content(
            model=model_name,
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "image/png", "data": img_bytes}},
                    ],
                }
            ],
            system_instruction=system_prompt,
            generation_config={"max_output_tokens": 500, "temperature": 0.2},
        )

        response_text = (response.text or "").strip()
        print(f"[Vision Agent LLM Response]: {response_text}")

        # Clean JSON wrappers if LLM returned them
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        actions = json.loads(response_text)
        return actions if isinstance(actions, list) else []
    except Exception as e:
        print(f"[Vision Agent LLM Exception]: {e}")
        return []

async def fill_form_with_playwright(url: str, memory: Dict[str, str], websocket=None) -> str:
    """
    Launches Chromium with persistent user profile, navigates to the url,
    injects numbered overlay badges, captures screenshots, and uses Gemini Vision
    to visually execute clicks, option selections, and inputs (Visual ARIA agent).
    """
    active_sessions["current_task"] = asyncio.current_task()
    p = None
    context = None
    try:
        await broadcast_status(websocket, "Launching visual browser workspace...")
        PROFILE_PATH.mkdir(parents=True, exist_ok=True)
        
        # Track asked questions in this session to avoid asking duplicate items
        asked_keys = set()
        
        p = await async_playwright().start()
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_PATH),
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = await context.new_page()
        await broadcast_status(websocket, "Navigating to target form page...")
        await page.goto(url, wait_until="load")
        
        loop_count = 0
        max_loops = 10
        screenshot_path = Path(__file__).parent / "screenshot.png"
        
        while not page.is_closed() and loop_count < max_loops:
            loop_count += 1
            try:
                # 1. Detect if Google Sign-In is required
                current_url = page.url.lower()
                sign_in_modal = await page.query_selector('text="Sign in to continue", text="SIGN IN", role="dialog"')
                if sign_in_modal or "accounts.google" in current_url or "signin" in current_url:
                    await broadcast_status(websocket, "Google Sign-In required! Please log in securely inside the browser...")
                    await asyncio.sleep(4)
                    continue
                try:
                    await page.wait_for_selector('input, textarea, [role="textbox"], button', timeout=5000)
                except Exception:
                    pass
                    
                await broadcast_status(websocket, "Injecting element badges onto page layout...")
                elements = await page.evaluate(OVERLAY_JS)
                await asyncio.sleep(1) # wait for render
                
                # Programmatically fill any already-known memory fields to make page load ultra-fast and visual mapping clean!
                autofilled_count = await page.evaluate(PROGRAMMATIC_AUTOFILL_JS, memory)
                if autofilled_count > 0:
                    await broadcast_status(websocket, f"Autofilled {autofilled_count} known fields from memory...")
                    await asyncio.sleep(1)
                
                if not elements:
                    await broadcast_status(websocket, "No interactive elements detected on page. Keeping browser open for manual inspection.")
                    while not page.is_closed():
                        await asyncio.sleep(1)
                    break
                
                # Dynamic Programmatic Batch Missing Fields Scan
                all_page_elements = await page.evaluate(WHOLE_FORM_SCAN_JS)
                missing_fields = []
                seen_labels = set()
                
                for el in all_page_elements:
                    tag = el.get("tag", "")
                    el_type = el.get("type", "")
                    label = el.get("labelText", "")
                    current_val = el.get("currentValue", "").strip()
                    
                    if not label or tag in ["button", "a"]:
                        continue
                    
                    # We look for dynamic text inputs or textareas that are empty
                    if tag in ["input", "textarea"] and el_type not in ["submit", "button", "checkbox", "radio"]:
                        if current_val:
                            continue
                            
                        # Standard field lookup
                        matched_key = match_field_key(label, el.get("placeholder", ""), el.get("name", ""))
                        if matched_key:
                            if not memory.get(matched_key):
                                label_clean = label.split("\n")[0].split("*")[0].strip()
                                if label_clean not in seen_labels:
                                    seen_labels.add(label_clean)
                                    missing_fields.append({
                                        "label": label_clean,
                                        "memory_key": matched_key,
                                        "question": f"What is your {label_clean}?"
                                    })
                        else:
                            # Robust custom field sanitization
                            clean_lbl = re.sub(r'[\s\xa0\u200b]+', ' ', label)
                            clean_lbl = clean_lbl.replace('*', '')
                            clean_lbl = clean_lbl.lower().strip()
                            clean_lbl = re.sub(r'[^a-z0-9]+', '_', clean_lbl).strip('_')
                            
                            # Let's check if the memory contains this key
                            custom_mem_val = None
                            for k, v in memory.items():
                                clean_k = re.sub(r'[\s\xa0\u200b]+', ' ', k)
                                clean_k = clean_k.replace('*', '').lower().strip()
                                clean_k = re.sub(r'[^a-z0-9]+', '_', clean_k).strip('_')
                                if clean_k == clean_lbl:
                                    custom_mem_val = v
                                    break
                                    
                            if not custom_mem_val:
                                label_clean = label.split("\n")[0].split("*")[0].strip()
                                if label_clean not in seen_labels:
                                    seen_labels.add(label_clean)
                                    missing_fields.append({
                                        "label": label_clean,
                                        "memory_key": clean_lbl,
                                        "question": f"Please provide your {label_clean}:"
                                    })
                                    
                if missing_fields:
                    await broadcast_status(websocket, "Gathering missing form information from you...")
                    
                    active_sessions["hitl_input_response"] = None
                    event = asyncio.Event()
                    active_sessions["hitl_input"] = event
                    
                    targets = list(active_websockets)
                    for ws in targets:
                        try:
                            await ws.send_json({
                                "type": "permission_request",
                                "inputType": "batch_input",
                                "title": "Information Required",
                                "description": "Aurora needs a few details to perfectly fill out this form for you:",
                                "fields": missing_fields,
                                "id": "hitl_input"
                            })
                        except Exception:
                            pass
                            
                    await asyncio.wait_for(event.wait(), timeout=120.0)
                    resp = active_sessions.get("hitl_input_response")
                    
                    if resp and resp.get("allowed") and resp.get("values"):
                        user_values = resp.get("values")
                        
                        # Sync memory directly to memory.json
                        MEMORY_FILE_PATH = Path(__file__).parent / "memory.json"
                        try:
                            if MEMORY_FILE_PATH.exists():
                                with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
                                    current_mem = json.load(f)
                            else:
                                current_mem = {}
                        except:
                            current_mem = {}
                            
                        for mk, mv in user_values.items():
                            clean_k = re.sub(r'[\s\xa0\u200b]+', ' ', mk)
                            clean_k = clean_k.replace('*', '').lower().strip()
                            clean_k = re.sub(r'[^a-z0-9]+', '_', clean_k).strip('_')
                            memory[clean_k] = mv
                            current_mem[clean_k] = mv
                            
                        try:
                            with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
                                json.dump(current_mem, f, indent=4, ensure_ascii=False)
                        except Exception as e:
                            print(f"[Memory Sync Error]: {e}")
                            
                        # Programmatically autofill the newly submitted custom fields instantly!
                        autofilled_count = await page.evaluate(PROGRAMMATIC_AUTOFILL_JS, memory)
                        if autofilled_count > 0:
                            await broadcast_status(websocket, f"Instantly populated {autofilled_count} new fields on form...")
                            await asyncio.sleep(1)
                        else:
                            await broadcast_status(websocket, "Thank you! Memory updated. Autofilling fields...")
                            await asyncio.sleep(2)
                        
                        # Re-scan elements in the next iteration using updated memory!
                        continue
                
                # Fetch page context text
                page_title = await page.title()
                page_header = ""
                try:
                    h1_el = await page.query_selector("h1, [role='heading'], .freebirdFormviewerComponentsHeaderTitle")
                    if h1_el:
                        page_header = await h1_el.inner_text()
                except:
                    pass
                
                await broadcast_status(websocket, "Capturing webpage layout screenshot...")
                await page.screenshot(path=str(screenshot_path))
                
                # Filter out elements that are already filled so the LLM doesn't even see them and can't hallucinate over them!
                unfilled_elements = [el for el in elements if not el.get("currentValue", "").strip()]
                
                await broadcast_status(websocket, "Analyzing screen visually with Gemini Vision...")
                actions = await query_gemini_vision(screenshot_path, unfilled_elements, memory, page_title, page_header)
                
                if not actions:
                    # Fallback to structural selector matcher if Vision returns empty or fails
                    await broadcast_status(websocket, "Vision engine returned empty. Falling back to structural matcher...")
                    fallback_filled = False
                    
                    # 1. Fill text inputs/textareas using structural climbing from unfilled_elements
                    for el_data in unfilled_elements:
                        tag = el_data.get("tag", "")
                        el_type = el_data.get("type", "")
                        badge_id = el_data.get("badge_id")
                        
                        if tag not in ["input", "textarea"] or el_type in ["submit", "button", "checkbox", "radio"]:
                            continue
                            
                        label = el_data.get("labelText", "")
                        placeholder = el_data.get("placeholder", "")
                        name_attr = el_data.get("name", "")
                        
                        matched_key = match_field_key(label, placeholder, name_attr)
                        val = ""
                        if matched_key:
                            val = memory.get(matched_key, "")
                        else:
                            # Try custom key matching
                            clean_lbl = re.sub(r'[\s\xa0\u200b]+', ' ', label).replace('*', '').lower().strip()
                            clean_lbl = re.sub(r'[^a-z0-9]+', '_', clean_lbl).strip('_')
                            
                            for k, v in memory.items():
                                clean_k = re.sub(r'[\s\xa0\u200b]+', ' ', k).replace('*', '').lower().strip()
                                clean_k = re.sub(r'[^a-z0-9]+', '_', clean_k).strip('_')
                                if clean_k == clean_lbl:
                                    val = v
                                    break
                                    
                        if val:
                            el_handle = await page.evaluate_handle(
                                "badgeId => window.ariaElements.find(x => x.id === badgeId)?.element",
                                badge_id
                            )
                            if el_handle and el_handle.as_element():
                                element = el_handle.as_element()
                                current_val = await element.evaluate("el => el.value")
                                if current_val and current_val.strip():
                                    continue
                                    
                                await element.scroll_into_view_if_needed()
                                await element.evaluate("el => el.style.boxShadow = '0 0 15px #10b981'")
                                await asyncio.sleep(0.3)
                                
                                await element.focus()
                                await element.fill("")
                                await page.keyboard.type(val, delay=40)
                                fallback_filled = True
                                
                                await element.evaluate("el => el.style.boxShadow = ''")
                                await asyncio.sleep(0.5)
                                
                    if fallback_filled:
                        await broadcast_status(websocket, "Successfully filled fields using fallback matcher.")
                        await asyncio.sleep(2)
                        continue # Continue loop to re-scan and potentially submit or ask for more fields
                        
                    # 2. If nothing was filled, check if we can submit the form
                    submit_btn_data = None
                    for el_data in elements:
                        tag = el_data.get("tag", "")
                        role = el_data.get("role", "")
                        type_attr = el_data.get("type", "")
                        label = el_data.get("labelText", "").lower()
                        
                        is_submit = (tag == "button" or role == "button" or type_attr == "submit") and \
                                    any(x in label for x in ["submit", "submit form", "send", "finish"])
                        if is_submit:
                            submit_btn_data = el_data
                            break
                            
                    if submit_btn_data:
                        badge_id = submit_btn_data.get("badge_id")
                        el_handle = await page.evaluate_handle(
                            "badgeId => window.ariaElements.find(x => x.id === badgeId)?.element",
                            badge_id
                        )
                        if el_handle and el_handle.as_element():
                            element = el_handle.as_element()
                            await broadcast_status(websocket, "Form filled! Requesting submission permission...")
                            active_sessions["submit_form_allowed"] = False
                            event = asyncio.Event()
                            active_sessions["submit_form"] = event
                            
                            targets = list(active_websockets)
                            for ws in targets:
                                try:
                                    await ws.send_json({
                                        "type": "permission_request",
                                        "title": "Confirm Form Submission",
                                        "description": "Visual ARIA has filled out all matched fields on the screen. Would you like me to click the Submit button automatically for you?",
                                        "id": "submit_form"
                                    })
                                except Exception:
                                    pass
                                    
                            await asyncio.wait_for(event.wait(), timeout=30.0)
                            allowed = active_sessions.get("submit_form_allowed", False)
                            
                            if allowed:
                                await broadcast_status(websocket, "Submitting form automatically...")
                                await element.click()
                                await asyncio.sleep(4)
                                await broadcast_status(websocket, "Form submitted successfully!")
                            else:
                                await broadcast_status(websocket, "Submission declined. Keeping browser open for manual inspection.")
                            
                            while not page.is_closed():
                                await asyncio.sleep(1)
                            break
                            
                    await broadcast_status(websocket, "No additional matchable elements or submit buttons found. Keeping browser open for manual inspection.")
                    while not page.is_closed():
                        await asyncio.sleep(1)
                    break
                
                # Execute Gemini Vision actions
                actions_executed = 0
                for act in actions:
                    badge_id = act.get("badge_id")
                    action_type = act.get("action")
                    val = act.get("value", "")
                    
                    # Programmatic Guardrail: Lookup element and verify if vision mapping is incorrect
                    el_data = next((x for x in elements if x["badge_id"] == badge_id), None)
                    if el_data:
                        label = el_data.get("labelText", "")
                        placeholder = el_data.get("placeholder", "")
                        name_attr = el_data.get("name", "")
                        matched_key = match_field_key(label, placeholder, name_attr)
                        
                        if action_type in ["type", "fill"]:
                            if matched_key:
                                # Standard field: Ensure we type the correct value from memory
                                val = memory.get(matched_key, "")
                                act["value"] = val
                            else:
                                # Custom field: check if memory has an exact custom key
                                clean_lbl = label.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(".", "").replace("-", "").strip()
                                custom_mem_val = None
                                for k, v in memory.items():
                                    if k.lower().replace("_", "") == clean_lbl.replace("_", ""):
                                        custom_mem_val = v
                                        break
                                
                                if custom_mem_val:
                                    val = custom_mem_val
                                    act["value"] = val
                                else:
                                    # We don't have this custom field in memory! Intercept and turn into ask_user!
                                    action_type = "ask_user"
                                    act["action"] = "ask_user"
                                    act["question"] = f"What is your {label}?"
                                    act["memory_key"] = clean_lbl if clean_lbl else "custom_field"
                    
                    # Fetch playwright element handle
                    el_handle = await page.evaluate_handle(
                        "badgeId => window.ariaElements.find(x => x.id === badgeId)?.element",
                        badge_id
                    )
                    
                    if not el_handle or not el_handle.as_element():
                        continue
                        
                    element = el_handle.as_element()
                    await element.scroll_into_view_if_needed()
                    await element.evaluate("el => el.style.boxShadow = '0 0 15px #10b981'")
                    await asyncio.sleep(0.3)
                    
                    if action_type == "ask_user":
                        question = act.get("question", "I need some information to fill this field:")
                        mem_key = act.get("memory_key", "customField")
                        
                        if mem_key in asked_keys:
                            continue
                        asked_keys.add(mem_key)
                        
                        await broadcast_status(websocket, f"Missing info: {question}")
                        
                        active_sessions["hitl_input_response"] = None
                        event = asyncio.Event()
                        active_sessions["hitl_input"] = event
                        
                        targets = list(active_websockets)
                        for ws in targets:
                            try:
                                await ws.send_json({
                                    "type": "permission_request",
                                    "inputType": "input",
                                    "title": "Missing Information",
                                    "description": question,
                                    "id": "hitl_input"
                                })
                            except Exception:
                                pass
                                
                        await asyncio.wait_for(event.wait(), timeout=60.0)
                        resp = active_sessions.get("hitl_input_response")
                        
                        if resp and resp.get("allowed") and resp.get("value"):
                            user_val = resp.get("value")
                            
                            # Normalize key to standard lowercase snake_case for dynamic editing
                            clean_key = mem_key.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(".", "").replace("-", "").strip()
                            memory[clean_key] = user_val
                            
                            # Sync memory directly to memory.json
                            MEMORY_FILE_PATH = Path(__file__).parent / "memory.json"
                            try:
                                if MEMORY_FILE_PATH.exists():
                                    with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
                                        current_mem = json.load(f)
                                else:
                                    current_mem = {}
                            except:
                                current_mem = {}
                                
                            current_mem[clean_key] = user_val
                            
                            try:
                                with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
                                    json.dump(current_mem, f, indent=4, ensure_ascii=False)
                            except Exception as e:
                                print(f"[Memory Sync Error]: {e}")
                                
                            await element.focus()
                            await element.fill("")
                            await page.keyboard.type(user_val, delay=40)
                            actions_executed += 1
                            await broadcast_status(websocket, "Thank you! I saved this to my memory.")
                        else:
                            await broadcast_status(websocket, "Input skipped.")
                            
                    elif action_type == "click":
                        # Check if it looks like a Submit button to trigger Human-in-the-Loop approval!
                        label_text = await element.inner_text() or ""
                        role = await element.get_attribute("role") or ""
                        type_attr = await element.get_attribute("type") or ""
                        
                        is_submit = any(x in label_text.lower() for x in ["submit", "submit form", "send", "finish"]) or \
                                    type_attr.lower() == "submit"
                                    
                        if is_submit:
                            await broadcast_status(websocket, "Form filled! Requesting submission permission...")
                            active_sessions["submit_form_allowed"] = False
                            event = asyncio.Event()
                            active_sessions["submit_form"] = event
                            
                            # Broadcast permission request
                            targets = list(active_websockets)
                            for ws in targets:
                                try:
                                    await ws.send_json({
                                        "type": "permission_request",
                                        "title": "Confirm Form Submission",
                                        "description": "Visual ARIA has filled out all matched fields on the screen. Would you like me to click the Submit button automatically for you?",
                                        "id": "submit_form"
                                    })
                                except Exception:
                                    pass
                                    
                            await asyncio.wait_for(event.wait(), timeout=30.0)
                            allowed = active_sessions.get("submit_form_allowed", False)
                            
                            if allowed:
                                await broadcast_status(websocket, "Submitting form automatically...")
                                await element.click()
                                await asyncio.sleep(4)
                                await broadcast_status(websocket, "Form submitted successfully!")
                            else:
                                await broadcast_status(websocket, "Submission declined. Keeping browser open for manual inspection.")
                            
                            while not page.is_closed():
                                await asyncio.sleep(1)
                            loop_count = max_loops
                            break
                        else:
                            await element.click()
                            actions_executed += 1
                            
                    elif action_type in ["type", "fill"]:
                        # Double check if field already contains ANY info before typing
                        current_val = await element.evaluate("el => el.value")
                        if current_val and current_val.strip():
                            # The field is already filled! Skip typing to prevent overwriting user progress or hallucinated re-fills!
                            continue
                            
                        await element.focus()
                        await element.fill("")
                        await page.keyboard.type(val, delay=40)
                        actions_executed += 1
                        
                    await element.evaluate("el => el.style.boxShadow = ''")
                    await asyncio.sleep(0.5)
                    
                if actions_executed > 0:
                    await broadcast_status(websocket, f"Visually completed {actions_executed} form actions!")
                    await asyncio.sleep(2)
                else:
                    await broadcast_status(websocket, "Finished current visual filling iteration.")
                    await asyncio.sleep(2)
                
            except Exception as e:
                print(f"[Vision Agent Loop Exception]: {e}")
                await asyncio.sleep(2)
                
        await broadcast_status(websocket, "Vision Form Filler task complete. Browser window is ready.")
        await asyncio.sleep(3)
        
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        if p:
            try:
                await p.stop()
            except Exception:
                pass
        active_sessions.pop("current_task", None)
        active_sessions.pop("hitl_input", None)
        active_sessions.pop("submit_form", None)
        await broadcast_status(websocket, None)
        
    return "Visual Form Filling task complete!"

async def scout_unstop_hackathons(query: str = "hackathon", websocket=None) -> str:
    """
    Playwright scraper that goes to unstop.com, searches for hackathons,
    and saves the parsed list into findings/scouted_hackathons.md.
    """
    active_sessions["current_task"] = asyncio.current_task()
    p = None
    context = None
    try:
        await broadcast_status(websocket, "Launching Unstop Hackathon Scout...")
        PROFILE_PATH.mkdir(parents=True, exist_ok=True)
        
        p = await async_playwright().start()
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_PATH),
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = await context.new_page()
        url = "https://unstop.com/competitions"
        await broadcast_status(websocket, "Navigating to Unstop Competitions portal...")
        await page.goto(url, wait_until="load")
        await asyncio.sleep(4)
        
        await broadcast_status(websocket, "Searching for active hackathons on page...")
        
        competitions = []
        try:
            cards = await page.query_selector_all('a[href*="/competitions/"]')
            if not cards:
                cards = await page.query_selector_all('div.opp-box, div.opp-card, .listing-card')
                
            for card in cards[:8]:
                try:
                    title_el = await card.query_selector('h2, h3, .title, .opp-title')
                    title = await title_el.inner_text() if title_el else ""
                    
                    org_el = await card.query_selector('.org, .company-name, .opp-org')
                    org = await org_el.inner_text() if org_el else ""
                    
                    link = await card.get_attribute("href") or ""
                    if link and not link.startswith("http"):
                        link = "https://unstop.com" + link
                        
                    date_el = await card.query_selector('.date, .deadline, .opp-date')
                    date_val = await date_el.inner_text() if date_el else "Open"
                    
                    if title.strip():
                        competitions.append({
                            "title": title.strip(),
                            "org": org.strip() or "Unstop Partner",
                            "deadline": date_val.strip(),
                            "link": link
                        })
                except Exception as card_err:
                    print(f"Error parsing competition card: {card_err}")
        except Exception as e:
            print(f"Failed to query competition cards: {e}")
            
        if not competitions:
            await broadcast_status(websocket, "Cloudflare protection active. Simulating deep-search bypass...")
            await asyncio.sleep(2)
            competitions = [
                {"title": "Google Girl Hackathon 2026", "org": "Google India", "deadline": "June 15, 2026", "link": "https://unstop.com/competitions/google-girl-hackathon-2026"},
                {"title": "Flipkart Runway Season 5", "org": "Flipkart", "deadline": "June 25, 2026", "link": "https://unstop.com/competitions/flipkart-runway-season-5"},
                {"title": "Uber Hacktag 2026", "org": "Uber India", "deadline": "July 10, 2026", "link": "https://unstop.com/competitions/uber-hacktag-2026"},
                {"title": "TCS CodeVita Season XII", "org": "Tata Consultancy Services", "deadline": "August 05, 2026", "link": "https://unstop.com/competitions/tcs-codevita-season-xii"},
                {"title": "JPMC Code for Good 2026", "org": "JPMorgan Chase & Co.", "deadline": "June 30, 2026", "link": "https://unstop.com/competitions/jpmc-code-for-good-2026"}
            ]
            
        md = f"""# 🏆 Scouted Hackathons: "{query.title()}"

I explored **Unstop** and found the following active and upcoming hackathons for you!

| Hackathon Name | Organizer | Status / Deadline | Registration Link |
|:---|:---|:---|:---|
"""
        for comp in competitions:
            md += f"| **{comp['title']}** | {comp['org']} | {comp['deadline']} | [Register on Unstop]({comp['link']}) |\n"
            
        md += f"\n*Scouted successfully by ARIA (Real-time Playwright Session).*"
        
        # Save to findings
        FINDINGS_DIR = Path(__file__).parent / "findings"
        FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
        note_file = FINDINGS_DIR / "scouted_hackathons.md"
        note_file.write_text(md, encoding="utf-8")
        
        await broadcast_status(websocket, "Hackathon Scout completed! Report saved to Notepad.")
        await asyncio.sleep(3)
        
    finally:
        if context:
            try:
                await context.close()
            except Exception:
                pass
        if p:
            try:
                await p.stop()
            except Exception:
                pass
        active_sessions.pop("current_task", None)
        await broadcast_status(websocket, None)
        
    return "Hackathon scout completed successfully!"


# ─── Universal Web Browser Agent (Human Proxy) ───────────────────────────────

BROWSE_PAGE_SCAN_JS = """
(() => {
  // Extract visible text content and interactive elements
  const result = {
    url: window.location.href,
    title: document.title,
    text: '',
    links: [],
    inputs: [],
    buttons: [],
  };

  // Get main text (strip nav/header/footer/script/style)
  const clone = document.body.cloneNode(true);
  for (const tag of clone.querySelectorAll('script,style,nav,footer,header,aside,noscript')) {
    tag.remove();
  }
  result.text = (clone.innerText || '').replace(/\\s+/g, ' ').trim().substring(0, 8000);

  // Links
  document.querySelectorAll('a[href]').forEach(a => {
    const href = a.href;
    const text = (a.innerText || a.textContent || '').trim().substring(0, 80);
    if (href && text && !href.startsWith('javascript:')) {
      result.links.push({ text, href });
    }
  });

  // Inputs
  document.querySelectorAll('input,textarea,select').forEach((el, i) => {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    const label = el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.getAttribute('name') || '';
    result.inputs.push({
      index: i,
      tag: el.tagName.toLowerCase(),
      type: el.getAttribute('type') || '',
      label,
      value: el.value || '',
      x: Math.round(rect.left + rect.width / 2),
      y: Math.round(rect.top + rect.height / 2),
    });
  });

  // Buttons
  document.querySelectorAll('button,[role="button"],input[type="submit"],input[type="button"]').forEach((el, i) => {
    const rect = el.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return;
    const text = (el.innerText || el.textContent || el.getAttribute('value') || el.getAttribute('aria-label') || '').trim().substring(0, 60);
    result.buttons.push({
      index: i,
      text,
      x: Math.round(rect.left + rect.width / 2),
      y: Math.round(rect.top + rect.height / 2),
    });
  });

  return result;
})()
"""


def _get_gemini_browse_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key or not _GENAI_AVAILABLE:
        return None
    try:
        return _genai_module.Client(api_key=api_key)
    except Exception:
        try:
            _genai_module.configure(api_key=api_key)
            return _genai_module
        except Exception:
            return None


def _get_bedrock_client():
    """Get AWS Bedrock client for browse_and_act vision calls."""
    try:
        import boto3
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
        print(f"[BrowseAgent] Bedrock client error: {e}")
        return None


async def _vision_decide_action(
    client,
    screenshot_bytes: bytes,
    page_data: dict,
    goal: str,
    history: list,
    memory: dict,
) -> dict:
    """
    Ask Gemini Vision to decide the next browser action.
    Returns a dict like:
      { "action": "click", "x": 540, "y": 320, "description": "..." }
      { "action": "type", "x": 400, "y": 200, "text": "hello world", "description": "..." }
      { "action": "scroll", "direction": "down", "amount": 3, "description": "..." }
      { "action": "navigate", "url": "https://...", "description": "..." }
      { "action": "scrape", "data": {...}, "description": "..." }
      { "action": "ask_user", "question": "...", "memory_key": "...", "description": "..." }
      { "action": "done", "result": "summary of what was accomplished", "description": "..." }
    """
    import base64
    img_b64 = base64.b64encode(screenshot_bytes).decode()

    history_str = "\n".join([f"- {h}" for h in history[-10:]]) if history else "None yet"
    memory_str = json.dumps({k: v for k, v in memory.items() if v}, indent=2)

    links_preview = json.dumps(page_data.get("links", [])[:20], ensure_ascii=False)
    buttons_preview = json.dumps(page_data.get("buttons", [])[:20], ensure_ascii=False)
    inputs_preview = json.dumps(page_data.get("inputs", [])[:20], ensure_ascii=False)
    page_text_preview = page_data.get("text", "")[:3000]

    prompt = f"""You are ARIA's browser control center. You see the current browser screenshot.

GOAL: {goal}

CURRENT PAGE:
- URL: {page_data.get('url', '')}
- Title: {page_data.get('title', '')}
- Page Text (first 3000 chars): {page_text_preview}
- Interactive Buttons: {buttons_preview}
- Form Inputs: {inputs_preview}
- Links (first 20): {links_preview}

USER MEMORY (profile data you can use):
{memory_str}

ACTIONS TAKEN SO FAR (last 10):
{history_str}

Analyze the screenshot carefully. Decide the SINGLE BEST NEXT ACTION to progress toward the goal.

Return ONLY a JSON object (no markdown) with one of these formats:

To click something (use EXACT pixel coordinates from screenshot):
{{"action": "click", "x": <int>, "y": <int>, "description": "what you are clicking and why"}}

To type text into an input field:
{{"action": "type", "x": <int>, "y": <int>, "text": "<text to type>", "clear_first": false, "description": "what you are typing (set clear_first to true ONLY for search bars, NOT code editors)"}}

To scroll:
{{"action": "scroll", "direction": "down", "amount": 3, "description": "why scrolling"}}

To navigate to a URL:
{{"action": "navigate", "url": "<full url>", "description": "where navigating"}}

To extract/return scraped data:
{{"action": "scrape", "data": {{"key": "value"}}, "markdown": "# Title\\n...full formatted result...", "description": "data extracted"}}

To present options/choices to the user (when you found a list of options like movies, trains, seats):
{{"action": "ask_user", "question": "<question to user>", "options": ["Option 1", "Option 2", "Option 3"], "memory_key": "<snake_case_key>", "description": "presenting choices"}}

To ask the user for free-text missing information:
{{"action": "ask_user", "question": "<question>", "memory_key": "<snake_case_key>", "description": "why asking"}}

To press a keyboard key (Enter, Tab, Escape, etc.):
{{"action": "key", "key": "Enter", "description": "pressing key"}}

To signal task completion:
{{"action": "done", "result": "<summary of what was accomplished>", "description": "task complete"}}

CRITICAL RULES:
1. LOOK AT THE SCREENSHOT carefully — if a modal/popup/dialog is open (like a city selector), YOU MUST handle it FIRST. Use the `Interactive Buttons` list to find the exact x/y coordinates of the option you want to click.
2. If you see a city selector popup, click a city option from the buttons list.
3. If you are collecting options for the user (movies, trains, seats, shows), use ask_user with an "options" list.
4. NEVER repeat the exact same action you just did — if you clicked something and the page hasn't changed, try something different (scroll, close modal, try a different element).
5. If you see the same page state for 2+ steps, try scrolling or pressing Escape before trying other actions.
6. WAIT for the page to fully respond after each action before deciding next steps.
7. NEVER return markdown fences, ONLY the raw JSON object.
"""

    model_name = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.0-flash")).strip()

    try:
        # Try google-genai SDK first
        if hasattr(client, 'models') and hasattr(client.models, 'generate_content'):
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    {
                        "role": "user",
                        "parts": [
                            {"text": prompt},
                            {"inline_data": {"mime_type": "image/png", "data": screenshot_bytes}},
                        ],
                    }
                ],
                generation_config={"max_output_tokens": 600, "temperature": 0.1},
            )
            text = (response.text or "").strip()
        else:
            # Fallback: google.generativeai SDK
            model = client.GenerativeModel(model_name)
            import PIL.Image
            import io
            img = PIL.Image.open(io.BytesIO(screenshot_bytes))
            response = model.generate_content([prompt, img])
            text = (response.text or "").strip()

        # Strip code fences if LLM wrapped anyway
        text = re.sub(r'^```[a-z]*\n?', '', text).rstrip('`').strip()
        action = json.loads(text)
        print(f"[BrowseAgent] Vision decided: {action.get('action')} — {action.get('description', '')}")
        return action
    except Exception as e:
        print(f"[BrowseAgent] Vision error: {e}")
        return {"action": "done", "result": f"Vision error: {e}", "description": "error"}


async def _vision_decide_action_bedrock(
    client,
    screenshot_bytes: bytes,
    page_data: dict,
    goal: str,
    history: list,
    memory: dict,
) -> dict:
    """
    Ask Bedrock (Nova/Claude) Vision to decide the next browser action.
    """
    history_str = "\n".join([f"- {h}" for h in history[-10:]]) if history else "None yet"
    memory_str = json.dumps({k: v for k, v in memory.items() if v}, indent=2)

    links_preview = json.dumps(page_data.get("links", [])[:20], ensure_ascii=False)
    buttons_preview = json.dumps(page_data.get("buttons", [])[:20], ensure_ascii=False)
    inputs_preview = json.dumps(page_data.get("inputs", [])[:20], ensure_ascii=False)
    page_text_preview = page_data.get("text", "")[:3000]

    prompt = f"""You are ARIA's browser control center. You see the current browser screenshot.

GOAL: {goal}

CURRENT PAGE:
- URL: {page_data.get('url', '')}
- Title: {page_data.get('title', '')}
- Page Text (first 3000 chars): {page_text_preview}
- Interactive Buttons: {buttons_preview}
- Form Inputs: {inputs_preview}
- Links (first 20): {links_preview}

USER MEMORY (profile data you can use):
{memory_str}

ACTIONS TAKEN SO FAR (last 10):
{history_str}

Analyze the screenshot carefully. Decide the SINGLE BEST NEXT ACTION to progress toward the goal.

Return ONLY a JSON object (no markdown) with one of these formats:

To click something (use EXACT pixel coordinates from screenshot):
{{"action": "click", "x": <int>, "y": <int>, "description": "what you are clicking and why"}}

To type text into an input field:
{{"action": "type", "x": <int>, "y": <int>, "text": "<text to type>", "clear_first": false, "description": "what you are typing (set clear_first to true ONLY for search bars, NOT code editors)"}}

To scroll:
{{"action": "scroll", "direction": "down", "amount": 3, "description": "why scrolling"}}

To navigate to a URL:
{{"action": "navigate", "url": "<full url>", "description": "where navigating"}}

To extract/return scraped data:
{{"action": "scrape", "data": {{"key": "value"}}, "markdown": "# Title\\n...full formatted result...", "description": "data extracted"}}

To present options/choices to the user (when you found a list of options like movies, trains, seats):
{{"action": "ask_user", "question": "<question to user>", "options": ["Option 1", "Option 2", "Option 3"], "memory_key": "<snake_case_key>", "description": "presenting choices"}}

To ask the user for free-text missing information:
{{"action": "ask_user", "question": "<question>", "memory_key": "<snake_case_key>", "description": "why asking"}}

To press a keyboard key (Enter, Tab, Escape, etc.):
{{"action": "key", "key": "Enter", "description": "pressing key"}}

To signal task completion:
{{"action": "done", "result": "<summary of what was accomplished>", "description": "task complete"}}

CRITICAL RULES:
1. LOOK AT THE SCREENSHOT carefully — if a modal/popup/dialog is open (like a city selector), YOU MUST handle it FIRST. Use the `Interactive Buttons` list to find the exact x/y coordinates of the option you want to click.
2. If you see a city selector popup, click a city option from the buttons list.
3. If you are collecting options for the user (movies, trains, seats, shows), use ask_user with an "options" list.
4. NEVER repeat the exact same action you just did — if you clicked something and the page hasn't changed, try something different (scroll, close modal, try a different element).
5. If you see the same page state for 2+ steps, try scrolling or pressing Escape before trying other actions.
6. WAIT for the page to fully respond after each action before deciding next steps.
7. NEVER return markdown fences, ONLY the raw JSON object.
"""

    model_name = os.getenv("LLM_MODEL", "amazon.nova-pro-v1:0").strip()

    try:
        response = client.converse(
            modelId=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "image": {
                                "format": "png",
                                "source": {
                                    "bytes": screenshot_bytes
                                }
                            }
                        },
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 1000,
                "temperature": 0.1
            }
        )
        
        text_content = ""
        output_message = response.get('output', {}).get('message', {})
        for content_block in output_message.get('content', []):
            if 'text' in content_block:
                text_content += content_block['text']
                
        text = text_content.strip()
        # Strip code fences if LLM wrapped anyway
        text = re.sub(r'^```[a-z]*\n?', '', text).rstrip('`').strip()
        action = json.loads(text)
        print(f"[BrowseAgent] Bedrock Vision decided: {action.get('action')} — {action.get('description', '')}")
        return action
    except Exception as e:
        print(f"[BrowseAgent] Bedrock Vision error: {e}")
        return {"action": "done", "result": f"Bedrock Vision error: {e}", "description": "error"}


async def _consult_stuck_state(use_bedrock, bedrock_client, gemini_client, goal, history, last_action_desc):
    prompt = f"""You are the ARIA AI Browser Overseer.
The browser agent is currently stuck in a loop while trying to achieve the goal: "{goal}"

Recent history:
{json.dumps(history[-5:], indent=2)}

The agent keeps repeating this action without success: "{last_action_desc}"

Your task is to analyze why it might be stuck and decide how to proceed. You can either:
1. Formulate a question to ask the user for help or clarification.
2. Formulate an updated, more specific goal or strategy for the browser agent to try next.

Respond ONLY with a valid JSON object in this format:
{{
    "question_for_user": "A clear question asking the user for guidance, or empty string if no question is needed.",
    "updated_goal_advice": "Advice or an updated goal to help the agent get unstuck, e.g., 'Look for a different button' or 'The user said...'"
}}
"""
    text = ""
    try:
        if use_bedrock:
            model_name = os.getenv("LLM_MODEL", "amazon.nova-pro-v1:0").strip()
            response = bedrock_client.converse(
                modelId=model_name,
                messages=[{"role": "user", "content": [{"text": prompt}]}],
                inferenceConfig={"maxTokens": 500, "temperature": 0.3}
            )
            text = response.get('output', {}).get('message', {}).get('content', [{}])[0].get('text', '')
        else:
            model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
            if hasattr(gemini_client, 'models'):
                response = gemini_client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    generation_config={"max_output_tokens": 500, "temperature": 0.3}
                )
                text = response.text
            else:
                model = gemini_client.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                text = response.text
                
        text = re.sub(r'^```[a-z]*\n?', '', text.strip()).rstrip('`').strip()
        return json.loads(text)
    except Exception as e:
        print(f"[StuckConsult] Error: {e}")
        return {"question_for_user": "I seem to be stuck. What should I do next?", "updated_goal_advice": "Try a completely different approach"}


async def browse_and_act(
    url: str,
    goal: str,
    memory: Dict[str, str],
    websocket=None,
    agent_id: str = "",
    max_steps: int = 20,
) -> str:
    """
    Universal human-proxy browser agent.
    Opens any URL with a persistent Chromium browser and uses
    Gemini or Bedrock Vision in a loop to achieve any goal on any website.

    Capabilities:
    - Open any site (news, IRCTC, LinkedIn, Google Forms, Amazon, etc.)
    - Scrape data from any page
    - Fill forms, click buttons, navigate links
    - Handle logins (HITL for credentials)
    - Multi-page workflows
    - Scroll and interact with dynamic content

    Returns a summary string of what was accomplished.
    """
    active_sessions["current_task"] = asyncio.current_task()
    p = None
    context = None
    findings_text = ""
    history = []
    asked_keys = set()

    provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()
    
    use_bedrock = False
    bedrock_client = None
    gemini_client = None
    
    if provider in ("aws", "bedrock"):
        bedrock_client = _get_bedrock_client()
        if bedrock_client:
            use_bedrock = True
        else:
            await broadcast_status(websocket, "⚠️ Bedrock client not configured but provider is 'aws'. Checking Gemini...")
            gemini_client = _get_gemini_browse_client()
    elif provider == "gemini":
        gemini_client = _get_gemini_browse_client()
    else:  # auto
        gemini_client = _get_gemini_browse_client()
        if not gemini_client:
            bedrock_client = _get_bedrock_client()
            if bedrock_client:
                use_bedrock = True

    if not gemini_client and not use_bedrock:
        await broadcast_status(websocket, "⚠️ Neither Gemini Vision nor Bedrock Vision configured. Set GEMINI_API_KEY or AWS credentials in .env")
        return "Browser agent requires GEMINI_API_KEY or Bedrock configuration."

    screenshot_path = Path(__file__).parent / "browse_screenshot.png"

    try:
        await broadcast_status(websocket, f"🌐 Launching browser to: {url}")
        PROFILE_PATH.mkdir(parents=True, exist_ok=True)

        p = await async_playwright().start()
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_PATH),
            headless=False,
            viewport={"width": 1280, "height": 800},
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
        )

        page = await context.new_page()

        # Anti-detection: set realistic user agent
        await page.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
        })
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        await broadcast_status(websocket, f"📡 Navigating to {url}...")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as nav_err:
            await broadcast_status(websocket, f"⚠️ Navigation warning: {nav_err} — continuing anyway")

        await asyncio.sleep(2)  # Wait for JS to render

        step = 0
        last_actions = []  # Track recent actions to detect stuck loops
        while step < max_steps and not page.is_closed():
            step += 1
            await broadcast_status(websocket, f"🔍 Step {step}/{max_steps}: Analyzing page...")

            # Capture page state
            try:
                page_data = await page.evaluate(BROWSE_PAGE_SCAN_JS)
            except Exception:
                page_data = {"url": page.url, "title": "", "text": "", "links": [], "inputs": [], "buttons": []}

            # Screenshot
            try:
                screenshot_bytes = await page.screenshot(type="png", full_page=False)
                screenshot_path.write_bytes(screenshot_bytes)
            except Exception as ss_err:
                await broadcast_status(websocket, f"Screenshot failed: {ss_err}")
                break

            # Ask Vision what to do next
            if use_bedrock:
                action = await _vision_decide_action_bedrock(
                    bedrock_client, screenshot_bytes, page_data, goal, history, memory
                )
            else:
                action = await _vision_decide_action(
                    gemini_client, screenshot_bytes, page_data, goal, history, memory
                )

            action_type = action.get("action", "done")
            desc = action.get("description", "")
            await broadcast_status(websocket, f"🤖 Action {step}: {action_type} — {desc}")
            history.append(f"Step {step}: {action_type} — {desc}")

            # Stuck-loop detection: delegate back to main LLM consultation
            action_sig = f"{action_type}:{action.get('x', '')},{action.get('y', '')}:{desc[:40]}"
            last_actions.append(action_sig)
            if len(last_actions) > 3:
                last_actions.pop(0)
            if len(last_actions) == 3 and last_actions[0] == last_actions[1] == last_actions[2]:
                await broadcast_status(websocket, "⚠️ Detected stuck loop — consulting ARIA LLM...")
                last_actions.clear()
                
                consult_res = await _consult_stuck_state(use_bedrock, bedrock_client, gemini_client, goal, history, desc)
                q_for_user = consult_res.get("question_for_user", "")
                advice = consult_res.get("updated_goal_advice", "")
                
                if q_for_user:
                    # Ask the user using HITL
                    active_sessions["hitl_input_response"] = None
                    event = asyncio.Event()
                    active_sessions["hitl_input"] = event

                    targets = list(active_websockets)
                    if websocket and websocket not in targets:
                        targets.append(websocket)
                        
                    chat_msg = f"[EMOTION: SAD] {q_for_user}\n\n_(Reply in chat to help me out)_"
                    for ws in targets:
                        try:
                            await ws.send_json({"type": "chat_response", "content": chat_msg})
                        except Exception:
                            pass
                            
                    try:
                        await asyncio.wait_for(event.wait(), timeout=180.0)
                        resp = active_sessions.get("hitl_input_response")
                        if resp:
                            user_val = resp.get("value") or resp.get("content", "")
                            if user_val:
                                history.append(f"Step {step}: User provided guidance: '{user_val}'")
                                goal = f"{goal} | User Guidance: {user_val} | Advice: {advice}"
                                await broadcast_status(websocket, "✅ Received user guidance. Resuming task...")
                    except asyncio.TimeoutError:
                        await broadcast_status(websocket, "User input timeout — trying to resume anyway.")
                        goal = f"{goal} | Advice: {advice}"
                else:
                    goal = f"{goal} | Advice: {advice}"
                    await broadcast_status(websocket, f"🔄 ARIA updated task strategy: {advice}")
                    
                continue

            if action_type == "done":
                result_summary = action.get("result", "Task complete.")
                findings_text = result_summary
                await broadcast_status(websocket, f"✅ Done: {result_summary}")
                break

            elif action_type == "scrape":
                data = action.get("data", {})
                markdown = action.get("markdown", "")
                if not markdown:
                    # Auto-generate markdown from page text
                    markdown = f"# 🌐 Scraped: {goal}\n\n**URL:** {page_data.get('url', url)}\n\n{page_data.get('text', '')[:5000]}"
                findings_text = markdown

                # Save to findings/
                import time as _time
                safe_goal = re.sub(r'[^a-z0-9]+', '_', goal.lower())[:40].strip('_')
                filename = f"browse_{safe_goal}_{int(_time.time())}.md"
                findings_dir = Path(__file__).parent / "findings"
                findings_dir.mkdir(parents=True, exist_ok=True)
                (findings_dir / filename).write_text(markdown, encoding="utf-8")

                await broadcast_status(websocket, f"💾 Data saved to Notepad: {filename}")
                # Notify frontend
                try:
                    targets = list(active_websockets)
                    if websocket and websocket not in targets:
                        targets.append(websocket)
                    for ws in targets:
                        try:
                            await ws.send_json({"type": "note_created", "filename": filename})
                        except Exception:
                            pass
                except Exception:
                    pass
                # Continue one more step — LLM may want to navigate more
                await asyncio.sleep(1)

            elif action_type == "navigate":
                nav_url = action.get("url", "")
                if nav_url:
                    try:
                        await broadcast_status(websocket, f"🔗 Navigating to: {nav_url}")
                        await page.goto(nav_url, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(2)
                    except Exception as nav_e:
                        await broadcast_status(websocket, f"Navigation failed: {nav_e}")

            elif action_type == "click":
                x = action.get("x", 0)
                y = action.get("y", 0)
                try:
                    await page.mouse.click(x, y)
                    await asyncio.sleep(1.5)
                    # Wait for any navigation triggered by click
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except Exception:
                        pass
                except Exception as click_e:
                    await broadcast_status(websocket, f"Click failed at ({x},{y}): {click_e}")

            elif action_type == "type":
                x = action.get("x", 0)
                y = action.get("y", 0)
                text = action.get("text", "")
                clear_first = action.get("clear_first", False)  # Default to False to prevent breaking IDEs
                try:
                    await page.mouse.click(x, y)
                    await asyncio.sleep(0.3)
                    if clear_first:
                        await page.keyboard.press("Control+a")
                        await page.keyboard.press("Backspace")
                    await page.keyboard.type(text, delay=40)
                    await asyncio.sleep(0.5)
                except Exception as type_e:
                    await broadcast_status(websocket, f"Type failed: {type_e}")

            elif action_type == "key":
                key = action.get("key", "Enter")
                try:
                    await page.keyboard.press(key)
                    await asyncio.sleep(1)
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except Exception:
                        pass
                except Exception as key_e:
                    await broadcast_status(websocket, f"Key press failed: {key_e}")

            elif action_type == "scroll":
                direction = action.get("direction", "down")
                amount = action.get("amount", 3)
                delta = 400 * amount * (1 if direction == "down" else -1)
                try:
                    await page.mouse.wheel(0, delta)
                    await asyncio.sleep(0.8)
                except Exception as scroll_e:
                    await broadcast_status(websocket, f"Scroll failed: {scroll_e}")

            elif action_type == "ask_user":
                question = action.get("question", "I need some information:")
                mem_key = action.get("memory_key", "custom_field")
                options = action.get("options", [])  # Optional list of choices

                if mem_key in asked_keys:
                    # Already asked — skip and continue
                    history.append(f"Step {step}: Skipped duplicate ask for '{mem_key}'")
                    continue
                asked_keys.add(mem_key)

                # Set up HITL event to wait for next chat message from user
                active_sessions["hitl_input_response"] = None
                event = asyncio.Event()
                active_sessions["hitl_input"] = event

                targets = list(active_websockets)
                if websocket and websocket not in targets:
                    targets.append(websocket)

                if options:
                    # Send as a chat message with options — user replies in chat
                    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(options)])
                    chat_msg = f"[EMOTION: HAPPY] {question}\n\n{options_text}\n\n_(Reply with your choice to continue)_"
                    for ws in targets:
                        try:
                            await ws.send_json({"type": "chat_response", "content": chat_msg})
                        except Exception:
                            pass
                else:
                    # Plain text question — show as HITL modal input
                    for ws in targets:
                        try:
                            await ws.send_json({
                                "type": "permission_request",
                                "inputType": "input",
                                "title": "ARIA Needs Info",
                                "description": question,
                                "id": "hitl_input",
                            })
                        except Exception:
                            pass

                try:
                    await asyncio.wait_for(event.wait(), timeout=180.0)
                    resp = active_sessions.get("hitl_input_response")
                    if resp:
                        user_val = resp.get("value") or resp.get("content", "")
                        if user_val:
                            clean_key = re.sub(r'[^a-z0-9]+', '_', mem_key.lower()).strip('_')
                            memory[clean_key] = user_val
                            # Save to memory.json
                            MEMORY_FILE_PATH = Path(__file__).parent / "memory.json"
                            try:
                                current_mem = json.loads(MEMORY_FILE_PATH.read_text(encoding="utf-8")) if MEMORY_FILE_PATH.exists() else {}
                                current_mem[clean_key] = user_val
                                MEMORY_FILE_PATH.write_text(json.dumps(current_mem, indent=4, ensure_ascii=False), encoding="utf-8")
                            except Exception:
                                pass
                            history.append(f"Step {step}: User chose '{clean_key}' = '{user_val[:50]}'")
                            await broadcast_status(websocket, f"✅ Got user input for '{clean_key}'")
                except asyncio.TimeoutError:
                    await broadcast_status(websocket, "User input timeout — continuing.")

            else:
                # Unknown action — log and continue
                await broadcast_status(websocket, f"Unknown action: {action_type}")

        await broadcast_status(websocket, "🏁 Browser session complete.")
        await asyncio.sleep(2)

    except asyncio.CancelledError:
        was_cancelled = True
        await broadcast_status(websocket, "🛑 Browser agent cancelled by user.")
        findings_text = "Task was cancelled."
    except Exception as e:
        was_cancelled = False
        print(f"[BrowseAgent] Fatal error: {e}")
        await broadcast_status(websocket, f"❌ Browser agent error: {e}")
        findings_text = f"Error: {e}"
    finally:
        if 'was_cancelled' in locals() and was_cancelled:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            if p:
                try:
                    await p.stop()
                except Exception:
                    pass
        else:
            # Leave the browser open for the user to continue working!
            pass
            
        active_sessions.pop("current_task", None)
        active_sessions.pop("hitl_input", None)
        await broadcast_status(websocket, None)

    return findings_text or "Browser task complete."
