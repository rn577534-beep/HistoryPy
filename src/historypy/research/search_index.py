"""Reusable in-memory substring index for repeated lexical dataset searches."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from collections.abc import Iterable

from historypy.core.dataset import HistoricalDataset
from historypy.research.query import SearchHit, _searchable_records


@dataclass(frozen=True, slots=True)
class DatasetSearchIndex:
    """Immutable inverted substring index; rebuild after changing the source dataset."""

    records: tuple[tuple[str, str, str], ...]
    postings: dict[str, tuple[int, ...]]

    @classmethod
    def build(cls, dataset: HistoricalDataset) -> "DatasetSearchIndex":
        records: list[tuple[str, str, str]] = []
        mutable: dict[str, set[int]] = defaultdict(set)
        for kind, record_id, label, searchable in _searchable_records(dataset):
            index = len(records)
            records.append((kind, record_id, label))
            tokens = set(searchable.casefold().split())
            for token in tokens:
                for start in range(len(token)):
                    for end in range(start + 1, len(token) + 1):
                        mutable[token[start:end]].add(index)
        return cls(
            tuple(records),
            {key: tuple(sorted(value)) for key, value in mutable.items()},
        )

    def search(
        self, query: str, *, kinds: Iterable[str] | None = None, limit: int | None = 20
    ) -> tuple[SearchHit, ...]:
        """Match every query term as a substring, like search_dataset()."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool)):
            raise TypeError("limit must be an integer or None")
        if limit is not None and limit <= 0:
            return ()
        terms = tuple(dict.fromkeys(query.casefold().split()))
        if not terms:
            return ()
        if any(term not in self.postings for term in terms):
            return ()
        candidates = set(self.postings[terms[0]])
        for term in terms[1:]:
            candidates.intersection_update(self.postings[term])
        allowed = set(kinds) if kinds is not None else None
        hits = []
        for index in candidates:
            kind, record_id, label = self.records[index]
            if allowed is None or kind in allowed:
                hits.append(SearchHit(kind, record_id, label, terms))
        hits.sort(key=lambda hit: (-len(hit.matched_terms), hit.kind, hit.record_id))
        return tuple(hits[:limit] if limit is not None else hits)
