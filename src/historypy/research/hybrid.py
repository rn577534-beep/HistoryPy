"""Hybrid and entity-aware retrieval with transparent rank fusion.

Retrieval scores are relevance signals only. Entity aliases are exact phrase
matches over researcher-supplied names; they are not identity adjudications.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.research.bm25 import BM25SearchIndex
from historypy.research.search_index import DatasetSearchIndex
from historypy.research.semantic import EmbeddingBatch, SemanticSearchIndex


@dataclass(frozen=True, slots=True)
class HybridSearchHit:
    """A fused result with per-retriever ranks and exact entity matches."""

    kind: str
    record_id: str
    label: str
    score: float
    bm25_rank: int | None
    trigram_rank: int | None
    semantic_rank: int | None
    entity_rank: int | None
    matched_entity_aliases: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DecomposedQuery:
    """Original question and conservative, searchable sub-questions."""

    original: str
    parts: tuple[str, ...]


def _normalize_phrase(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", plain, flags=re.UNICODE))


def decompose_research_question(question: str) -> DecomposedQuery:
    """Split only explicit multi-hop/comparison constructions; never guess facts."""
    if not isinstance(question, str):
        raise TypeError("question must be a string")
    original = question.strip()
    if not original:
        return DecomposedQuery(question, ())
    normalized = re.sub(r"\s+", " ", original)
    separators = (
        r"\s+compared\s+with\s+",
        r"\s+in\s+comparison\s+with\s+",
        r"\s+versus\s+",
        r"\s+vs\.?\s+",
        r"\s+and\s+(?=(?:what|which|who|when|where|why|how|whose|did|does|was|were|is|are)\b)",
        r"\s*;\s*",
    )
    parts = [normalized]
    for pattern in separators:
        next_parts = []
        for part in parts:
            next_parts.extend(re.split(pattern, part, flags=re.IGNORECASE))
        parts = next_parts
    cleaned = tuple(dict.fromkeys(part.strip(" ?.!") for part in parts if part.strip(" ?.!")))
    return DecomposedQuery(original, cleaned or (original,))


class HybridSearchIndex:
    """Reciprocal-rank fusion over trigram, BM25, and optional semantic search.

    The component indexes must represent the same dataset snapshot. Semantic
    search requires the same caller-supplied embedding space used at build time.
    """

    def __init__(
        self,
        trigram: DatasetSearchIndex,
        bm25: BM25SearchIndex,
        semantic: SemanticSearchIndex | None = None,
        *,
        entity_index: EntityAwareSearchIndex | None = None,
        rrf_k: int = 60,
    ) -> None:
        if rrf_k < 1:
            raise ValueError("rrf_k must be positive")
        trigram_ids = tuple((row[0], row[1]) for row in trigram.records)
        bm25_ids = tuple((row[0], row[1]) for row in bm25.records)
        if trigram_ids != bm25_ids:
            raise ValueError("retrieval indexes must contain the same ordered records")
        if semantic is not None:
            semantic_ids = tuple((row[0], row[1]) for row in semantic.records)
            if semantic_ids != trigram_ids:
                raise ValueError("semantic index must contain the same ordered records")
        self.trigram = trigram
        self.bm25 = bm25
        self.semantic = semantic
        self.entity_index = entity_index
        self.rrf_k = rrf_k

    def search(
        self,
        query: str,
        *,
        embedder: EmbeddingBatch | None = None,
        kinds: Iterable[str] | None = None,
        limit: int = 20,
        decompose: bool = False,
    ) -> tuple[HybridSearchHit, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query cannot be empty")
        if self.semantic is not None and embedder is None:
            raise ValueError("embedder is required when a semantic index is configured")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        if limit == 0:
            return ()
        parts = decompose_research_question(query).parts if decompose else (query.strip(),)
        allowed = tuple(kinds) if kinds is not None else None
        scores: dict[tuple[str, str], float] = defaultdict(float)
        labels: dict[tuple[str, str], str] = {}
        ranks: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
        matched_aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
        for part in parts:
            result_sets = [
                ("trigram", self.trigram.search(part, kinds=allowed, limit=None)),
                ("bm25", self.bm25.search(part, kinds=allowed, limit=None)),
            ]
            if self.semantic is not None and embedder is not None:
                result_sets.append((
                    "semantic",
                    self.semantic.search(
                        part, embedder=embedder, kinds=allowed,
                        limit=len(self.semantic.records),
                    ),
                ))
            for method, hits in result_sets:
                for rank, hit in enumerate(hits, start=1):
                    key = (hit.kind, hit.record_id)
                    labels[key] = hit.label
                    ranks[key][method] = min(rank, ranks[key].get(method, rank))
                    scores[key] += 1.0 / (self.rrf_k + rank)
            if self.entity_index is not None:
                entity_hits = self.entity_index.resolve(part, kinds=allowed)
                for rank, entity in enumerate(entity_hits, start=1):
                    key = (entity.kind, entity.record_id)
                    labels.setdefault(key, entity.canonical_name)
                    ranks[key]["entity"] = min(
                        rank, ranks[key].get("entity", rank)
                    )
                    matched_aliases[key].add(entity.matched_alias)
                    scores[key] += 1.0 / (self.rrf_k + rank)
        ordered = sorted(scores, key=lambda key: (-scores[key], key[0], key[1]))
        return tuple(
            HybridSearchHit(
                kind=key[0], record_id=key[1], label=labels[key],
                score=scores[key],
                bm25_rank=ranks[key].get("bm25"),
                trigram_rank=ranks[key].get("trigram"),
                semantic_rank=ranks[key].get("semantic"),
                entity_rank=ranks[key].get("entity"),
                matched_entity_aliases=tuple(sorted(matched_aliases[key])),
            )
            for key in ordered[:limit]
        )


@dataclass(frozen=True, slots=True)
class EntityAliasMatch:
    """Exact normalized alias match linked to a typed entity record."""

    kind: str
    record_id: str
    canonical_name: str
    matched_alias: str


class EntityAwareSearchIndex:
    """Exact alias resolver for people, places, civilizations, organizations."""

    _KINDS = ("person", "place", "civilization", "organization")

    def __init__(self, aliases: dict[str, tuple[EntityAliasMatch, ...]]) -> None:
        self._aliases = aliases

    @classmethod
    def build(cls, dataset: HistoricalDataset) -> EntityAwareSearchIndex:
        rows: dict[str, list[EntityAliasMatch]] = defaultdict(list)
        groups = (
            ("person", dataset.people),
            ("place", dataset.places),
            ("civilization", dataset.civilizations),
            ("organization", dataset.organizations),
        )
        for kind, records in groups:
            for record in records:
                for alias in dict.fromkeys((record.name, *record.aliases)):
                    normalized = _normalize_phrase(alias)
                    if normalized:
                        rows[normalized].append(EntityAliasMatch(
                            kind, record.id, record.name, alias
                        ))
        return cls({
            key: tuple(sorted(values, key=lambda item: (item.kind, item.record_id, item.matched_alias)))
            for key, values in rows.items()
        })

    def resolve(
        self, query: str, *, kinds: Iterable[str] | None = None
    ) -> tuple[EntityAliasMatch, ...]:
        """Find exact full-name/alias phrases present in the query.

        Ambiguous aliases intentionally return every matching entity.
        """
        normalized = _normalize_phrase(query)
        if not normalized:
            return ()
        allowed = set(kinds) if kinds is not None else None
        matches = []
        for alias, entities in self._aliases.items():
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
                matches.extend(
                    entity for entity in entities
                    if allowed is None or entity.kind in allowed
                )
        return tuple(sorted(
            matches, key=lambda item: (item.kind, item.record_id, item.matched_alias)
        ))
