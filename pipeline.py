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


def _parse_time_str(t: str) -> float | None:
    """'HH:MM:SS' 또는 'HH:MM:SS.mmm' → 초. 파싱 실패 시 None."""
    if not t:
        return None
    try:
        parts = t.split(":")
        if len(parts) != 3:
            return None
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    except (ValueError, TypeError):
        return None


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
        self._reference_collector = None
        self._stt_corrector = None
        # 직전 발화의 스트림 경과초 — 발화 간격으로 침묵 길이 추정
        self._last_utterance_seconds: float | None = None
        self._manual_meeting_title: bool = False

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
        """새 회의 시작 → 이전 회의 상태 초기화 + DB에 레코드 생성."""
        import db

        # 이전 회의가 아직 열려 있으면 종료 처리 (요약 저장)
        if self.meeting_id:
            try:
                await self.end_meeting()
            except Exception:
                logger.warning("이전 회의 종료 중 오류 — 상태 초기화 계속", exc_info=True)

        # 메모리 상태 초기화 — 이전 회의 덤프 데이터가 남지 않도록
        self.state = MeetingState()
        self.topic_detector._topic_counter = 0
        self.topic_detector.segments = []
        self.topic_detector._recent = []
        self.topic_detector._last_silence_ms = 0.0
        self.topic_detector._utterances_since_last_check = 0
        self.issue_structurer._cache = {}
        self.issue_structurer._pending = {}
        self._stt_corrector = None
        self._last_utterance_seconds = None
        self._manual_meeting_title = False

        self.meeting_id = await db.create_meeting(title=title, audio_path=audio_path)
        # 회의 컨텍스트 설정 → STT 교정에 활용
        if company or description:
            from analysis.correction import MeetingContext
            self.stt_corrector.set_context(MeetingContext(company=company, description=description))
        logger.info("회의 시작: meeting_id=%d", self.meeting_id)
        return self.meeting_id

    async def update_meeting_title(self, title: str) -> None:
        """사용자가 지정한 회의 제목 저장."""
        if not self.meeting_id:
            return
        import db
        await db.update_meeting_title(self.meeting_id, title)
        self._manual_meeting_title = True
        logger.info("회의 제목 수동 변경: '%s'", title)

    async def end_meeting(self) -> dict | None:
        """회의 종료 → 제목 생성 + 회의록 요약 생성 → DB에 저장."""
        summary = None
        if self.meeting_id:
            import db
            from analysis.summary import generate_summary

            # 회의 제목 자동 생성 (발화 내용 기반). 사용자가 직접 바꾼 제목은 보존.
            if not self._manual_meeting_title:
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

        # 2) 토픽 전환 감지 — 3단계 필터(키워드→키워드2개+→LLM) + N발화마다 강제 LLM 판정
        # 직전 발화와의 시간 간격을 침묵 길이 추정치로 TopicDetector에 주입
        new_topic = None
        async with timer.step("토픽감지"):
            try:
                cur_seconds = _parse_time_str(utterance.time)
                if cur_seconds is not None and self._last_utterance_seconds is not None:
                    gap_ms = max(0.0, (cur_seconds - self._last_utterance_seconds) * 1000.0)
                    self.topic_detector._last_silence_ms = gap_ms
                else:
                    self.topic_detector._last_silence_ms = 0.0
                if cur_seconds is not None:
                    self._last_utterance_seconds = cur_seconds

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
        # 트리거 감지는 키워드+카운터 기반이라 매우 빠르므로 먼저 순차 실행.
        async with timer.step("트리거감지"):
            await self._check_triggers(utterance)

        # 쟁점구조화 → 갱신된 경우에만 자료수집 (요약본 기준 검색).
        # 발화당 검색이 아니라 issue_token_threshold마다 1회 → 웹 호출 대폭 감소.
        async with timer.step("쟁점구조화"):
            updated_issue = await self._update_issues(utterance)

        if updated_issue is not None and self.state.topics:
            async with timer.step("자료수집"):
                await self._search_references(self.state.topics[-1], updated_issue)

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

    async def _update_issues(self, utterance: Utterance) -> IssueGraph | None:
        """쟁점 구조 갱신. 실제로 갱신된 경우에만 IssueGraph 반환, 아니면 None."""
        if not self.state.topics:
            return None
        try:
            current = self.state.topics[-1]
            issue = await self.issue_structurer.update(current, utterance)
            if issue is None:
                return None
            self.state.issues[current.id] = issue
            # DB 저장
            if self.meeting_id:
                import db
                await db.save_issue(
                    self.meeting_id, current.id, dataclasses.asdict(issue),
                )
            return issue
        except Exception:
            logger.warning("쟁점 구조화 실패", exc_info=True)
            return None

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
                        iv.level.value, iv.topic_id, iv.time,
                    )
        except Exception:
            logger.warning("트리거 감지 실패", exc_info=True)

    async def _search_references(self, topic: Topic, issue: IssueGraph) -> None:
        """쟁점 구조(요약본) 기준으로 사내DB+웹 검색.

        쟁점 구조가 갱신될 때만 호출되므로 발화당 검색 대비 호출 횟수가 크게 줄어든다.
        쿼리는 안건 제목 + 쟁점 토픽 + 첫 open_question 으로 구성.
        """
        try:
            refs = await self.reference_collector.search_for_issue(topic, issue)
            if not refs:
                return
            self.state.references.extend(refs)
            await self._emit("references", self.state.references[-5:])
            if self.meeting_id:
                import db
                for ref in refs:
                    await db.save_reference(
                        self.meeting_id, ref.query, ref.source,
                        ref.title, ref.snippet, ref.url, ref.relevance_score,
                    )
        except Exception:
            logger.warning("자료 수집 실패", exc_info=True)
