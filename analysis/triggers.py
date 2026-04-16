"""개입 트리거 감지 & 액션 생성.

트리거 종류:
  - 논의 순환: 같은 키워드 3회+ 반복
  - 긴 침묵: 5초+ 무음
  - 시간 초과: 안건별 10분+
  - 합의 신호: "그렇게 하죠" 등
  - 정보 부족: "확인해봐야" 등
  - 결론 없이 전환
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from config import settings
from models import Utterance, Intervention, AlertLevel

if TYPE_CHECKING:
    from pipeline import MeetingState

CONSENSUS_KEYWORDS = ["그렇게 하죠", "동의합니다", "좋습니다", "그렇게 합시다"]
INFO_NEEDED_KEYWORDS = ["확인해봐야", "자료가 있나", "데이터를 봐야", "찾아봐야"]
# loop 감지에서 제외할 불용어 (일반적으로 자주 쓰이는 단어)
_STOPWORDS = {
    "정도", "것", "수", "거", "때", "때문에", "이번", "다음", "하는",
    "있는", "없는", "하고", "해서", "그래서", "근데", "그리고", "하면",
    "되는", "같은", "좀", "더", "안", "못", "잘", "또", "이",
    "그", "저", "네", "아", "예", "뭐", "어떻게", "얼마나",
    "합니다", "됩니다", "입니다", "있습니다", "없습니다", "했습니다",
    "하겠습니다", "같습니다", "봅니다", "있어요", "없어요", "해요",
    "건데", "건데요", "거든요", "거예요",
}


class TriggerDetector:
    """개입 트리거 감지 + 카드 생성."""

    def __init__(self) -> None:
        self._emitted_no_decision: set[int] = set()

    async def check(self, utterance: Utterance, state: MeetingState) -> list[Intervention]:
        results: list[Intervention] = []

        if inv := self._check_consensus(utterance):
            results.append(inv)
        if inv := self._check_info_needed(utterance):
            results.append(inv)
        if inv := self._check_no_decision(state):
            results.append(inv)
        if inv := self._check_loop(state):
            results.append(inv)
        if inv := self._check_silence(state):
            results.append(inv)
        if inv := self._check_time_over(utterance, state):
            results.append(inv)

        for inv in results:
            inv.time = utterance.time

        return results

    # --- 키워드 기반 트리거 ---

    def _check_consensus(self, utterance: Utterance) -> Intervention | None:
        """합의 신호 감지. 오탐 방지: 키워드 제거 후 남은 텍스트가 10자 초과면 무시.
        예) "좋습니다" → 합의 O / "좋습니다. 민준 씨 쪽 대시보드는..." → 합의 X (발화의 도입부일 뿐)
        """
        for kw in CONSENSUS_KEYWORDS:
            if kw in utterance.text:
                remainder = utterance.text.replace(kw, "", 1).strip().strip(".,!?~")
                if len(remainder) > 10:
                    continue
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
        if prev.id in self._emitted_no_decision:
            return None
        prev_issue = state.issues.get(prev.id)
        if prev_issue and prev_issue.decision is None:
            self._emitted_no_decision.add(prev.id)
            return Intervention(
                trigger_type="no_decision",
                message=f"이전 안건 '{prev.title}'에 대한 결정이 내려지지 않았습니다",
                level=AlertLevel.WARNING,
                topic_id=prev.id,
            )
        return None

    # --- 패턴 기반 트리거 ---

    def _check_loop(self, state: MeetingState) -> Intervention | None:
        """논의 순환 감지: 현재 토픽의 최근 10개 발화에서 같은 단어가 3회+ 반복되면 경고.

        동작:
        1. 현재 토픽의 최근 10개 발화에서 모든 단어 추출 (2자 미만, 불용어 제외)
        2. Counter로 빈도 계산 → 상위 5개 중 3회+ 반복 단어 탐지
        3. 반복 단어가 있으면 "논의가 반복되고 있습니다" 경고

        불용어 필터(_STOPWORDS)가 없으면 "합니다", "정도" 같은 일반 단어로 오탐 발생.
        """
        if not state.topics:
            return None
        current = state.topics[-1]
        recent = current.utterances[-10:]
        if len(recent) < settings.loop_detection_count:
            return None

        words: list[str] = []
        for u in recent:
            words.extend(w for w in u.text.split() if len(w) >= 2 and w not in _STOPWORDS)
        counter = Counter(words)
        repeated = [
            w for w, c in counter.most_common(5)
            if c >= settings.loop_detection_count
        ]

        if repeated:
            return Intervention(
                trigger_type="loop",
                message=f"논의가 반복되고 있습니다 (반복 키워드: {', '.join(repeated[:3])})",
                level=AlertLevel.WARNING,
                topic_id=current.id,
            )
        return None

    def _check_silence(self, state: MeetingState) -> Intervention | None:
        """긴 침묵 감지."""
        if state.current_silence_ms >= settings.long_silence_sec * 1000:
            return Intervention(
                trigger_type="silence",
                message="긴 침묵이 감지되었습니다. 다음 안건으로 넘어갈까요?",
                level=AlertLevel.INFO,
            )
        return None

    def _check_time_over(
        self, utterance: Utterance, state: MeetingState
    ) -> Intervention | None:
        """안건별 시간 초과 감지."""
        if not state.topics:
            return None
        current = state.topics[-1]
        elapsed = _time_diff_minutes(current.start_time, utterance.time)
        if elapsed > settings.time_over_alert_min:
            over = elapsed - settings.time_over_alert_min
            return Intervention(
                trigger_type="time_over",
                message=f"현재 안건이 예정 시간을 {over:.0f}분 초과했습니다",
                level=AlertLevel.WARNING,
                topic_id=current.id,
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


def _time_diff_minutes(start: str, end: str) -> float:
    """'HH:MM:SS' 시간 차이를 분 단위로 반환."""
    def _to_sec(t: str) -> int:
        parts = t.split(":")
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    diff = _to_sec(end) - _to_sec(start)
    return max(diff, 0) / 60
