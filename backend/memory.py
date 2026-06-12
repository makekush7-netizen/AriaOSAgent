"""
ARIA Memory Manager — Robust 3-Layer Architecture
═══════════════════════════════════════════════════

Layer 1 — Working Memory (Session Context)
    Short-term conversation buffer.  Kept in-process as a Python list.
    Discarded on session end.  Gives ARIA immediate conversational context.

Layer 2 — Episodic Memory (What Happened)
    Stored in a local ChromaDB vector database.  After every completed task the
    LLM generates a compressed summary; we embed it and store it.  On new tasks
    the top-N relevant episodes are pulled semantically and injected as context.

Layer 3 — Semantic Profile (Who the User Is)
    A structured JSON file (profile.json) that actively updates as conversations
    happen.  Contains hard facts: name, email, phone, college, roll number …
    Supports *contextual values* (e.g. work-email vs personal-email) and secure
    AWS credential storage for Bedrock integration.

Design Principles
─────────────────
•  Graceful degradation — ChromaDB and sentence-transformers are optional.
   The system always works with at least Layer 3 (flat JSON).
•  Zero duplication — main.py should import memory_mgr and stop maintaining
   its own load_memory/save_memory helpers.
•  Future-proof — Every public method is usable from FastAPI routes, the
   agent orchestrator, the browser agent, or any future sub-agent.

Usage:
    from memory import memory_mgr
    profile = memory_mgr.get_profile()
    memory_mgr.update_profile({"email": "new@example.com"})
    memory_mgr.add_episode("web_task", "Filled hackathon form", ["name","email"])
    context = memory_mgr.get_relevant_context("fill hackathon form")
"""

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

# ─── Logging ──────────────────────────────────────────────────────────────────
logger = logging.getLogger("aria.memory")
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("[MemoryManager] %(message)s"))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)

# ─── Paths ────────────────────────────────────────────────────────────────────
APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
ARIA_DIR = Path(APPDATA) / "ARIA"
ARIA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_DIR = ARIA_DIR / "chroma"
PROFILE_PATH = Path(__file__).parent / "memory.json"

# ─── Key normalisation map ────────────────────────────────────────────────────
# Maps messy user-supplied key variants to canonical profile keys.
_KEY_ALIASES: Dict[str, list[str]] = {
    "name":       ["name", "full name", "first name", "last name", "fullname"],
    "email":      ["email", "e-mail", "mail id", "mail", "email id", "email address"],
    "phone":      ["phone", "mobile", "contact", "tel", "telephone", "mob", "phone number", "mobile number", "contact number"],
    "college":    ["college", "university", "institute", "institution", "school", "uni"],
    "department": ["department", "dept", "branch", "course", "stream", "major"],
    "rollNo":     ["rollno", "roll no", "roll number", "reg", "registration", "registration number", "enrollment", "enrolment"],
    "gender":     ["gender", "sex"],
    "dob":        ["dob", "date of birth", "birthday", "birth date"],
    "address":    ["address", "home address", "residential address"],
    "city":       ["city", "town"],
    "state":      ["state", "province"],
    "pincode":    ["pincode", "pin code", "zip", "zipcode", "zip code", "postal code"],
    "country":    ["country", "nation"],
    "linkedin":   ["linkedin", "linkedin url", "linkedin profile"],
    "github":     ["github", "github url", "github profile"],
}

# Build reverse lookup: alias → canonical
_ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical, aliases in _KEY_ALIASES.items():
    for alias in aliases:
        _ALIAS_TO_CANONICAL[alias] = canonical

# Keys that are sensitive and must NEVER be logged or sent to the LLM context
_SENSITIVE_KEYS = frozenset({
    "aws_access_key_id",
    "aws_secret_access_key",
    "aws_session_token",
    "password",
    "api_key",
    "secret",
})

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
    logger.warning("chromadb not installed — episodic memory disabled.  pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    _SentenceTransformer = SentenceTransformer
    _embedder_available = True
except ImportError:
    logger.warning("sentence-transformers not installed — vector search disabled.  pip install sentence-transformers")


# ═════════════════════════════════════════════════════════════════════════════
#  MemoryManager
# ═════════════════════════════════════════════════════════════════════════════

class MemoryManager:
    """
    Three-layer memory system for ARIA.

    Layer 1 — Working Memory   : managed externally (chat history list).
    Layer 2 — Episodic Memory  : ChromaDB vector store (this class).
    Layer 3 — Semantic Profile : profile.json on disk (this class).
    """

    # ──────────────────────────────────────────────────────────────────────────
    #  Initialisation
    # ──────────────────────────────────────────────────────────────────────────

    def __init__(self):
        # Layer 3 — profile
        self._profile: dict = self._load_profile()

        # Layer 2 — ChromaDB
        self._chroma_client = None
        self._episodes_col = None
        self._skills_col = None
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
                self._skills_col = self._chroma_client.get_or_create_collection(
                    name="skills",
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info(
                    "ChromaDB ready at %s — %d episodes, %d skills.",
                    CHROMA_DIR,
                    self._episodes_col.count(),
                    self._skills_col.count(),
                )
            except Exception as exc:
                logger.error("ChromaDB init failed: %s", exc)

        if _embedder_available:
            try:
                self._embedder = _SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Sentence embedder loaded (all-MiniLM-L6-v2).")
            except Exception as exc:
                logger.error("Embedder load failed: %s", exc)

    # ──────────────────────────────────────────────────────────────────────────
    #  Layer 3 — Semantic Profile
    # ──────────────────────────────────────────────────────────────────────────

    def _load_profile(self) -> dict:
        """Read profile.json from disk."""
        if PROFILE_PATH.exists():
            try:
                with open(PROFILE_PATH, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                return data if isinstance(data, dict) else {}
            except Exception:
                pass
        return {}

    def _save_profile(self) -> None:
        """Persist current in-memory profile to disk."""
        try:
            with open(PROFILE_PATH, "w", encoding="utf-8") as fh:
                json.dump(self._profile, fh, indent=4, ensure_ascii=False)
        except Exception as exc:
            logger.error("Profile save error: %s", exc)

    @staticmethod
    def normalise_key(raw_key: str) -> str:
        """
        Convert a user-supplied key to its canonical form.

        Examples:
            "Mail ID"       → "email"
            "mob"           → "phone"
            "university"    → "college"
            "Father's Name" → "fathers_name"
        """
        cleaned = raw_key.strip().lower()
        cleaned = re.sub(r"[''`]", "", cleaned)           # remove apostrophes
        cleaned = re.sub(r"[\s\xa0\u200b]+", " ", cleaned)  # normalise whitespace

        # Check known aliases first
        if cleaned in _ALIAS_TO_CANONICAL:
            return _ALIAS_TO_CANONICAL[cleaned]

        # Partial match: if the cleaned key *contains* an alias
        for alias, canonical in _ALIAS_TO_CANONICAL.items():
            if alias in cleaned:
                # But exclude false positives like "father name" matching "name"
                other_words = cleaned.replace(alias, "").strip()
                if not other_words:
                    return canonical

        # General fallback: snake_case
        clean = re.sub(r"[^a-z0-9]+", "_", cleaned).strip("_")
        return clean or raw_key.strip()

    # ── Public Profile API ─────────────────────────────────────────────────

    def get_profile(self) -> dict:
        """Return the full profile dict (re-reads from disk for freshness)."""
        self._profile = self._load_profile()
        return self._profile

    def get_profile_for_llm(self) -> dict:
        """
        Return a *safe* version of the profile suitable for injecting into
        LLM context.  Strips sensitive keys (AWS creds, passwords, etc.).
        """
        return {
            k: v for k, v in self.get_profile().items()
            if k.lower() not in _SENSITIVE_KEYS
        }

    def get_field(self, key: str, context: Optional[str] = None) -> Any:
        """
        Smart field getter with contextual resolution.

        If the stored value is a plain string, return it.
        If it is a dict (contextual values), return the context-specific
        value or the "default" entry.

        Example:
            profile = {"email": {"personal": "a@g.com", "work": "a@w.com", "default": "a@g.com"}}
            get_field("email")                → "a@g.com"
            get_field("email", "work")        → "a@w.com"
            get_field("email", "personal")    → "a@g.com"
        """
        canonical = self.normalise_key(key)
        value = self._profile.get(canonical)

        if value is None:
            return None

        if isinstance(value, dict):
            if context and context in value:
                return value[context]
            return value.get("default", next(iter(value.values()), None))

        return value

    def update_profile(self, updates: dict) -> dict:
        """
        Merge updates into the existing profile.

        - Keys are normalised automatically.
        - Empty/None values are ignored (won't overwrite existing data).
        - Contextual values (dicts) are merged, not replaced.
        - Saves to disk immediately.
        """
        current = self._load_profile()

        for raw_key, value in updates.items():
            canonical = self.normalise_key(raw_key)

            if not canonical:
                continue

            # Skip empty updates
            if value is None or (isinstance(value, str) and not value.strip()):
                continue

            # Strip trailing/leading whitespace from string values
            if isinstance(value, str):
                value = value.strip()

            existing = current.get(canonical)

            # Contextual merge: if new value is a dict, merge into existing
            if isinstance(value, dict) and isinstance(existing, dict):
                existing.update(value)
                current[canonical] = existing
            elif isinstance(value, dict) and isinstance(existing, str):
                # Promote existing flat value to contextual
                value.setdefault("default", existing)
                current[canonical] = value
            elif isinstance(existing, dict) and isinstance(value, str):
                # Update the default in the contextual dict
                existing["default"] = value
                current[canonical] = existing
            else:
                # Simple overwrite
                current[canonical] = value

        self._profile = current
        self._save_profile()
        logger.info("Profile updated: %s", list(updates.keys()))
        return current

    def set_contextual_value(self, key: str, context: str, value: str) -> dict:
        """
        Set a context-specific value for a profile field.

        Example:
            set_contextual_value("email", "work", "me@company.com")
            → profile["email"] = {"default": "old@gmail.com", "work": "me@company.com"}
        """
        canonical = self.normalise_key(key)
        existing = self._profile.get(canonical)

        if isinstance(existing, dict):
            existing[context] = value
        elif isinstance(existing, str):
            self._profile[canonical] = {"default": existing, context: value}
        else:
            self._profile[canonical] = {"default": value, context: value}

        self._save_profile()
        return self._profile

    def get_all_contexts_for_field(self, key: str) -> Dict[str, str]:
        """
        Return all context-value pairs for a field.
        If the field is a plain string, returns {"default": value}.
        """
        canonical = self.normalise_key(key)
        value = self._profile.get(canonical)
        if isinstance(value, dict):
            return value
        elif value is not None:
            return {"default": str(value)}
        return {}

    # ── AWS Credential Helpers ─────────────────────────────────────────────

    def get_aws_credentials(self) -> Dict[str, str]:
        """
        Return AWS credentials for Bedrock.
        Priority: profile.json → environment variables → empty.

        Credentials are NEVER logged or sent to the LLM.
        """
        profile = self.get_profile()

        access_key = (
            profile.get("aws_access_key_id")
            or os.getenv("AWS_ACCESS_KEY_ID", "")
        ).strip() if isinstance(profile.get("aws_access_key_id"), str) else os.getenv("AWS_ACCESS_KEY_ID", "").strip()

        secret_key = (
            profile.get("aws_secret_access_key")
            or os.getenv("AWS_SECRET_ACCESS_KEY", "")
        ).strip() if isinstance(profile.get("aws_secret_access_key"), str) else os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

        region = (
            profile.get("aws_region")
            or os.getenv("AWS_REGION", "us-east-1")
        ).strip() if isinstance(profile.get("aws_region"), str) else os.getenv("AWS_REGION", "us-east-1").strip()

        return {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "aws_region": region,
        }

    def set_aws_credentials(
        self,
        access_key_id: str,
        secret_access_key: str,
        region: str = "us-east-1",
    ) -> None:
        """
        Store AWS credentials securely in the profile.
        These are excluded from get_profile_for_llm() so they never leak.
        """
        self._profile["aws_access_key_id"] = access_key_id.strip()
        self._profile["aws_secret_access_key"] = secret_access_key.strip()
        self._profile["aws_region"] = region.strip()
        self._save_profile()
        logger.info("AWS credentials stored in profile (keys redacted from LLM context).")

    # ──────────────────────────────────────────────────────────────────────────
    #  Layer 2 — Episodic Memory (ChromaDB)
    # ──────────────────────────────────────────────────────────────────────────

    def _embed(self, text: str) -> list:
        """Return embedding vector for text.  Returns [] on failure."""
        if self._embedder is None:
            return []
        try:
            vec = self._embedder.encode(text, show_progress_bar=False)
            return vec.tolist()
        except Exception as exc:
            logger.error("Embedding error: %s", exc)
            return []

    def add_episode(
        self,
        task_type: str,
        summary: str,
        data_used: Optional[List[str]] = None,
    ) -> None:
        """
        Store a conversation/task episode in ChromaDB.
        Automatically prunes to keep only the last 200 episodes.
        """
        if self._episodes_col is None:
            return

        embedding = self._embed(summary)
        if not embedding:
            return

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
                all_items = self._episodes_col.get(include=["metadatas"])
                ids_with_time = list(zip(
                    all_items["ids"],
                    [m.get("timestamp", 0) for m in all_items["metadatas"]],
                ))
                ids_with_time.sort(key=lambda x: x[1])
                to_delete = [item[0] for item in ids_with_time[: count - 200]]
                if to_delete:
                    self._episodes_col.delete(ids=to_delete)

            logger.info("Episode stored: %s — %s", task_type, summary[:60])
        except Exception as exc:
            logger.error("Episode add error: %s", exc)

    def get_relevant_context(self, query: str, n_results: int = 5) -> List[str]:
        """
        Semantic search over stored episodes.
        Returns episode summaries sorted by relevance.
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
        except Exception as exc:
            logger.error("Context retrieval error: %s", exc)
            return []

    # ── Skills Collection ──────────────────────────────────────────────────

    def add_skill(self, skill_name: str, description: str) -> None:
        """Store a learned skill/pattern in the skills collection."""
        if self._skills_col is None:
            return
        embedding = self._embed(description)
        if not embedding:
            return
        try:
            skill_id = f"sk_{int(time.time() * 1000)}"
            self._skills_col.add(
                ids=[skill_id],
                embeddings=[embedding],
                documents=[description],
                metadatas=[{"skill_name": skill_name, "timestamp": time.time()}],
            )
            logger.info("Skill stored: %s", skill_name)
        except Exception as exc:
            logger.error("Skill add error: %s", exc)

    def get_relevant_skills(self, query: str, n_results: int = 3) -> List[str]:
        """Semantic search over learned skills."""
        if self._skills_col is None or self._embedder is None:
            return []
        try:
            count = self._skills_col.count()
            if count == 0:
                return []
            embedding = self._embed(query)
            if not embedding:
                return []
            results = self._skills_col.query(
                query_embeddings=[embedding],
                n_results=min(n_results, count),
                include=["documents"],
            )
            return results.get("documents", [[]])[0]
        except Exception as exc:
            logger.error("Skill retrieval error: %s", exc)
            return []

    # ──────────────────────────────────────────────────────────────────────────
    #  Layer 1 — Working Memory helpers
    # ──────────────────────────────────────────────────────────────────────────
    # Working memory (chat history) lives in main.py as a list.
    # These helpers assist with session summarisation.

    def summarize_session(self, messages: List[dict], llm_client=None) -> str:
        """
        Use LLM to summarize a conversation session for episode storage.
        Falls back to a simple concatenation if LLM is unavailable.
        """
        if not messages:
            return ""

        if llm_client is None:
            lines = [
                f"{m.get('role', '?')}: {m.get('content', '')[:100]}"
                for m in messages[-6:]
            ]
            return " | ".join(lines)

        try:
            import google.genai as genai

            conversation_text = "\n".join(
                f"{m.get('role', '?').upper()}: {m.get('content', '')}"
                for m in messages[-20:]
            )
            prompt = (
                "Summarize what happened in this conversation. Focus on: "
                "what task was done, what user data was used, what the user "
                "corrected or added, what worked and what didn't. "
                "Be concise (max 100 words).\n\n"
                f"Conversation:\n{conversation_text}"
            )
            response = llm_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )
            return (response.text or "").strip()
        except Exception as exc:
            logger.error("Session summarize error: %s", exc)
            return ""

    # ──────────────────────────────────────────────────────────────────────────
    #  Profile extraction from conversation (LLM-assisted)
    # ──────────────────────────────────────────────────────────────────────────

    def extract_profile_updates_from_message(self, user_message: str, llm_client=None) -> dict:
        """
        Given a raw user message, use the LLM to detect if the user is
        providing new profile information (e.g. "my new email is x@y.com").

        Returns a dict of updates to merge, or {} if nothing was detected.
        This method is safe to call on every message — it only fires the LLM
        if the message looks like it contains personal info.
        """
        # Quick heuristic: skip if the message is too short or clearly not
        # a profile update (saves LLM calls)
        msg_lower = user_message.lower()
        trigger_words = [
            "my ", "i am ", "i'm ", "name is", "email is", "phone is",
            "number is", "college is", "roll", "call me", "address is",
            "updated", "changed", "new email", "new phone", "new number",
            "use this", "remember that", "remember my",
        ]
        if not any(word in msg_lower for word in trigger_words):
            return {}

        if llm_client is None:
            return {}

        try:
            import google.genai as genai

            prompt = (
                "The user sent the following message.  If the user is sharing or updating "
                "personal profile information (like name, email, phone, college, roll number, "
                "address, date of birth, gender, department, LinkedIn, GitHub, etc.), "
                "extract the key-value pairs.  Return ONLY a JSON object with the extracted "
                "fields.  If no profile information is detected, return exactly: {}\n\n"
                "Rules:\n"
                "- Use canonical field names: name, email, phone, college, department, rollNo, "
                "  gender, dob, address, city, state, pincode, country, linkedin, github\n"
                "- If the user specifies a context (e.g. 'my work email'), return it as: "
                '  {"email": {"work": "value"}}\n'
                "- Only extract facts the user explicitly states.  Do not infer.\n"
                "- Return ONLY the JSON object, no markdown fences, no explanation.\n\n"
                f'User message: "{user_message}"'
            )

            response = llm_client.models.generate_content(
                model="gemini-1.5-flash",
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )
            raw = (response.text or "").strip()

            # Strip code fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("`").strip()

            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed:
                logger.info("Extracted profile updates from message: %s", list(parsed.keys()))
                return parsed
            return {}

        except Exception as exc:
            logger.debug("Profile extraction skipped: %s", exc)
            return {}

    # ──────────────────────────────────────────────────────────────────────────
    #  Tool definition for the LLM agent
    # ──────────────────────────────────────────────────────────────────────────

    @staticmethod
    def get_tool_definitions() -> list[dict]:
        """
        Return tool definitions that can be injected into the LLM system prompt
        so ARIA can proactively update the user's profile.
        """
        return [
            {
                "name": "update_user_profile",
                "description": (
                    "Update the user's personal profile with new information.  "
                    "Call this when the user provides or corrects personal details like "
                    "name, email, phone, college, roll number, address, etc.  "
                    "Pass each field as a key-value pair in the 'updates' argument."
                ),
                "args": {
                    "updates": (
                        "A JSON object of field-value pairs to update.  "
                        "Use canonical keys: name, email, phone, college, department, rollNo, "
                        "gender, dob, address, city, state, pincode, country, linkedin, github.  "
                        "For context-specific values use nested objects: "
                        '{"email": {"work": "x@company.com"}}'
                    ),
                },
            },
            {
                "name": "get_user_profile",
                "description": (
                    "Retrieve the user's full profile.  Use this to check what "
                    "information is already saved before asking the user."
                ),
                "args": {},
            },
        ]


# ═════════════════════════════════════════════════════════════════════════════
#  Global singleton — import this in main.py, research.py, etc.
# ═════════════════════════════════════════════════════════════════════════════
memory_mgr = MemoryManager()
