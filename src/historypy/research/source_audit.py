"""Source-record metadata audits; never a source credibility score."""

from __future__ import annotations

from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import SourceRecord


@dataclass(frozen=True, slots=True)
class SourceMetadataAudit:
    """A transparent checklist of present and absent bibliographic metadata."""

    source_id: str
    title: str
    source_type: str
    present_fields: tuple[str, ...]
    missing_recommended_fields: tuple[str, ...]

    @property
    def has_locator(self) -> bool:
        """Whether a URL or archival/catalogue locator is recorded."""
        return "url" in self.present_fields or "archive_reference" in self.present_fields


def audit_source_record(source: SourceRecord) -> SourceMetadataAudit:
    """Report metadata gaps without inferring reliability or authenticity."""
    if not isinstance(source, SourceRecord):
        raise TypeError("source must be a SourceRecord")
    checks = (
        ("creator", source.creator),
        ("publication_date", source.publication_date),
        ("publisher", source.publisher),
        ("language", source.language),
        ("url_or_archive_reference", source.url or source.archive_reference),
        ("accessed_on", source.accessed_on),
    )
    present = tuple(name for name, value in checks if value)
    missing = tuple(name for name, value in checks if not value)
    return SourceMetadataAudit(
        source_id=source.id,
        title=source.title,
        source_type=source.source_type,
        present_fields=present,
        missing_recommended_fields=missing,
    )


def audit_dataset_sources(
    dataset: HistoricalDataset,
) -> tuple[SourceMetadataAudit, ...]:
    """Audit every source in dataset order; missing metadata is not a verdict."""
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    return tuple(audit_source_record(source) for source in dataset.sources)
