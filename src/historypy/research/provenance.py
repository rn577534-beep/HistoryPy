"""Dataset-level source provenance and coverage reports."""
from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset


@dataclass(frozen=True, slots=True)
class DatasetProvenanceReport:
    """Counts recorded source links without scoring credibility or truth."""
    source_usage_counts: tuple[tuple[str, int], ...]
    orphan_source_ids: tuple[str, ...]
    claims_without_evidence: tuple[str, ...]
    records_without_sources: tuple[tuple[str, int], ...]
    evidence_relation_counts: tuple[tuple[str, int], ...]
    potential_source_dependency_pairs: tuple[tuple[str, str, str], ...] = ()

    @property
    def linked_source_count(self) -> int:
        return sum(count > 0 for _, count in self.source_usage_counts)

    @property
    def total_source_links(self) -> int:
        return sum(count for _, count in self.source_usage_counts)


def audit_dataset_provenance(dataset: HistoricalDataset) -> DatasetProvenanceReport:
    """Summarize source references across all record types deterministically."""
    usage = {source.id: 0 for source in dataset.sources}
    records_without: list[tuple[str, int]] = []
    collections = (
        ("event", dataset.events), ("person", dataset.people), ("place", dataset.places),
        ("civilization", dataset.civilizations), ("organization", dataset.organizations),
        ("relationship", dataset.relationships),
    )
    for kind, records in collections:
        missing = 0
        for record in records:
            source_ids = record.source_ids
            if not source_ids:
                missing += 1
            for source_id in source_ids:
                if source_id in usage:
                    usage[source_id] += 1
        records_without.append((kind, missing))

    for link in dataset.evidence:
        if link.source_id in usage:
            usage[link.source_id] += 1

    relation_names = ("supports", "contradicts", "contextualizes", "mentions")
    relation_counts = tuple(sorted(
        (relation, sum(link.relation == relation for link in dataset.evidence))
        for relation in relation_names
    ))
    claims_with_evidence = {link.claim_id for link in dataset.evidence}
    sorted_usage = tuple(sorted(usage.items()))
    dependency_pairs: set[tuple[str, str, str]] = set()
    for source in dataset.sources:
        for parent_id in source.derived_from_source_ids:
            if parent_id in usage:
                dependency_pairs.add((source.id, parent_id, "derived_from"))
    group_members: dict[str, list[str]] = {}
    for source in dataset.sources:
        for group_id in source.shared_evidence_group_ids:
            group_members.setdefault(group_id, []).append(source.id)
    for group_id, members in group_members.items():
        ordered_members = sorted(set(members))
        for index, source_id in enumerate(ordered_members):
            for related_id in ordered_members[index + 1:]:
                dependency_pairs.add((
                    source_id, related_id, f"shared_evidence_group:{group_id}"
                ))
    return DatasetProvenanceReport(
        source_usage_counts=sorted_usage,
        orphan_source_ids=tuple(source_id for source_id, count in sorted_usage if count == 0),
        claims_without_evidence=tuple(
            claim.id for claim in dataset.claims if claim.id not in claims_with_evidence
        ),
        records_without_sources=tuple(records_without),
        evidence_relation_counts=relation_counts,
        potential_source_dependency_pairs=tuple(sorted(dependency_pairs)),
    )
