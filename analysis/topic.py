"""토픽 전환 감지 & 안건 세그멘테이션.

3단계 감지:
  1차 필터: 키워드 1개+ 매칭 또는 긴 침묵(3초+) → 후보 선별
  2차 필터: 키워드 2개+ 동시 매칭 → LLM 없이 전환 확정
  3차 판단: 1차 통과 & 2차 미통과 → LLM이 최종 판단
"""

from __future__ import annotations

from config import settings
from models import Utterance, Topic
from analysis.llm import ask_json


class TopicDetector:
    """토픽 전환 감지 + 안건 세그멘테이션."""

    def __init__(self) -> None:
        self._topic_counter = 0
        self._last_silence_ms: float = 0.0
        self.segments: list[Topic] = []
        self._recent: list[Utterance] = []

    async def check(self, utterance: Utterance) -> Topic | None:
        """새 발화가 토픽 전환인지 판단. 전환이면 새 Topic 반환."""
        self._recent.append(utterance)
        self._recent = self._recent[-10:]

        # 첫 발화 시 초기 토픽 자동 생성
        if not self.segments:
            self._topic_counter += 1
            initial = Topic(
                id=self._topic_counter,
                title="회의 시작",
                start_time=utterance.time,
            )
            self.segments.append(initial)
            return initial

        if not self._first_filter(utterance):
            return None

        # 2차 필터: 키워드 2개+ → LLM 스킵
        new_topic = self._second_filter(utterance)
        if new_topic is None:
            # 3차 판단: LLM 최종 판단
            new_topic = await self._llm_judge(utterance)
        if new_topic:
            if self.segments:
                self.segments[-1].end_time = new_topic.start_time
            self.segments.append(new_topic)
        return new_topic

    # 2차 필터 키워드 — 2개+ 동시 매칭 시 전환 확정
    _SECOND_FILTER_KEYWORDS = ["마무리", "정리", "넘어가서", "다음 안건", "다음으로"]

    def _second_filter(self, utterance: Utterance) -> Topic | None:
        """2차 필터: 키워드 2개+ 동시 매칭 → LLM 없이 전환 확정."""
        matched = [kw for kw in self._SECOND_FILTER_KEYWORDS if kw in utterance.text]
        if len(matched) >= 2:
            self._topic_counter += 1
            # 매칭된 키워드에서 토픽명 유추
            if any(kw in matched for kw in ("마무리", "정리")):
                title = "마무리 및 정리"
            else:
                title = "다음 안건"
            return Topic(id=self._topic_counter, title=title, start_time=utterance.time)
        return None

    def _first_filter(self, utterance: Utterance) -> bool:
        """1차 필터: 키워드 1개+ 또는 긴 침묵 → 후보 선별."""
        for keyword in settings.topic_keywords:
            if keyword in utterance.text:
                return True
        if self._last_silence_ms >= settings.topic_silence_threshold_sec * 1000:
            return True
        return False

    async def _llm_judge(self, utterance: Utterance) -> Topic | None:
        """3차 판단: LLM이 토픽 전환 여부 + 토픽명 최종 결정."""
        context = "\n".join(
            f"[{u.speaker}] {u.text}" for u in self._recent
        )
        prompt = (
            "다음은 회의 중 최근 발화입니다:\n\n"
            f"{context}\n\n"
            "마지막 발화 기준으로 새로운 토픽/안건이 시작되었는지 판단하세요.\n"
            "중요: '마무리', '정리', '넘어가서', '다음으로' 등 wrap-up/전환 표현이 있으면 "
            "현재 토픽의 연장이 아니라 새로운 토픽(마무리/정리 안건)으로 분류하세요.\n"
            'JSON: {"changed": true/false, "title": "토픽명 (10자 이내)"}'
        )
        data = await ask_json(prompt)

        if data.get("changed"):
            self._topic_counter += 1
            return Topic(
                id=self._topic_counter,
                title=data.get("title", ""),
                start_time=utterance.time,
            )
        return None

    def get_current(self) -> Topic | None:
        return self.segments[-1] if self.segments else None

    def get_summary(self) -> list[dict]:
        return [
            {"id": t.id, "title": t.title, "start": t.start_time, "end": t.end_time or "진행중"}
            for t in self.segments
        ]
