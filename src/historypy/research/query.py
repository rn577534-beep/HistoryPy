"""Deterministic text and chronology queries over a historical dataset.

Search is lexical, not semantic: it does not resolve aliases to identities or
infer that similarly named records refer to the same person or place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import HistoricalDate, HistoricalEvent


@dataclass(frozen=True, slots=True)
class SearchHit:
    """One lexical match, with a stable record type and identifier."""

    kind: str
    record_id: str
    label: str
    matched_terms: tuple[str, ...]


def _searchable_records(dataset: HistoricalDataset) -> Iterable[tuple[str, str, str, str]]:
    """Yield kind, ID, display label, and searchable text for each record."""
    for record in dataset.people:
        yield "person", record.id, record.name, " ".join(
            (record.name, *record.aliases, *record.occupations, record.description)
        )
    for record in dataset.places:
        yield "place", record.id, record.name, " ".join(
            (record.name, *record.aliases, record.place_type, record.description)
        )
    for record in dataset.civilizations:
        yield "civilization", record.id, record.name, " ".join(
            (record.name, *record.languages, record.description)
        )
    for record in dataset.organizations:
        yield "organization", record.id, record.name, " ".join(
            (record.name, record.organization_type, record.description)
        )
    for record in dataset.events:
        yield "event", record.id, record.title, " ".join(
            (record.title, record.summary, *record.tags, record.notes or "")
        )
    for record in dataset.claims:
        yield "claim", record.id, record.statement, " ".join(
            (record.statement, record.scope_note or "", record.interpretation_note or "")
        )
    for record in dataset.sources:
        yield "source", record.id, record.title, " ".join(
            (record.title, record.creator or "", record.publisher or "",
             record.language or "", record.archive_reference or "", record.notes or "")
        )


def search_dataset(
    dataset: HistoricalDataset,
    query: str,
    *,
    kinds: Iterable[str] | None = None,
    limit: int | None = 20,
) -> tuple[SearchHit, ...]:
    """Search records by requiring every query term to occur in searchable text.

    Results are ordered by number of matched terms (descending), then by kind
    and identifier. An empty query returns no results. A non-positive limit
    returns no results. This is intentionally transparent lexical retrieval.
    """
    if not isinstance(query, str):
        raise TypeError("query must be a string")
    if limit is not None and (
        not isinstance(limit, int) or isinstance(limit, bool)
    ):
        raise TypeError("limit must be an integer or None")
    if limit is not None and limit <= 0:
        return ()
    terms = tuple(dict.fromkeys(query.casefold().split()))
    if not terms:
        return ()
    allowed = set(kinds) if kinds is not None else None
    hits: list[SearchHit] = []
    for kind, record_id, label, searchable in _searchable_records(dataset):
        if allowed is not None and kind not in allowed:
            continue
        normalized = searchable.casefold()
        matched = tuple(term for term in terms if term in normalized)
        if len(matched) == len(terms):
            hits.append(SearchHit(kind, record_id, label, matched))
    hits.sort(key=lambda hit: (-len(hit.matched_terms), hit.kind, hit.record_id))
    return tuple(hits[:limit] if limit is not None else hits)


def events_overlapping(
    dataset: HistoricalDataset,
    period: HistoricalDate,
    *,
    include_indeterminate: bool = False,
) -> tuple[HistoricalEvent, ...]:
    """Return events whose date intervals overlap a period.

    Events with incompatible, unspecified, or unbounded comparison data are
    excluded unless include_indeterminate=True. Input order is preserved.
    """
    if not isinstance(period, HistoricalDate):
        raise TypeError("period must be a HistoricalDate")
    if not isinstance(include_indeterminate, bool):
        raise TypeError("include_indeterminate must be a bool")
    matches = []
    for event in dataset.events:
        overlap = event.date.overlaps(period)
        if overlap is True or (overlap is None and include_indeterminate):
            matches.append(event)
    return tuple(matches)
