"""자료 자동 수집 — 엔티티 추출 + 사내/웹 검색.

발화에서 엔티티 추출 → 사내 문서 검색 (ChromaDB) + 웹 검색 (Tavily) → 관련도 정렬
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import chromadb

from analysis.llm import ask_json
from config import settings
from models import Reference, Utterance

logger = logging.getLogger(__name__)


@dataclass
class Entity:
    """추출된 엔티티."""

    text: str
    entity_type: str  # "document" | "data" | "person" | "org" | "metric"
    search_query: str


class EntityExtractor:
    """발화에서 검색 가능한 엔티티 추출."""

    _PROMPT = (
        "다음 회의 발화에서 참조하는 문서, 데이터, 수치, 인물, 조직이 있는지 판단하라.\n"
        "있다면 검색에 사용할 쿼리를 생성하라. 없다면 빈 배열을 반환하라.\n\n"
        '발화: "{text}"\n\n'
        "예시:\n"
        '- 발화: "PG사 응답이 3초 넘어가는 케이스가 하루에 열두 건 발생" → {{"entities": [{{"text": "PG사", "type": "org", "query": "PG사 결제 응답 지연 원인"}}]}}\n'
        '- 발화: "Figma에 업데이트해둘 테니까" → {{"entities": [{{"text": "Figma", "type": "document", "query": "Figma 디자인 시안 공유"}}]}}\n'
        '- 발화: "네 알겠습니다" → {{"entities": []}}\n\n'
        "JSON 형식으로 응답:\n"
        '{{"entities": [{{"text": "원문에서 해당 부분", "type": "document|data|person|org|metric", "query": "웹 검색에 사용할 구체적 쿼리"}}]}}'
    )

    async def extract(self, utterance: Utterance) -> list[Entity]:
        if not utterance.text.strip():
            return []

        prompt = self._PROMPT.format(text=utterance.text)
        try:
            result = await ask_json(prompt)
            entities = []
            for e in result.get("entities", []):
                if not isinstance(e, dict):
                    continue
                text = e.get("text", "")
                etype = e.get("type", "")
                query = e.get("query", "").strip()
                if not text or not etype:
                    continue
                # 빈 query면 entity text를 폴백으로 사용
                if not query:
                    query = text
                entities.append(Entity(text=text, entity_type=etype, search_query=query))
            return entities
        except Exception:
            logger.warning("엔티티 추출 실패: %s", utterance.text[:50], exc_info=True)
            return []


class InternalSearch:
    """ChromaDB 기반 사내 문서 벡터 검색 (임베디드 모드)."""

    def __init__(self) -> None:
        self._client = chromadb.PersistentClient(path=settings.chromadb_path)
        self._collection = self._client.get_or_create_collection("documents")

    async def search(self, query: str, top_k: int = 3) -> list[Reference]:
        results = await asyncio.to_thread(
            self._collection.query, query_texts=[query], n_results=top_k
        )

        if not results or not results["documents"] or not results["documents"][0]:
            return []

        docs = results["documents"][0]
        metadatas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        return [
            Reference(
                query=query,
                source="internal",
                title=meta.get("title", "사내 문서"),
                snippet=doc[:200],
                url=meta.get("url"),
                relevance_score=max(0.0, 1.0 - dist),
            )
            for doc, meta, dist in zip(docs, metadatas, distances)
        ]


class WebSearch:
    """Tavily API 기반 웹 검색 + DuckDuckGo 폴백."""

    async def search(self, query: str, top_k: int = 3) -> list[Reference]:
        if not query or not query.strip():
            return []
        if not settings.tavily_api_key:
            return await self._fallback(query, top_k)

        try:
            from tavily import AsyncTavilyClient

            client = AsyncTavilyClient(api_key=settings.tavily_api_key)
            response = await client.search(query=query, max_results=top_k)
            return [
                Reference(
                    query=query,
                    source="web",
                    title=r.get("title", ""),
                    snippet=r.get("content", "")[:200],
                    url=r.get("url"),
                    relevance_score=r.get("score", 0.0),
                )
                for r in response.get("results", [])
            ]
        except Exception:
            logger.warning("Tavily 검색 실패, DuckDuckGo 폴백", exc_info=True)
            return await self._fallback(query, top_k)

    async def _fallback(self, query: str, top_k: int) -> list[Reference]:
        try:
            from duckduckgo_search import DDGS

            results = await asyncio.to_thread(
                lambda: list(DDGS().text(query, max_results=top_k))
            )
            return [
                Reference(
                    query=query,
                    source="web",
                    title=r.get("title", ""),
                    snippet=r.get("body", "")[:200],
                    url=r.get("href"),
                    relevance_score=0.0,
                )
                for r in results
            ]
        except Exception:
            logger.warning("DuckDuckGo 폴백도 실패", exc_info=True)
            return []


class ReferenceCollector:
    """사내 DB (벡터 검색) + 웹 검색 통합.

    두 소스를 병렬로 검색한 뒤 relevance_score 기준 내림차순 정렬하여 반환.
    사내 문서 relevance_score = 1.0 - cosine_distance (0~1)
    웹 검색 relevance_score = Tavily score 또는 0.0 (DuckDuckGo 폴백)
    """

    def __init__(self) -> None:
        self.internal = InternalSearch()
        self.web = WebSearch()

    async def search(self, entity: Entity, top_k: int = 3) -> list[Reference]:
        """엔티티의 search_query로 사내+웹 동시 검색 → 관련도 순 정렬."""
        internal_results, web_results = await asyncio.gather(
            self.internal.search(entity.search_query, top_k),
            self.web.search(entity.search_query, top_k),
        )
        combined = internal_results + web_results
        combined.sort(key=lambda r: r.relevance_score, reverse=True)
        return combined
