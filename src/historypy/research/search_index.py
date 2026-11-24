"""Reusable compact trigram index for repeated lexical dataset searches."""
from __future__ import annotations

from array import array
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType

from historypy.core.dataset import HistoricalDataset
from historypy.research.query import SearchHit, _searchable_records


@dataclass(frozen=True, slots=True)
class DatasetSearchIndex:
    """Immutable compact trigram index; rebuild after changing the dataset.

    Posting lists use read-only memory views over packed unsigned integers.
    This avoids the large Python-int/set overhead of a conventional postings
    dictionary. Record indexes are 32-bit, supporting up to 2^32-1 records.
    """

    records: tuple[tuple[str, str, str, str], ...]
    postings: Mapping[str, memoryview]

    @classmethod
    def build(cls, dataset: HistoricalDataset) -> DatasetSearchIndex:
        records: list[tuple[str, str, str, str]] = []
        mutable: dict[str, array] = {}
        for kind, record_id, label, searchable in _searchable_records(dataset):
            normalized = searchable.casefold()
            index = len(records)
            if index > 0xFFFFFFFF:
                raise ValueError("DatasetSearchIndex supports at most 2^32 records")
            records.append((kind, record_id, label, normalized))
            for token in set(normalized.split()):
                if len(token) < 3:
                    continue
                for gram in {
                    token[start:start + 3] for start in range(len(token) - 2)
                }:
                    posting = mutable.get(gram)
                    if posting is None:
                        posting = array("I")
                        mutable[gram] = posting
                    # Records are visited in increasing order, so each posting
                    # list is already sorted and contains no duplicate index.
                    posting.append(index)
        postings = MappingProxyType({
            gram: memoryview(values).toreadonly() for gram, values in mutable.items()
        })
        return cls(tuple(records), postings)

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
        long_terms = [term for term in terms if len(term) >= 3]
        if any(
            trigram not in self.postings
            for term in long_terms
            for trigram in {term[i:i + 3] for i in range(len(term) - 2)}
        ):
            return ()
        if long_terms:
            first = long_terms[0]
            grams = {first[i:i + 3] for i in range(len(first) - 2)}
            candidates = set.intersection(*(set(self.postings[gram]) for gram in grams))
            for term in long_terms[1:]:
                term_grams = {term[i:i + 3] for i in range(len(term) - 2)}
                term_candidates = set.intersection(
                    *(set(self.postings[gram]) for gram in term_grams)
                )
                candidates.intersection_update(term_candidates)
        else:
            candidates = set(range(len(self.records)))
        allowed = set(kinds) if kinds is not None else None
        hits = []
        for index in candidates:
            kind, record_id, label, searchable = self.records[index]
            if (allowed is None or kind in allowed) and all(term in searchable for term in terms):
                hits.append(SearchHit(kind, record_id, label, terms))
        hits.sort(key=lambda hit: (-len(hit.matched_terms), hit.kind, hit.record_id))
        return tuple(hits[:limit] if limit is not None else hits)
