"""토픽 전환 감지 & 안건 세그멘테이션.

3단계 감지:
  1차 필터: 전환 키워드 또는 긴 침묵+전환 의도 → 후보 선별
  2차 필터: 키워드 2개+ 동시 매칭 → LLM 없이 전환 확정
  3차 판단: 1차 통과 & 2차 미통과 → LLM이 최종 판단
"""

from __future__ import annotations

from collections import deque
from difflib import SequenceMatcher
import logging
import re

from config import settings
from models import Utterance, Topic
from analysis.llm import ask_json

logger = logging.getLogger(__name__)


class TopicDetector:
    """토픽 전환 감지 + 안건 세그멘테이션."""

    def __init__(self) -> None:
        self._topic_counter = 0
        self._last_silence_ms: float = 0.0
        self.segments: list[Topic] = []
        self._recent: deque[Utterance] = deque(maxlen=10)
        # 마지막 LLM 토픽 판단 후 누적된 발화 수. 임계치 도달 시 키워드 없어도 LLM 강제 호출.
        self._utterances_since_last_check: int = 0

    async def check(self, utterance: Utterance) -> Topic | None:
        """새 발화가 토픽 전환인지 판단. 전환이면 새 Topic 반환.

        3단계 판단 프로세스:
          1차 필터: 전환 키워드 또는 긴 침묵+전환 의도 → 후보 선별 (빠름, 비용 0)
          2차 필터: 명시적 전환 패턴 → LLM 없이 전환 확정 (빠름, 비용 0)
          3차 판단: 1차 통과 & 2차 미통과 → LLM이 최종 판단 (느림, LLM 호출 비용)
        + 강제 검사: 설정된 경우에만 N발화마다 LLM 판단 1회
        """
        self._recent.append(utterance)

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
        direct_title = self._direct_transition_title(utterance)
        if direct_title:
            return self._accept_topic(direct_title, utterance)

        first_pass = self._first_filter(utterance)
        force_check = (
            settings.topic_force_check_utterances > 0
            and self._utterances_since_last_check
            >= settings.topic_force_check_utterances
        )

        # 키워드/침묵 없고 강제 검사 임계치도 안 넘었으면 LLM 호출 없이 종료
        if not first_pass and not force_check:
            return None

        # 2차 필터 통과 시 LLM 호출 없이 즉시 토픽 전환 확정.
        title = self._second_filter_title(utterance) if first_pass else None
        if title is None:
            # 1차/강제 검사 진입 → LLM에게 최종 판단 위임
            title = await self._llm_judge_title(utterance)
            self._utterances_since_last_check = 0  # LLM 호출했으니 카운터 리셋

        if title:
            return self._accept_topic(title, utterance)
        return None

    # 2차 필터 키워드 — 2개+ 동시 매칭 시 전환 확정.
    # "마무리/정리"는 현재 안건의 결론일 가능성이 높아 자동 전환에서 제외.
    _SECOND_FILTER_KEYWORDS = ["넘어가서", "다음 안건", "다음 한건", "다음 한권", "다음으로", "다른 주제"]

    def _second_filter_title(self, utterance: Utterance) -> str | None:
        """2차 필터: 키워드 2개+ 동시 매칭 → LLM 없이 전환 확정."""
        matched = [kw for kw in self._SECOND_FILTER_KEYWORDS if kw in utterance.text]
        if len(matched) >= 2:
            return self._infer_title_from_text(utterance.text)
        return None

    def _first_filter(self, utterance: Utterance) -> bool:
        """1차 필터: 전환 키워드 또는 긴 침묵+전환 의도 → 후보 선별.

        긴 침묵 단독으로 LLM 판단을 태우면 실제 녹음에서 정상 발화 간격까지
        안건 후보가 되어 과분리되므로, 침묵은 전환 의도 표현이 있을 때만 보조 신호로 쓴다.
        """
        for keyword in settings.topic_keywords:
            if keyword in utterance.text:
                return True
        if (
            self._last_silence_ms >= settings.topic_silence_threshold_sec * 1000
            and self._has_transition_intent(utterance.text)
        ):
            return True
        return False

    async def _llm_judge_title(self, utterance: Utterance) -> str | None:
        """3차 판단: LLM이 토픽 전환 여부 + 토픽명 최종 결정."""
        context = "\n".join(
            f"[{u.speaker}] {u.text}" for u in self._recent
        )
        prompt = (
            "다음은 회의 중 최근 발화입니다:\n\n"
            f"{context}\n\n"
            "마지막 발화 기준으로 새로운 토픽/안건이 시작되었는지 판단하세요.\n"
            "매우 보수적으로 판단하세요. 명시적으로 '다음 안건', '다른 주제로', '넘어가서'처럼 "
            "새 주제를 시작한다는 표현이 있는 경우에만 changed=true입니다.\n"
            "침묵만 있거나 발화 간격이 길다는 이유만으로는 새 안건이 아닙니다.\n"
            "중요: 지금 논의의 결론 정리, 마무리, 액션 아이템 확인, 같은 안건의 세부 질문은 새 안건이 아닙니다.\n"
            'JSON: {"changed": true/false, "title": "토픽명 (10자 이내)"}'
        )
        data = await ask_json(prompt)

        if data.get("changed"):
            return data.get("title", "")
        return None

    def _direct_transition_title(self, utterance: Utterance) -> str | None:
        """명시적 전환 표현을 규칙으로 처리해 STT 오인식과 LLM 흔들림을 줄인다."""
        text = utterance.text
        normalized = re.sub(r"\s+", "", text)

        # "다음 안건"이 "다음 한건/한권/안권"으로 오인식되는 케이스 보정.
        next_agenda = re.search(r"다음\s*(안건|한건|한권|안권)", text) or re.search(r"다음(안건|한건|한권|안권)", normalized)
        if next_agenda and ("넘어가" in text or "넘어가" in normalized or self._has_topic_noun(text)):
            return self._infer_title_from_text(text)

        if ("넘어가" in text or "넘어가" in normalized) and self._has_transition_intent(text):
            return self._infer_title_from_text(text)

        if "자 이제" in text and ("마지막" in text or self._has_topic_noun(text)):
            return self._infer_title_from_text(text)

        if "그건 그렇고" in text and self._has_topic_noun(text):
            return self._infer_title_from_text(text)

        return None

    def _has_transition_intent(self, text: str) -> bool:
        return any(
            token in text
            for token in (
                "다음 안건", "다음 한건", "다음 한권", "다른 주제",
                "새 주제", "자 이제", "마지막", "넘어가",
            )
        )

    def _has_topic_noun(self, text: str) -> bool:
        topic_words = (
            "회식", "예산", "사무실", "자리", "배치", "워크숍", "일정",
            "결제", "재무", "제품", "프로덕트", "디자인", "개발", "마케팅",
        )
        return any(word in text for word in topic_words)

    def _infer_title_from_text(self, text: str) -> str:
        if "워크숍" in text:
            return "워크숍 일정" if "일정" in text or "마지막" in text else "워크숍"
        if "사무실" in text and ("자리" in text or "배치" in text):
            return "사무실 자리 배치"
        if "회식" in text and "예산" in text:
            return "회식 예산"
        if "마케팅" in text and "예산" in text:
            return "마케팅 예산"
        if "자리" in text and "배치" in text:
            return "자리 배치"

        cleaned = re.sub(
            r"(네|자 이제|그건 그렇고|다음\s*(안건|한건|한권|안권)|다음으로|넘어가서|넘어가|마지막|얘기|이야기|해보죠|해보겠습니다|논의|관련)",
            " ",
            text,
        )
        cleaned = re.sub(r"[^0-9A-Za-z가-힣\s]", " ", cleaned)
        words = [w for w in cleaned.split() if len(w) > 1 and w not in {"으로", "부터", "대해"}]
        if not words:
            return "다음 안건"
        return " ".join(words[:3])[:20]

    def _accept_topic(self, title: str, utterance: Utterance) -> Topic | None:
        title = (title or "").strip()[:20] or "다음 안건"
        if not self._can_open_topic(title, utterance):
            return None

        self._topic_counter += 1
        new_topic = Topic(id=self._topic_counter, title=title, start_time=utterance.time)
        if self.segments:
            self.segments[-1].end_time = new_topic.start_time
        self.segments.append(new_topic)
        return new_topic

    def _can_open_topic(self, title: str, utterance: Utterance) -> bool:
        if not self.segments:
            return True

        current = self.segments[-1]
        if self._titles_similar(current.title, title):
            logger.info("유사 안건 전환 차단: '%s' -> '%s'", current.title, title)
            return False

        age_sec = self._topic_age_sec(current, utterance)
        utterance_count = len(current.utterances)
        if (
            age_sec is not None
            and age_sec < settings.topic_min_duration_sec
            and utterance_count < settings.topic_min_utterances
        ):
            logger.info(
                "짧은 안건 전환 차단: '%s' -> '%s' (%.1fs, %d발화)",
                current.title, title, age_sec, utterance_count,
            )
            return False
        return True

    def _topic_age_sec(self, topic: Topic, utterance: Utterance) -> float | None:
        start = _parse_time(topic.start_time)
        cur = _parse_time(utterance.time)
        if start is None or cur is None:
            return None
        return max(0.0, cur - start)

    def _titles_similar(self, left: str, right: str) -> bool:
        a = _normalize_title(left)
        b = _normalize_title(right)
        if not a or not b:
            return False
        return SequenceMatcher(None, a, b).ratio() >= 0.68

    def get_current(self) -> Topic | None:
        return self.segments[-1] if self.segments else None

    def get_summary(self) -> list[dict]:
        return [
            {"id": t.id, "title": t.title, "start": t.start_time, "end": t.end_time or "진행중"}
            for t in self.segments
        ]


def _parse_time(value: str | None) -> float | None:
    if not value:
        return None
    try:
        h, m, s = value.split(":")
        return int(h) * 3600 + int(m) * 60 + int(s)
    except Exception:
        return None


def _normalize_title(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z가-힣]", "", (value or "").lower())
    for token in ("안건", "회의", "주제", "논의", "얘기", "이야기", "관련"):
        text = text.replace(token, "")
    return text
