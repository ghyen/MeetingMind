"""쟁점 구조화 — 안건별 논점 그래프 구축.

점진적 업데이트: 발화 3개마다 batch로 delta 반영.
"""

from __future__ import annotations

import json

from config import settings
from models import Topic, Utterance, IssueGraph, Position
from analysis.llm import ask_json

_BATCH_SIZE = 5
_MAX_UTTERANCES_IN_PROMPT = 15

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

    async def update(self, topic: Topic, new_utterance: Utterance) -> IssueGraph:
        """새 발화를 반영하여 쟁점 구조 점진적 업데이트."""
        existing = self._cache.get(topic.id)
        self._pending.setdefault(topic.id, []).append(new_utterance)

        if existing is None:
            issue = await self._create_initial(topic)
            self._pending[topic.id] = []
        elif len(self._pending[topic.id]) >= _BATCH_SIZE:
            issue = await self._apply_delta(existing, self._pending[topic.id])
            self._pending[topic.id] = []
        else:
            return existing

        self._cache[topic.id] = issue
        return issue

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


def _parse_issue_graph(data: dict) -> IssueGraph:
    positions = [
        Position(
            speaker=p.get("speaker", ""),
            stance=p.get("stance", ""),
            arguments=p.get("arguments", []),
            evidence=p.get("evidence", []),
        )
        for p in data.get("positions", [])
    ]
    return IssueGraph(
        topic=data.get("topic", ""),
        positions=positions,
        consensus=data.get("consensus"),
        open_questions=data.get("open_questions", []),
        decision=data.get("decision"),
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
