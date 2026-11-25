"""Versioned, citation-backed multilingual entity alias assertions.

Verified aliases are kept separate from candidates and disputed forms. Exact
lookup preserves homonyms and never merges entity records.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date
from typing import Literal

from historypy.core.dataset import HistoricalDataset

EntityKind = Literal["person", "place", "civilization", "organization"]
AliasType = Literal[
    "transliteration", "historical_name", "exonym", "endonym", "title",
    "spelling_variant", "other",
]
ReviewStatus = Literal["candidate", "verified", "disputed", "rejected"]

_ALIAS_TYPES = {
    "transliteration", "historical_name", "exonym", "endonym", "title",
    "spelling_variant", "other",
}
_REVIEW_STATUSES = {"candidate", "verified", "disputed", "rejected"}
_LANGUAGE_RE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")
_SCRIPT_RE = re.compile(r"^[A-Za-z]{4}$")
_ENTITY_COLLECTIONS = {
    "person": "people",
    "place": "places",
    "civilization": "civilizations",
    "organization": "organizations",
}


def _iso_date(value: str, field_name: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be an ISO date string")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD") from exc
    if parsed.isoformat() != value:
        raise ValueError(f"{field_name} must use YYYY-MM-DD")


def _normalize_alias(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", plain, flags=re.UNICODE))


@dataclass(frozen=True, slots=True)
class AliasAssertion:
    """One sourced assertion that an alias refers to a canonical entity."""

    alias_id: str
    entity_kind: EntityKind
    entity_id: str
    alias: str
    language: str
    alias_type: AliasType
    source_id: str
    locator: str
    license: str
    review_status: ReviewStatus = "candidate"
    script: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "alias_id", "entity_id", "alias", "language", "source_id",
            "locator", "license",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
        if self.entity_kind not in _ENTITY_COLLECTIONS:
            raise ValueError(f"Unsupported entity_kind: {self.entity_kind}")
        if self.alias_type not in _ALIAS_TYPES:
            raise ValueError(f"Unsupported alias_type: {self.alias_type}")
        if self.review_status not in _REVIEW_STATUSES:
            raise ValueError(f"Unsupported review_status: {self.review_status}")
        if not _LANGUAGE_RE.fullmatch(self.language):
            raise ValueError("language must be a valid BCP-47-style language tag")
        if self.script is not None and not _SCRIPT_RE.fullmatch(self.script):
            raise ValueError("script must be a four-letter ISO 15924 code")
        if self.valid_from:
            _iso_date(self.valid_from, "valid_from")
        if self.valid_to:
            _iso_date(self.valid_to, "valid_to")
        if self.valid_from and self.valid_to and self.valid_from > self.valid_to:
            raise ValueError("valid_from cannot be later than valid_to")
        if self.review_status == "verified":
            if not self.reviewer or not self.reviewer.strip():
                raise ValueError("verified aliases require a reviewer")
            if not self.reviewed_at:
                raise ValueError("verified aliases require reviewed_at")
            _iso_date(self.reviewed_at, "reviewed_at")


@dataclass(frozen=True, slots=True)
class AliasMatch:
    """Exact alias match with its evidence and ambiguity preserved."""

    alias_id: str
    entity_kind: str
    entity_id: str
    canonical_name: str
    alias: str
    language: str
    alias_type: str
    review_status: str
    source_id: str
    locator: str
    ambiguity_count: int

    @property
    def ambiguous(self) -> bool:
        return self.ambiguity_count > 1


class AliasRegistry:
    """Immutable, versioned alias index with evidence and review-state filters."""

    schema = "historypy.alias-registry"
    schema_version = 1

    def __init__(
        self,
        dataset: HistoricalDataset,
        assertions: tuple[AliasAssertion, ...] | list[AliasAssertion],
        *,
        registry_version: str,
        dataset_version: str,
    ) -> None:
        if not registry_version.strip() or not dataset_version.strip():
            raise ValueError("registry_version and dataset_version cannot be empty")
        self.dataset = dataset
        self.assertions = tuple(assertions)
        if any(not isinstance(item, AliasAssertion) for item in self.assertions):
            raise TypeError("assertions must contain AliasAssertion records")
        self.registry_version = registry_version
        self.dataset_version = dataset_version
        ids = [item.alias_id for item in self.assertions]
        if len(ids) != len(set(ids)):
            raise ValueError("alias_id values must be unique")
        self._entities: dict[tuple[str, str], str] = {}
        self._sources = {source.id for source in dataset.sources}
        for kind, collection_name in _ENTITY_COLLECTIONS.items():
            for entity in getattr(dataset, collection_name):
                self._entities[(kind, entity.id)] = entity.name
        index: dict[str, list[AliasAssertion]] = {}
        for item in self.assertions:
            if (item.entity_kind, item.entity_id) not in self._entities:
                raise ValueError(
                    f"Unknown {item.entity_kind} entity id: {item.entity_id}"
                )
            if item.source_id not in self._sources:
                raise ValueError(f"Unknown source id for alias {item.alias_id}: {item.source_id}")
            normalized = _normalize_alias(item.alias)
            if normalized:
                index.setdefault(normalized, []).append(item)
        self._index = {
            key: tuple(sorted(rows, key=lambda row: (row.entity_kind, row.entity_id, row.alias_id)))
            for key, rows in index.items()
        }

    def resolve(
        self,
        query: str,
        *,
        language: str | None = None,
        include_unverified: bool = False,
    ) -> tuple[AliasMatch, ...]:
        """Resolve exact aliases; verified-only by default and never fuzzy-merges.

        include_unverified exposes candidate and disputed assertions for review.
        Rejected assertions are never returned.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query cannot be empty")
        if language is not None and not _LANGUAGE_RE.fullmatch(language):
            raise ValueError("language must be a valid BCP-47-style language tag")
        if not isinstance(include_unverified, bool):
            raise TypeError("include_unverified must be a bool")
        rows = self._index.get(_normalize_alias(query), ())
        selected = tuple(
            row for row in rows
            if row.review_status != "rejected"
            and (row.review_status == "verified" or include_unverified)
            and (language is None or row.language.casefold() == language.casefold())
        )
        ambiguity = len({(row.entity_kind, row.entity_id) for row in selected})
        return tuple(
            AliasMatch(
                alias_id=row.alias_id,
                entity_kind=row.entity_kind,
                entity_id=row.entity_id,
                canonical_name=self._entities[(row.entity_kind, row.entity_id)],
                alias=row.alias,
                language=row.language,
                alias_type=row.alias_type,
                review_status=row.review_status,
                source_id=row.source_id,
                locator=row.locator,
                ambiguity_count=ambiguity,
            )
            for row in selected
        )

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic, JSON-compatible versioned registry payload."""
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "registry_version": self.registry_version,
            "dataset_version": self.dataset_version,
            "assertions": [
                asdict(item) for item in sorted(self.assertions, key=lambda row: row.alias_id)
            ],
        }

    @classmethod
    def from_dict(
        cls, dataset: HistoricalDataset, payload: object
    ) -> AliasRegistry:
        """Load a registry payload while rejecting unknown fields and versions."""
        if not isinstance(payload, dict):
            raise TypeError("An alias registry must be a dictionary")
        allowed = {
            "schema", "schema_version", "registry_version", "dataset_version",
            "assertions",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"Unknown alias registry field(s): {', '.join(sorted(unknown))}")
        if payload.get("schema") != cls.schema:
            raise ValueError(f"Expected schema {cls.schema!r}")
        if payload.get("schema_version") != cls.schema_version:
            raise ValueError(f"Unsupported alias registry schema version: {payload.get('schema_version')!r}")
        rows = payload.get("assertions")
        if not isinstance(rows, list):
            raise TypeError("assertions must be a list")
        allowed_assertion_fields = set(AliasAssertion.__dataclass_fields__)
        assertions = []
        for row in rows:
            if not isinstance(row, dict):
                raise TypeError("Each alias assertion must be a dictionary")
            extra = set(row) - allowed_assertion_fields
            if extra:
                raise ValueError(f"Unknown alias assertion field(s): {', '.join(sorted(extra))}")
            assertions.append(AliasAssertion(**row))
        return cls(
            dataset,
            assertions,
            registry_version=payload.get("registry_version", ""),
            dataset_version=payload.get("dataset_version", ""),
        )


__all__ = [
    "AliasAssertion",
    "AliasMatch",
    "AliasRegistry",
]
