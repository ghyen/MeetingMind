"""분석 파이프라인 — 모듈 간 데이터 흐름 오케스트레이션.

흐름:
  마이크 → STT → 텍스트 버퍼 → [토픽 감지 | 쟁점 구조화 | 개입 감지 | 자료 수집]
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from models import Utterance, Topic, IssueGraph, Intervention, Reference
from stt.sensevoice import SenseVoiceEngine
from analysis.topic import TopicDetector
from analysis.issues import IssueStructurer
from analysis.triggers import TriggerDetector
from search import EntityExtractor


@dataclass
class MeetingState:
    """회의 전체 상태."""

    utterances: list[Utterance] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    issues: dict[int, IssueGraph] = field(default_factory=dict)
    interventions: list[Intervention] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)


class Pipeline:
    """메인 파이프라인 — STT 결과를 받아 분석 모듈들에 전달."""

    def __init__(self) -> None:
        self.state = MeetingState()
        self.stt = SenseVoiceEngine()
        self.topic_detector = TopicDetector()
        self.issue_structurer = IssueStructurer()
        self.trigger_detector = TriggerDetector()
        self.entity_extractor = EntityExtractor()

    async def on_utterance(self, utterance: Utterance) -> None:
        """새 발화 수신 → 전체 파이프라인 트리거."""
        self.state.utterances.append(utterance)

        # 토픽 전환 감지
        new_topic = await self.topic_detector.check(utterance)
        if new_topic:
            self.state.topics.append(new_topic)

        # 현재 토픽에 발화 추가
        if self.state.topics:
            self.state.topics[-1].utterances.append(utterance)

        # 쟁점 구조화 / 개입 감지 / 자료 수집 — 병렬 실행
        await asyncio.gather(
            self._update_issues(utterance),
            self._check_triggers(utterance),
            self._search_references(utterance),
        )

    async def _update_issues(self, utterance: Utterance) -> None:
        if not self.state.topics:
            return
        current = self.state.topics[-1]
        issue = await self.issue_structurer.update(current, utterance)
        self.state.issues[current.id] = issue

    async def _check_triggers(self, utterance: Utterance) -> None:
        interventions = await self.trigger_detector.check(utterance, self.state)
        self.state.interventions.extend(interventions)

    async def _search_references(self, utterance: Utterance) -> None:
        entities = await self.entity_extractor.extract(utterance)
        # TODO: 엔티티 기반 검색 수행
