"""분석 파이프라인 — 모듈 간 데이터 흐름 오케스트레이션.

흐름:
  마이크 → STT → 텍스트 버퍼 → [토픽 감지 | 쟁점 구조화 | 개입 감지 | 자료 수집]
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from dataclasses import dataclass, field

from models import Utterance, Topic, IssueGraph, Intervention, Reference

logger = logging.getLogger(__name__)


@dataclass
class MeetingState:
    """회의 전체 상태."""

    utterances: list[Utterance] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    issues: dict[int, IssueGraph] = field(default_factory=dict)
    interventions: list[Intervention] = field(default_factory=list)
    latest_interventions: list[Intervention] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    current_silence_ms: float = 0.0


class Pipeline:
    """메인 파이프라인 — STT 결과를 받아 분석 모듈들에 전달."""

    def __init__(self) -> None:
        self.state = MeetingState()
        self.meeting_id: int | None = None
        self._on_update: list = []
        self._stt = None
        self._topic_detector = None
        self._issue_structurer = None
        self._trigger_detector = None
        self._entity_extractor = None
        self._reference_collector = None

    def add_listener(self, callback) -> None:
        """상태 변경 시 호출할 콜백 등록."""
        self._on_update.append(callback)

    async def _emit(self, event_type: str, data=None) -> None:
        for cb in self._on_update:
            try:
                await cb(event_type, data)
            except Exception:
                logger.warning("이벤트 콜백 실패", exc_info=True)

    @property
    def stt(self):
        if self._stt is None:
            from stt.sensevoice import SenseVoiceEngine
            self._stt = SenseVoiceEngine()
        return self._stt

    @property
    def topic_detector(self):
        if self._topic_detector is None:
            from analysis.topic import TopicDetector
            self._topic_detector = TopicDetector()
        return self._topic_detector

    @property
    def issue_structurer(self):
        if self._issue_structurer is None:
            from analysis.issues import IssueStructurer
            self._issue_structurer = IssueStructurer()
        return self._issue_structurer

    @property
    def trigger_detector(self):
        if self._trigger_detector is None:
            from analysis.triggers import TriggerDetector
            self._trigger_detector = TriggerDetector()
        return self._trigger_detector

    @property
    def entity_extractor(self):
        if self._entity_extractor is None:
            from search import EntityExtractor
            self._entity_extractor = EntityExtractor()
        return self._entity_extractor

    @property
    def reference_collector(self):
        if self._reference_collector is None:
            from search import ReferenceCollector
            self._reference_collector = ReferenceCollector()
        return self._reference_collector

    async def start_meeting(self, title: str | None = None, audio_path: str | None = None) -> int:
        """새 회의 시작 → DB에 레코드 생성, meeting_id 반환."""
        import db
        self.meeting_id = await db.create_meeting(title=title, audio_path=audio_path)
        logger.info("회의 시작: meeting_id=%d", self.meeting_id)
        return self.meeting_id

    async def end_meeting(self) -> None:
        """회의 종료 → DB에 ended_at 기록."""
        if self.meeting_id:
            import db
            await db.end_meeting(self.meeting_id)
            logger.info("회의 종료: meeting_id=%d", self.meeting_id)

    async def on_utterance(self, utterance: Utterance) -> None:
        """새 발화 수신 → 전체 파이프라인 트리거."""
        self.state.utterances.append(utterance)

        # DB 저장
        await self._save_utterance(utterance)

        # 토픽 전환 감지
        new_topic = None
        try:
            new_topic = await self.topic_detector.check(utterance)
            if new_topic:
                self.state.topics.append(new_topic)
                await self._save_topic(new_topic)
        except Exception:
            logger.warning("토픽 감지 실패", exc_info=True)

        # 현재 토픽에 발화 추가
        if self.state.topics:
            self.state.topics[-1].utterances.append(utterance)

        # 쟁점 구조화 / 개입 감지 / 자료 수집 — 병렬 실행
        await asyncio.gather(
            self._update_issues(utterance),
            self._check_triggers(utterance),
            self._search_references(utterance),
            return_exceptions=True,
        )

        # WebSocket broadcast
        await self._emit("utterance", utterance)
        if new_topic:
            await self._emit("topic", new_topic)

    async def _save_utterance(self, utterance: Utterance) -> None:
        if not self.meeting_id:
            return
        try:
            import db
            await db.save_utterance(
                self.meeting_id, utterance.time, utterance.speaker, utterance.text,
            )
        except Exception:
            logger.warning("발화 DB 저장 실패", exc_info=True)

    async def _save_topic(self, topic: Topic) -> None:
        if not self.meeting_id:
            return
        try:
            import db
            # 이전 토픽 end_time 업데이트
            if len(self.state.topics) >= 2:
                prev = self.state.topics[-2]
                if prev.end_time:
                    await db.update_topic_end_time(self.meeting_id, prev.id, prev.end_time)
            await db.save_topic(
                self.meeting_id, topic.id, topic.title, topic.start_time,
            )
        except Exception:
            logger.warning("토픽 DB 저장 실패", exc_info=True)

    async def _update_issues(self, utterance: Utterance) -> None:
        if not self.state.topics:
            return
        try:
            current = self.state.topics[-1]
            issue = await self.issue_structurer.update(current, utterance)
            self.state.issues[current.id] = issue
            # DB 저장
            if self.meeting_id and issue:
                import db
                await db.save_issue(
                    self.meeting_id, current.id, dataclasses.asdict(issue),
                )
        except Exception:
            logger.warning("쟁점 구조화 실패", exc_info=True)

    async def _check_triggers(self, utterance: Utterance) -> None:
        try:
            interventions = await self.trigger_detector.check(utterance, self.state)
            self.state.latest_interventions = interventions
            self.state.interventions.extend(interventions)
            # DB 저장
            if self.meeting_id and interventions:
                import db
                for iv in interventions:
                    await db.save_intervention(
                        self.meeting_id, iv.trigger_type, iv.message,
                        iv.level.value, iv.topic_id,
                    )
        except Exception:
            logger.warning("트리거 감지 실패", exc_info=True)

    async def _search_references(self, utterance: Utterance) -> None:
        try:
            entities = await self.entity_extractor.extract(utterance)
            for entity in entities:
                refs = await self.reference_collector.search(entity)
                self.state.references.extend(refs)
                # DB 저장
                if self.meeting_id and refs:
                    import db
                    for ref in refs:
                        await db.save_reference(
                            self.meeting_id, ref.query, ref.source,
                            ref.title, ref.snippet, ref.url, ref.relevance_score,
                        )
        except Exception:
            logger.warning("자료 수집 실패", exc_info=True)
