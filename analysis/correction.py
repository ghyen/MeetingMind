"""STT 후처리 교정 — 회의 컨텍스트 기반 발화 텍스트 교정.

발화 5개가 쌓일 때마다 LLM을 호출하여 음성 인식 오류를 교정.
회사/회의 정보를 활용해 도메인 특화 교정 수행.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from models import Utterance

logger = logging.getLogger(__name__)

_BATCH_SIZE = 5


@dataclass
class MeetingContext:
    """회의 배경 정보 — 교정 프롬프트에 포함."""

    company: str = ""
    description: str = ""


class STTCorrector:
    """발화 텍스트 배치 교정기."""

    def __init__(self) -> None:
        self._pending: list[Utterance] = []
        self._context: MeetingContext = MeetingContext()

    def set_context(self, context: MeetingContext) -> None:
        self._context = context

    async def feed(self, utterance: Utterance) -> list[Utterance] | None:
        """발화 추가. 배치가 차면 교정 실행 후 교정된 발화 목록 반환."""
        self._pending.append(utterance)
        if len(self._pending) < _BATCH_SIZE:
            return None

        batch = self._pending[:_BATCH_SIZE]
        self._pending = self._pending[_BATCH_SIZE:]
        return await self._correct_batch(batch)

    async def _correct_batch(self, batch: list[Utterance]) -> list[Utterance]:
        """LLM으로 배치 교정."""
        from analysis.llm import ask_json
        from config import settings

        lines = []
        for i, u in enumerate(batch):
            lines.append(f"{i}: [{u.speaker}] {u.text}")
        utterances_text = "\n".join(lines)

        context_parts = []
        if self._context.company:
            context_parts.append(f"회사: {self._context.company}")
        if self._context.description:
            context_parts.append(f"회의 내용: {self._context.description}")
        context_str = "\n".join(context_parts) if context_parts else "정보 없음"

        prompt = f"""회의 음성 인식(STT) 결과를 교정해주세요.

[회의 배경]
{context_str}

[교정 규칙]
- 음성 인식 오류만 교정 (예: "매줄"→"매출", "결제"→"결재", 동음이의어 오류)
- 회사/회의 맥락에 맞는 전문 용어로 교정
- 문맥상 명백한 오류만 수정, 확실하지 않으면 원문 유지
- 문장 구조나 의미를 변경하지 않음

[발화 목록]
{utterances_text}

다음 JSON 형식으로 응답:
{{"corrections": [{{"index": 0, "text": "교정된 텍스트"}}, ...]}}

교정이 필요 없는 발화는 corrections에 포함하지 마세요."""

        try:
            result = await ask_json(prompt, model=settings.llm_model_fast)
            corrections = {c["index"]: c["text"] for c in result.get("corrections", [])}

            corrected = []
            for i, u in enumerate(batch):
                if i in corrections and corrections[i] != u.text:
                    logger.info("교정: [%s] %r → %r", u.speaker, u.text, corrections[i])
                    u.text = corrections[i]
                    corrected.append(u)

            return corrected if corrected else []
        except Exception:
            logger.warning("STT 교정 실패", exc_info=True)
            return []
