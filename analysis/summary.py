"""회의 종료 시 전체 회의록 요약 생성."""

from __future__ import annotations

import dataclasses
import logging

from analysis.llm import ask_json

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """\
당신은 회의록 정리 전문가입니다. 아래 회의 데이터를 바탕으로 구조화된 회의록을 작성하세요.

## 회의 데이터

### 발화 기록
{utterances}

### 안건별 쟁점 구조
{issues}

## 출력 형식 (JSON)
{{
  "one_line": "회의 전체를 한 문장으로 요약 (60자 이내)",
  "title": "회의 내용을 대표하는 제목 (15자 이내)",
  "participants": ["화자1", "화자2"],
  "topics": [
    {{
      "title": "안건명",
      "summary": "논의 내용 2~3문장 요약",
      "decision": "결정된 사항 (없으면 null)",
      "open_questions": ["미결 이슈"]
    }}
  ],
  "decisions": ["주요 결정 사항 목록"],
  "action_items": [
    {{"speaker": "Speaker N", "who": "담당자 실명 또는 미정", "task": "할 일", "due": "기한 (없으면 null)"}}
  ]
}}

규칙:
- 발화 기록에 근거한 내용만 작성. 추측하지 마세요.
- action_items의 who는 발화에서 명시적으로 담당자가 언급된 경우에만 기재. 불명확하면 "미정"으로.
- action_items의 speaker는 해당 담당자의 화자 라벨(예: "Speaker 2"). 불명확하면 null.
- action_items의 due는 발화에 기한이 언급된 경우에만 기재 (예: "이번 주 금요일"). 없으면 null.
- 결정된 사항이 없는 안건은 topics[].decision을 null로.
- JSON만 출력하세요.
"""


async def generate_summary(state) -> dict | None:
    """MeetingState → LLM 기반 회의록 요약 생성.

    state에 발화가 없으면 None 반환.
    """
    if not state.utterances:
        return None

    # 발화 기록 포맷
    utt_lines = []
    for u in state.utterances:
        utt_lines.append(f"[{u.time}] {u.speaker}: {u.text}")
    utterances_text = "\n".join(utt_lines)

    # 쟁점 구조 포맷
    issues_parts = []
    for topic in state.topics:
        issue = state.issues.get(topic.id)
        if issue:
            issue_dict = dataclasses.asdict(issue) if dataclasses.is_dataclass(issue) else issue
            issues_parts.append(f"안건 '{topic.title}': {issue_dict}")
        else:
            issues_parts.append(f"안건 '{topic.title}': 쟁점 없음")
    issues_text = "\n".join(issues_parts) if issues_parts else "안건 없음"

    prompt = _SUMMARY_PROMPT.format(
        utterances=utterances_text,
        issues=issues_text,
    )

    try:
        return await ask_json(prompt)
    except Exception:
        logger.warning("회의록 요약 생성 실패", exc_info=True)
        return None
