"""자료 자동 수집 — 엔티티 추출 + 사내/웹 검색.

발화에서 엔티티 추출 → 사내 문서 검색 (RAG) + 웹 검색 → 관련도 정렬
"""

from __future__ import annotations

from dataclasses import dataclass

from models import Utterance, Reference


@dataclass
class Entity:
    """추출된 엔티티."""

    text: str
    entity_type: str  # "document" | "data" | "person" | "org" | "metric"
    search_query: str


class EntityExtractor:
    """발화에서 검색 가능한 엔티티 추출."""

    async def extract(self, utterance: Utterance) -> list[Entity]:
        # TODO: LLM으로 엔티티 추출
        return []


class ReferenceCollector:
    """사내 DB (벡터 검색) + 웹 검색 통합."""

    async def search(self, entity: Entity, top_k: int = 3) -> list[Reference]:
        """엔티티 기반 검색 후 관련도 순 정렬."""
        # TODO: 벡터 DB 검색 + 웹 검색 병렬 실행
        return []
