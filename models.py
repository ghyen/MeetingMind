"""데이터 모델 — 모든 모듈에서 공유하는 스키마."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Utterance:
    """STT + 화자 분리 결과 단위."""

    time: str  # "00:01:23"
    speaker: str  # "A", "B", ...
    text: str
    is_final: bool = True


@dataclass
class Topic:
    """토픽 세그먼트."""

    id: int
    title: str
    start_time: str
    end_time: str | None = None
    utterances: list[Utterance] = field(default_factory=list)


@dataclass
class Position:
    """한 화자의 입장."""

    speaker: str
    stance: str
    arguments: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


@dataclass
class IssueGraph:
    """안건별 논점 그래프."""

    topic: str
    positions: list[Position] = field(default_factory=list)
    consensus: str | None = None
    open_questions: list[str] = field(default_factory=list)
    decision: str | None = None


class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ACTION_REQUIRED = "action_required"


@dataclass
class Intervention:
    """UI에 표시할 개입 카드."""

    trigger_type: str  # "loop" | "no_decision" | "consensus" | "silence" | "info_needed" | "time_over"
    message: str
    level: AlertLevel = AlertLevel.INFO
    topic_id: int | None = None


@dataclass
class Reference:
    """자동 수집된 참고 자료."""

    query: str
    source: str  # "internal" | "web"
    title: str
    snippet: str
    url: str | None = None
    relevance_score: float = 0.0
