"""Unified, uncertainty-aware timelines for historical datasets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import HistoricalDate


@dataclass(frozen=True, slots=True)
class TimelineEntry:
    """A dated record represented as a possibly uncertain interval."""
    kind: str
    record_id: str
    label: str
    date: HistoricalDate | None
    source_ids: tuple[str, ...] = ()

    @property
    def date_label(self) -> str:
        return self.date.display() if self.date else "date unknown"


@dataclass(frozen=True, slots=True)
class TimelineResult:
    """A deterministic timeline with counts for excluded records."""
    entries: tuple[TimelineEntry, ...]
    undated_count: int
    excluded_indeterminate_count: int


def _combine_interval(start: HistoricalDate | None, end: HistoricalDate | None) -> HistoricalDate | None:
    if start is None:
        return end
    if end is None or start.calendar != end.calendar:
        return start
    if start.earliest_year is not None or end.latest_year is not None:
        if start.earliest is not None or end.latest is not None:
            return start
        return HistoricalDate(
            earliest_year=start.earliest_year, latest_year=end.latest_year,
            precision="year", calendar=start.calendar,
            circa=start.circa or end.circa,
        )
    return HistoricalDate(
        earliest=start.earliest, latest=end.latest,
        precision=start.precision if start.precision == end.precision else "unknown",
        calendar=start.calendar, circa=start.circa or end.circa,
    )


def _has_bounds(value: HistoricalDate) -> bool:
    return any((value.earliest, value.latest, value.earliest_year is not None, value.latest_year is not None))


def _sort_key(entry: TimelineEntry) -> tuple[object, ...]:
    value = entry.date
    if value is None:
        return (1, 0, 0, 0, entry.kind, entry.record_id)
    if value.earliest_year is not None:
        bound = (value.earliest_year, 1, 1)
    elif value.earliest is not None:
        parsed = date.fromisoformat(value.earliest)
        bound = (parsed.year, parsed.month, parsed.day)
    elif value.latest_year is not None:
        bound = (value.latest_year, 12, 31)
    elif value.latest is not None:
        parsed = date.fromisoformat(value.latest)
        bound = (parsed.year, parsed.month, parsed.day)
    else:
        return (1, 0, 0, 0, entry.kind, entry.record_id)
    return (0, *bound, value.calendar, entry.kind, entry.record_id)


def timeline_for_dataset(
    dataset: HistoricalDataset, *, period: HistoricalDate | None = None,
    kinds: tuple[str, ...] = ("event", "person", "civilization", "organization"),
    include_indeterminate: bool = False,
) -> TimelineResult:
    """Build a cross-record timeline without implicit calendar conversion.

    Lifespans and institutional/civilizational spans are represented as intervals.
    Undated records are counted and omitted by default. Incomparable calendar
    intervals are omitted for period queries unless explicitly requested.
    """
    allowed = {"event", "person", "civilization", "organization"}
    unknown = set(kinds) - allowed
    if unknown:
        raise ValueError(f"Unsupported timeline kinds: {', '.join(sorted(unknown))}")

    candidates: list[TimelineEntry] = []
    for item in dataset.events:
        if "event" in kinds:
            candidates.append(TimelineEntry("event", item.id, item.title, item.date, item.source_ids))
    for item in dataset.people:
        if "person" in kinds:
            candidates.append(TimelineEntry(
                "person", item.id, item.name,
                _combine_interval(item.birth_date, item.death_date), item.source_ids,
            ))
    for item in dataset.civilizations:
        if "civilization" in kinds:
            candidates.append(TimelineEntry(
                "civilization", item.id, item.name,
                _combine_interval(item.start_date, item.end_date), item.source_ids,
            ))
    for item in dataset.organizations:
        if "organization" in kinds:
            candidates.append(TimelineEntry(
                "organization", item.id, item.name,
                _combine_interval(item.founded, item.dissolved), item.source_ids,
            ))

    selected: list[TimelineEntry] = []
    undated_count = 0
    excluded_indeterminate_count = 0
    for entry in candidates:
        if entry.date is None or not _has_bounds(entry.date):
            undated_count += 1
            if include_indeterminate:
                selected.append(entry)
            elif period is not None:
                excluded_indeterminate_count += 1
            continue
        if period is not None:
            overlap = entry.date.overlaps(period)
            if overlap is False:
                continue
            if overlap is None:
                if not include_indeterminate:
                    excluded_indeterminate_count += 1
                    continue
        selected.append(entry)
    return TimelineResult(
        tuple(sorted(selected, key=_sort_key)), undated_count,
        excluded_indeterminate_count,
    )
