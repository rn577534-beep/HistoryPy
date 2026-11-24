"""Typed, dependency-free data models for historical research.

These models store information and provenance. They do not independently
authenticate a source or decide whether a historical claim is true.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

DatePrecision = Literal["day", "month", "year", "decade", "century", "unknown"]
SourceType = Literal[
    "primary", "secondary", "tertiary", "archaeological", "oral",
    "epigraphic", "numismatic", "archival", "other",
]
EvidenceRelation = Literal["supports", "contradicts", "contextualizes", "mentions"]


def _validate_iso_date(value: str, field_name: str) -> None:
    try:
        date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a valid ISO date (YYYY-MM-DD)") from exc


def _format_astronomical_year(year: int) -> str:
    """Format astronomical year numbering (1 CE=1, 1 BCE=0, 2 BCE=-1)."""
    if year > 0:
        return f"{year} CE"
    return f"{1 - year} BCE"


@dataclass(frozen=True, slots=True)
class HistoricalDate:
    """A date or bounded date range with explicit calendar and precision metadata.

    ISO bounds use YYYY-MM-DD and therefore represent positive Gregorian years.
    For BCE and year-only dates, use earliest_year/latest_year with astronomical
    year numbering: 1 CE=1, 1 BCE=0, 2 BCE=-1. Do not mix the two bound formats.
    Preserve non-Gregorian source wording in original_expression. Calendar
    conversion is never performed implicitly.
    """

    earliest: str | None = None
    latest: str | None = None
    precision: DatePrecision = "unknown"
    calendar: str = "unspecified"
    circa: bool = False
    original_expression: str | None = None
    earliest_year: int | None = None
    latest_year: int | None = None

    def __post_init__(self) -> None:
        if self.earliest is not None:
            _validate_iso_date(self.earliest, "earliest")
        if self.latest is not None:
            _validate_iso_date(self.latest, "latest")
        if self.earliest and self.latest and self.earliest > self.latest:
            raise ValueError("earliest cannot be later than latest")
        if (self.earliest_year is not None or self.latest_year is not None) and (
            self.earliest is not None or self.latest is not None
        ):
            raise ValueError("Use ISO bounds or astronomical year bounds, not both")
        if (
            self.earliest_year is not None
            and self.latest_year is not None
            and self.earliest_year > self.latest_year
        ):
            raise ValueError("earliest_year cannot be later than latest_year")
        if self.precision not in {"day", "month", "year", "decade", "century", "unknown"}:
            raise ValueError(f"Unsupported date precision: {self.precision}")
        if not self.calendar.strip():
            raise ValueError("calendar cannot be empty")
        if not any((
            self.earliest, self.latest, self.earliest_year is not None,
            self.latest_year is not None, self.original_expression,
        )):
            raise ValueError("Provide a normalized date bound or an original expression")

    def _comparison_bounds(self) -> tuple[tuple[int, int, int] | None, tuple[int, int, int] | None]:
        if self.earliest_year is not None or self.latest_year is not None:
            start = (self.earliest_year, 1, 1) if self.earliest_year is not None else None
            end = (self.latest_year, 12, 31) if self.latest_year is not None else None
            return start, end
        start_date = date.fromisoformat(self.earliest) if self.earliest else None
        end_date = date.fromisoformat(self.latest) if self.latest else None
        start = (start_date.year, start_date.month, start_date.day) if start_date else None
        end = (end_date.year, end_date.month, end_date.day) if end_date else None
        return start, end

    def overlaps(self, other: HistoricalDate) -> bool | None:
        """Compare date intervals; return None when overlap cannot be established.

        The comparison is only meaningful when both records use the same
        calendar. An expression-only date has no computable bounds.
        """
        if self.calendar != other.calendar:
            return None
        left_start, left_end = self._comparison_bounds()
        right_start, right_end = other._comparison_bounds()
        if left_start is None and left_end is None:
            return None
        if right_start is None and right_end is None:
            return None
        lower_left = left_start or (-(10**9), 1, 1)
        upper_left = left_end or (10**9, 12, 31)
        lower_right = right_start or (-(10**9), 1, 1)
        upper_right = right_end or (10**9, 12, 31)
        return lower_left <= upper_right and lower_right <= upper_left

    def display(self) -> str:
        """Return a compact human-readable representation."""
        if self.earliest_year is not None or self.latest_year is not None:
            if self.earliest_year == self.latest_year and self.earliest_year is not None:
                result = _format_astronomical_year(self.earliest_year)
            elif self.earliest_year is not None and self.latest_year is not None:
                result = (
                    f"{_format_astronomical_year(self.earliest_year)} to "
                    f"{_format_astronomical_year(self.latest_year)}"
                )
            elif self.earliest_year is not None:
                result = f"from {_format_astronomical_year(self.earliest_year)}"
            else:
                result = f"until {_format_astronomical_year(self.latest_year)}"
        elif self.original_expression and not (self.earliest or self.latest):
            result = self.original_expression
        elif self.earliest == self.latest and self.earliest:
            result = self.earliest
        elif self.earliest and self.latest:
            result = f"{self.earliest} to {self.latest}"
        elif self.earliest:
            result = f"from {self.earliest}"
        elif self.latest:
            result = f"until {self.latest}"
        else:
            result = "date unknown"
        if self.circa:
            result = f"circa {result}"
        if self.calendar != "unspecified":
            result = f"{result} ({self.calendar})"
        return result


@dataclass(frozen=True, slots=True)
class HistoricalClaim:
    """A researchable proposition, kept distinct from events and evidence."""

    id: str
    statement: str
    scope_note: str | None = None
    subject_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    interpretation_note: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.statement.strip():
            raise ValueError("Claim id and statement cannot be empty")


@dataclass(frozen=True, slots=True)
class SourceRecord:
    """Bibliographic and provenance metadata for a source."""

    id: str
    title: str
    source_type: SourceType
    creator: str | None = None
    publication_date: str | None = None
    publisher: str | None = None
    url: str | None = None
    accessed_on: str | None = None
    language: str | None = None
    archive_reference: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.title.strip():
            raise ValueError("Source id and title cannot be empty")
        if self.publication_date:
            _validate_iso_date(self.publication_date, "publication_date")
        if self.accessed_on:
            _validate_iso_date(self.accessed_on, "accessed_on")


@dataclass(frozen=True, slots=True)
class EvidenceLink:
    """A traceable relationship between a research claim and a source."""

    claim_id: str
    source_id: str
    relation: EvidenceRelation
    locator: str | None = None
    quotation: str | None = None
    interpretation_note: str | None = None

    def __post_init__(self) -> None:
        if not self.claim_id.strip() or not self.source_id.strip():
            raise ValueError("claim_id and source_id cannot be empty")
        if self.relation not in {"supports", "contradicts", "contextualizes", "mentions"}:
            raise ValueError(f"Unsupported evidence relation: {self.relation}")


@dataclass(frozen=True, slots=True)
class HistoricalEvent:
    """A historical event record with explicit date and source references."""

    id: str
    title: str
    date: HistoricalDate
    summary: str = ""
    place_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.title.strip():
            raise ValueError("Event id and title cannot be empty")
        if not isinstance(self.date, HistoricalDate):
            raise TypeError("date must be a HistoricalDate instance")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("source_ids must not contain duplicates")
