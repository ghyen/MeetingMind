"""LLM 클라이언트 — OpenRouter / Ollama / Bonsai 전환 지원."""

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

_bonsai_client = AsyncOpenAI(
    api_key="bonsai",
    base_url=settings.bonsai_base_url,
)

# ── 런타임 상태 ─────────────────────────────────────────

_active_provider: str = settings.llm_provider  # "openrouter" | "ollama" | "bonsai"
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


async def list_bonsai_models() -> list[str]:
    """Bonsai(llama.cpp/MLX) 서버에서 사용 가능한 모델 목록 조회."""
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{settings.bonsai_base_url}/models", timeout=3)
            r.raise_for_status()
            return [m["id"] for m in r.json().get("data", [])]
    except Exception:
        return [settings.bonsai_model]


def _get_client() -> AsyncOpenAI:
    if _active_provider == "ollama":
        return _ollama_client
    if _active_provider == "bonsai":
        return _bonsai_client
    return _openrouter_client


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


async def _ask_bonsai(prompt: str, model: str) -> str:
    """Bonsai(llama.cpp/MLX) 서버 OpenAI 호환 API 호출."""
    client = _bonsai_client
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt + "\n\nRespond ONLY with a valid JSON object. No extra text."}],
        temperature=0.6,
    )
    return response.choices[0].message.content


async def ask_json(prompt: str, *, model: str | None = None) -> dict:
    """LLM 호출 → JSON dict 반환.

    모든 분석 모듈(토픽 감지, 쟁점 구조화, 엔티티 추출)이 이 함수를 통해 LLM에 접근.
    프로바이더에 따라 Ollama 네이티브 API, Bonsai 서버, 또는 OpenAI 호환 API를 사용.
    응답에서 마크다운 코드블록(```json ... ```)을 제거한 뒤 JSON 파싱.
    """
    use_model = model or _active_model

    if _active_provider == "ollama":
        text = await _ask_ollama(prompt, use_model)
    elif _active_provider == "bonsai":
        text = await _ask_bonsai(prompt, use_model)
    else:
        client = _get_client()
        response = await client.chat.completions.create(
            model=use_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content

    # LLM이 ```json ... ``` 형태로 감싸서 응답하는 경우 코드블록 마커 제거
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.startswith("```")]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # gemma 계열은 응답 끝에 <channel|> 같은 종료 마커를 붙이는 경우가 있음 →
        # 첫 '{' ~ 마지막 '}' 구간만 추출하여 재시도
        lb, rb = text.find("{"), text.rfind("}")
        if lb != -1 and rb > lb:
            try:
                return json.loads(text[lb : rb + 1])
            except json.JSONDecodeError:
                pass
        import logging
        logging.getLogger(__name__).warning(
            "LLM JSON 파싱 실패 — 응답(앞 200자): %s", text[:200]
        )
        raise
