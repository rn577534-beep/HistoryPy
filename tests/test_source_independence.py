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

def test_multiple_disconnected_dependency_families_remain_separate():
    dataset = _dataset(
        (
            SourceRecord(
                id="wire-a", title="Wire A", source_type="primary",
                shared_evidence_group_ids=("dispatch-a",),
            ),
            SourceRecord(
                id="paper-a", title="Paper A", source_type="secondary",
                shared_evidence_group_ids=("dispatch-a",),
            ),
            SourceRecord(
                id="wire-b", title="Wire B", source_type="primary",
                shared_evidence_group_ids=("dispatch-b",),
            ),
            SourceRecord(
                id="paper-b", title="Paper B", source_type="secondary",
                shared_evidence_group_ids=("dispatch-b",),
            ),
            SourceRecord(id="unknown", title="Unknown origin", source_type="other"),
        ),
        ("paper-a", "paper-b", "unknown"),
    )

    report = analyze_claim_source_independence(dataset, "claim-1")

    assert report.status == "known_dependence_and_unknown"
    assert [cluster.evidence_source_ids for cluster in report.dependent_clusters] == [
        ("paper-a",), ("paper-b",)
    ]
    assert [cluster.bridge_source_ids for cluster in report.dependent_clusters] == [
        ("wire-a",), ("wire-b",)
    ]
    assert report.unknown_source_ids == ("unknown",)


def test_transitive_shared_evidence_groups_preserve_intermediate_bridge():
    dataset = _dataset(
        (
            SourceRecord(
                id="source-a", title="A", source_type="secondary",
                shared_evidence_group_ids=("family-one",),
            ),
            SourceRecord(
                id="source-bridge", title="Bridge", source_type="primary",
                shared_evidence_group_ids=("family-one", "family-two"),
            ),
            SourceRecord(
                id="source-b", title="B", source_type="secondary",
                shared_evidence_group_ids=("family-two",),
            ),
        ),
        ("source-a", "source-b"),
    )

    report = analyze_claim_source_independence(dataset, "claim-1")

    assert report.status == "known_dependence"
    assert len(report.dependent_clusters) == 1
    cluster = report.dependent_clusters[0]
    assert cluster.evidence_source_ids == ("source-a", "source-b")
    assert cluster.bridge_source_ids == ("source-bridge",)
    assert {
        edge.relation for edge in cluster.dependency_edges
    } == {"shared_evidence_group:family-one", "shared_evidence_group:family-two"}


def test_circular_derivation_is_reported_by_dataset_validation():
    dataset = _dataset(
        (
            SourceRecord(
                id="source-a", title="A", source_type="secondary",
                derived_from_source_ids=("source-b",),
            ),
            SourceRecord(
                id="source-b", title="B", source_type="secondary",
                derived_from_source_ids=("source-a",),
            ),
        ),
        ("source-a", "source-b"),
    )

    issues = dataset.validate()
    report = analyze_claim_source_independence(dataset, "claim-1")

    assert any(issue.code == "source_derivation_cycle" for issue in issues)
    assert report.status == "known_dependence"
    assert report.dependent_clusters[0].evidence_source_ids == ("source-a", "source-b")


def test_missing_genealogy_parent_is_not_assumed_to_be_independent():
    dataset = _dataset(
        (
            SourceRecord(
                id="source-a", title="A", source_type="secondary",
                derived_from_source_ids=("not-in-dataset",),
            ),
        ),
        ("source-a",),
    )

    issues = dataset.validate()
    report = analyze_claim_source_independence(dataset, "claim-1")

    assert any(issue.code == "missing_derived_source" for issue in issues)
    assert report.status == "single_source_dependence_unknown"
    assert report.unknown_source_ids == ("source-a",)

