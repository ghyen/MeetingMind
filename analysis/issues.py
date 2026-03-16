"""쟁점 구조화 — 안건별 논점 그래프 구축.

핵심: 점진적 업데이트 (incremental update)
  - 새 발화 → 기존 구조에 delta만 반영 (전체 재분석 X)
  - 프롬프트: "기존 구조화 결과가 있다. 새 발화를 반영해 변경된 부분만 업데이트하라"
"""

from __future__ import annotations

from models import Topic, Utterance, IssueGraph


class IssueStructurer:
    """안건별 쟁점을 논점 그래프로 구조화."""

    def __init__(self) -> None:
        self._cache: dict[int, IssueGraph] = {}

    async def update(self, topic: Topic, new_utterance: Utterance) -> IssueGraph:
        """새 발화를 반영하여 쟁점 구조 점진적 업데이트."""
        existing = self._cache.get(topic.id)

        if existing is None:
            issue = await self._create_initial(topic, new_utterance)
        else:
            issue = await self._apply_delta(existing, new_utterance)

        self._cache[topic.id] = issue
        return issue

    async def _create_initial(self, topic: Topic, utterance: Utterance) -> IssueGraph:
        """첫 발화로 초기 쟁점 구조 생성."""
        # TODO: LLM 호출
        return IssueGraph(topic=topic.title)

    async def _apply_delta(self, existing: IssueGraph, utterance: Utterance) -> IssueGraph:
        """기존 구조에 새 발화의 변경분만 반영."""
        # TODO: LLM 호출 — delta 업데이트
        return existing
