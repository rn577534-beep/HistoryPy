"""Timeline utilities for ordering and comparing historical events."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from itertools import combinations

from historypy.core.models import HistoricalDate, HistoricalEvent


def _start_key(value: HistoricalDate) -> tuple[int, int, int, int]:
    """Return a stable sortable key; records without computable bounds sort last."""
    if value.earliest_year is not None:
        return (0, value.earliest_year, 1, 1)
    if value.earliest is not None:
        parsed = date.fromisoformat(value.earliest)
        return (0, parsed.year, parsed.month, parsed.day)
    return (1, 0, 1, 1)


def sort_events(events: Iterable[HistoricalEvent]) -> list[HistoricalEvent]:
    """Sort events by earliest normalized date, leaving unknown dates at the end.

    This orders stored bounds; it does not convert calendar systems. If a
    collection mixes calendars, callers should group or normalize them first.
    """
    records = list(events)
    dated = [
        event for event in records
        if event.date.earliest is not None
        or event.date.earliest_year is not None
    ]
    calendars = {event.date.calendar for event in dated}
    if "unspecified" in calendars or len(calendars) > 1:
        raise ValueError(
            "Normalize events to one explicit calendar before sorting a timeline"
        )
    return sorted(records, key=lambda event: (_start_key(event.date), event.title.casefold()))


def find_overlapping_events(
    events: Iterable[HistoricalEvent],
) -> list[tuple[HistoricalEvent, HistoricalEvent]]:
    """Return event pairs whose date intervals are known to overlap.

    Pairs with unknown dates or incompatible calendar metadata are omitted,
    rather than treated as confirmed overlaps.
    """
    results = []
    for first, second in combinations(events, 2):
        if first.date.overlaps(second.date) is True:
            results.append((first, second))
    return results
