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


@dataclass(frozen=True, slots=True)
class HistoricalDate:
    """A date or bounded date range with explicit calendar and precision metadata.

    For another calendar, preserve its original expression and name the calendar.
    Bounds are normalized ISO dates; they do not imply certainty.
    """

    earliest: str | None = None
    latest: str | None = None
    precision: DatePrecision = "unknown"
    calendar: str = "unspecified"
    circa: bool = False
    original_expression: str | None = None

    def __post_init__(self) -> None:
        if self.earliest is not None:
            _validate_iso_date(self.earliest, "earliest")
        if self.latest is not None:
            _validate_iso_date(self.latest, "latest")
        if self.earliest and self.latest and self.earliest > self.latest:
            raise ValueError("earliest cannot be later than latest")
        if self.precision not in {"day", "month", "year", "decade", "century", "unknown"}:
            raise ValueError(f"Unsupported date precision: {self.precision}")
        if not self.calendar.strip():
            raise ValueError("calendar cannot be empty")
        if self.earliest is None and self.latest is None and not self.original_expression:
            raise ValueError("Provide a normalized date bound or an original expression")

    def overlaps(self, other: HistoricalDate) -> bool:
        """Return whether two bounded intervals overlap; no calendar conversion is done."""
        left_start = self.earliest or "0001-01-01"
        left_end = self.latest or "9999-12-31"
        right_start = other.earliest or "0001-01-01"
        right_end = other.latest or "9999-12-31"
        return left_start <= right_end and right_start <= left_end

    def display(self) -> str:
        """Return a compact human-readable representation."""
        if self.original_expression and not (self.earliest or self.latest):
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
