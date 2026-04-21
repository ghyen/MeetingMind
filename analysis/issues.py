"""쟁점 구조화 — 안건별 논점 그래프 구축.

점진적 업데이트: 누적 발화 토큰 수가 임계치를 넘으면 delta 반영 (settings.issue_token_threshold).
토큰 카운트는 tiktoken cl100k_base 기준 (다국어 근사치, 실제 LLM 토크나이저와 완전 동일하진 않지만 일관됨).
"""

from __future__ import annotations

import json
from functools import lru_cache

import tiktoken

from config import settings
from models import Topic, Utterance, IssueGraph, Position
from analysis.llm import ask_json
_MAX_UTTERANCES_IN_PROMPT = 15


@lru_cache(maxsize=1)
def _tokenizer() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def _count_tokens(text: str) -> int:
    return len(_tokenizer().encode(text))

_FEW_SHOT_EXAMPLE = """\
예시:
입력: [A] 배포 주기를 2주에서 1주로 줄이자 / [B] 테스트 자동화 없이 주간 배포는 위험하다
출력: {"topic": "배포 주기 단축", "positions": [{"speaker": "A", "stance": "배포 주기 2주→1주 단축 제안", "arguments": ["빠른 피드백 반영"], "evidence": []}, {"speaker": "B", "stance": "테스트 자동화 선행 필요", "arguments": ["자동화 없이 주간 배포 시 장애 위험"], "evidence": []}], "consensus": null, "open_questions": ["테스트 자동화 일정"], "decision": null}
"""


class IssueStructurer:
    """안건별 쟁점을 논점 그래프로 구조화."""

    def __init__(self) -> None:
        self._cache: dict[int, IssueGraph] = {}
        self._pending: dict[int, list[Utterance]] = {}
        self._pending_tokens: dict[int, int] = {}

    async def update(self, topic: Topic, new_utterance: Utterance) -> IssueGraph:
        """새 발화를 반영하여 쟁점 구조 점진적 업데이트.

        매 발화마다 LLM을 호출하면 비용과 지연이 크므로 배치 전략 사용:
        - 첫 발화: 즉시 _create_initial()로 초기 구조 생성
        - 이후: pending 큐에 축적 → 누적 토큰 수가 임계치를 넘으면 _apply_delta()로 일괄 반영
        - 임계치 미만: 기존 구조를 그대로 반환 (LLM 호출 안 함)
        """
        existing = self._cache.get(topic.id)
        self._pending.setdefault(topic.id, []).append(new_utterance)
        self._pending_tokens[topic.id] = (
            self._pending_tokens.get(topic.id, 0) + _count_tokens(new_utterance.text)
        )

        if existing is None:
            issue = await self._create_initial(topic)
            self._pending[topic.id] = []
            self._pending_tokens[topic.id] = 0
        elif self._pending_tokens[topic.id] >= settings.issue_token_threshold:
            issue = await self._apply_delta(existing, self._pending[topic.id])
            self._pending[topic.id] = []
            self._pending_tokens[topic.id] = 0
        else:
            return existing

        self._cache[topic.id] = issue
        return issue

    def get_pending_tokens(self, topic_id: int) -> int:
        """토픽별 현재 누적 토큰 수 반환."""
        return self._pending_tokens.get(topic_id, 0)

    async def _create_initial(self, topic: Topic) -> IssueGraph:
        """토픽의 발화들로 초기 쟁점 구조 생성 (Pro 모델)."""
        recent = topic.utterances[-_MAX_UTTERANCES_IN_PROMPT:]
        lines = "\n".join(f"[{u.speaker}] {u.text}" for u in recent)
        prompt = (
            f"회의 안건: {topic.title}\n\n"
            f"발화:\n{lines}\n\n"
            "위 내용을 분석하여 쟁점을 구조화하세요.\n"
            "규칙:\n"
            "- topic은 10자 이내로 핵심만 (예: '배포 주기 단축')\n"
            "- 같은 화자의 발언은 하나의 입장으로 병합하세요\n"
            "- positions는 최대 5개 이내로 유지하세요\n"
            "- stance에 구체적 수치/사실을 포함하세요 (예: '2주→1주 단축 제안')\n"
            "- consensus, decision은 문자열 또는 null\n\n"
            f"{_FEW_SHOT_EXAMPLE}\n"
            "JSON 형식으로 응답:"
        )
        data = await ask_json(prompt)
        return _parse_issue_graph(data)

    async def _apply_delta(
        self, existing: IssueGraph, new_utterances: list[Utterance]
    ) -> IssueGraph:
        """기존 구조에 새 발화들의 변경분만 반영 (Flash 모델)."""
        existing_json = json.dumps(
            _serialize_issue_graph(existing), ensure_ascii=False
        )
        lines = "\n".join(f"[{u.speaker}] {u.text}" for u in new_utterances)
        prompt = (
            f"기존 쟁점 구조:\n{existing_json}\n\n"
            f"새 발화:\n{lines}\n\n"
            "새 발화를 반영하여 업데이트된 전체 JSON을 반환하세요.\n"
            "규칙:\n"
            "- 같은 화자의 입장은 기존 항목에 병합하세요 (새 항목으로 추가하지 마세요)\n"
            "- positions는 최대 5개 이내로 유지하세요\n"
            "- stance에 구체적 수치/사실을 포함하세요 (예: '2주→1주 단축 제안')\n"
            "- topic은 10자 이내, consensus/decision은 문자열 또는 null"
        )
        data = await ask_json(prompt)
        return _parse_issue_graph(data)


_MAX_POSITIONS = 5


def _merge_positions(positions: list[Position]) -> list[Position]:
    """같은 화자의 position을 병합하고 최대 개수를 제한.

    LLM이 같은 화자를 별도 Position으로 반환하는 경우가 있으므로
    코드 레벨에서 강제 병합하여 화자당 1개 Position을 보장.
    stance는 더 상세한(긴) 것을 채택, arguments/evidence는 합산(중복 제거).
    """
    by_speaker: dict[str, Position] = {}
    for p in positions:
        if p.speaker in by_speaker:
            existing = by_speaker[p.speaker]
            if len(p.stance) > len(existing.stance):
                existing.stance = p.stance
            for arg in p.arguments:
                if arg not in existing.arguments:
                    existing.arguments.append(arg)
            for ev in p.evidence:
                if ev not in existing.evidence:
                    existing.evidence.append(ev)
        else:
            by_speaker[p.speaker] = Position(
                speaker=p.speaker,
                stance=p.stance,
                arguments=list(p.arguments),
                evidence=list(p.evidence),
            )
    merged = list(by_speaker.values())
    return merged[:_MAX_POSITIONS]


def _parse_issue_graph(data: dict) -> IssueGraph:
    raw_positions = [
        Position(
            speaker=p.get("speaker", ""),
            stance=p.get("stance", ""),
            arguments=p.get("arguments", []),
            evidence=p.get("evidence", []),
        )
        for p in data.get("positions", [])
    ]
    positions = _merge_positions(raw_positions)
    consensus = data.get("consensus")
    decision = data.get("decision")
    return IssueGraph(
        topic=data.get("topic", ""),
        positions=positions,
        consensus=str(consensus) if consensus and not isinstance(consensus, str) else consensus,
        open_questions=data.get("open_questions", []),
        decision=str(decision) if decision and not isinstance(decision, str) else decision,
    )


def _serialize_issue_graph(graph: IssueGraph) -> dict:
    return {
        "topic": graph.topic,
        "positions": [
            {
                "speaker": p.speaker,
                "stance": p.stance,
                "arguments": p.arguments,
                "evidence": p.evidence,
            }
            for p in graph.positions
        ],
        "consensus": graph.consensus,
        "open_questions": graph.open_questions,
        "decision": graph.decision,
    }
