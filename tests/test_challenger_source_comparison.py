from historypy import (
    audit_citation_completeness,
    audit_dataset_provenance,
    render_event_source_comparison,
)
from historypy.examples.challenger_source_comparison import build_challenger_dataset


def test_challenger_case_study_keeps_report_testimony_and_derivative_review_distinct():
    dataset = build_challenger_dataset()
    report = render_event_source_comparison(
        dataset, "challenger_51l_1986"
    )

    assert "Presidential Commission" in report
    assert "Volume V, May 2 session" in report
    assert "House Report 99-1016" in report
    assert "The decision to launch the Challenger was flawed." in report
    assert "No, it wasn't. It was kind of a one-liner" in report
    assert "page: 2754" in report

    provenance = audit_dataset_provenance(dataset)
    assert (
        "challenger_hearing_volume_v",
        "rogers_commission_report",
        "shared_evidence_group:presidential-commission-record",
    ) in provenance.potential_source_dependency_pairs
    assert (
        "house_report_99_1016",
        "rogers_commission_report",
        "derived_from",
    ) in provenance.potential_source_dependency_pairs


def test_challenger_case_study_has_complete_traceable_citations():
    audit = audit_citation_completeness(build_challenger_dataset())
    assert audit.total_evidence_links > 0
    assert audit.complete_citation_coverage == 1.0
    assert audit.missing_locator_indices == ()
    assert audit.missing_quotation_indices == ()
    assert audit.missing_source_url_indices == ()
