"""토픽 전환 감지 & 안건 세그멘테이션.

3단계 감지:
  1차 필터: 키워드 1개+ 매칭 또는 긴 침묵 → 후보 선별
  2차 필터: 키워드 2개+ 동시 매칭 → LLM 없이 전환 확정
  3차 판단: 1차 통과 & 2차 미통과 → LLM이 최종 판단
"""

from __future__ import annotations

from config import settings
from models import Utterance, Topic
from analysis.llm import ask_json


class TopicDetector:
    """토픽 전환 감지 + 안건 세그멘테이션."""

    def __init__(self) -> None:
        self._topic_counter = 0
        self._last_silence_ms: float = 0.0
        self.segments: list[Topic] = []
        self._recent: list[Utterance] = []
        # 마지막 LLM 토픽 판단 후 누적된 발화 수. 임계치 도달 시 키워드 없어도 LLM 강제 호출.
        self._utterances_since_last_check: int = 0

    async def check(self, utterance: Utterance) -> Topic | None:
        """새 발화가 토픽 전환인지 판단. 전환이면 새 Topic 반환.

        3단계 판단 프로세스:
          1차 필터: 키워드 1개+ 또는 긴 침묵(3초+) → 후보 선별 (빠름, 비용 0)
          2차 필터: 키워드 2개+ 동시 매칭 → LLM 없이 전환 확정 (빠름, 비용 0)
          3차 판단: 1차 통과 & 2차 미통과 → LLM이 최종 판단 (느림, LLM 호출 비용)
        + 강제 검사: 위 셋 모두 안 걸렸어도 N발화마다 LLM 판단 1회 (자연 대화 흐름 대응)
        """
        self._recent.append(utterance)
        self._recent = self._recent[-10:]  # LLM 컨텍스트용 최근 발화 유지

        # 첫 발화 시 초기 토픽 자동 생성 — 회의 시작 시점의 기본 토픽
        if not self.segments:
            self._topic_counter += 1
            initial = Topic(
                id=self._topic_counter,
                title="회의 시작",
                start_time=utterance.time,
            )
            self.segments.append(initial)
            self._utterances_since_last_check = 0
            return initial

        self._utterances_since_last_check += 1
        first_pass = self._first_filter(utterance)
        force_check = (
            settings.topic_force_check_utterances > 0
            and self._utterances_since_last_check
            >= settings.topic_force_check_utterances
        )

        # 키워드/침묵 없고 강제 검사 임계치도 안 넘었으면 LLM 호출 없이 종료
        if not first_pass and not force_check:
            return None

        # 2차 필터 통과 시 LLM 호출 없이 즉시 토픽 전환 확정 (강제 검사 모드에선 키워드 없으므로 항상 None)
        new_topic = self._second_filter(utterance) if first_pass else None
        if new_topic is None:
            # 1차/강제 검사 진입 → LLM에게 최종 판단 위임
            new_topic = await self._llm_judge(utterance)
            self._utterances_since_last_check = 0  # LLM 호출했으니 카운터 리셋

        if new_topic:
            # 이전 토픽의 종료 시각 = 새 토픽의 시작 시각
            if self.segments:
                self.segments[-1].end_time = new_topic.start_time
            self.segments.append(new_topic)
        return new_topic

    # 2차 필터 키워드 — 2개+ 동시 매칭 시 전환 확정.
    # "마무리/정리"는 현재 안건의 결론일 가능성이 높아 자동 전환에서 제외.
    _SECOND_FILTER_KEYWORDS = ["넘어가서", "다음 안건", "다음으로", "다른 주제"]

    def _second_filter(self, utterance: Utterance) -> Topic | None:
        """2차 필터: 키워드 2개+ 동시 매칭 → LLM 없이 전환 확정."""
        matched = [kw for kw in self._SECOND_FILTER_KEYWORDS if kw in utterance.text]
        if len(matched) >= 2:
            self._topic_counter += 1
            title = "다음 안건"
            return Topic(id=self._topic_counter, title=title, start_time=utterance.time)
        return None

    def _first_filter(self, utterance: Utterance) -> bool:
        """1차 필터: 키워드 1개+ 또는 긴 침묵 → 후보 선별."""
        for keyword in settings.topic_keywords:
            if keyword in utterance.text:
                return True
        if self._last_silence_ms >= settings.topic_silence_threshold_sec * 1000:
            return True
        return False

    async def _llm_judge(self, utterance: Utterance) -> Topic | None:
        """3차 판단: LLM이 토픽 전환 여부 + 토픽명 최종 결정."""
        context = "\n".join(
            f"[{u.speaker}] {u.text}" for u in self._recent
        )
        prompt = (
            "다음은 회의 중 최근 발화입니다:\n\n"
            f"{context}\n\n"
            "마지막 발화 기준으로 새로운 토픽/안건이 시작되었는지 판단하세요.\n"
            "매우 보수적으로 판단하세요. 명시적으로 '다음 안건', '다른 주제로', '넘어가서'처럼 "
            "새 주제를 시작한다는 표현이 있거나, 긴 침묵 뒤 완전히 다른 업무/결정 주제로 이동한 경우에만 changed=true입니다.\n"
            "중요: 지금 논의의 결론 정리, 마무리, 액션 아이템 확인, 같은 안건의 세부 질문은 새 안건이 아닙니다.\n"
            'JSON: {"changed": true/false, "title": "토픽명 (10자 이내)"}'
        )
        data = await ask_json(prompt)

        if data.get("changed"):
            self._topic_counter += 1
            return Topic(
                id=self._topic_counter,
                title=data.get("title", ""),
                start_time=utterance.time,
            )
        return None

    def get_current(self) -> Topic | None:
        return self.segments[-1] if self.segments else None

    def get_summary(self) -> list[dict]:
        return [
            {"id": t.id, "title": t.title, "start": t.start_time, "end": t.end_time or "진행중"}
            for t in self.segments
        ]
