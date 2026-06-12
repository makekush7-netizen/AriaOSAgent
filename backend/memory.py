"""
ARIA Memory Manager — Layer 2 (Episodic) + Layer 3 (Profile)
Stores conversation episodes in ChromaDB for semantic retrieval.
Falls back gracefully to memory.json only if chromadb is not installed.

Usage:
    from memory import MemoryManager
    memory_mgr = MemoryManager()
    memory_mgr.add_episode("web_task", "Filled form on unstop.com for user Kush", ["name","email"])
    context = memory_mgr.get_relevant_context("fill hackathon form")
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Optional

# ─── Paths ────────────────────────────────────────────────────────────────────
APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
ARIA_DIR = Path(APPDATA) / "ARIA"
ARIA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR = ARIA_DIR / "chroma"
PROFILE_PATH = Path(__file__).parent / "memory.json"

# ─── Optional imports (graceful fallback) ─────────────────────────────────────
_chromadb_available = False
_embedder_available = False
_chromadb = None
_SentenceTransformer = None

try:
    import chromadb
    _chromadb = chromadb
    _chromadb_available = True
except ImportError:
    print("[MemoryManager] chromadb not installed — episodic memory disabled. Run: pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    _SentenceTransformer = SentenceTransformer
    _embedder_available = True
except ImportError:
    print("[MemoryManager] sentence-transformers not installed — vector search disabled. Run: pip install sentence-transformers")


class MemoryManager:
    """
    Two-layer memory system:
      Layer 3 — Flat JSON profile (memory.json) — always available
      Layer 2 — ChromaDB episodic memory — available when chromadb is installed
    """

    def __init__(self):
        self._profile: dict = self._load_profile()
        self._chroma_client = None
        self._episodes_col = None
        self._embedder = None
        self._embedding_dim = 384  # all-MiniLM-L6-v2

        if _chromadb_available:
            try:
                CHROMA_DIR.mkdir(parents=True, exist_ok=True)
                self._chroma_client = _chromadb.PersistentClient(path=str(CHROMA_DIR))
                self._episodes_col = self._chroma_client.get_or_create_collection(
                    name="episodes",
                    metadata={"hnsw:space": "cosine"},
                )
                print(f"[MemoryManager] ChromaDB initialized at {CHROMA_DIR} — {self._episodes_col.count()} episodes stored.")
            except Exception as e:
                print(f"[MemoryManager] ChromaDB init failed: {e}")

        if _embedder_available:
            try:
                self._embedder = _SentenceTransformer("all-MiniLM-L6-v2")
                print("[MemoryManager] Sentence embedder loaded.")
            except Exception as e:
                print(f"[MemoryManager] Embedder load failed: {e}")

    # ─── Layer 3: Profile ─────────────────────────────────────────────────────

    def _load_profile(self) -> dict:
        if PROFILE_PATH.exists():
            try:
                with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_profile(self) -> dict:
        self._profile = self._load_profile()
        return self._profile

    def update_profile(self, updates: dict) -> dict:
        current = self._load_profile()
        current.update(updates)
        try:
            with open(PROFILE_PATH, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[MemoryManager] Profile save error: {e}")
        self._profile = current
        return current

    # ─── Layer 2: Episodic ────────────────────────────────────────────────────

    def _embed(self, text: str) -> list:
        """Return embedding vector for text. Returns empty list on failure."""
        if self._embedder is None:
            return []
        try:
            vec = self._embedder.encode(text, show_progress_bar=False)
            return vec.tolist()
        except Exception as e:
            print(f"[MemoryManager] Embedding error: {e}")
            return []

    def add_episode(self, task_type: str, summary: str, data_used: list[str] | None = None):
        """
        Store a conversation episode in ChromaDB.
        Automatically prunes to keep only the last 200 episodes.
        """
        if self._episodes_col is None:
            return  # ChromaDB not available, skip silently

        embedding = self._embed(summary)
        if not embedding:
            return  # No embedder, skip

        episode_id = f"ep_{int(time.time() * 1000)}"
        metadata = {
            "task_type": task_type,
            "timestamp": time.time(),
            "data_used": json.dumps(data_used or []),
        }

        try:
            self._episodes_col.add(
                ids=[episode_id],
                embeddings=[embedding],
                documents=[summary],
                metadatas=[metadata],
            )

            # Prune to last 200 episodes
            count = self._episodes_col.count()
            if count > 200:
                # Get oldest IDs
                all_items = self._episodes_col.get(include=["metadatas"])
                ids_with_time = list(zip(
                    all_items["ids"],
                    [m.get("timestamp", 0) for m in all_items["metadatas"]],
                ))
                ids_with_time.sort(key=lambda x: x[1])
                to_delete = [item[0] for item in ids_with_time[:count - 200]]
                if to_delete:
                    self._episodes_col.delete(ids=to_delete)

            print(f"[MemoryManager] Episode stored: {task_type} — {summary[:60]}...")
        except Exception as e:
            print(f"[MemoryManager] Episode add error: {e}")

    def get_relevant_context(self, query: str, n_results: int = 5) -> list[str]:
        """
        Semantic search over stored episodes.
        Returns list of episode summary strings, most relevant first.
        """
        if self._episodes_col is None or self._embedder is None:
            return []

        try:
            count = self._episodes_col.count()
            if count == 0:
                return []

            embedding = self._embed(query)
            if not embedding:
                return []

            results = self._episodes_col.query(
                query_embeddings=[embedding],
                n_results=min(n_results, count),
                include=["documents"],
            )
            return results.get("documents", [[]])[0]
        except Exception as e:
            print(f"[MemoryManager] Context retrieval error: {e}")
            return []

    def summarize_session(self, messages: list[dict], llm_client=None) -> str:
        """
        Use LLM to summarize a conversation session for episode storage.
        Falls back to a simple string if LLM is unavailable.
        """
        if not messages:
            return ""

        if llm_client is None:
            # Simple fallback: join last few messages
            lines = [f"{m.get('role','?')}: {m.get('content','')[:100]}" for m in messages[-6:]]
            return " | ".join(lines)

        try:
            import boto3
            aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
            aws_secret_access_key = os.getenv("AWS_SECRET_access_key", "").strip()
            if not aws_secret_access_key:
                 aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
            region_name = os.getenv("AWS_REGION", "us-east-1").strip()
            
            client = boto3.client(
                service_name='bedrock-runtime',
                region_name=region_name,
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
            )
            
            conversation_text = "\n".join(
                [f"{m.get('role','?').upper()}: {m.get('content','')}" for m in messages[-20:]]
            )
            prompt = (
                "Summarize what happened in this conversation. Focus on: "
                "what task was done, what user data was used, what the user corrected or added, "
                "what worked and what didn't. Be concise (max 100 words).\n\n"
                f"Conversation:\n{conversation_text}"
            )
            
            model_name = os.getenv("LLM_MODEL", "amazon.nova-pro-v1:0").strip()
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            
            response = client.converse(
                modelId=model_name,
                messages=messages,
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
                    
            return text_content.strip()
        except Exception as e:
            print(f"[MemoryManager] Session summarize error: {e}")
            return ""


# Global singleton — import this in main.py
memory_mgr = MemoryManager()
