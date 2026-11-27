"""Local OpenAI-compatible llama.cpp runtime client with health probes."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import DEFAULT_LLM_BASE_URL, DEFAULT_MODEL_NAME
from .db import get_setting


def get_llm_base_url() -> str:
    """Return configured local llama.cpp base URL."""

    return (get_setting("llm_base_url", DEFAULT_LLM_BASE_URL) or DEFAULT_LLM_BASE_URL).rstrip("/")


def probe_llm_runtime(timeout_seconds: float = 1.5) -> dict[str, object]:
    """Check whether a local llama.cpp HTTP server is currently reachable."""

    base_url = get_llm_base_url()
    models_url = f"{base_url}/models"
    request = urllib.request.Request(models_url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return {
            "available": True,
            "base_url": base_url,
            "models": payload.get("data", []),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {
            "available": False,
            "base_url": base_url,
            "models": [],
        }


def request_structured_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    model_name: str | None = None,
    timeout_seconds: int = 30,
) -> str | None:
    """Query the local llama.cpp chat endpoint for JSON document planning if online."""

    base_url = get_llm_base_url()
    endpoint = f"{base_url}/chat/completions"
    body = json.dumps(
        {
            "model": model_name or get_setting("active_model", DEFAULT_MODEL_NAME) or DEFAULT_MODEL_NAME,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        choices = payload.get("choices") or []
        if not choices:
            return None
        message = choices[0].get("message") or {}
        content = message.get("content")
        return str(content) if isinstance(content, str) and content.strip() else None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
