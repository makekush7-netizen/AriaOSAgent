"""
LLM Router — Unified AI inference layer for ARIA.
Supports: AWS Bedrock (Nova Pro/Lite/Micro), Google Gemini, with auto-fallback.

Usage:
    from llm_router import llm_call, llm_vision_call, get_active_provider_info

    # Text inference (auto-routes to best provider)
    response = llm_call(
        system_prompt="You are ARIA...",
        messages=[{"role": "user", "content": "Hello!"}],
        task_type="reasoning",  # "reasoning", "fast", or "micro"
    )

    # Vision inference
    response = llm_vision_call(
        system_prompt="You are a visual AI...",
        text_prompt="What fields are on this form?",
        image_bytes=screenshot_bytes,
    )
"""

import os
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent / ".env")


# ═══════════════════════════════════════════════════════════════
#  Provider Detection
# ═══════════════════════════════════════════════════════════════

def get_provider() -> str:
    """Get configured LLM provider: 'bedrock', 'gemini', or 'auto'."""
    return os.getenv("LLM_PROVIDER", "gemini").strip().lower()


def is_bedrock_configured() -> bool:
    """Check if AWS credentials are set."""
    return bool(
        os.getenv("AWS_ACCESS_KEY_ID", "").strip()
        and os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    )


def is_gemini_configured() -> bool:
    """Check if Gemini API key is set."""
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


# ═══════════════════════════════════════════════════════════════
#  AWS Bedrock Client
# ═══════════════════════════════════════════════════════════════

_bedrock_client = None


def _get_bedrock_client():
    """Lazy-init Bedrock Runtime client."""
    global _bedrock_client
    if _bedrock_client is None:
        import boto3
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )
    return _bedrock_client


# Model IDs for each tier
BEDROCK_MODELS = {
    "reasoning": "amazon.nova-pro-v1:0",     # Complex tasks, planning, multi-step
    "fast":      "amazon.nova-lite-v1:0",     # Quick responses, vision-capable
    "micro":     "amazon.nova-micro-v1:0",    # Intent classification, simple replies
}


# ═══════════════════════════════════════════════════════════════
#  Bedrock Text Inference
# ═══════════════════════════════════════════════════════════════

def call_bedrock(
    system_prompt: str,
    messages: list,
    model_tier: str = "reasoning",
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """
    Call AWS Bedrock using the Converse API.

    Args:
        system_prompt: System instruction text
        messages: List of {"role": "user"|"assistant", "content": "text"}
        model_tier: "reasoning" (Nova Pro), "fast" (Nova Lite), "micro" (Nova Micro)
        max_tokens: Maximum response tokens
        temperature: Sampling temperature (0.0 - 1.0)

    Returns:
        Response text string
    """
    client = _get_bedrock_client()
    model_id = BEDROCK_MODELS.get(model_tier, BEDROCK_MODELS["reasoning"])

    # Build Bedrock Converse API message format
    bedrock_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        # Bedrock uses "user" and "assistant" roles
        if role == "model":
            role = "assistant"
        bedrock_messages.append({
            "role": role,
            "content": [{"text": content}]
        })

    # Ensure messages alternate user/assistant (Bedrock requirement)
    bedrock_messages = _ensure_alternating_roles(bedrock_messages)

    try:
        print(f"[Bedrock] Calling {model_id}...")
        response = client.converse(
            modelId=model_id,
            system=[{"text": system_prompt}],
            messages=bedrock_messages,
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": temperature,
            }
        )

        # Extract text from response
        output = response.get("output", {}).get("message", {}).get("content", [])
        text = output[0]["text"] if output else ""
        print(f"[Bedrock] Response received ({len(text)} chars)")
        return text

    except Exception as e:
        print(f"[Bedrock Error] {model_id}: {e}")
        raise


def _ensure_alternating_roles(messages: list) -> list:
    """
    Bedrock requires messages to alternate between user and assistant.
    Merge consecutive same-role messages if needed.
    """
    if not messages:
        return messages

    cleaned = [messages[0]]
    for msg in messages[1:]:
        if msg["role"] == cleaned[-1]["role"]:
            # Merge with previous message
            prev_text = cleaned[-1]["content"][0]["text"]
            curr_text = msg["content"][0]["text"]
            cleaned[-1]["content"][0]["text"] = prev_text + "\n" + curr_text
        else:
            cleaned.append(msg)

    # Bedrock requires first message to be from "user"
    if cleaned and cleaned[0]["role"] != "user":
        cleaned.insert(0, {"role": "user", "content": [{"text": "Hello."}]})

    return cleaned


# ═══════════════════════════════════════════════════════════════
#  Bedrock Vision Inference
# ═══════════════════════════════════════════════════════════════

def call_bedrock_vision(
    system_prompt: str,
    text_prompt: str,
    image_bytes: bytes,
    image_format: str = "png",
    model_tier: str = "fast",
    max_tokens: int = 4096,
) -> str:
    """
    Call AWS Bedrock with an image (vision task).
    Uses Nova Lite by default (vision-capable and cost-effective).

    Args:
        system_prompt: System instruction text
        text_prompt: The text question about the image
        image_bytes: Raw bytes of the image file
        image_format: "png", "jpeg", "gif", or "webp"
        model_tier: Which model to use (default: "fast" = Nova Lite)
        max_tokens: Maximum response tokens

    Returns:
        Response text string
    """
    client = _get_bedrock_client()
    model_id = BEDROCK_MODELS.get(model_tier, BEDROCK_MODELS["fast"])

    try:
        print(f"[Bedrock Vision] Calling {model_id} with {len(image_bytes)} byte image...")
        response = client.converse(
            modelId=model_id,
            system=[{"text": system_prompt}],
            messages=[{
                "role": "user",
                "content": [
                    {
                        "image": {
                            "format": image_format,
                            "source": {"bytes": image_bytes}
                        }
                    },
                    {"text": text_prompt}
                ]
            }],
            inferenceConfig={
                "maxTokens": max_tokens,
                "temperature": 0.3,  # Lower temp for vision accuracy
            }
        )

        output = response.get("output", {}).get("message", {}).get("content", [])
        text = output[0]["text"] if output else ""
        print(f"[Bedrock Vision] Response received ({len(text)} chars)")
        return text

    except Exception as e:
        print(f"[Bedrock Vision Error] {model_id}: {e}")
        raise


# ═══════════════════════════════════════════════════════════════
#  Gemini Client (wraps existing integration)
# ═══════════════════════════════════════════════════════════════

_gemini_client = None


def _get_gemini_client():
    """Get or create Gemini client."""
    global _gemini_client
    if _gemini_client is None:
        import google.genai as genai
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        if not api_key:
            return None
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def call_gemini(
    system_prompt: str,
    messages: list,
    model_name: Optional[str] = None,
) -> str:
    """
    Call Google Gemini API.

    Args:
        system_prompt: System instruction
        messages: List of {"role": "user"|"assistant", "content": "text"}
        model_name: Override model (default: from .env GEMINI_MODEL)

    Returns:
        Response text string
    """
    import google.genai as genai

    client = _get_gemini_client()
    if not client:
        raise RuntimeError("GEMINI_API_KEY not configured")

    if model_name is None:
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

    # Convert to Gemini content format
    contents = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else msg["role"]
        parts = [genai.types.Part.from_text(text=msg["content"])]
        contents.append(genai.types.Content(role=role, parts=parts))

    print(f"[Gemini] Calling {model_name}...")
    response = client.models.generate_content(
        model=model_name,
        contents=contents,
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
        )
    )
    text = (response.text or "").strip()
    print(f"[Gemini] Response received ({len(text)} chars)")
    return text


def call_gemini_vision(
    system_prompt: str,
    text_prompt: str,
    image_bytes: bytes,
    model_name: Optional[str] = None,
) -> str:
    """
    Call Gemini with an image (vision task).

    Args:
        system_prompt: System instruction
        text_prompt: Text question about the image
        image_bytes: Raw image bytes
        model_name: Override model (default: from .env GEMINI_VISION_MODEL)

    Returns:
        Response text string
    """
    import google.genai as genai

    client = _get_gemini_client()
    if not client:
        raise RuntimeError("GEMINI_API_KEY not configured")

    if model_name is None:
        model_name = os.getenv("GEMINI_VISION_MODEL", "gemini-1.5-flash").strip()

    image_part = genai.types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    text_part = genai.types.Part.from_text(text=text_prompt)

    print(f"[Gemini Vision] Calling {model_name}...")
    response = client.models.generate_content(
        model=model_name,
        contents=[genai.types.Content(role="user", parts=[image_part, text_part])],
        config=genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
        )
    )
    text = (response.text or "").strip()
    print(f"[Gemini Vision] Response received ({len(text)} chars)")
    return text


# ═══════════════════════════════════════════════════════════════
#  Unified Router — The main functions you call
# ═══════════════════════════════════════════════════════════════

def llm_call(
    system_prompt: str,
    messages: list,
    task_type: str = "reasoning",
    max_tokens: int = 2048,
    temperature: float = 0.7,
) -> str:
    """
    Unified LLM call — routes to the best available provider.

    Routing logic:
      - LLM_PROVIDER=bedrock  → Bedrock only (fails if unconfigured)
      - LLM_PROVIDER=gemini   → Gemini only (fails if unconfigured)
      - LLM_PROVIDER=auto     → Try Bedrock first, fall back to Gemini

    Args:
        system_prompt: System instruction for the model
        messages: [{"role": "user"|"assistant", "content": "..."}]
        task_type: "reasoning" (Nova Pro), "fast" (Nova Lite), "micro" (Nova Micro)
        max_tokens: Max response tokens
        temperature: Sampling temperature (0.0 - 1.0)

    Returns:
        Response text string
    """
    provider = get_provider()

    # ── Try Bedrock first if configured ──
    if provider in ("bedrock", "auto") and is_bedrock_configured():
        try:
            return call_bedrock(
                system_prompt=system_prompt,
                messages=messages,
                model_tier=task_type,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            print(f"[Router] Bedrock failed: {e}")
            if provider == "bedrock":
                raise  # Don't fallback if explicitly set to bedrock-only
            print("[Router] Falling back to Gemini...")

    # ── Try Gemini ──
    if is_gemini_configured():
        try:
            return call_gemini(
                system_prompt=system_prompt,
                messages=messages,
            )
        except Exception as e:
            print(f"[Router] Gemini also failed: {e}")
            raise

    raise RuntimeError(
        "No LLM provider configured! "
        "Set AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY for Bedrock, "
        "or GEMINI_API_KEY for Gemini in backend/.env"
    )


def llm_vision_call(
    system_prompt: str,
    text_prompt: str,
    image_bytes: bytes,
    image_format: str = "png",
) -> str:
    """
    Unified vision LLM call — routes to the best available provider.

    Args:
        system_prompt: System instruction
        text_prompt: Text question about the image
        image_bytes: Raw image bytes
        image_format: Image format ("png", "jpeg")

    Returns:
        Response text string
    """
    provider = get_provider()

    # ── Try Bedrock Vision first ──
    if provider in ("bedrock", "auto") and is_bedrock_configured():
        try:
            return call_bedrock_vision(
                system_prompt=system_prompt,
                text_prompt=text_prompt,
                image_bytes=image_bytes,
                image_format=image_format,
            )
        except Exception as e:
            print(f"[Router] Bedrock Vision failed: {e}")
            if provider == "bedrock":
                raise
            print("[Router] Falling back to Gemini Vision...")

    # ── Try Gemini Vision ──
    if is_gemini_configured():
        try:
            return call_gemini_vision(
                system_prompt=system_prompt,
                text_prompt=text_prompt,
                image_bytes=image_bytes,
            )
        except Exception as e:
            print(f"[Router] Gemini Vision also failed: {e}")
            raise

    raise RuntimeError("No vision-capable LLM configured.")


# ═══════════════════════════════════════════════════════════════
#  Status / Info (for Settings page & debugging)
# ═══════════════════════════════════════════════════════════════

def get_active_provider_info() -> dict:
    """Return info about which LLM provider is active."""
    provider = get_provider()
    bedrock_ok = is_bedrock_configured()
    gemini_ok = is_gemini_configured()

    # Determine which model is actually being used
    if provider == "bedrock" and bedrock_ok:
        active = BEDROCK_MODELS["reasoning"]
    elif provider == "auto" and bedrock_ok:
        active = f"{BEDROCK_MODELS['reasoning']} (Bedrock primary, Gemini fallback)"
    elif gemini_ok:
        active = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    else:
        active = "none — no provider configured"

    return {
        "configured_provider": provider,
        "bedrock_available": bedrock_ok,
        "gemini_available": gemini_ok,
        "active_model": active,
        "bedrock_region": os.getenv("AWS_REGION", "us-east-1") if bedrock_ok else None,
        "bedrock_models": BEDROCK_MODELS if bedrock_ok else None,
    }
