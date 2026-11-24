"""BM25 lexical retrieval for historical datasets."""
from __future__ import annotations

import collections.abc
import math
import re
import unicodedata
from dataclasses import dataclass
from types import MappingProxyType

from historypy.core.dataset import HistoricalDataset
from historypy.research.query import _searchable_records


_TOKEN_PATTERN = re.compile(r"[^\W_]+", re.UNICODE)


def _tokens(text: str) -> tuple[str, ...]:
    folded = unicodedata.normalize("NFKD", text.casefold())
    normalized = "".join(
        character for character in folded
        if not unicodedata.combining(character)
    )
    return tuple(token for token in _TOKEN_PATTERN.findall(normalized) if len(token) > 1)


@dataclass(frozen=True, slots=True)
class BM25SearchHit:
    """One BM25-ranked result; score is a retrieval signal, not confidence."""

    kind: str
    record_id: str
    label: str
    score: float
    matched_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BM25SearchIndex:
    """An in-memory BM25 index with accent-insensitive Unicode tokenization."""

    records: tuple[tuple[str, str, str], ...]
    term_frequencies: tuple[collections.abc.Mapping[str, int], ...]
    postings: collections.abc.Mapping[str, tuple[tuple[int, int], ...]]
    document_lengths: tuple[int, ...]
    average_document_length: float
    k1: float = 1.5
    b: float = 0.75

    @classmethod
    def build(
        cls, dataset: HistoricalDataset, *, k1: float = 1.5, b: float = 0.75
    ) -> BM25SearchIndex:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if not 0 <= b <= 1:
            raise ValueError("b must be between 0 and 1")

        records = []
        frequencies = []
        mutable_postings: dict[str, list[tuple[int, int]]] = collections.defaultdict(list)
        lengths = []
        for kind, record_id, label, searchable in _searchable_records(dataset):
            index = len(records)
            counts = collections.Counter(_tokens(searchable))
            records.append((kind, record_id, label))
            frequencies.append(MappingProxyType(dict(counts)))
            lengths.append(sum(counts.values()))
            for term, frequency in counts.items():
                mutable_postings[term].append((index, frequency))

        average_length = sum(lengths) / len(lengths) if lengths else 0.0
        return cls(
            records=tuple(records),
            term_frequencies=tuple(frequencies),
            postings=MappingProxyType({
                term: tuple(values) for term, values in mutable_postings.items()
            }),
            document_lengths=tuple(lengths),
            average_document_length=average_length,
            k1=k1,
            b=b,
        )

    def search(
        self,
        query: str,
        *,
        kinds: collections.abc.Iterable[str] | None = None,
        limit: int | None = 20,
    ) -> tuple[BM25SearchHit, ...]:
        """Return OR-matched results ordered by BM25 score, then stable IDs."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool)):
            raise TypeError("limit must be an integer or None")
        if limit is not None and limit <= 0:
            return ()

        terms = tuple(dict.fromkeys(_tokens(query)))
        if not terms or not self.records:
            return ()
        allowed = set(kinds) if kinds is not None else None
        candidates = {
            record_index
            for term in terms
            for record_index, _ in self.postings.get(term, ())
        }
        if not candidates:
            return ()

        document_count = len(self.records)
        average_length = self.average_document_length or 1.0
        hits = []
        for index in candidates:
            kind, record_id, label = self.records[index]
            if allowed is not None and kind not in allowed:
                continue
            frequencies = self.term_frequencies[index]
            matched_terms = tuple(term for term in terms if term in frequencies)
            score = 0.0
            document_length = self.document_lengths[index]
            for term in matched_terms:
                frequency = frequencies[term]
                document_frequency = len(self.postings[term])
                inverse_document_frequency = math.log(
                    1 + (document_count - document_frequency + 0.5)
                    / (document_frequency + 0.5)
                )
                denominator = frequency + self.k1 * (
                    1 - self.b + self.b * document_length / average_length
                )
                score += inverse_document_frequency * (
                    frequency * (self.k1 + 1) / denominator
                )
            hits.append(BM25SearchHit(
                kind, record_id, label, score, matched_terms
            ))

        hits.sort(key=lambda hit: (-hit.score, hit.kind, hit.record_id))
        return tuple(hits[:limit] if limit is not None else hits)
