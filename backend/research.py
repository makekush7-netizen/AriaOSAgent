"""
ARIA Research Agent
Multi-step research pipeline: decompose → search → fetch → synthesize → assemble.

Requires: tavily-python, httpx, beautifulsoup4
Falls back gracefully if these are not installed.

Usage:
    from research import ResearchAgent, research_agent
    result = await research_agent.research("What is the state of robotics in India?", ws, agent_id)
    print(result.to_markdown())
"""

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# ─── Optional imports ────────────────────────────────────────────────────────
_tavily_available = False
_httpx_available = False
_bs4_available = False

try:
    from tavily import TavilyClient
    _tavily_available = True
except ImportError:
    print("[ResearchAgent] tavily-python not installed. Run: pip install tavily-python")

try:
    import httpx
    _httpx_available = True
except ImportError:
    print("[ResearchAgent] httpx not installed. Run: pip install httpx")

try:
    from bs4 import BeautifulSoup
    _bs4_available = True
except ImportError:
    print("[ResearchAgent] beautifulsoup4 not installed. Run: pip install beautifulsoup4")

# ─── Result dataclass ────────────────────────────────────────────────────────

@dataclass
class ResearchResult:
    query: str
    sub_questions: list[str] = field(default_factory=list)
    findings: dict = field(default_factory=dict)  # sub_question → synthesis
    sources: list[dict] = field(default_factory=list)  # {url, title, used_for}

    def to_markdown(self) -> str:
        lines = [f"# 🔬 Research: {self.query}\n"]

        for i, q in enumerate(self.sub_questions, 1):
            lines.append(f"## {i}. {q}")
            synthesis = self.findings.get(q, "No synthesis available.")
            lines.append(synthesis)
            lines.append("")

        if self.sources:
            lines.append("## Sources")
            for s in self.sources:
                title = s.get("title") or s.get("url", "")
                url = s.get("url", "")
                used_for = s.get("used_for", "")
                lines.append(f"- [{title}]({url})" + (f" — *{used_for}*" if used_for else ""))

        lines.append(f"\n*Research completed by ARIA at {time.strftime('%Y-%m-%d %H:%M')}*")
        return "\n".join(lines)


# ─── Research Agent ───────────────────────────────────────────────────────────

FINDINGS_DIR = Path(__file__).parent / "findings"
FINDINGS_DIR.mkdir(parents=True, exist_ok=True)


class ResearchAgent:
    """
    Five-step research pipeline. Requires tavily-python + httpx + beautifulsoup4.
    Falls back to a helpful error message if dependencies are missing.
    """

    def __init__(self):
        self._tavily: Optional[TavilyClient] = None  # type: ignore
        if _tavily_available:
            api_key = os.getenv("TAVILY_API_KEY", "").strip()
            if api_key:
                self._tavily = TavilyClient(api_key=api_key)
            else:
                print("[ResearchAgent] TAVILY_API_KEY not set in .env — search will be skipped.")

    def _get_gemini_client(self):
        try:
            import google.genai as genai
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not api_key:
                return None
            return genai.Client(api_key=api_key)
        except Exception:
            return None

    def _llm(self, prompt: str, max_tokens: int = 1000) -> str:
        """Simple single-turn Gemini call."""
        client = self._get_gemini_client()
        if not client:
            return ""
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config={"max_output_tokens": max_tokens, "temperature": 0.3},
            )
            text = (response.text or "").strip()
            # Strip code fences if present
            if text.startswith("```"):
                text = re.sub(r'^```[a-z]*\n?', '', text).rstrip('`').strip()
            return text
        except Exception as e:
            print(f"[ResearchAgent] LLM error: {e}")
            return ""

    async def _broadcast(self, websocket, message: dict):
        """Send to primary websocket + all active_websockets."""
        targets = set()
        if websocket:
            targets.add(websocket)
        try:
            from agent_tools import active_websockets
            for ws in active_websockets:
                targets.add(ws)
        except Exception:
            pass
        for ws in targets:
            try:
                await ws.send_json(message)
            except Exception:
                pass

    async def _heartbeat(self, agent_id: str, step: str, websocket):
        await self._broadcast(websocket, {
            "type": "agent_heartbeat",
            "agentId": agent_id,
            "status": "running",
            "step": step,
        })
        # Also send as task_update for backward compat
        await self._broadcast(websocket, {
            "type": "task_update",
            "task": step,
        })

    async def research(self, query: str, websocket, agent_id: str) -> ResearchResult:
        """
        Full 5-step research pipeline. Sends heartbeats at each step.
        """
        result = ResearchResult(query=query)

        # ── Step 1: Decompose ────────────────────────────────────────────────
        await self._heartbeat(agent_id, "Step 1/5: Decomposing research query...", websocket)

        decompose_prompt = (
            f'Break this research query into 3-4 focused sub-questions that together fully answer it.\n'
            f'Return ONLY a JSON array of strings. No extra text.\n\n'
            f'Query: "{query}"'
        )
        loop = asyncio.get_event_loop()
        decompose_raw = await loop.run_in_executor(None, self._llm, decompose_prompt, 300)

        try:
            sub_questions = json.loads(decompose_raw)
            if not isinstance(sub_questions, list):
                raise ValueError("Not a list")
        except Exception:
            # Fallback: use the original query as a single sub-question
            sub_questions = [query]

        result.sub_questions = sub_questions[:4]  # Cap at 4
        await self._heartbeat(agent_id, f"Step 2/5: Searching {len(result.sub_questions)} sub-questions...", websocket)

        # ── Step 2: Search (parallel) ────────────────────────────────────────
        search_results: dict[str, list[dict]] = {}

        if self._tavily:
            async def _search_one(sq: str):
                try:
                    resp = await loop.run_in_executor(
                        None,
                        lambda: self._tavily.search(sq, max_results=3)
                    )
                    return sq, resp.get("results", [])
                except Exception as e:
                    print(f"[ResearchAgent] Search error for '{sq}': {e}")
                    return sq, []

            search_tasks = [_search_one(sq) for sq in result.sub_questions]
            search_outputs = await asyncio.gather(*search_tasks)
            for sq, res in search_outputs:
                search_results[sq] = res
        else:
            # No Tavily — synthesize from LLM knowledge only
            for sq in result.sub_questions:
                search_results[sq] = []

        # Collect unique URLs + build source list
        url_to_content: dict[str, str] = {}
        for sq, res_list in search_results.items():
            for r in res_list:
                url = r.get("url", "")
                title = r.get("title", url)
                if url:
                    result.sources.append({"url": url, "title": title, "used_for": sq})
                    if url not in url_to_content:
                        url_to_content[url] = r.get("content", "")  # Tavily sometimes returns excerpt

        await self._heartbeat(agent_id, f"Step 3/5: Fetching {len(url_to_content)} pages...", websocket)

        # ── Step 3: Fetch (parallel) ─────────────────────────────────────────
        if _httpx_available and _bs4_available and url_to_content:
            async def _fetch_one(url: str) -> tuple[str, str]:
                if url_to_content.get(url):
                    return url, url_to_content[url][:2000]  # Already have excerpt
                try:
                    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
                        r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                        soup = BeautifulSoup(r.text, "html.parser")
                        # Remove nav/footer/script/style tags
                        for tag in soup(["nav", "footer", "script", "style", "aside", "header"]):
                            tag.decompose()
                        text = soup.get_text(separator=" ", strip=True)
                        return url, text[:2000]
                except Exception:
                    return url, ""

            fetch_tasks = [_fetch_one(url) for url in list(url_to_content.keys())[:12]]
            fetch_results = await asyncio.gather(*fetch_tasks)
            for url, content in fetch_results:
                if content:
                    url_to_content[url] = content

        await self._heartbeat(agent_id, "Step 4/5: Synthesizing findings...", websocket)

        # ── Step 4: Synthesize ───────────────────────────────────────────────
        for i, sq in enumerate(result.sub_questions):
            # Gather relevant excerpts for this sub-question
            relevant_excerpts = []
            sq_sources = search_results.get(sq, [])
            for j, r in enumerate(sq_sources):
                url = r.get("url", "")
                content = url_to_content.get(url, r.get("content", ""))[:1500]
                if content:
                    relevant_excerpts.append(f"[Source {j+1}] ({url})\n{content}")

            if relevant_excerpts:
                context_str = "\n\n".join(relevant_excerpts[:3])
                synth_prompt = (
                    f"Based on the following sources, answer this sub-question in 2-3 clear sentences. "
                    f"Be factual and direct. Cite sources as [Source N].\n\n"
                    f"Sub-question: {sq}\n\n"
                    f"Sources:\n{context_str}"
                )
            else:
                # No sources — answer from LLM knowledge
                synth_prompt = (
                    f"Answer this question in 2-3 clear, factual sentences based on your knowledge:\n\n{sq}"
                )

            synthesis = await loop.run_in_executor(None, lambda p=synth_prompt: self._llm(p, 300))
            result.findings[sq] = synthesis or "No synthesis available."

            await self._heartbeat(
                agent_id,
                f"Step 4/5: Synthesized {i+1}/{len(result.sub_questions)} sub-questions...",
                websocket
            )

        # ── Step 5: Assemble & save ─────────────────────────────────────────
        await self._heartbeat(agent_id, "Step 5/5: Assembling research report...", websocket)

        md_content = result.to_markdown()
        timestamp = int(time.time())
        safe_query = re.sub(r'[^a-z0-9]+', '_', query.lower())[:40].strip('_')
        filename = f"research_{safe_query}_{timestamp}.md"
        output_path = FINDINGS_DIR / filename

        try:
            output_path.write_text(md_content, encoding="utf-8")
            print(f"[ResearchAgent] Report saved: {output_path}")
        except Exception as e:
            print(f"[ResearchAgent] Save error: {e}")

        # Notify frontend about the new note (so NotepadPanel refreshes)
        await self._broadcast(websocket, {
            "type": "note_created",
            "filename": filename,
        })

        return result


# Global singleton
research_agent = ResearchAgent()
