from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    SourceRecord,
    analyze_claim_source_independence,
    audit_source_independence,
)


def _dataset(sources, evidence_source_ids):
    return HistoricalDataset(
        sources=tuple(sources),
        claims=(HistoricalClaim(id="claim-1", statement="A testable claim."),),
        evidence=tuple(
            EvidenceLink(
                claim_id="claim-1",
                source_id=source_id,
                relation="supports",
                locator="page 1",
            )
            for source_id in evidence_source_ids
        ),
    )


def test_syndicated_outlets_in_one_shared_group_are_not_counted_as_independent():
    dataset = _dataset(
        (
            SourceRecord(
                id="wire", title="Wire dispatch", source_type="primary",
                shared_evidence_group_ids=("dispatch-42",),
            ),
            SourceRecord(
                id="paper-a", title="Newspaper A", source_type="secondary",
                shared_evidence_group_ids=("dispatch-42",),
            ),
            SourceRecord(
                id="paper-b", title="Newspaper B", source_type="secondary",
                shared_evidence_group_ids=("dispatch-42",),
            ),
        ),
        ("paper-a", "paper-b"),
    )

    report = analyze_claim_source_independence(dataset, "claim-1")

    assert report.status == "known_dependence"
    assert report.dependency_cluster_count == 1
    assert report.dependent_clusters[0].evidence_source_ids == ("paper-a", "paper-b")
    assert report.dependent_clusters[0].bridge_source_ids == ("wire",)
    assert report.unknown_source_ids == ()


def test_transitive_derivation_through_a_non_cited_source_is_detected():
    dataset = _dataset(
        (
            SourceRecord(
                id="book-a", title="Book A", source_type="secondary",
                derived_from_source_ids=("archive-report",),
            ),
            SourceRecord(
                id="archive-report", title="Archive report", source_type="primary",
                derived_from_source_ids=("witness-record",),
            ),
            SourceRecord(
                id="book-b", title="Book B", source_type="secondary",
            ),
            SourceRecord(
                id="witness-record", title="Witness record", source_type="primary",
            ),
        ),
        ("book-a", "witness-record"),
    )

    report = analyze_claim_source_independence(dataset, "claim-1")

    assert report.status == "known_dependence"
    assert report.dependent_clusters[0].evidence_source_ids == (
        "book-a", "witness-record"
    )
    assert report.dependent_clusters[0].bridge_source_ids == (
        "archive-report",
    )
    assert any(
        edge.relation == "derived_from"
        for edge in report.dependent_clusters[0].dependency_edges
    )


def test_sources_without_dependency_metadata_are_unknown_not_independent():
    dataset = _dataset(
        (
            SourceRecord(id="source-a", title="A", source_type="primary"),
            SourceRecord(id="source-b", title="B", source_type="primary"),
        ),
        ("source-a", "source-b"),
    )

    report = analyze_claim_source_independence(dataset, "claim-1")

    assert report.status == "dependence_unknown"
    assert report.dependent_clusters == ()
    assert report.unknown_source_ids == ("source-a", "source-b")


def test_mixed_known_dependency_and_unknown_source_is_reported_separately():
    dataset = _dataset(
        (
            SourceRecord(
                id="source-a", title="A", source_type="secondary",
                derived_from_source_ids=("source-b",),
            ),
            SourceRecord(id="source-b", title="B", source_type="primary"),
            SourceRecord(id="source-c", title="C", source_type="primary"),
        ),
        ("source-a", "source-b", "source-c"),
    )

    report = analyze_claim_source_independence(dataset, "claim-1")

    assert report.status == "known_dependence_and_unknown"
    assert report.dependent_clusters[0].evidence_source_ids == ("source-a", "source-b")
    assert report.unknown_source_ids == ("source-c",)


def test_audit_reports_empty_claims_and_rejects_unknown_claim_ids():
    dataset = HistoricalDataset(
        claims=(
            HistoricalClaim(id="claim-empty", statement="No evidence yet."),
            HistoricalClaim(id="claim-with-evidence", statement="Evidence exists."),
        ),
        sources=(SourceRecord(id="s1", title="Source", source_type="primary"),),
        evidence=(
            EvidenceLink(
                claim_id="claim-with-evidence",
                source_id="s1",
                relation="supports",
            ),
        ),
    )

    report = audit_source_independence(dataset)

    assert report.claims_with_evidence == 1
    assert report.claims_with_known_dependence == 0
    assert report.claims_with_unknown_dependence == 1
    assert report.for_claim("claim-empty").status == "no_evidence"

    try:
        analyze_claim_source_independence(dataset, "missing")
    except KeyError:
        pass
    else:
        raise AssertionError("Unknown claim IDs must raise KeyError")
