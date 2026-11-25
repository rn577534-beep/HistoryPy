"""Historical entities: people, places, civilizations, and organizations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from historypy.core.models import HistoricalDate

PlaceType = Literal[
    "settlement", "city", "region", "country", "site", "building",
    "battlefield", "archaeological_site", "other",
]
OrganizationType = Literal[
    "state", "dynasty", "kingdom", "empire", "government", "institution",
    "military", "religious", "trade", "political", "other",
]


def _validate_ids(values: tuple[str, ...], field_name: str) -> None:
    if any(not value.strip() for value in values):
        raise ValueError(f"{field_name} cannot contain empty identifiers")
    if len(set(values)) != len(values):
        raise ValueError(f"{field_name} must not contain duplicates")


@dataclass(frozen=True, slots=True)
class HistoricalPerson:
    """A person record. Identity claims should be supported by source records."""

    id: str
    name: str
    birth_date: HistoricalDate | None = None
    death_date: HistoricalDate | None = None
    aliases: tuple[str, ...] = ()
    occupations: tuple[str, ...] = ()
    description: str = ""
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Person id and name cannot be empty")
        _validate_ids(self.source_ids, "source_ids")


@dataclass(frozen=True, slots=True)
class HistoricalPlace:
    """A geographic or archaeological place with optional coordinates."""

    id: str
    name: str
    place_type: PlaceType = "other"
    latitude: float | None = None
    longitude: float | None = None
    parent_place_ids: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()
    description: str = ""
    source_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Place id and name cannot be empty")
        if self.place_type not in {
            "settlement", "city", "region", "country", "site", "building",
            "battlefield", "archaeological_site", "other",
        }:
            raise ValueError(f"Unsupported place type: {self.place_type}")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be supplied together")
        if self.latitude is not None and (
            isinstance(self.latitude, bool) or not -90 <= self.latitude <= 90
        ):
            raise ValueError("latitude must be a number between -90 and 90")
        if self.longitude is not None and (
            isinstance(self.longitude, bool) or not -180 <= self.longitude <= 180
        ):
            raise ValueError("longitude must be a number between -180 and 180")
        _validate_ids(self.parent_place_ids, "parent_place_ids")
        _validate_ids(self.source_ids, "source_ids")
        if self.id in self.parent_place_ids:
            raise ValueError("A place cannot be its own parent")


@dataclass(frozen=True, slots=True)
class HistoricalCivilization:
    """A civilization as a research category, not an assumed homogeneous entity."""

    id: str
    name: str
    start_date: HistoricalDate | None = None
    end_date: HistoricalDate | None = None
    region_place_ids: tuple[str, ...] = ()
    predecessor_ids: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    description: str = ""
    source_ids: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Civilization id and name cannot be empty")
        _validate_ids(self.aliases, "aliases")
        _validate_ids(self.region_place_ids, "region_place_ids")
        _validate_ids(self.predecessor_ids, "predecessor_ids")
        _validate_ids(self.source_ids, "source_ids")
        if self.id in self.predecessor_ids:
            raise ValueError("A civilization cannot be its own predecessor")


@dataclass(frozen=True, slots=True)
class HistoricalOrganization:
    """An organization, state, dynasty, institution, or other formal group."""

    id: str
    name: str
    organization_type: OrganizationType = "other"
    founded: HistoricalDate | None = None
    dissolved: HistoricalDate | None = None
    place_ids: tuple[str, ...] = ()
    member_person_ids: tuple[str, ...] = ()
    parent_organization_ids: tuple[str, ...] = ()
    description: str = ""
    source_ids: tuple[str, ...] = ()
    aliases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Organization id and name cannot be empty")
        _validate_ids(self.aliases, "aliases")
        if self.organization_type not in {
            "state", "dynasty", "kingdom", "empire", "government", "institution",
            "military", "religious", "trade", "political", "other",
        }:
            raise ValueError(f"Unsupported organization type: {self.organization_type}")
        _validate_ids(self.place_ids, "place_ids")
        _validate_ids(self.member_person_ids, "member_person_ids")
        _validate_ids(self.parent_organization_ids, "parent_organization_ids")
        _validate_ids(self.source_ids, "source_ids")
        if self.id in self.parent_organization_ids:
            raise ValueError("An organization cannot be its own parent")


@dataclass(frozen=True, slots=True)
class HistoricalRelationship:
    """A sourced, directed relationship between two historical entities."""

    id: str
    subject_id: str
    predicate: str
    object_id: str
    source_ids: tuple[str, ...] = ()
    valid_from: HistoricalDate | None = None
    valid_to: HistoricalDate | None = None
    confidence: float | None = None
    notes: str | None = None
    claim_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not all(value.strip() for value in (
            self.id, self.subject_id, self.predicate, self.object_id
        )):
            raise ValueError("Relationship identifiers and predicate cannot be empty")
        if self.confidence is not None and (
            isinstance(self.confidence, bool) or not 0.0 <= self.confidence <= 1.0
        ):
            raise ValueError("confidence must be a number between 0.0 and 1.0")
        _validate_ids(self.source_ids, "source_ids")
        _validate_ids(self.claim_ids, "claim_ids")
        if self.valid_from and self.valid_to:
            if (
                self.valid_from.calendar == self.valid_to.calendar
                and self.valid_from.calendar != "unspecified"
            ):
                start_bounds = self.valid_from._comparison_bounds()
                end_bounds = self.valid_to._comparison_bounds()
                start = start_bounds[0] or start_bounds[1]
                end = end_bounds[1] or end_bounds[0]
                if start is not None and end is not None and start > end:
                    raise ValueError("valid_from cannot be later than valid_to")
