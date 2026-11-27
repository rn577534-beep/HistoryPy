# Claim-level evidence citations

HistoryPy can audit the traceability metadata attached to each claim/evidence
link and render a conservative Markdown citation from recorded fields.

## Audit citation metadata

```python
from historypy import audit_evidence_citations

# Audit every evidence link in the dataset.
audit = audit_evidence_citations(dataset)
print(audit.total_links)
print(audit.complete_links)
print(audit.coverage)
for finding in audit.findings:
    print(
        finding.evidence_index,
        finding.claim_id,
        finding.source_id,
        finding.code,
        finding.message,
    )

# Or audit only the evidence attached to one known claim.
claim_audit = audit_evidence_citations(dataset, claim_id="claim-001")
```

A citation is counted as complete when its evidence link has a locator and a
quotation, and its source record has an absolute HTTP(S) URL. Findings use
zero-based positions in dataset.evidence and stable codes:

- missing_locator
- missing_quotation
- missing_source_url
- invalid_source_url

An empty audit has coverage=None and is not considered complete. An unknown
claim ID raises KeyError.

## Render one recorded citation

```python
from historypy import format_evidence_citation

print(format_evidence_citation(dataset, evidence_index=0))
```

The formatter includes only metadata actually present in the source and
evidence records: creator, title, publisher, publication date, locator, URL,
access date, source ID, and evidence relation. It does not invent missing
bibliographic details.

## What this audit does not establish

This is a metadata and traceability check. It does not:

- open URLs or confirm that a page is currently available;
- prove that a quotation is transcribed accurately or appears at the locator;
- authenticate a document or establish its provenance;
- determine source reliability or independence;
- decide whether a historical claim is true.

A complete citation can still point to a misleading, misquoted, or unreliable
source. Researchers must inspect the original source and compare independent
evidence. For the existing dataset-wide locator/quotation/URL coverage report,
see audit_citation_completeness; for source-by-source claim analysis, see
analyze_claim_evidence and render_claim_report.
