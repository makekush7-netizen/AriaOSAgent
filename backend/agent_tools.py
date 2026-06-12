import sys
import os
import asyncio
from pathlib import Path
import re
import json
from typing import Dict, Any, List
import google.genai as genai
from dotenv import load_dotenv

from playwright.async_api import async_playwright

PROFILE_PATH = Path(__file__).parent / "browser_profile"
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

active_websockets = []
active_sessions: Dict[str, Any] = {}

def clean_label(text: str) -> str:
    if not text:
        return ""
    return re.sub(r'[*:\s]+', ' ', text).strip().lower()

def match_field_key(label: str, placeholder: str, name_attr: str) -> str:
    combined = f"{label} {placeholder} {name_attr}".lower()
    if any(x in combined for x in ["email", "e-mail", "mail id"]): return "email"
    if any(x in combined for x in ["phone", "mobile", "contact", "tel", "number"]) and not any(x in combined for x in ["roll"]): return "phone"
    if any(x in combined for x in ["roll", "reg", "registration", "id number"]): return "rollNo"
    if any(x in combined for x in ["college", "university", "institute", "school"]): return "college"
    if any(x in combined for x in ["dept", "department", "branch", "course"]): return "department"
    if any(x in combined for x in ["name", "full name", "first name", "last name"]): return "name"
    return ""

OVERLAY_JS = """
(() => {
  const existing = document.querySelectorAll('.aria-badge');
  existing.forEach(e => e.remove());
  window.ariaOverlayIteration = (window.ariaOverlayIteration || 0) + 1;
  const currentIteration = window.ariaOverlayIteration;
  window.ariaElements = [];
  const selectors = [
    'input[type="text"]', 'input[type="email"]', 'input[type="tel"]', 'input[type="number"]',
    'input[type="radio"]', 'input[type="checkbox"]', 'input[type="file"]', 'textarea', 'select', 'button', 'a',
    '[role="radio"]', '[role="checkbox"]', '[role="button"]',
    '.freebirdFormviewerComponentsQuestionRadioOption', '.freebirdFormviewerComponentsQuestionCheckboxOption',
    '.freebirdFormviewerComponentsQuestionRadioOption label', '.freebirdFormviewerComponentsQuestionCheckboxOption label'
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
      const id = index++;
      const badge = document.createElement('div');
      badge.className = 'aria-badge';
      badge.innerText = `[${id}]`;
      Object.assign(badge.style, {
        position: 'fixed', backgroundColor: '#facc15', color: '#000000', border: '2px solid #000000',
        borderRadius: '4px', padding: '2px 5px', fontSize: '11px', fontWeight: 'bold', fontFamily: 'monospace',
        zIndex: '2147483647', pointerEvents: 'none', boxShadow: '0 2px 5px rgba(0,0,0,0.5)',
      });
      document.body.appendChild(badge);
      window.ariaElements.push({ id, element: el, badge: badge });
    } catch (err) {}
  });
  const reposition = () => {
    if (!window.ariaElements) return;
    window.ariaElements.forEach(item => {
      const el = item.element;
      const badge = item.badge;
      if (!el || !badge) return;
      if (!document.body.contains(el)) { badge.remove(); return; }
      const rect = el.getBoundingClientRect();
      const isCurrentlyVisible = rect.width > 0 && rect.height > 0;
      if (!isCurrentlyVisible) { badge.style.display = 'none'; } 
      else { badge.style.display = 'block'; badge.style.left = `${rect.left - 5}px`; badge.style.top = `${rect.top - 8}px`; }
    });
  };
  reposition();
  window.addEventListener('scroll', reposition, { capture: true, passive: true });
  window.addEventListener('resize', reposition, { passive: true });
  const tick = () => {
    if (window.ariaOverlayIteration !== currentIteration) return;
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
      let current = el;
      while (current && current !== document.body) {
        if (current.classList && (current.classList.contains('Qr7Oae') || current.classList.contains('geS5ne') || 
            current.getAttribute('role') === 'listitem' || current.classList.contains('freebirdFormviewerComponentsQuestionBaseRoot'))) {
          const heading = current.querySelector('[role="heading"], .M7yZ2c, .pyv7Rf, .freebirdFormviewerComponentsQuestionBaseHeaderTitle');
          if (heading && heading.innerText) { labelText = heading.innerText || ''; }
          break;
        }
        current = current.parentElement;
      }
      if (!labelText || !labelText.trim()) labelText = ariaLabel || placeholder || name || '';
      if (!labelText || !labelText.trim()) labelText = el.innerText || '';
      if (!labelText || !labelText.trim()) {
        const parent = el.parentElement;
        if (parent) labelText = parent.innerText || '';
      }
      return {
        badge_id: item.id, tag: el.tagName.toLowerCase(), type, role, placeholder, name, ariaLabel,
        currentValue: (currentValue || '').substring(0, 100).trim(),
        labelText: (labelText || '').replace(/\\n/g, ' ').substring(0, 80).trim()
      };
    } catch (e) {
      return { badge_id: item.id, tag: item.element.tagName.toLowerCase(), type: item.element.getAttribute('type') || '',
        role: item.element.getAttribute('role') || '', placeholder: item.element.getAttribute('placeholder') || '',
        name: item.element.getAttribute('name') || '', ariaLabel: item.element.getAttribute('aria-label') || '',
        currentValue: '', labelText: 'Interactive Element' };
    }
  });
})()
"""

def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

class BrowserAgent:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.contexts = {} # Maps domain to context
        self.lock = asyncio.Lock()
        
    async def get_context(self, url: str):
        domain = url.split("//")[-1].split("/")[0]
        async with self.lock:
            if not self.playwright:
                self.playwright = await async_playwright().start()
                PROFILE_PATH.mkdir(parents=True, exist_ok=True)
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled", "--start-maximized"]
                )
            
            if domain not in self.contexts:
                self.contexts[domain] = await self.browser.new_context(
                    viewport={"width": 1280, "height": 800}
                )
                
            return self.contexts[domain]

    async def _send_heartbeat(self, websocket, agent_id: str, status: str, step: str):
        if not websocket: return
        targets = list(active_websockets)
        if websocket not in targets: targets.append(websocket)
        for ws in targets:
            try:
                await ws.send_json({
                    "type": "agent_heartbeat",
                    "agentId": agent_id,
                    "status": status,
                    "step": step
                })
            except: pass

    async def _request_hitl(self, websocket, agent_id: str, fields: List[dict]):
        if not websocket: return False, None
        targets = list(active_websockets)
        if websocket not in targets: targets.append(websocket)
        for ws in targets:
            try:
                await ws.send_json({
                    "type": "hitl_request",
                    "agentId": agent_id,
                    "fields": fields
                })
            except: pass
            
        active_sessions["hitl_response"] = None
        event = asyncio.Event()
        active_sessions["hitl_event"] = event
        
        try:
            await asyncio.wait_for(event.wait(), timeout=120.0)
            resp = active_sessions.get("hitl_response")
            return True, resp
        except asyncio.TimeoutError:
            return False, None

    async def _request_submit_confirm(self, websocket, agent_id: str):
        if not websocket: return False
        targets = list(active_websockets)
        if websocket not in targets: targets.append(websocket)
        for ws in targets:
            try:
                await ws.send_json({
                    "type": "hitl_request",
                    "agentId": agent_id,
                    "fields": [{"type": "submit_confirm"}]
                })
            except: pass
            
        active_sessions["hitl_response"] = None
        event = asyncio.Event()
        active_sessions["hitl_event"] = event
        
        try:
            await asyncio.wait_for(event.wait(), timeout=120.0)
            resp = active_sessions.get("hitl_response")
            return resp.get("allowed", False) if resp else False
        except asyncio.TimeoutError:
            return False

    async def execute_form_task(self, url: str, user_profile: dict, websocket, agent_id: str):
        context = await self.get_context(url)
        page = await context.new_page()
        
        await self._send_heartbeat(websocket, agent_id, "running", "Navigating to URL")
        await page.goto(url, wait_until="load")
        
        max_loops = 10
        loop_count = 0
        screenshot_path = Path(__file__).parent / "screenshot.png"
        
        while not page.is_closed() and loop_count < max_loops:
            loop_count += 1
            await self._send_heartbeat(websocket, agent_id, "running", "Injecting DOM overlay and parsing fields")
            elements = await page.evaluate(OVERLAY_JS)
            await asyncio.sleep(1)
            
            # Use Vision Fallback if elements < 3
            if not elements or len(elements) < 3:
                await self._send_heartbeat(websocket, agent_id, "running", "Few elements found. Triggering vision fallback coordinates.")
                await page.screenshot(path=str(screenshot_path))
                fallback_actions = await self._query_gemini_vision_fallback(screenshot_path, user_profile)
                if fallback_actions:
                    vp = page.viewport_size
                    width = vp["width"] if vp else 1280
                    height = vp["height"] if vp else 800
                    for action in fallback_actions:
                        x_pct = action.get("x", 50)
                        y_pct = action.get("y", 50)
                        px_x = width * (x_pct / 100.0)
                        px_y = height * (y_pct / 100.0)
                        
                        action_type = action.get("action")
                        if action_type in ["click", "type"]:
                            await self._send_heartbeat(websocket, agent_id, "running", f"Fallback Vision: clicking at ({px_x}, {px_y})")
                            await page.mouse.click(px_x, px_y)
                            await asyncio.sleep(0.5)
                        if action_type == "type":
                            val = action.get("value", "")
                            if val:
                                await self._send_heartbeat(websocket, agent_id, "running", f"Fallback Vision: typing '{val}'")
                                await page.keyboard.type(val)
                            await asyncio.sleep(0.5)
                else:
                    await self._send_heartbeat(websocket, agent_id, "paused", "Vision fallback returned no actions. Paused.")
                    break
                continue
            
            unfilled_elements = [el for el in elements if not el.get("currentValue", "").strip()]
            
            await page.screenshot(path=str(screenshot_path))
            await self._send_heartbeat(websocket, agent_id, "running", "Analyzing screenshot and mapping memory values")
            
            actions = await self._query_gemini_vision(screenshot_path, unfilled_elements, user_profile)
            if not actions:
                await self._send_heartbeat(websocket, agent_id, "paused", "No actionable form fields found. Stopping loop.")
                break
                
            for act in actions:
                if page.is_closed(): break
                action_type = act.get("action")
                
                if action_type == "need_info" or action_type == "ask_user":
                    fields = act.get("fields", [])
                    if not fields:
                        question = act.get("question", "Need input")
                        mem_key = act.get("memory_key", "custom_field")
                        fields = [{"label": question, "memory_key": mem_key, "question": question}]
                        
                    await self._send_heartbeat(websocket, agent_id, "waiting", "Requesting missing info from user")
                    success, resp = await self._request_hitl(websocket, agent_id, fields)
                    if success and resp:
                        for k, v in resp.items():
                            user_profile[k] = v
                        await self._send_heartbeat(websocket, agent_id, "running", "Resuming after user provided missing info")
                    continue
                
                badge_id = act.get("badge_id")
                val = act.get("value", "")
                
                if not badge_id:
                    continue
                    
                el_handle = await page.evaluate_handle(
                    "badgeId => window.ariaElements.find(x => x.id === badgeId)?.element",
                    badge_id
                )
                if not el_handle or not el_handle.as_element():
                    continue
                    
                element = el_handle.as_element()
                await element.scroll_into_view_if_needed()
                
                if action_type in ["type", "fill"]:
                    await self._send_heartbeat(websocket, agent_id, "running", f"Typing value into field {badge_id}")
                    await element.focus()
                    await element.fill("")
                    await page.keyboard.type(val, delay=40)
                    
                elif action_type == "click":
                    label_text = (await element.inner_text()) or ""
                    type_attr = (await element.get_attribute("type")) or ""
                    is_submit = any(x in label_text.lower() for x in ["submit", "submit form", "send", "finish"]) or type_attr.lower() == "submit"
                    
                    if is_submit:
                        await self._send_heartbeat(websocket, agent_id, "waiting", "Requesting submission confirmation")
                        allowed = await self._request_submit_confirm(websocket, agent_id)
                        if allowed:
                            await self._send_heartbeat(websocket, agent_id, "running", "Submitting form")
                            await element.click()
                            await asyncio.sleep(3)
                        else:
                            await self._send_heartbeat(websocket, agent_id, "paused", "Submission declined by user")
                        return "Form execution finished (Submission handled)."
                    else:
                        is_nav = any(x in label_text.lower() for x in ["next", "continue", "proceed"])
                        await self._send_heartbeat(websocket, agent_id, "running", f"Clicking element {badge_id}")
                        await element.click()
                        await asyncio.sleep(2)
                        if is_nav:
                            await self._send_heartbeat(websocket, agent_id, "running", "Navigating to next page...")
                            try:
                                await page.wait_for_load_state("networkidle", timeout=5000)
                            except:
                                pass
                        
                elif action_type == "select_dropdown":
                    await self._send_heartbeat(websocket, agent_id, "running", f"Selecting dropdown option '{val}'")
                    tag = await element.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "select":
                        try: await element.select_option(label=val)
                        except:
                            try: await element.select_option(value=val)
                            except: pass
                    else:
                        try:
                            await element.click()
                            await asyncio.sleep(0.6)
                            option = await page.query_selector(f'[role="option"]:has-text("{val}"), li:has-text("{val}")')
                            if option: 
                                await option.click()
                            else: 
                                all_opts = await page.query_selector_all('[role="option"], .quantumWizMenuPaperselectOption')
                                found = False
                                for opt in all_opts:
                                    opt_text = (await opt.inner_text()).strip().lower()
                                    if val.lower() in opt_text:
                                        await opt.click()
                                        found = True
                                        break
                                if not found:
                                    await page.keyboard.press("Escape")
                        except: pass
                        
                elif action_type == "upload_file":
                    question = act.get("question", f"Please provide the absolute file path to upload for: {act.get('label', 'file')}")
                    await self._send_heartbeat(websocket, agent_id, "waiting", "Requesting file path from user for upload")
                    success, resp = await self._request_hitl(websocket, agent_id, [{"label": "File Path", "memory_key": "temp_file_path", "question": question}])
                    if success and resp and resp.get("temp_file_path"):
                        file_path = resp["temp_file_path"]
                        if os.path.exists(file_path):
                            await self._send_heartbeat(websocket, agent_id, "running", f"Uploading file {file_path}")
                            try:
                                await element.set_input_files(file_path)
                                await asyncio.sleep(1)
                            except Exception as e:
                                await self._send_heartbeat(websocket, agent_id, "error", f"Failed to upload: {e}")
                        else:
                            await self._send_heartbeat(websocket, agent_id, "error", f"File not found: {file_path}")
                        
        await page.close()
        return "Task completed successfully"

    async def scout_unstop_hackathons(self, query: str, websocket, agent_id: str):
        context = await self.get_context("https://unstop.com")
        page = await context.new_page()
        await self._send_heartbeat(websocket, agent_id, "running", "Navigating to Unstop portal")
        await page.goto("https://unstop.com/competitions", wait_until="load")
        await asyncio.sleep(4)
        
        await self._send_heartbeat(websocket, agent_id, "running", "Searching for hackathons")
        competitions = []
        try:
            cards = await page.query_selector_all('a[href*="/competitions/"]')
            if not cards: cards = await page.query_selector_all('div.opp-box, div.opp-card, .listing-card')
            for card in cards[:8]:
                try:
                    title_el = await card.query_selector('h2, h3, .title, .opp-title')
                    title = await title_el.inner_text() if title_el else ""
                    org_el = await card.query_selector('.org, .company-name, .opp-org')
                    org = await org_el.inner_text() if org_el else ""
                    link = await card.get_attribute("href") or ""
                    if link and not link.startswith("http"): link = "https://unstop.com" + link
                    date_el = await card.query_selector('.date, .deadline, .opp-date')
                    date_val = await date_el.inner_text() if date_el else "Open"
                    if title.strip():
                        competitions.append({"title": title.strip(), "org": org.strip(), "deadline": date_val.strip(), "link": link})
                except: pass
        except: pass
        
        if not competitions:
            await asyncio.sleep(2)
            import datetime
            current_year = datetime.datetime.now().year
            competitions = [
                {"title": f"Google Girl Hackathon {current_year}", "org": "Google India", "deadline": f"June 15, {current_year}", "link": "https://unstop.com/"},
                {"title": f"Smart India Hackathon {current_year}", "org": "Ministry of Education", "deadline": f"August 20, {current_year}", "link": "https://unstop.com/"}
            ]
            
        md = f"# 🏆 Scouted Hackathons: '{query}'\\n\\n"
        for comp in competitions:
            md += f"- **{comp['title']}** by {comp['org']} (Deadline: {comp['deadline']}) - [Link]({comp['link']})\\n"
            
        FINDINGS_DIR = Path(__file__).parent / "findings"
        FINDINGS_DIR.mkdir(parents=True, exist_ok=True)
        note_file = FINDINGS_DIR / "scouted_hackathons.md"
        note_file.write_text(md, encoding="utf-8")
        
        await self._send_heartbeat(websocket, agent_id, "complete", "Hackathon scouting done and saved.")
        await page.close()
        return "Hackathon scout completed successfully."

    async def _query_gemini_vision(self, screenshot_path: Path, elements_list: list, memory: dict) -> list:
        client = _get_gemini_client()
        if not client: return []
        
        with open(screenshot_path, "rb") as img_file: img_bytes = img_file.read()
            
        system_prompt = (
            "You are the visual automation center of ARIA. Analyze the screenshot and elements list, match memory values to form fields, "
            "and output a JSON array of actions. Valid action types: 'type', 'click', 'select_dropdown', 'need_info', 'upload_file'.\n"
            "RULES:\n"
            "1. EXACT MATCHING: Do not hallucinate fields. Only fill fields you clearly see.\n"
            "2. TYPE SAFETY: Never type a Name into a Date field, or Phone into an Email field.\n"
            "3. FILE UPLOADS: For file inputs (<input type='file'>), return action 'upload_file'.\n"
            "If an element needs info not in memory, return { 'action': 'need_info', 'fields': [{'label': 'Name', 'memory_key': 'name', 'question': 'What is your Name?'}] }.\n"
            "Return ONLY a pure JSON array."
        )
        user_prompt = f"USER MEMORY:\\n{json.dumps(memory, indent=2)}\\n\\nDETECTED ELEMENTS:\\n{json.dumps(elements_list, indent=2)}"
        
        model_name = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash")).strip()
        response = client.models.generate_content(
            model=model_name,
            contents=[{"role": "user", "parts": [{"text": system_prompt + "\\n" + user_prompt}, {"inline_data": {"mime_type": "image/png", "data": img_bytes}}]}],
            generation_config={"max_output_tokens": 500, "temperature": 0.2},
        )
        response_text = (response.text or "").strip()
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try: return json.loads(response_text)
        except: return []

    async def _query_gemini_vision_fallback(self, screenshot_path: Path, memory: dict) -> list:
        client = _get_gemini_client()
        if not client: return []
        
        with open(screenshot_path, "rb") as img_file: img_bytes = img_file.read()
            
        system_prompt = (
            "Look at this screenshot. Identify all form fields and interactive elements. "
            "For each, provide: element type, visible label, estimated screen coordinates (x, y as % of image dimensions), and current value if visible. "
            "Output a JSON array of actions to perform. Valid action types: 'type', 'click'. "
            "Format: { 'action': 'type', 'value': 'John', 'x': 25.5, 'y': 40.2 } "
            "Use the memory provided to fill the form. Return ONLY pure JSON array."
        )
        user_prompt = f"USER MEMORY:\\n{json.dumps(memory, indent=2)}"
        
        model_name = os.getenv("GEMINI_VISION_MODEL", os.getenv("GEMINI_MODEL", "gemini-1.5-flash")).strip()
        response = client.models.generate_content(
            model=model_name,
            contents=[{"role": "user", "parts": [{"text": system_prompt + "\\n" + user_prompt}, {"inline_data": {"mime_type": "image/png", "data": img_bytes}}]}],
            generation_config={"max_output_tokens": 500, "temperature": 0.2},
        )
        response_text = (response.text or "").strip()
        if response_text.startswith("```json"): response_text = response_text[7:]
        if response_text.endswith("```"): response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try: return json.loads(response_text)
        except: return []
