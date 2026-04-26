"""API 공용 유틸."""

from __future__ import annotations

import dataclasses
from enum import Enum


def _serialize(obj):
    """dataclass/enum → dict 재귀 직렬화."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _serialize(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, list):
        return [_serialize(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    return obj


def _get_pipeline():
    """공유 Pipeline 인스턴스 lazy 조회 (순환 import 방지)."""
    from main import pipeline
    return pipeline
