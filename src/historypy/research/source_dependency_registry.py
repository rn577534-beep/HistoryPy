"""Reviewable source-genealogy assertions with conservative application rules.

Candidate or disputed genealogy never affects independence analysis. Only
researcher-verified assertions can be applied to a dataset's source metadata.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
from typing import Literal

from historypy.core.dataset import HistoricalDataset

DependencyType = Literal[
    "derived_from",
    "shared_witness",
    "shared_archive_record",
    "syndicated_from",
    "shared_dataset",
    "other_shared_evidence",
]
DependencyReviewStatus = Literal["candidate", "verified", "disputed", "rejected"]

_DEPENDENCY_TYPES = {
    "derived_from",
    "shared_witness",
    "shared_archive_record",
    "syndicated_from",
    "shared_dataset",
    "other_shared_evidence",
}
_SHARED_TYPES = _DEPENDENCY_TYPES - {"derived_from"}
_REVIEW_STATUSES = {"candidate", "verified", "disputed", "rejected"}


@dataclass(frozen=True, slots=True)
class SourceDependencyAssertion:
    """A cited assertion that two source records share a research origin."""

    assertion_id: str
    source_id: str
    related_source_id: str
    dependency_type: DependencyType
    evidence_source_id: str
    locator: str
    license: str
    review_status: DependencyReviewStatus = "candidate"
    shared_group_id: str | None = None
    reviewer: str | None = None
    reviewed_at: str | None = None
    note: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "assertion_id", "source_id", "related_source_id",
            "evidence_source_id", "locator", "license",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
        if self.source_id == self.related_source_id:
            raise ValueError("A source cannot depend on itself")
        if self.dependency_type not in _DEPENDENCY_TYPES:
            raise ValueError(f"Unsupported dependency_type: {self.dependency_type}")
        if self.review_status not in _REVIEW_STATUSES:
            raise ValueError(f"Unsupported review_status: {self.review_status}")
        if self.dependency_type in _SHARED_TYPES:
            if (
                not isinstance(self.shared_group_id, str)
                or not self.shared_group_id.strip()
            ):
                raise ValueError(
                    "shared dependency types require a shared_group_id"
                )
        elif self.shared_group_id is not None:
            raise ValueError("derived_from assertions cannot set shared_group_id")
        if self.review_status == "verified":
            if not isinstance(self.reviewer, str) or not self.reviewer.strip():
                raise ValueError("verified assertions require a reviewer")
            if not self.reviewed_at:
                raise ValueError("verified assertions require reviewed_at")
        if self.reviewed_at:
            try:
                parsed = date.fromisoformat(self.reviewed_at)
            except ValueError as exc:
                raise ValueError("reviewed_at must use YYYY-MM-DD") from exc
            if parsed.isoformat() != self.reviewed_at:
                raise ValueError("reviewed_at must use YYYY-MM-DD")


class SourceDependencyRegistry:
    """Versioned registry for cited, human-reviewed source genealogy."""

    schema = "historypy.source-dependency-registry"
    schema_version = 1

    def __init__(
        self,
        dataset: HistoricalDataset,
        assertions: tuple[SourceDependencyAssertion, ...] | list[SourceDependencyAssertion],
        *,
        registry_version: str,
        dataset_version: str,
    ) -> None:
        if not isinstance(dataset, HistoricalDataset):
            raise TypeError("dataset must be a HistoricalDataset")
        dataset.require_valid()
        if (
            not isinstance(registry_version, str) or not registry_version.strip()
            or not isinstance(dataset_version, str) or not dataset_version.strip()
        ):
            raise ValueError("registry_version and dataset_version cannot be empty")
        if any(not isinstance(row, SourceDependencyAssertion) for row in assertions):
            raise TypeError("assertions must contain SourceDependencyAssertion records")
        self.dataset = dataset
        self.assertions = tuple(assertions)
        self.registry_version = registry_version
        self.dataset_version = dataset_version
        source_ids = {source.id for source in dataset.sources}
        assertion_ids = [row.assertion_id for row in self.assertions]
        if len(assertion_ids) != len(set(assertion_ids)):
            raise ValueError("assertion_id values must be unique")
        for row in self.assertions:
            for source_id in (row.source_id, row.related_source_id, row.evidence_source_id):
                if source_id not in source_ids:
                    raise ValueError(
                        f"Unknown source id in dependency assertion {row.assertion_id}: "
                        f"{source_id}"
                    )

    @property
    def verified_assertions(self) -> tuple[SourceDependencyAssertion, ...]:
        return tuple(
            row for row in self.assertions if row.review_status == "verified"
        )

    def apply_verified(self) -> HistoricalDataset:
        """Return a new dataset with only verified genealogy assertions applied."""
        source_map = {source.id: source for source in self.dataset.sources}
        for row in self.verified_assertions:
            source = source_map[row.source_id]
            related = source_map[row.related_source_id]
            if row.dependency_type == "derived_from":
                source_map[row.source_id] = replace(
                    source,
                    derived_from_source_ids=tuple(sorted(
                        set(source.derived_from_source_ids) | {row.related_source_id}
                    )),
                )
            else:
                group_id = row.shared_group_id
                source_map[row.source_id] = replace(
                    source,
                    shared_evidence_group_ids=tuple(sorted(
                        set(source.shared_evidence_group_ids) | {group_id}
                    )),
                )
                source_map[row.related_source_id] = replace(
                    related,
                    shared_evidence_group_ids=tuple(sorted(
                        set(related.shared_evidence_group_ids) | {group_id}
                    )),
                )
        return replace(
            self.dataset,
            sources=tuple(source_map[source.id] for source in self.dataset.sources),
        )

    def to_dict(self) -> dict[str, object]:
        """Return a deterministic JSON-compatible registry payload."""
        return {
            "schema": self.schema,
            "schema_version": self.schema_version,
            "registry_version": self.registry_version,
            "dataset_version": self.dataset_version,
            "assertions": [
                asdict(row) for row in sorted(
                    self.assertions, key=lambda item: item.assertion_id
                )
            ],
        }

    @classmethod
    def from_dict(
        cls, dataset: HistoricalDataset, payload: object
    ) -> SourceDependencyRegistry:
        """Load a strict, versioned source-dependency registry."""
        if not isinstance(payload, dict):
            raise TypeError("A source dependency registry must be a dictionary")
        allowed = {
            "schema", "schema_version", "registry_version", "dataset_version",
            "assertions",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(
                f"Unknown registry field(s): {', '.join(sorted(unknown))}"
            )
        if payload.get("schema") != cls.schema:
            raise ValueError(f"Expected schema {cls.schema!r}")
        if payload.get("schema_version") != cls.schema_version:
            raise ValueError(
                f"Unsupported source dependency registry schema version: "
                f"{payload.get('schema_version')!r}"
            )
        rows = payload.get("assertions")
        if not isinstance(rows, list):
            raise TypeError("assertions must be a list")
        allowed_fields = set(SourceDependencyAssertion.__dataclass_fields__)
        assertions = []
        for row in rows:
            if not isinstance(row, dict):
                raise TypeError("Each dependency assertion must be a dictionary")
            extra = set(row) - allowed_fields
            if extra:
                raise ValueError(
                    f"Unknown dependency assertion field(s): {', '.join(sorted(extra))}"
                )
            assertions.append(SourceDependencyAssertion(**row))
        return cls(
            dataset,
            assertions,
            registry_version=payload.get("registry_version", ""),
            dataset_version=payload.get("dataset_version", ""),
        )


__all__ = [
    "DependencyReviewStatus",
    "DependencyType",
    "SourceDependencyAssertion",
    "SourceDependencyRegistry",
]
