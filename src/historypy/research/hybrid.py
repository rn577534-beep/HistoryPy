"""Hybrid and entity-aware retrieval with transparent rank fusion.

Retrieval scores are relevance signals only. Entity aliases are exact phrase
matches over researcher-supplied names; they are not identity adjudications.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, replace
from difflib import SequenceMatcher

from historypy.core.dataset import HistoricalDataset
from historypy.research.alias_registry import AliasRegistry
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
    matched_entity_evidence: tuple[EntityAliasMatch, ...] = ()


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
        r"\s+en\s+comparaison\s+avec\s+",
        r"\s+compar(?:é|ée|és|ées)\s+à\s+",
        r"\s+par\s+rapport\s+à\s+",
        r"\s+contre\s+",
        r"\s+and\s+(?=(?:what|which|who|when|where|why|how|whose|did|does|was|were|is|are)\b)",
        r"\s+et\s+(?=(?:que|quel|quelle|quels|quelles|qui|quand|où|comment|pourquoi|combien|est|était|étaient|a|ont|avait)\b)",
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
        entity_fuzzy_threshold: float | None = None,
    ) -> tuple[HybridSearchHit, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query cannot be empty")
        if self.semantic is not None and embedder is None:
            raise ValueError("embedder is required when a semantic index is configured")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        if entity_fuzzy_threshold is not None and not 0.0 <= entity_fuzzy_threshold <= 1.0:
            raise ValueError("entity_fuzzy_threshold must be between 0 and 1")
        if limit == 0:
            return ()
        if decompose:
            decomposition = decompose_research_question(query)
            # Keep the full question as an anchor: sub-questions add evidence
            # without discarding context carried by the original wording.
            parts = tuple(dict.fromkeys((query.strip(), *decomposition.parts)))
        else:
            parts = (query.strip(),)
        allowed = tuple(kinds) if kinds is not None else None
        scores: dict[tuple[str, str], float] = defaultdict(float)
        labels: dict[tuple[str, str], str] = {}
        ranks: dict[tuple[str, str], dict[str, int]] = defaultdict(dict)
        matched_aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
        matched_entity_evidence: dict[tuple[str, str], dict[tuple[str, str], EntityAliasMatch]] = defaultdict(dict)
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
                entity_ranks: dict[tuple[str, str], int] = {}
                for entity in entity_hits:
                    key = (entity.kind, entity.record_id)
                    labels.setdefault(key, entity.canonical_name)
                    if key not in entity_ranks:
                        entity_ranks[key] = len(entity_ranks) + 1
                        rank = entity_ranks[key]
                        ranks[key]["entity"] = min(
                            rank, ranks[key].get("entity", rank)
                        )
                        scores[key] += 1.0 / (self.rrf_k + rank)
                    matched_aliases[key].add(entity.matched_alias)
                    evidence_key = (entity.match_type, entity.alias_id or entity.matched_alias)
                    matched_entity_evidence[key][evidence_key] = entity
                if entity_fuzzy_threshold is not None:
                    exact_keys = {
                        (entity.kind, entity.record_id) for entity in entity_hits
                    }
                    suggestions = tuple(
                        entity for entity in self.entity_index.suggest(
                            part, kinds=allowed, threshold=entity_fuzzy_threshold
                        )
                        if (entity.kind, entity.record_id) not in exact_keys
                    )
                    for rank, entity in enumerate(suggestions, start=1):
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
                matched_entity_evidence=tuple(
                    matched_entity_evidence[key][evidence_key]
                    for evidence_key in sorted(matched_entity_evidence[key])
                ),
            )
            for key in ordered[:limit]
        )


@dataclass(frozen=True, slots=True)
class EntityAliasMatch:
    """Exact normalized alias match with review state and citation provenance."""

    kind: str
    record_id: str
    canonical_name: str
    matched_alias: str
    ambiguity_count: int = 1
    match_type: str = "legacy_alias"
    review_status: str = "unverified"
    alias_id: str | None = None
    source_id: str | None = None
    locator: str | None = None
    language: str | None = None

    @property
    def ambiguous(self) -> bool:
        return self.ambiguity_count > 1


@dataclass(frozen=True, slots=True)
class EntityAliasSuggestion:
    """A fuzzy alias candidate; it is never an automatic identity merge."""

    kind: str
    record_id: str
    canonical_name: str
    matched_alias: str
    similarity: float
    ambiguity_count: int = 1

    @property
    def ambiguous(self) -> bool:
        return self.ambiguity_count > 1


class EntityAwareSearchIndex:
    """Exact alias resolver for people, places, civilizations, organizations."""

    _KINDS = ("person", "place", "civilization", "organization")

    def __init__(self, aliases: dict[str, tuple[EntityAliasMatch, ...]]) -> None:
        self._aliases = aliases

    @classmethod
    def build(
        cls,
        dataset: HistoricalDataset,
        *,
        alias_registry: AliasRegistry | None = None,
    ) -> EntityAwareSearchIndex:
        """Build an entity index; only verified registry assertions gain verified status."""
        if alias_registry is not None and alias_registry.dataset != dataset:
            raise ValueError("alias_registry must match the indexed dataset snapshot")
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
                        is_canonical = alias == record.name
                        rows[normalized].append(EntityAliasMatch(
                            kind=kind,
                            record_id=record.id,
                            canonical_name=record.name,
                            matched_alias=alias,
                            match_type="canonical_name" if is_canonical else "legacy_alias",
                            review_status="canonical_record" if is_canonical else "unverified",
                        ))
        if alias_registry is not None:
            for assertion in alias_registry.assertions:
                if assertion.review_status != "verified":
                    continue
                match = alias_registry.resolve(assertion.alias)
                for resolved in match:
                    normalized = _normalize_phrase(resolved.alias)
                    rows[normalized].append(EntityAliasMatch(
                        kind=resolved.entity_kind,
                        record_id=resolved.entity_id,
                        canonical_name=resolved.canonical_name,
                        matched_alias=resolved.alias,
                        match_type="verified_alias",
                        review_status="verified",
                        alias_id=resolved.alias_id,
                        source_id=resolved.source_id,
                        locator=resolved.locator,
                        language=resolved.language,
                    ))
        return cls({
            key: tuple(sorted(
                values,
                key=lambda item: (
                    item.kind, item.record_id, item.matched_alias,
                    item.match_type, item.alias_id or "",
                ),
            ))
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
        matches: dict[tuple[str, str, str], EntityAliasMatch] = {}
        for alias, entities in self._aliases.items():
            if not re.search(rf"(?<!\\w){re.escape(alias)}(?!\\w)", normalized):
                continue
            eligible = [
                entity for entity in entities
                if allowed is None or entity.kind in allowed
            ]
            ambiguity_count = len({
                (entity.kind, entity.record_id) for entity in eligible
            })
            for entity in eligible:
                candidate = replace(entity, ambiguity_count=max(1, ambiguity_count))
                key = (entity.kind, entity.record_id, alias)
                previous = matches.get(key)
                priority = {
                    "legacy_alias": 0,
                    "canonical_name": 1,
                    "verified_alias": 2,
                }
                if (
                    previous is None
                    or priority.get(candidate.match_type, 0)
                    > priority.get(previous.match_type, 0)
                ):
                    matches[key] = candidate
        return tuple(sorted(
            matches.values(),
            key=lambda item: (item.kind, item.record_id, item.matched_alias)
        ))

    def suggest(
        self,
        query: str,
        *,
        kinds: Iterable[str] | None = None,
        threshold: float = 0.88,
        limit: int = 10,
    ) -> tuple[EntityAliasSuggestion, ...]:
        """Suggest spelling-near aliases without merging or asserting identity.

        Transliteration and historical name changes must be recorded as explicit
        aliases. Fuzzy matching is only a review queue for typographic variants.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise ValueError("limit must be a positive integer")
        query_tokens = _normalize_phrase(query).split()
        query_tokens = [token for token in query_tokens if len(token) >= 4]
        if not query_tokens:
            return ()
        allowed = set(kinds) if kinds is not None else None
        best: dict[tuple[str, str], EntityAliasSuggestion] = {}
        for alias, entities in self._aliases.items():
            alias_tokens = [token for token in alias.split() if len(token) >= 4]
            if not alias_tokens:
                continue
            similarity = max(
                SequenceMatcher(None, query_token, alias_token).ratio()
                for query_token in query_tokens
                for alias_token in alias_tokens
            )
            if similarity < threshold:
                continue
            eligible = [
                entity for entity in entities
                if allowed is None or entity.kind in allowed
            ]
            ambiguity = len({(item.kind, item.record_id) for item in eligible})
            for entity in eligible:
                key = (entity.kind, entity.record_id)
                candidate = EntityAliasSuggestion(
                    entity.kind, entity.record_id, entity.canonical_name,
                    entity.matched_alias, similarity, max(1, ambiguity)
                )
                previous = best.get(key)
                if previous is None or (
                    candidate.similarity, candidate.matched_alias
                ) > (previous.similarity, previous.matched_alias):
                    best[key] = candidate
        ordered = sorted(
            best.values(),
            key=lambda item: (-item.similarity, item.kind, item.record_id)
        )
        return tuple(ordered[:limit])
