"""Versioned JSON interchange for HistoryPy historical datasets."""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any, Mapping, TypeVar

from historypy.core.dataset import HistoricalDataset
from historypy.core.entities import (
    HistoricalCivilization,
    HistoricalOrganization,
    HistoricalPerson,
    HistoricalPlace,
    HistoricalRelationship,
)
from historypy.core.models import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDate,
    HistoricalEvent,
    SourceRecord,
)

SCHEMA_NAME = "historypy.dataset"
SCHEMA_VERSION = 1
T = TypeVar("T")


def _date_to_dict(value: HistoricalDate | None) -> dict[str, Any] | None:
    if value is None:
        return None
    return {
        "earliest": value.earliest,
        "latest": value.latest,
        "precision": value.precision,
        "calendar": value.calendar,
        "circa": value.circa,
        "original_expression": value.original_expression,
        "earliest_year": value.earliest_year,
        "latest_year": value.latest_year,
    }


def _date_from_dict(value: Any) -> HistoricalDate | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError("A historical date must be a JSON object or null")
    allowed = {
        "earliest", "latest", "precision", "calendar", "circa",
        "original_expression", "earliest_year", "latest_year",
    }
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"Unknown historical date field(s): {', '.join(sorted(unknown))}")
    return HistoricalDate(**dict(value))


def _record_to_dict(record: object, date_fields: tuple[str, ...] = ()) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for item in fields(record):
        value = getattr(record, item.name)
        if item.name in date_fields:
            result[item.name] = _date_to_dict(value)
        elif isinstance(value, tuple):
            result[item.name] = list(value)
        else:
            result[item.name] = value
    return result


def _record_from_dict(
    record_type: type[T],
    value: Any,
    *,
    tuple_fields: tuple[str, ...] = (),
    date_fields: tuple[str, ...] = (),
) -> T:
    if not isinstance(value, Mapping):
        raise TypeError(f"{record_type.__name__} record must be a JSON object")
    allowed = {item.name for item in fields(record_type)}
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(
            f"Unknown {record_type.__name__} field(s): {', '.join(sorted(unknown))}"
        )
    data = dict(value)
    for name in tuple_fields:
        if name in data:
            if not isinstance(data[name], list):
                raise TypeError(f"{record_type.__name__}.{name} must be a JSON array")
            data[name] = tuple(data[name])
    for name in date_fields:
        if name in data:
            data[name] = _date_from_dict(data[name])
    return record_type(**data)


def dataset_to_dict(dataset: HistoricalDataset) -> dict[str, Any]:
    """Convert a dataset to a versioned, JSON-compatible dictionary."""
    return {
        "schema": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "metadata": dict(dataset.metadata),
        "sources": [_record_to_dict(item) for item in dataset.sources],
        "claims": [
            _record_to_dict(item, ("",)) for item in dataset.claims
        ],
        "events": [
            _record_to_dict(item, ("date",)) for item in dataset.events
        ],
        "people": [
            _record_to_dict(item, ("birth_date", "death_date"))
            for item in dataset.people
        ],
        "places": [_record_to_dict(item) for item in dataset.places],
        "civilizations": [
            _record_to_dict(item, ("start_date", "end_date"))
            for item in dataset.civilizations
        ],
        "organizations": [
            _record_to_dict(item, ("founded", "dissolved"))
            for item in dataset.organizations
        ],
        "relationships": [
            _record_to_dict(item, ("valid_from", "valid_to"))
            for item in dataset.relationships
        ],
        "evidence": [_record_to_dict(item) for item in dataset.evidence],
    }


def dataset_from_dict(
    payload: Any, *, validate: bool = True
) -> HistoricalDataset:
    """Parse a versioned dictionary, rejecting unknown schema versions and fields."""
    if not isinstance(payload, Mapping):
        raise TypeError("A HistoryPy dataset must be a JSON object")
    if payload.get("schema") != SCHEMA_NAME:
        raise ValueError(f"Expected schema {SCHEMA_NAME!r}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported HistoryPy schema version: {payload.get('schema_version')!r}"
        )
    allowed = {
        "schema", "schema_version", "metadata", "sources", "claims", "events",
        "people", "places", "civilizations", "organizations", "relationships",
        "evidence",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"Unknown dataset field(s): {', '.join(sorted(unknown))}")

    def records(name: str, record_type: type[T], **options: Any) -> tuple[T, ...]:
        raw = payload.get(name, [])
        if not isinstance(raw, list):
            raise TypeError(f"Dataset field {name!r} must be a JSON array")
        return tuple(_record_from_dict(record_type, item, **options) for item in raw)

    metadata = payload.get("metadata", {})
    if not isinstance(metadata, Mapping) or any(
        not isinstance(key, str) or not isinstance(value, str)
        for key, value in metadata.items()
    ):
        raise TypeError("metadata must be an object containing only string keys and values")

    dataset = HistoricalDataset(
        sources=records("sources", SourceRecord),
        claims=records(
            "claims", HistoricalClaim, tuple_fields=("subject_ids", "event_ids")
        ),
        events=records(
            "events", HistoricalEvent,
            tuple_fields=("place_ids", "source_ids", "tags"),
            date_fields=("date",),
        ),
        people=records(
            "people", HistoricalPerson,
            tuple_fields=("aliases", "occupations", "source_ids"),
            date_fields=("birth_date", "death_date"),
        ),
        places=records(
            "places", HistoricalPlace,
            tuple_fields=("parent_place_ids", "aliases", "source_ids"),
        ),
        civilizations=records(
            "civilizations", HistoricalCivilization,
            tuple_fields=("region_place_ids", "predecessor_ids", "languages", "source_ids"),
            date_fields=("start_date", "end_date"),
        ),
        organizations=records(
            "organizations", HistoricalOrganization,
            tuple_fields=(
                "place_ids", "member_person_ids", "parent_organization_ids", "source_ids"
            ),
            date_fields=("founded", "dissolved"),
        ),
        relationships=records(
            "relationships", HistoricalRelationship,
            tuple_fields=("source_ids",),
            date_fields=("valid_from", "valid_to"),
        ),
        evidence=records("evidence", EvidenceLink),
        metadata=dict(metadata),
    )
    if validate:
        dataset.require_valid()
    return dataset


def dataset_to_json(dataset: HistoricalDataset, *, indent: int | None = 2) -> str:
    """Serialize a dataset to deterministic, UTF-8-friendly JSON text."""
    return json.dumps(
        dataset_to_dict(dataset),
        ensure_ascii=False,
        indent=indent,
        sort_keys=True,
    )


def dataset_from_json(payload: str, *, validate: bool = True) -> HistoricalDataset:
    """Parse JSON text into a HistoryPy dataset."""
    return dataset_from_dict(json.loads(payload), validate=validate)


def save_dataset(
    dataset: HistoricalDataset,
    path: str | Path,
    *,
    indent: int | None = 2,
    validate: bool = True,
) -> None:
    """Write a dataset to a UTF-8 JSON file."""
    if validate:
        dataset.require_valid()
    Path(path).write_text(dataset_to_json(dataset, indent=indent) + "\n", encoding="utf-8")


def load_dataset(
    path: str | Path, *, validate: bool = True
) -> HistoricalDataset:
    """Read a HistoryPy JSON dataset from a UTF-8 file."""
    payload = Path(path).read_text(encoding="utf-8")
    return dataset_from_json(payload, validate=validate)
