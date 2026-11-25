"""Conservative claim-level analysis of known source dependence.

Known shared origins are grouped so repeated reporting is not mistaken for
independent corroboration. Missing dependency metadata is always reported as
unknown; absence of a recorded link is never interpreted as independence.
"""

from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset


@dataclass(frozen=True, slots=True)
class SourceDependency:
    """A recorded relationship that makes two sources non-independent."""

    source_id: str
    related_source_id: str
    relation: str


@dataclass(frozen=True, slots=True)
class DependencyCluster:
    """Evidence sources connected by one or more known dependency paths.

    bridge_source_ids are intermediate sources in a dependency path that are
    not themselves directly linked as evidence for the claim.
    """

    evidence_source_ids: tuple[str, ...]
    bridge_source_ids: tuple[str, ...]
    dependency_edges: tuple[SourceDependency, ...]


@dataclass(frozen=True, slots=True)
class ClaimSourceIndependenceReport:
    """Claim-level source genealogy summary, deliberately without truth scores."""

    claim_id: str
    evidence_source_ids: tuple[str, ...]
    dependent_clusters: tuple[DependencyCluster, ...]
    unknown_source_ids: tuple[str, ...]
    status: str

    @property
    def known_dependent_source_count(self) -> int:
        return sum(len(cluster.evidence_source_ids) for cluster in self.dependent_clusters)

    @property
    def dependency_cluster_count(self) -> int:
        return len(self.dependent_clusters)


@dataclass(frozen=True, slots=True)
class DatasetSourceIndependenceReport:
    """Dataset-wide counts and claim reports for known/unknown source dependence."""

    claim_reports: tuple[ClaimSourceIndependenceReport, ...]
    claims_with_evidence: int
    claims_with_known_dependence: int
    claims_with_unknown_dependence: int

    def for_claim(self, claim_id: str) -> ClaimSourceIndependenceReport:
        """Return a report for a claim or raise KeyError if it was not analyzed."""
        for report in self.claim_reports:
            if report.claim_id == claim_id:
                return report
        raise KeyError(f"Unknown claim id: {claim_id}")


def _dependency_edges(dataset: HistoricalDataset) -> tuple[SourceDependency, ...]:
    source_ids = {source.id for source in dataset.sources}
    edges: set[SourceDependency] = set()
    group_members: dict[str, set[str]] = {}

    for source in dataset.sources:
        for parent_id in source.derived_from_source_ids:
            if parent_id in source_ids and parent_id != source.id:
                edges.add(SourceDependency(source.id, parent_id, "derived_from"))
        for group_id in source.shared_evidence_group_ids:
            group_members.setdefault(group_id, set()).add(source.id)

    for group_id, members in group_members.items():
        ordered = sorted(members)
        for index, source_id in enumerate(ordered):
            for related_id in ordered[index + 1:]:
                edges.add(SourceDependency(
                    source_id, related_id, f"shared_evidence_group:{group_id}"
                ))

    return tuple(sorted(
        edges,
        key=lambda edge: (edge.source_id, edge.related_source_id, edge.relation),
    ))


def analyze_claim_source_independence(
    dataset: HistoricalDataset, claim_id: str
) -> ClaimSourceIndependenceReport:
    """Group evidence sources connected by recorded source-genealogy links.

    Direct and transitive derivation links and shared-evidence groups are
    treated as known dependence. Intermediate sources are retained as bridge
    nodes. Sources without a documented path to another evidence source are
    classified as unknown, never independent.

    This is a metadata audit, not an authenticity, reliability, or truth test.
    """
    if not any(claim.id == claim_id for claim in dataset.claims):
        raise KeyError(f"Unknown claim id: {claim_id}")

    source_ids = {source.id for source in dataset.sources}
    evidence_source_ids = tuple(sorted({
        link.source_id
        for link in dataset.evidence
        if link.claim_id == claim_id and link.source_id in source_ids
    }))
    if not evidence_source_ids:
        return ClaimSourceIndependenceReport(
            claim_id, (), (), (), "no_evidence"
        )

    edges = _dependency_edges(dataset)
    adjacency: dict[str, set[str]] = {source_id: set() for source_id in source_ids}
    for edge in edges:
        adjacency[edge.source_id].add(edge.related_source_id)
        adjacency[edge.related_source_id].add(edge.source_id)

    evidence_set = set(evidence_source_ids)
    visited: set[str] = set()
    clusters: list[DependencyCluster] = []
    clustered_evidence: set[str] = set()

    for start in evidence_source_ids:
        if start in visited:
            continue
        component: set[str] = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            pending.extend(sorted(adjacency[current] - visited, reverse=True))

        component_evidence = tuple(sorted(component & evidence_set))
        if len(component_evidence) < 2:
            continue

        component_edges = tuple(
            edge for edge in edges
            if edge.source_id in component and edge.related_source_id in component
        )
        clusters.append(DependencyCluster(
            evidence_source_ids=component_evidence,
            bridge_source_ids=tuple(sorted(component - evidence_set)),
            dependency_edges=component_edges,
        ))
        clustered_evidence.update(component_evidence)

    clusters.sort(key=lambda cluster: cluster.evidence_source_ids)
    unknown = tuple(sorted(evidence_set - clustered_evidence))

    if clusters and unknown:
        status = "known_dependence_and_unknown"
    elif clusters:
        status = "known_dependence"
    elif len(evidence_source_ids) == 1:
        status = "single_source_dependence_unknown"
    else:
        status = "dependence_unknown"

    return ClaimSourceIndependenceReport(
        claim_id=claim_id,
        evidence_source_ids=evidence_source_ids,
        dependent_clusters=tuple(clusters),
        unknown_source_ids=unknown,
        status=status,
    )


def audit_source_independence(
    dataset: HistoricalDataset,
) -> DatasetSourceIndependenceReport:
    """Analyze every claim and summarize known dependence versus unknowns."""
    reports = tuple(
        analyze_claim_source_independence(dataset, claim.id)
        for claim in sorted(dataset.claims, key=lambda item: item.id)
    )
    with_evidence = sum(bool(report.evidence_source_ids) for report in reports)
    known = sum(bool(report.dependent_clusters) for report in reports)
    unknown = sum(bool(report.unknown_source_ids) for report in reports)
    return DatasetSourceIndependenceReport(
        claim_reports=reports,
        claims_with_evidence=with_evidence,
        claims_with_known_dependence=known,
        claims_with_unknown_dependence=unknown,
    )
