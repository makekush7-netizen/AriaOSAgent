"""
ARIA Sub-Agent Orchestrator
Manages lifecycle of background agents: spawn, heartbeat, HITL, complete.
Emits WebSocket messages: agent_spawn, agent_heartbeat, agent_complete.

All agents run as asyncio Tasks so the WebSocket event loop is never blocked.
"""

import asyncio
import uuid
from typing import Dict, Any, Callable, Coroutine, Optional
from pathlib import Path
import json


class AgentSession:
    """Holds state for a single running sub-agent."""

    def __init__(self, agent_id: str, name: str, accent_color: str):
        self.agent_id = agent_id
        self.name = name
        self.accent_color = accent_color
        self.status = "starting"
        self.step = "Initializing..."
        self.task: Optional[asyncio.Task] = None


class AgentOrchestrator:
    """
    Central orchestrator for ARIA sub-agents.

    Usage:
        orchestrator = AgentOrchestrator()

        # Spawn an agent
        agent_id = await orchestrator.spawn_agent(
            name="BrowserBot",
            coro=fill_form_with_playwright(url, memory, ws),
            websocket=ws,
            accent_color="#10b981"
        )
    """

    def __init__(self):
        self.agents: Dict[str, AgentSession] = {}

    async def spawn_agent(
        self,
        name: str,
        coro: Coroutine,
        websocket,
        accent_color: str = "#10b981",
    ) -> str:
        """
        Spawn a new sub-agent:
        1. Emit agent_spawn to frontend.
        2. Wrap the coroutine to emit agent_complete when done.
        3. Launch as asyncio.Task.
        Returns the agentId string.
        """
        agent_id = str(uuid.uuid4())[:8]
        session = AgentSession(agent_id, name, accent_color)
        self.agents[agent_id] = session

        # Notify frontend: chip should appear
        await self._broadcast(websocket, {
            "type": "agent_spawn",
            "agentId": agent_id,
            "name": name,
            "accentColor": accent_color,
            "status": "starting",
            "step": "Initializing...",
        })

        # Wrap coro so we always send agent_complete at the end
        async def _runner():
            try:
                result = await coro
                await self._complete_agent(agent_id, result or "Task complete", websocket)
            except asyncio.CancelledError:
                await self._complete_agent(agent_id, "Cancelled by user.", websocket)
            except Exception as e:
                await self._complete_agent(agent_id, f"Error: {e}", websocket)

        task = asyncio.create_task(_runner())
        session.task = task

        # Store task ref in active_sessions for stop_task compatibility
        try:
            from agent_tools import active_sessions
            active_sessions["current_task"] = task
        except Exception:
            pass

        return agent_id

    async def send_heartbeat(
        self,
        agent_id: str,
        status: str,
        step: str,
        websocket,
    ):
        """Emit agent_heartbeat to frontend and update local session state."""
        session = self.agents.get(agent_id)
        if session:
            session.status = status
            session.step = step

        await self._broadcast(websocket, {
            "type": "agent_heartbeat",
            "agentId": agent_id,
            "status": status,
            "step": step,
        })

    async def _complete_agent(self, agent_id: str, result: Any, websocket):
        """Emit agent_complete to frontend and remove session."""
        session = self.agents.pop(agent_id, None)

        await self._broadcast(websocket, {
            "type": "agent_complete",
            "agentId": agent_id,
            "result": {"summary": str(result)},
        })

        # Clear current_task ref
        try:
            from agent_tools import active_sessions
            if active_sessions.get("current_task") is (session.task if session else None):
                active_sessions.pop("current_task", None)
        except Exception:
            pass

    async def cancel_agent(self, agent_id: str, websocket):
        """Cancel a running agent by its ID."""
        session = self.agents.get(agent_id)
        if session and session.task and not session.task.done():
            session.task.cancel()
            await self._broadcast(websocket, {
                "type": "agent_complete",
                "agentId": agent_id,
                "result": {"summary": "Cancelled by user."},
            })
            self.agents.pop(agent_id, None)

    async def _broadcast(self, primary_websocket, message: dict):
        """Send to primary websocket, then all active_websockets."""
        targets = set()
        if primary_websocket:
            targets.add(primary_websocket)
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


# Global singleton — import this in main.py
orchestrator = AgentOrchestrator()
