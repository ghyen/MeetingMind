"""토픽 전환 감지 & 안건 세그멘테이션.

2단계 감지:
  1. 규칙 기반: 긴 침묵(3초+), 키워드("다음 안건", "그건 그렇고" 등)
  2. LLM 판단: 트리거 조건 충족 시에만 호출 (Haiku급 소형 모델)
"""

from __future__ import annotations

from config import settings
from models import Utterance, Topic


class TopicDetector:
    """토픽 전환 감지 + 안건 세그멘테이션."""

    def __init__(self) -> None:
        self._topic_counter = 0
        self._last_silence_ms: float = 0.0
        self.segments: list[Topic] = []

    async def check(self, utterance: Utterance) -> Topic | None:
        """새 발화가 토픽 전환인지 판단. 전환이면 새 Topic 반환."""
        if not self._is_trigger(utterance):
            return None

        new_topic = await self._llm_judge(utterance)
        if new_topic:
            # 이전 토픽 종료
            if self.segments:
                self.segments[-1].end_time = new_topic.start_time
            self.segments.append(new_topic)
        return new_topic

    def _is_trigger(self, utterance: Utterance) -> bool:
        """규칙 기반 1차 필터."""
        for keyword in settings.topic_keywords:
            if keyword in utterance.text:
                return True
        if self._last_silence_ms >= settings.topic_silence_threshold_sec * 1000:
            return True
        return False

    async def _llm_judge(self, utterance: Utterance) -> Topic | None:
        """LLM 2차 판단 — 토픽 전환 여부 + 토픽명 추출."""
        # TODO: LLM 호출
        self._topic_counter += 1
        return Topic(
            id=self._topic_counter,
            title="",  # LLM이 생성
            start_time=utterance.time,
        )

    def get_current(self) -> Topic | None:
        return self.segments[-1] if self.segments else None

    def get_summary(self) -> list[dict]:
        return [
            {"id": t.id, "title": t.title, "start": t.start_time, "end": t.end_time or "진행중"}
            for t in self.segments
        ]
