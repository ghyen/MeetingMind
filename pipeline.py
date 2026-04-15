"""분석 파이프라인 — 모듈 간 데이터 흐름 오케스트레이션.

흐름:
  마이크 → STT → 텍스트 버퍼 → [토픽 감지 | 쟁점 구조화 | 개입 감지 | 자료 수집]
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
import time
from dataclasses import dataclass, field

from models import Utterance, Topic, IssueGraph, Intervention, Reference

logger = logging.getLogger(__name__)


class _StepTimer:
    """파이프라인 단계별 소요 시간 측정."""

    def __init__(self) -> None:
        self._steps: list[tuple[str, float]] = []
        self._t0 = time.perf_counter()

    def step(self, name: str) -> "_StepCtx":
        return _StepCtx(name, self._steps)

    def log_summary(self, label: str) -> None:
        total = time.perf_counter() - self._t0
        if total == 0:
            return
        parts = []
        for name, elapsed in self._steps:
            pct = elapsed / total * 100
            parts.append(f"{name}: {elapsed:.2f}s ({pct:.0f}%)")
        logger.info(
            "[%s] 총 %.2f초 | %s",
            label, total, " | ".join(parts),
        )


class _StepCtx:
    def __init__(self, name: str, steps: list) -> None:
        self._name = name
        self._steps = steps

    async def __aenter__(self):
        self._start = time.perf_counter()
        return self

    async def __aexit__(self, *exc):
        self._steps.append((self._name, time.perf_counter() - self._start))


@dataclass
class MeetingState:
    """회의 전체 상태."""

    utterances: list[Utterance] = field(default_factory=list)
    topics: list[Topic] = field(default_factory=list)
    issues: dict[int, IssueGraph] = field(default_factory=dict)
    interventions: list[Intervention] = field(default_factory=list)
    latest_interventions: list[Intervention] = field(default_factory=list)
    references: list[Reference] = field(default_factory=list)
    latest_corrections: list[Utterance] = field(default_factory=list)
    current_silence_ms: float = 0.0


class Pipeline:
    """메인 파이프라인 — STT 결과를 받아 분석 모듈들에 전달."""

    def __init__(self) -> None:
        self.state = MeetingState()
        self.meeting_id: int | None = None
        self._on_update: list = []
        self._topic_detector = None
        self._issue_structurer = None
        self._trigger_detector = None
        self._entity_extractor = None
        self._reference_collector = None
        self._stt_corrector = None

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

    @property
    def stt_corrector(self):
        if self._stt_corrector is None:
            from analysis.correction import STTCorrector
            self._stt_corrector = STTCorrector()
        return self._stt_corrector

    async def start_meeting(
        self,
        title: str | None = None,
        audio_path: str | None = None,
        company: str = "",
        description: str = "",
    ) -> int:
        """새 회의 시작 → DB에 레코드 생성, meeting_id 반환."""
        import db
        self.meeting_id = await db.create_meeting(title=title, audio_path=audio_path)
        # 회의 컨텍스트 설정 → STT 교정에 활용
        if company or description:
            from analysis.correction import MeetingContext
            self.stt_corrector.set_context(MeetingContext(company=company, description=description))
        logger.info("회의 시작: meeting_id=%d", self.meeting_id)
        return self.meeting_id

    async def end_meeting(self) -> dict | None:
        """회의 종료 → 제목 생성 + 회의록 요약 생성 → DB에 저장."""
        summary = None
        if self.meeting_id:
            import db
            from analysis.summary import generate_summary

            # 회의 제목 자동 생성 (발화 내용 기반)
            title = await self._generate_title()
            if title:
                await db.update_meeting_title(self.meeting_id, title)
                logger.info("회의 제목 생성: '%s'", title)

            summary = await generate_summary(self.state)
            if summary:
                await db.save_summary(self.meeting_id, summary)
                logger.info("회의록 요약 생성 완료: meeting_id=%d", self.meeting_id)

            await db.end_meeting(self.meeting_id)
            logger.info("회의 종료: meeting_id=%d", self.meeting_id)
        return summary

    async def _generate_title(self) -> str | None:
        """발화 내용에서 회의 제목을 짧게 생성 (10자 이내)."""
        if not self.state.utterances:
            return None
        try:
            from analysis.llm import ask_json
            # 최근 발화에서 핵심 주제 추출
            recent = self.state.utterances[:10] + self.state.utterances[-5:]
            lines = "\n".join(f"[{u.speaker}] {u.text}" for u in recent)
            topics = ", ".join(t.title for t in self.state.topics) if self.state.topics else ""
            data = await ask_json(
                f"회의 발화:\n{lines}\n\n안건: {topics}\n\n"
                "이 회의의 제목을 10자 이내 한국어로 생성하세요.\n"
                '{"title": "회의 제목"}'
            )
            return data.get("title", "")[:20] or None
        except Exception:
            logger.warning("회의 제목 생성 실패", exc_info=True)
            return None

    async def on_utterance(self, utterance: Utterance) -> None:
        """새 발화 수신 → 전체 파이프라인 트리거.

        모든 입력 경로(WebSocket, 파일 업로드, 시뮬레이션)가 최종적으로 이 메서드를 호출.
        처리 순서: DB저장 → 토픽감지 → 트리거감지 → 쟁점구조화+자료수집 → WS broadcast
        """
        timer = _StepTimer()
        self.state.utterances.append(utterance)

        # 1) DB 저장 — 발화 원문을 즉시 영구 저장
        async with timer.step("DB저장"):
            await self._save_utterance(utterance)

        # 1.5) STT 교정 — 5개 발화마다 배치 교정
        async with timer.step("STT교정"):
            await self._correct_stt(utterance)

        # 2) 토픽 전환 감지 — 3단계 필터(키워드→키워드2개+→LLM)로 판단
        new_topic = None
        async with timer.step("토픽감지"):
            try:
                new_topic = await self.topic_detector.check(utterance)
                if new_topic:
                    self.state.topics.append(new_topic)
                    await self._save_topic(new_topic)
            except Exception:
                logger.warning("토픽 감지 실패", exc_info=True)

        # 3) 현재 토픽에 발화 연결 — 토픽별 발화 목록은 쟁점구조화/loop감지에 사용
        if self.state.topics:
            self.state.topics[-1].utterances.append(utterance)

        # 4) 분석 모듈 실행
        # Ollama는 내부적으로 요청을 직렬 처리하므로 병렬 호출해도 이득이 없음.
        # OpenRouter 등 외부 API는 병렬 호출로 쟁점구조화+자료수집을 동시에 처리.
        from analysis.llm import _active_provider
        if _active_provider in ("ollama", "bonsai"):
            async with timer.step("트리거감지"):
                await self._check_triggers(utterance)
            async with timer.step("쟁점구조화"):
                await self._update_issues(utterance)
            async with timer.step("자료수집"):
                await self._search_references(utterance)
        else:
            # 트리거 감지는 키워드 기반이라 빠르므로 먼저 순차 실행
            async with timer.step("트리거감지"):
                await self._check_triggers(utterance)
            # 쟁점구조화와 자료수집은 각각 LLM 호출이 필요하므로 병렬로 실행
            t_issues = time.perf_counter()
            t_refs = time.perf_counter()

            async def _timed_issues():
                nonlocal t_issues
                await self._update_issues(utterance)
                t_issues = time.perf_counter() - t_issues

            async def _timed_refs():
                nonlocal t_refs
                await self._search_references(utterance)
                t_refs = time.perf_counter() - t_refs

            await asyncio.gather(
                _timed_issues(), _timed_refs(), return_exceptions=True,
            )
            timer._steps.append(("쟁점구조화", t_issues))
            timer._steps.append(("자료수집", t_refs))

        # 5) WebSocket broadcast — 연결된 모든 클라이언트에 실시간 push
        await self._emit("utterance", utterance)
        if new_topic:
            await self._emit("topic", new_topic)

        timer.log_summary(f"파이프라인 발화#{len(self.state.utterances)}")

    async def _correct_stt(self, utterance: Utterance) -> None:
        """STT 교정 — 5개 발화 배치 교정 후 UI 반영."""
        self.state.latest_corrections = []
        try:
            corrected = await self.stt_corrector.feed(utterance)
            if corrected:
                self.state.latest_corrections = corrected
                await self._emit("correction", corrected)
                # DB에 교정된 텍스트 업데이트
                if self.meeting_id:
                    import db
                    for u in corrected:
                        await db.update_utterance_text(
                            self.meeting_id, u.time, u.speaker, u.text,
                        )
        except Exception:
            logger.warning("STT 교정 실패", exc_info=True)

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
        """발화에서 엔티티 추출 → 각 엔티티별 사내DB+웹 검색 → 결과 축적."""
        try:
            entities = await self.entity_extractor.extract(utterance)
            for entity in entities:
                refs = await self.reference_collector.search(entity)
                if not refs:
                    continue
                self.state.references.extend(refs)
                # 검색 완료 즉시 UI에 push — on_utterance 전체 완료를 기다리지 않음
                await self._emit("references", self.state.references[-5:])
                # DB 저장
                if self.meeting_id:
                    import db
                    for ref in refs:
                        await db.save_reference(
                            self.meeting_id, ref.query, ref.source,
                            ref.title, ref.snippet, ref.url, ref.relevance_score,
                        )
        except Exception:
            logger.warning("자료 수집 실패", exc_info=True)
