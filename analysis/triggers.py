"""개입 트리거 감지 & 액션 생성.

트리거 종류:
  - 논의 순환: 같은 키워드/논점 3회+ 반복
  - 결론 없이 전환: 토픽 전환 + decision=null
  - 합의 신호: "그렇게 하죠", "동의합니다" 등
  - 정보 부족: "확인해봐야", "자료가 있나" 등

개입 방식: 사이드바 카드 (info / warning / action_required)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from models import Utterance, Intervention, AlertLevel

if TYPE_CHECKING:
    from pipeline import MeetingState

CONSENSUS_KEYWORDS = ["그렇게 하죠", "동의합니다", "좋습니다", "그렇게 합시다"]
INFO_NEEDED_KEYWORDS = ["확인해봐야", "자료가 있나", "데이터를 봐야", "찾아봐야"]


class TriggerDetector:
    """개입 트리거 감지 + 카드 생성."""

    async def check(self, utterance: Utterance, state: MeetingState) -> list[Intervention]:
        results: list[Intervention] = []

        if inv := self._check_consensus(utterance):
            results.append(inv)
        if inv := self._check_info_needed(utterance):
            results.append(inv)
        if inv := self._check_no_decision(state):
            results.append(inv)

        return results

    def _check_consensus(self, utterance: Utterance) -> Intervention | None:
        for kw in CONSENSUS_KEYWORDS:
            if kw in utterance.text:
                return Intervention(
                    trigger_type="consensus",
                    message=f"결정사항으로 기록합니다: {utterance.text}",
                    level=AlertLevel.INFO,
                )
        return None

    def _check_info_needed(self, utterance: Utterance) -> Intervention | None:
        for kw in INFO_NEEDED_KEYWORDS:
            if kw in utterance.text:
                return Intervention(
                    trigger_type="info_needed",
                    message=f"관련 자료를 검색합니다: {utterance.text}",
                    level=AlertLevel.INFO,
                )
        return None

    def _check_no_decision(self, state: MeetingState) -> Intervention | None:
        if len(state.topics) < 2:
            return None
        prev = state.topics[-2]
        prev_issue = state.issues.get(prev.id)
        if prev_issue and prev_issue.decision is None:
            return Intervention(
                trigger_type="no_decision",
                message=f"이전 안건 '{prev.title}'에 대한 결정이 내려지지 않았습니다",
                level=AlertLevel.WARNING,
                topic_id=prev.id,
            )
        return None

    @staticmethod
    def format_card(intervention: Intervention) -> dict:
        """Intervention → 프론트엔드 카드 데이터."""
        styles = {
            AlertLevel.INFO: {"color": "blue", "icon": "info"},
            AlertLevel.WARNING: {"color": "orange", "icon": "warning"},
            AlertLevel.ACTION_REQUIRED: {"color": "red", "icon": "alert"},
        }
        return {
            "type": intervention.trigger_type,
            "message": intervention.message,
            "level": intervention.level.value,
            "topic_id": intervention.topic_id,
            "style": styles[intervention.level],
        }
