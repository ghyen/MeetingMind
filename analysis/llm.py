"""LLM 클라이언트 — OpenRouter / Ollama 전환 지원."""

from __future__ import annotations

import json

import httpx
from openai import AsyncOpenAI

from config import settings

# ── 클라이언트 풀 ───────────────────────────────────────

_openrouter_client = AsyncOpenAI(
    api_key=settings.llm_api_key,
    base_url="https://openrouter.ai/api/v1",
)

_ollama_client = AsyncOpenAI(
    api_key="ollama",
    base_url=settings.ollama_base_url,
)

# ── 런타임 상태 ─────────────────────────────────────────

_active_provider: str = settings.llm_provider  # "openrouter" | "ollama"
_active_model: str = settings.llm_model_fast


def get_active_model() -> dict:
    return {"provider": _active_provider, "model": _active_model}


def set_active_model(provider: str, model: str) -> dict:
    global _active_provider, _active_model
    _active_provider = provider
    _active_model = model
    return get_active_model()


async def list_ollama_models() -> list[str]:
    """로컬 Ollama에서 사용 가능한 모델 목록 조회."""
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get("http://localhost:11434/api/tags", timeout=3)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        return []


def _get_client() -> AsyncOpenAI:
    return _ollama_client if _active_provider == "ollama" else _openrouter_client


# ── 공용 호출 함수 ──────────────────────────────────────

async def _ask_ollama(prompt: str, model: str) -> str:
    """Ollama 네이티브 API 호출 (thinking 비활성화)."""
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{settings.ollama_base_url.replace('/v1', '')}/api/chat".replace("//api", "/api"),
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt + "\n\nRespond ONLY with a valid JSON object. No extra text."}],
                "stream": False,
                "think": False,
            },
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["message"]["content"]


async def ask_json(prompt: str, *, model: str | None = None) -> dict:
    """LLM 호출 → JSON dict 반환."""
    use_model = model or _active_model

    if _active_provider == "ollama":
        text = await _ask_ollama(prompt, use_model)
    else:
        client = _get_client()
        response = await client.chat.completions.create(
            model=use_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content

    # JSON 추출 (마크다운 코드블록 등 제거)
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()

    return json.loads(text)
