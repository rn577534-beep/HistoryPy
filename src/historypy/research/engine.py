"""Structured, deterministic research queries across a HistoryPy dataset."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Literal

from historypy.core.dataset import HistoricalDataset
from historypy.core.entities import (
    HistoricalCivilization,
    HistoricalOrganization,
    HistoricalPerson,
    HistoricalPlace,
)
from historypy.core.models import HistoricalDate, HistoricalEvent, HistoricalClaim, SourceRecord
from historypy.research.query import SearchHit, _searchable_records, search_dataset

RecordKind = Literal[
    "person", "place", "civilization", "organization", "event", "claim", "source"
]
EvidenceStatus = Literal["supported", "contradicted", "mixed", "insufficient"]

_ALLOWED_KINDS = frozenset({
    "person", "place", "civilization", "organization", "event", "claim", "source"
})
_ALLOWED_EVIDENCE_STATUSES = frozenset({
    "supported", "contradicted", "mixed", "insufficient"
})


@dataclass(frozen=True, slots=True)
class ResearchQuery:
    """Composable filters for a reproducible dataset search.

    Filters are combined with AND semantics. Values in tags are exact,
    case-insensitive event-tag matches; evidence_status applies to claims.
    """

    text: str | None = None
    kinds: tuple[str, ...] | None = None
    period: HistoricalDate | None = None
    place_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    evidence_status: EvidenceStatus | None = None
    include_indeterminate: bool = False
    limit: int | None = 20
    offset: int = 0

    def __post_init__(self) -> None:
        if self.text is not None and not isinstance(self.text, str):
            raise TypeError("text must be a string or None")
        if self.kinds is not None:
            unknown = set(self.kinds) - _ALLOWED_KINDS
            if unknown:
                raise ValueError(f"Unsupported record kind(s): {', '.join(sorted(unknown))}")
            if len(set(self.kinds)) != len(self.kinds):
                raise ValueError("kinds must not contain duplicates")
        if self.period is not None and not isinstance(self.period, HistoricalDate):
            raise TypeError("period must be a HistoricalDate or None")
        for name, values in (("place_ids", self.place_ids), ("source_ids", self.source_ids),
                             ("tags", self.tags)):
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{name} must contain non-empty strings")
            if len(set(values)) != len(values):
                raise ValueError(f"{name} must not contain duplicates")
        if self.evidence_status is not None and self.evidence_status not in _ALLOWED_EVIDENCE_STATUSES:
            raise ValueError(f"Unsupported evidence status: {self.evidence_status}")
        if not isinstance(self.include_indeterminate, bool):
            raise TypeError("include_indeterminate must be a bool")
        if self.limit is not None and (
            not isinstance(self.limit, int) or isinstance(self.limit, bool)
        ):
            raise TypeError("limit must be an integer or None")
        if not isinstance(self.offset, int) or isinstance(self.offset, bool):
            raise TypeError("offset must be an integer")
        if self.offset < 0:
            raise ValueError("offset cannot be negative")


@dataclass(frozen=True, slots=True)
class ResearchFacets:
    """Counts across the full filtered result set, before pagination."""

    kind_counts: tuple[tuple[str, int], ...]
    evidence_status_counts: tuple[tuple[str, int], ...]
    tag_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True, slots=True)
class ResearchSearchResult:
    """A page of stable search hits plus total count and full-result facets."""

    hits: tuple[SearchHit, ...]
    total: int
    offset: int
    limit: int | None
    facets: ResearchFacets


def _claim_status(dataset: HistoricalDataset, claim_id: str) -> EvidenceStatus:
    relations = {
        item.relation for item in dataset.evidence if item.claim_id == claim_id
    }
    supports = "supports" in relations
    contradicts = "contradicts" in relations
    if supports and contradicts:
        return "mixed"
    if supports:
        return "supported"
    if contradicts:
        return "contradicted"
    return "insufficient"


def _record_maps(dataset: HistoricalDataset) -> dict[str, dict[str, object]]:
    return {
        "person": {item.id: item for item in dataset.people},
        "place": {item.id: item for item in dataset.places},
        "civilization": {item.id: item for item in dataset.civilizations},
        "organization": {item.id: item for item in dataset.organizations},
        "event": {item.id: item for item in dataset.events},
        "claim": {item.id: item for item in dataset.claims},
        "source": {item.id: item for item in dataset.sources},
    }


def _range_overlaps(
    start: HistoricalDate, end: HistoricalDate, period: HistoricalDate
) -> bool | None:
    if (
        start.calendar == "unspecified"
        or end.calendar != start.calendar
        or period.calendar != start.calendar
    ):
        return None
    start_lower, _ = start._comparison_bounds()
    _, end_upper = end._comparison_bounds()
    period_lower, period_upper = period._comparison_bounds()
    if period_lower is None and period_upper is None:
        return None
    lower = start_lower or (-(10**9), 1, 1)
    upper = end_upper or (10**9, 12, 31)
    query_lower = period_lower or (-(10**9), 1, 1)
    query_upper = period_upper or (10**9, 12, 31)
    return lower <= query_upper and query_lower <= upper


def _matches_period(record: object, period: HistoricalDate, include_indeterminate: bool) -> bool:
    if isinstance(record, HistoricalEvent):
        result = record.date.overlaps(period)
    elif isinstance(record, HistoricalPerson):
        if record.birth_date and record.death_date:
            result = _range_overlaps(record.birth_date, record.death_date, period)
        else:
            dates = tuple(item for item in (record.birth_date, record.death_date) if item)
            results = tuple(item.overlaps(period) for item in dates)
            result = True if True in results else (None if None in results else False)
    elif isinstance(record, HistoricalCivilization):
        if record.start_date and record.end_date:
            result = _range_overlaps(record.start_date, record.end_date, period)
        else:
            dates = tuple(item for item in (record.start_date, record.end_date) if item)
            results = tuple(item.overlaps(period) for item in dates)
            result = True if True in results else (None if None in results else False)
    elif isinstance(record, HistoricalOrganization):
        if record.founded and record.dissolved:
            result = _range_overlaps(record.founded, record.dissolved, period)
        else:
            dates = tuple(item for item in (record.founded, record.dissolved) if item)
            results = tuple(item.overlaps(period) for item in dates)
            result = True if True in results else (None if None in results else False)
    else:
        return False
    return result is True or (result is None and include_indeterminate)


def _matches_places(record: object, kind: str, requested: set[str]) -> bool:
    if kind == "place" and isinstance(record, HistoricalPlace):
        return record.id in requested
    if kind == "event" and isinstance(record, HistoricalEvent):
        return bool(requested.intersection(record.place_ids))
    if kind == "civilization" and isinstance(record, HistoricalCivilization):
        return bool(requested.intersection(record.region_place_ids))
    if kind == "organization" and isinstance(record, HistoricalOrganization):
        return bool(requested.intersection(record.place_ids))
    return False


def _matches_sources(
    dataset: HistoricalDataset, record: object, kind: str, requested: set[str]
) -> bool:
    if kind == "source" and isinstance(record, SourceRecord):
        return record.id in requested
    source_ids = getattr(record, "source_ids", ())
    if kind == "claim" and isinstance(record, HistoricalClaim):
        source_ids = tuple(
            item.source_id for item in dataset.evidence if item.claim_id == record.id
        )
    return bool(requested.intersection(source_ids))


def execute_research_query(
    dataset: HistoricalDataset, query: ResearchQuery
) -> ResearchSearchResult:
    """Execute all query filters and return deterministic, faceted results.

    Search uses literal case-insensitive substring matching, not semantic
    retrieval. Facets describe all filtered matches, not just the returned page.
    """
    if not isinstance(query, ResearchQuery):
        raise TypeError("query must be a ResearchQuery")
    dataset.require_valid()
    maps = _record_maps(dataset)
    if query.text and query.text.strip():
        candidates = search_dataset(dataset, query.text, kinds=query.kinds, limit=None)
    else:
        allowed = set(query.kinds) if query.kinds is not None else _ALLOWED_KINDS
        candidates = tuple(
            SearchHit(kind, record_id, label, ())
            for kind, record_id, label, _ in _searchable_records(dataset)
            if kind in allowed
        )

    place_filter = set(query.place_ids)
    source_filter = set(query.source_ids)
    filtered: list[SearchHit] = []
    for hit in candidates:
        record = maps[hit.kind][hit.record_id]
        if query.period is not None and not _matches_period(
            record, query.period, query.include_indeterminate
        ):
            continue
        if place_filter and not _matches_places(record, hit.kind, place_filter):
            continue
        if source_filter and not _matches_sources(
            dataset, record, hit.kind, source_filter
        ):
            continue
        if query.tags:
            if not isinstance(record, HistoricalEvent):
                continue
            record_tags = {tag.casefold() for tag in record.tags}
            if not {tag.casefold() for tag in query.tags}.issubset(record_tags):
                continue
        if query.evidence_status is not None:
            if not isinstance(record, HistoricalClaim):
                continue
            if _claim_status(dataset, record.id) != query.evidence_status:
                continue
        filtered.append(hit)

    filtered.sort(key=lambda hit: (-len(hit.matched_terms), hit.kind, hit.record_id))
    kind_counts = Counter(hit.kind for hit in filtered)
    status_counts = Counter()
    tag_counts = Counter()
    for hit in filtered:
        record = maps[hit.kind][hit.record_id]
        if isinstance(record, HistoricalClaim):
            status_counts[_claim_status(dataset, record.id)] += 1
        if isinstance(record, HistoricalEvent):
            tag_counts.update(set(record.tags))
    facets = ResearchFacets(
        kind_counts=tuple(sorted(kind_counts.items())),
        evidence_status_counts=tuple(sorted(status_counts.items())),
        tag_counts=tuple(sorted(tag_counts.items(), key=lambda item: (-item[1], item[0]))),
    )
    total = len(filtered)
    page = filtered[query.offset:]
    if query.limit is not None:
        page = page[:max(query.limit, 0)]
    return ResearchSearchResult(tuple(page), total, query.offset, query.limit, facets)
