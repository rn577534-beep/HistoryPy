"""Explainable dataset quality findings; no historical-truth scoring."""
from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.research.source_audit import audit_dataset_sources


@dataclass(frozen=True, slots=True)
class QualityFinding:
    code: str
    severity: str
    message: str
    record_id: str | None = None


@dataclass(frozen=True, slots=True)
class DatasetQualityReport:
    findings: tuple[QualityFinding, ...]

    @property
    def counts_by_severity(self) -> dict[str, int]:
        return {
            level: sum(item.severity == level for item in self.findings)
            for level in ("error", "warning", "info")
        }


def assess_dataset_quality(dataset: HistoricalDataset) -> DatasetQualityReport:
    """Report structural/provenance gaps without asserting a claim is true or false."""
    findings: list[QualityFinding] = []
    for issue in dataset.validate():
        findings.append(QualityFinding(
            issue.code, "error", issue.message, issue.record_id
        ))
    for audit in audit_dataset_sources(dataset):
        if audit.missing_recommended_fields:
            findings.append(QualityFinding(
                "source_metadata_incomplete", "warning",
                "Missing recommended catalogue fields: " + ", ".join(audit.missing_recommended_fields),
                audit.source_id,
            ))
    linked_claims = {item.claim_id for item in dataset.evidence}
    for claim in dataset.claims:
        if claim.id not in linked_claims:
            findings.append(QualityFinding(
                "claim_without_evidence", "warning",
                "Claim has no linked evidence record; this is a research gap, not proof of falsity.",
                claim.id,
            ))
    sourced_event_ids = {item.id for item in dataset.events if item.source_ids}
    for event in dataset.events:
        if event.id not in sourced_event_ids:
            findings.append(QualityFinding(
                "event_without_source", "warning",
                "Event has no directly linked source IDs.", event.id,
            ))
    return DatasetQualityReport(tuple(sorted(
        findings, key=lambda item: (item.severity, item.code, item.record_id or "")
    )))
