from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalResearchWorkflow,
    ResearchQueryVariant,
    SourceRecord,
    select_external_sources,
    render_integrated_research_report,
)
from historypy.integrations import ExternalRecord


class FixtureProvider:
    def search(self, query, *, limit=10):
        return (
            ExternalRecord(
                provider="Fixture",
                external_id=query.casefold().replace(" ", "-"),
                title=f"Archive catalogue: {query}",
                description="Metadata fixture; not source text.",
                url="https://example.org/catalogue",
                creator="Test archivist",
                date="1971",
                language="en",
                license="CC0",
                retrieved_at="2026-01-01T00:00:00+00:00",
            ),
        )


def _dataset():
    return HistoricalDataset(
        sources=(SourceRecord(
            "archive-1", "Research archive", "archival",
            url="https://example.org/archive",
        ),),
        claims=(HistoricalClaim("claim-1", "A documented historical claim."),),
        evidence=(EvidenceLink(
            "claim-1", "archive-1", "supports", page="12",
            quotation="A short recorded quotation.",
        ),),
    )


def test_integrated_workflow_runs_original_and_researcher_supplied_language_queries():
    dataset = _dataset()
    workflow = HistoricalResearchWorkflow(dataset, providers=(FixtureProvider(),))
    report = workflow.run(
        "historical event",
        query_variants=(
            ResearchQueryVariant("ঐতিহাসিক ঘটনা", "bn", "translation"),
            ResearchQueryVariant("tarikh-i waqia", "ur-Latn", "transliteration"),
        ),
        include_semantic=False,
        verify_sources=False,
        dossier_title="Research dossier",
    )
    assert [item.language for item in report.discoveries] == ["und", "bn", "ur-Latn"]
    assert len(report.external_records) == 3
    assert report.dossier.title == "Research dossier"
    assert report.source_verification is None
    assert "none was auto-imported as evidence" in " ".join(report.gaps)
    rendered = render_integrated_research_report(report)
    assert "Multilingual discovery" in rendered
    assert "Historical dossier" in rendered
    assert "not verdicts on historical truth" in rendered


def test_external_catalogue_records_are_only_imported_after_explicit_selection():
    dataset = _dataset()
    report = HistoricalResearchWorkflow(
        dataset, providers=(FixtureProvider(),)
    ).run("historical event", include_semantic=False, verify_sources=False)
    assert len(dataset.sources) == 1
    selected = select_external_sources(
        dataset, report, (("Fixture", "historical-event"),)
    )
    assert len(selected.sources) == 2
    imported = selected.sources[-1]
    assert imported.id.startswith("external-")
    assert "not claim evidence" in imported.notes
    assert selected.evidence == dataset.evidence


def test_workflow_deduplicates_query_variants_and_rejects_unreviewed_types():
    dataset = _dataset()
    workflow = HistoricalResearchWorkflow(dataset, providers=(FixtureProvider(),))
    report = workflow.run(
        "same query",
        query_variants=(ResearchQueryVariant(" SAME   QUERY ", "en"),),
        include_semantic=False,
        verify_sources=False,
    )
    assert len(report.discoveries) == 1
