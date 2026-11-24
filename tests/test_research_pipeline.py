from historypy import (
    HistoricalClaim, HistoricalDataset, SourceRecord, EvidenceLink,
    ResearchPipeline, render_research_report,
)
from historypy.integrations import ExternalRecord


class FakeProvider:
    def search(self, query, *, limit=10):
        return (
            ExternalRecord(
                provider="Fixture", external_id=query, title=f"Record about {query}",
                description="fixture only", url=f"https://example.org/{query.replace(' ', '-')}",
                creator=None, date=None, language="en", license="CC0",
                retrieved_at="2026-01-01T00:00:00+00:00",
            ),
        )


class BrokenProvider:
    def search(self, query, *, limit=10):
        raise RuntimeError("offline")


def test_pipeline_runs_literal_query_clauses_and_collects_sources():
    dataset = HistoricalDataset(
        sources=(SourceRecord("s1", "Archive", "primary"),),
        claims=(HistoricalClaim("c1", "Harbor trade expanded."),),
        evidence=(EvidenceLink("c1", "s1", "supports", page="4"),),
    )
    report = ResearchPipeline(dataset, providers=(FakeProvider(),)).run(
        "harbor; trade", include_semantic=False
    )
    assert [item.task.query for item in report.tasks] == ["harbor", "trade"]
    assert len(report.external_records) == 2
    assert report.claim_analyses[0].claim_id == "c1"
    assert report.duplicate_candidates == ()
    rendered = render_research_report(report)
    assert "https://example.org/harbor" in rendered
    assert "Discovery output only" in rendered


def test_pipeline_reports_provider_failures_and_no_truth_claims():
    dataset = HistoricalDataset(
        sources=(SourceRecord("s1", "Archive", "primary"),),
        claims=(HistoricalClaim("c1", "A claim without evidence"),),
    )
    report = ResearchPipeline(dataset, providers=(BrokenProvider(),)).run(
        "unmatched-term", include_semantic=False
    )
    assert report.provider_failures
    assert any("failed" in gap for gap in report.gaps)
    assert any("No matching records" in gap for gap in report.gaps)
    assert "not automatically imported" in render_research_report(report)


def test_pipeline_validates_inputs_and_semantic_configuration():
    dataset = HistoricalDataset()
    pipeline = ResearchPipeline(dataset)
    try:
        pipeline.run("  ")
    except ValueError as exc:
        assert "query" in str(exc)
    else:
        raise AssertionError("empty query should fail")
    assert pipeline.run("unmatched", include_external=False).gaps
