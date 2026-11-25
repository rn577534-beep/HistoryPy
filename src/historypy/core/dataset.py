"""Validated in-memory container for a HistoryPy research dataset."""

from __future__ import annotations

from dataclasses import dataclass, field

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
    HistoricalEvent,
    SourceRecord,
)


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A machine-readable dataset validation finding."""

    code: str
    message: str
    record_id: str | None = None
    field: str | None = None


@dataclass(frozen=True, slots=True)
class HistoricalDataset:
    """A self-contained collection of records with referential-integrity checks.

    Construction preserves the supplied records. Call validate() to inspect
    missing references and duplicate identifiers; validation never silently
    drops or rewrites historical data.
    """

    sources: tuple[SourceRecord, ...] = ()
    claims: tuple[HistoricalClaim, ...] = ()
    events: tuple[HistoricalEvent, ...] = ()
    people: tuple[HistoricalPerson, ...] = ()
    places: tuple[HistoricalPlace, ...] = ()
    civilizations: tuple[HistoricalCivilization, ...] = ()
    organizations: tuple[HistoricalOrganization, ...] = ()
    relationships: tuple[HistoricalRelationship, ...] = ()
    evidence: tuple[EvidenceLink, ...] = ()
    metadata: dict[str, str] = field(default_factory=dict)

    def validate(self) -> list[ValidationIssue]:
        """Return all detectable identifier and reference problems."""
        issues: list[ValidationIssue] = []
        collections = {
            "source": self.sources,
            "claim": self.claims,
            "event": self.events,
            "person": self.people,
            "place": self.places,
            "civilization": self.civilizations,
            "organization": self.organizations,
            "relationship": self.relationships,
        }
        indexes: dict[str, dict[str, object]] = {}
        for kind, records in collections.items():
            index: dict[str, object] = {}
            for record in records:
                record_id = record.id
                if record_id in index:
                    issues.append(ValidationIssue(
                        "duplicate_id", f"Duplicate {kind} id: {record_id}", record_id
                    ))
                else:
                    index[record_id] = record
            indexes[kind] = index

        source_ids = set(indexes["source"])
        source_adjacency: dict[str, tuple[str, ...]] = {}
        for source in self.sources:
            source_adjacency[source.id] = tuple(source.derived_from_source_ids)
            for parent_id in source.derived_from_source_ids:
                if parent_id not in source_ids:
                    issues.append(ValidationIssue(
                        "missing_derived_source",
                        f"Unknown derived-from source id: {parent_id}",
                        source.id, "derived_from_source_ids"
                    ))
        source_visited: set[str] = set()
        source_active: list[str] = []
        source_positions: dict[str, int] = {}
        for source_id in source_adjacency:
            if source_id in source_visited:
                continue
            stack = [(source_id, iter(source_adjacency[source_id]))]
            source_active.append(source_id)
            source_positions[source_id] = 0
            source_visited.add(source_id)
            while stack:
                node, neighbors = stack[-1]
                try:
                    neighbor = next(neighbors)
                except StopIteration:
                    stack.pop()
                    source_positions.pop(node, None)
                    source_active.pop()
                    continue
                if neighbor not in source_adjacency:
                    continue
                if neighbor in source_positions:
                    cycle = source_active[source_positions[neighbor]:] + [neighbor]
                    issues.append(ValidationIssue(
                        "source_derivation_cycle",
                        f"Circular source derivation: {' -> '.join(cycle)}",
                        node, "derived_from_source_ids"
                    ))
                elif neighbor not in source_visited:
                    source_visited.add(neighbor)
                    source_positions[neighbor] = len(source_active)
                    source_active.append(neighbor)
                    stack.append((neighbor, iter(source_adjacency[neighbor])))
        claim_ids = set(indexes["claim"])
        event_ids = set(indexes["event"])
        person_ids = set(indexes["person"])
        place_ids = set(indexes["place"])
        civilization_ids = set(indexes["civilization"])
        organization_ids = set(indexes["organization"])
        all_entity_ids = (
            person_ids | place_ids | civilization_ids | organization_ids | event_ids
        )
        entity_records = (
            ("event", self.events),
            ("person", self.people),
            ("place", self.places),
            ("civilization", self.civilizations),
            ("organization", self.organizations),
        )
        first_entity_kind: dict[str, str] = {}
        for kind, records in entity_records:
            for record in records:
                previous_kind = first_entity_kind.get(record.id)
                if previous_kind is not None and previous_kind != kind:
                    issues.append(ValidationIssue(
                        "duplicate_entity_id",
                        f"Entity id {record.id!r} is shared by {previous_kind} and {kind}",
                        record.id,
                    ))
                else:
                    first_entity_kind[record.id] = kind


        def detect_hierarchy_cycles(
            kind: str, records: tuple[object, ...], reference_field: str
        ) -> None:
            adjacency = {
                record.id: tuple(
                    ref for ref in getattr(record, reference_field)
                    if ref in {item.id for item in records}
                )
                for record in records
            }
            visited: set[str] = set()
            active: list[str] = []
            active_positions: dict[str, int] = {}
            reported: set[frozenset[str]] = set()

            def visit(node: str) -> None:
                visited.add(node)
                active_positions[node] = len(active)
                active.append(node)
                for neighbor in adjacency[node]:
                    if neighbor in active_positions:
                        cycle = active[active_positions[neighbor]:] + [neighbor]
                        identity = frozenset(cycle[:-1])
                        if identity not in reported:
                            reported.add(identity)
                            issues.append(ValidationIssue(
                                "hierarchy_cycle",
                                f"Circular {kind} hierarchy: {' -> '.join(cycle)}",
                                node,
                                reference_field,
                            ))
                    elif neighbor not in visited:
                        visit(neighbor)
                active.pop()
                active_positions.pop(node)
            
            for record_id in adjacency:
                if record_id not in visited:
                    visit(record_id)

        detect_hierarchy_cycles("place", self.places, "parent_place_ids")
        detect_hierarchy_cycles(
            "civilization", self.civilizations, "predecessor_ids"
        )
        detect_hierarchy_cycles(
            "organization", self.organizations, "parent_organization_ids"
        )

        def check_sources(record: object, record_id: str, source_refs: tuple[str, ...]) -> None:
            for source_id in source_refs:
                if source_id not in source_ids:
                    issues.append(ValidationIssue(
                        "missing_source", f"Unknown source id: {source_id}",
                        record_id, "source_ids"
                    ))

        for record in self.events:
            check_sources(record, record.id, record.source_ids)
            for place_id in record.place_ids:
                if place_id not in place_ids:
                    issues.append(ValidationIssue(
                        "missing_place", f"Unknown place id: {place_id}",
                        record.id, "place_ids"
                    ))
        for record in self.people:
            check_sources(record, record.id, record.source_ids)
        for record in self.places:
            check_sources(record, record.id, record.source_ids)
            for parent_id in record.parent_place_ids:
                if parent_id not in place_ids:
                    issues.append(ValidationIssue(
                        "missing_parent_place", f"Unknown parent place id: {parent_id}",
                        record.id, "parent_place_ids"
                    ))
        for record in self.civilizations:
            check_sources(record, record.id, record.source_ids)
            for place_id in record.region_place_ids:
                if place_id not in place_ids:
                    issues.append(ValidationIssue(
                        "missing_region", f"Unknown region place id: {place_id}",
                        record.id, "region_place_ids"
                    ))
            for predecessor_id in record.predecessor_ids:
                if predecessor_id not in civilization_ids:
                    issues.append(ValidationIssue(
                        "missing_predecessor",
                        f"Unknown predecessor civilization id: {predecessor_id}",
                        record.id, "predecessor_ids"
                    ))
        for record in self.organizations:
            check_sources(record, record.id, record.source_ids)
            for place_id in record.place_ids:
                if place_id not in place_ids:
                    issues.append(ValidationIssue(
                        "missing_place", f"Unknown place id: {place_id}",
                        record.id, "place_ids"
                    ))
            for person_id in record.member_person_ids:
                if person_id not in person_ids:
                    issues.append(ValidationIssue(
                        "missing_person", f"Unknown person id: {person_id}",
                        record.id, "member_person_ids"
                    ))
            for parent_id in record.parent_organization_ids:
                if parent_id not in organization_ids:
                    issues.append(ValidationIssue(
                        "missing_parent_organization",
                        f"Unknown parent organization id: {parent_id}",
                        record.id, "parent_organization_ids"
                    ))
        for record in self.relationships:
            check_sources(record, record.id, record.source_ids)
            for endpoint, field_name in (
                (record.subject_id, "subject_id"), (record.object_id, "object_id")
            ):
                if endpoint not in all_entity_ids:
                    issues.append(ValidationIssue(
                        "missing_relationship_endpoint",
                        f"Unknown relationship endpoint id: {endpoint}",
                        record.id, field_name
                    ))
        for link in self.evidence:
            if link.claim_id not in claim_ids:
                issues.append(ValidationIssue(
                    "missing_claim", f"Unknown claim id: {link.claim_id}",
                    link.claim_id, "claim_id"
                ))
            if link.source_id not in source_ids:
                issues.append(ValidationIssue(
                    "missing_source", f"Unknown source id: {link.source_id}",
                    link.claim_id, "source_id"
                ))
        for record in self.claims:
            for event_id in record.event_ids:
                if event_id not in event_ids:
                    issues.append(ValidationIssue(
                        "missing_event", f"Unknown event id: {event_id}",
                        record.id, "event_ids"
                    ))
            for subject_id in record.subject_ids:
                if subject_id not in all_entity_ids:
                    issues.append(ValidationIssue(
                        "missing_subject", f"Unknown subject id: {subject_id}",
                        record.id, "subject_ids"
                    ))
        return issues

    def is_valid(self) -> bool:
        """Return True only when validate() finds no issues."""
        return not self.validate()

    def require_valid(self) -> None:
        """Raise ValueError with a compact summary if the dataset is invalid."""
        issues = self.validate()
        if issues:
            summary = "; ".join(
                f"{issue.code}: {issue.message}" for issue in issues[:10]
            )
            if len(issues) > 10:
                summary += f"; and {len(issues) - 10} more issue(s)"
            raise ValueError(f"HistoricalDataset is invalid: {summary}")
