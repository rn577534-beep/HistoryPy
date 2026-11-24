"""Embedding-backed semantic retrieval with explicit model provenance.

HistoryPy does not ship or silently select an embedding model. Callers supply
an embedder so model choice, hosting, cost, and data handling stay explicit.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TypeAlias

from historypy.core.dataset import HistoricalDataset
from historypy.research.query import _searchable_records

EmbeddingBatch: TypeAlias = Callable[[Sequence[str]], Sequence[Sequence[float]]]


@dataclass(frozen=True, slots=True)
class SemanticSearchHit:
    """A record ranked by cosine similarity from a caller-supplied embedder."""

    kind: str
    record_id: str
    label: str
    similarity: float


def _validated_vector(values: Sequence[float], *, dimension: int | None = None) -> tuple[float, ...]:
    try:
        vector = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError("Embedding vectors must contain numeric values") from exc
    if not vector or any(not math.isfinite(value) for value in vector):
        raise ValueError("Embedding vectors must be non-empty and finite")
    if dimension is not None and len(vector) != dimension:
        raise ValueError("Embedding dimensions do not match the index")
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        raise ValueError("Embedding vectors cannot have zero magnitude")
    return tuple(value / norm for value in vector)


@dataclass(frozen=True, slots=True)
class SemanticSearchIndex:
    """Immutable normalized-vector snapshot for repeat semantic queries.

    Rebuild after changing the dataset or changing the embedding model. The
    supplied embedder must return vectors in exactly the same vector space for
    both indexed records and later queries.
    """

    model_id: str
    records: tuple[tuple[str, str, str, tuple[float, ...]], ...]
    dimension: int

    @classmethod
    def build(
        cls,
        dataset: HistoricalDataset,
        *,
        embedder: EmbeddingBatch,
        model_id: str,
        batch_size: int = 64,
    ) -> SemanticSearchIndex:
        """Embed searchable records in bounded batches and retain model ID."""
        if not callable(embedder):
            raise TypeError("embedder must be callable")
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id must be a non-empty identifier")
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        dataset.require_valid()
        rows = tuple(_searchable_records(dataset))
        vectors: list[tuple[float, ...]] = []
        dimension: int | None = None
        for start in range(0, len(rows), batch_size):
            batch = rows[start:start + batch_size]
            raw_vectors = embedder(tuple(row[3] for row in batch))
            if len(raw_vectors) != len(batch):
                raise ValueError("Embedder must return exactly one vector per input text")
            for raw in raw_vectors:
                vector = _validated_vector(raw, dimension=dimension)
                if dimension is None:
                    dimension = len(vector)
                vectors.append(vector)
        if not vectors:
            return cls(model_id.strip(), (), 0)
        indexed = tuple(
            (kind, record_id, label, vector)
            for (kind, record_id, label, _), vector in zip(rows, vectors, strict=True)
        )
        return cls(model_id.strip(), indexed, dimension or 0)

    def search(
        self,
        query: str,
        *,
        embedder: EmbeddingBatch,
        kinds: Sequence[str] | None = None,
        limit: int = 20,
        min_similarity: float = -1.0,
    ) -> tuple[SemanticSearchHit, ...]:
        """Rank records by cosine similarity; never interpret similarity as truth."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query cannot be empty")
        if not callable(embedder):
            raise TypeError("embedder must be callable")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        if not isinstance(min_similarity, (int, float)) or isinstance(min_similarity, bool):
            raise TypeError("min_similarity must be numeric")
        if not math.isfinite(min_similarity) or not -1 <= min_similarity <= 1:
            raise ValueError("min_similarity must be between -1 and 1")
        if limit == 0 or not self.records:
            return ()
        raw = embedder((query.strip(),))
        if len(raw) != 1:
            raise ValueError("Embedder must return exactly one vector for a query")
        vector = _validated_vector(raw[0], dimension=self.dimension)
        allowed = set(kinds) if kinds is not None else None
        hits = [
            SemanticSearchHit(kind, record_id, label, sum(a * b for a, b in zip(vector, stored, strict=True)))
            for kind, record_id, label, stored in self.records
            if allowed is None or kind in allowed
        ]
        hits = [hit for hit in hits if hit.similarity >= min_similarity]
        hits.sort(key=lambda hit: (-hit.similarity, hit.kind, hit.record_id))
        return tuple(hits[:limit])
