"""Claim-level citation auditing and conservative citation rendering.

The audit checks recorded metadata and traceability. It does not fetch sources,
authenticate quotations, assess source reliability, or decide historical truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import EvidenceLink, SourceRecord


@dataclass(frozen=True, slots=True)
class CitationFinding:
    """One actionable citation metadata finding for an evidence link."""

    evidence_index: int
    claim_id: str
    source_id: str
    code: str
    message: str


@dataclass(frozen=True, slots=True)
class EvidenceCitationAudit:
    """Claim-level or dataset-level citation traceability audit."""

    total_links: int
    complete_links: int
    findings: tuple[CitationFinding, ...]

    @property
    def coverage(self) -> float | None:
        """Fraction of links with a locator, quotation, and valid HTTP(S) URL."""
        if not self.total_links:
            return None
        return self.complete_links / self.total_links

    @property
    def is_complete(self) -> bool:
        """Whether every audited evidence link has complete citation metadata."""
        return self.total_links > 0 and self.complete_links == self.total_links


def _has_locator(link: EvidenceLink) -> bool:
    return any(
        value and value.strip()
        for value in (
            link.locator,
            link.page,
            link.paragraph,
            link.archive_shelfmark,
            link.url_fragment,
            link.transcription_line,
            link.timecode,
        )
    )


def _is_http_url(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    try:
        parsed = urlsplit(value.strip())
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)
    except ValueError:
        return False


def audit_evidence_citations(
    dataset: HistoricalDataset,
    claim_id: str | None = None,
) -> EvidenceCitationAudit:
    """Audit evidence citations for missing locators, quotations, and valid URLs.

    Findings point to zero-based positions in dataset.evidence. When claim_id
    is supplied, only that known claim is audited. A link counts as complete
    only when all three traceability fields are present and the source URL is
    a syntactically valid HTTP(S) URL.

    This is a metadata audit, not live URL checking or source verification.
    """
    dataset.require_valid()
    known_claim_ids = {claim.id for claim in dataset.claims}
    if claim_id is not None and claim_id not in known_claim_ids:
        raise KeyError(f"Unknown claim id: {claim_id}")

    sources = {source.id: source for source in dataset.sources}
    selected = (
        (index, link)
        for index, link in enumerate(dataset.evidence)
        if claim_id is None or link.claim_id == claim_id
    )
    findings: list[CitationFinding] = []
    total = complete = 0

    for index, link in selected:
        total += 1
        source = sources[link.source_id]
        missing: list[tuple[str, str]] = []
        if not _has_locator(link):
            missing.append(("missing_locator", "No page, paragraph, shelfmark, line, timecode, or locator is recorded."))
        if not link.quotation or not link.quotation.strip():
            missing.append(("missing_quotation", "No source quotation or excerpt is recorded."))
        if not source.url or not source.url.strip():
            missing.append(("missing_source_url", "The source record has no URL."))
        elif not _is_http_url(source.url):
            missing.append(("invalid_source_url", "The source URL is not a valid absolute HTTP(S) URL."))

        if not missing:
            complete += 1
        findings.extend(
            CitationFinding(index, link.claim_id, link.source_id, code, message)
            for code, message in missing
        )

    return EvidenceCitationAudit(total, complete, tuple(findings))


def format_evidence_citation(
    dataset: HistoricalDataset,
    evidence_index: int,
) -> str:
    """Render one recorded evidence link as a conservative Markdown citation.

    Only fields present in the dataset are rendered. The function does not
    manufacture missing publication details or citation locators.
    """
    dataset.require_valid()
    if not isinstance(evidence_index, int) or isinstance(evidence_index, bool):
        raise TypeError("evidence_index must be an integer")
    if evidence_index < 0 or evidence_index >= len(dataset.evidence):
        raise IndexError("evidence_index is outside dataset.evidence")

    link = dataset.evidence[evidence_index]
    sources = {source.id: source for source in dataset.sources}
    source: SourceRecord = sources[link.source_id]
    parts = []
    if source.creator:
        parts.append(source.creator)
    parts.append(f"*{source.title}*")
    publication = " ".join(
        value for value in (source.publisher, source.publication_date) if value
    )
    if publication:
        parts.append(publication)

    locator = next(
        (
            f"{label} {value}"
            for label, value in (
                ("p.", link.page),
                ("para.", link.paragraph),
                ("shelfmark", link.archive_shelfmark),
                ("line", link.transcription_line),
                ("timecode", link.timecode),
                ("locator", link.locator),
                ("URL fragment", link.url_fragment),
            )
            if value and value.strip()
        ),
        None,
    )
    if locator:
        parts.append(locator)
    if source.url:
        parts.append(source.url)
    if source.accessed_on:
        parts.append(f"accessed {source.accessed_on}")

    return ", ".join(parts) + f" [source ID: {source.id}; relation: {link.relation}]"
