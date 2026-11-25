"""Thin client for Vultr Serverless Inference (OpenAI-compatible API).

The LLM is only used to read messy human text (requests, donor replies). Every
answer is validated with Pydantic by the caller, and if the LLM is not configured,
times out, or returns junk, callers fall back to deterministic rules. Matching,
priority and status changes never depend on the LLM.
"""
import json
import logging
import re
from typing import Any

from app.core.config import get_settings

log = logging.getLogger("bloodbridge.llm")

_client = None


def _get_client():
    global _client
    if _client is None:
        from openai import OpenAI

        s = get_settings()
        _client = OpenAI(
            base_url=s.vultr_inference_base_url,
            api_key=s.vultr_inference_api_key,
            timeout=s.llm_timeout_seconds,
            max_retries=1,
        )
    return _client


def _extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    # strip ```json fences if the model added them
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                return data if isinstance(data, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def llm_json(system_prompt: str, user_prompt: str) -> dict[str, Any] | None:
    """Ask the model for a JSON object. Returns None if the LLM is unavailable or fails."""
    s = get_settings()
    if not s.llm_enabled:
        return None
    try:
        resp = _get_client().chat.completions.create(
            model=s.vultr_inference_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=500,
        )
        content = resp.choices[0].message.content or ""
        return _extract_json(content)
    except Exception as exc:  # network, auth, model errors -> deterministic fallback
        log.warning("LLM call failed, using rule-based fallback: %s", exc)
        return None
