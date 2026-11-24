import pytest

from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    SourceRecord,
)
from historypy.research import SemanticSearchIndex, analyze_claim_evidence


def sample_dataset():
    sources = (
        SourceRecord("primary-1", "Harbor archive", "primary"),
        SourceRecord("secondary-1", "Modern study", "secondary"),
    )
    claims = (HistoricalClaim("claim-1", "The harbor supported maritime trade."),)
    events = (
        HistoricalEvent(
            "harbor", "Harbor treaty",
            HistoricalDate(earliest_year=1200, calendar="gregorian"),
            summary="Maritime trade and coastal diplomacy",
        ),
        HistoricalEvent(
            "fort", "Mountain fort",
            HistoricalDate(earliest_year=1250, calendar="gregorian"),
            summary="Defensive structure in the highlands",
        ),
    )
    evidence = (
        EvidenceLink("claim-1", "primary-1", "supports", page="12"),
        EvidenceLink("claim-1", "secondary-1", "contradicts"),
        EvidenceLink("claim-1", "primary-1", "contextualizes", locator="catalogue 4"),
    )
    return HistoricalDataset(
        sources=sources, claims=claims, events=events, evidence=evidence
    )


def toy_embedder(texts):
    """Deterministic fixture only; not a production semantic model."""
    vectors = []
    for text in texts:
        normalized = text.casefold()
        vectors.append((1.0, 0.0) if any(
            term in normalized for term in ("harbor", "maritime", "trade", "coastal")
        ) else (0.0, 1.0))
    return vectors


def test_semantic_index_ranks_by_supplied_embedding_similarity():
    dataset = sample_dataset()
    index = SemanticSearchIndex.build(
        dataset, embedder=toy_embedder, model_id="fixture-v1", batch_size=1
    )
    hits = index.search("coastal trade", embedder=toy_embedder, kinds=("event",))
    assert hits[0].record_id == "harbor"
    assert hits[0].similarity == pytest.approx(1.0)
    assert index.model_id == "fixture-v1"


def test_semantic_index_validates_embedding_shapes_and_dimensions():
    dataset = sample_dataset()
    with pytest.raises(ValueError, match="one vector"):
        SemanticSearchIndex.build(
            dataset, embedder=lambda texts: [], model_id="broken"
        )
    index = SemanticSearchIndex.build(
        dataset, embedder=toy_embedder, model_id="fixture-v1"
    )
    with pytest.raises(ValueError, match="dimensions"):
        index.search("query", embedder=lambda texts: [(1.0, 2.0, 3.0)])


def test_semantic_index_validates_threshold_and_empty_query():
    index = SemanticSearchIndex.build(
        sample_dataset(), embedder=toy_embedder, model_id="fixture-v1"
    )
    with pytest.raises(ValueError, match="query"):
        index.search("  ", embedder=toy_embedder)
    with pytest.raises(ValueError, match="between -1 and 1"):
        index.search("harbor", embedder=toy_embedder, min_similarity=2)


def test_claim_evidence_analysis_reports_coverage_without_truth_score():
    result = analyze_claim_evidence(sample_dataset(), "claim-1")
    assert result.assessment_status == "mixed"
    assert dict(result.relation_counts) == {
        "contextualizes": 1, "contradicts": 1, "supports": 1
    }
    assert dict(result.source_type_counts) == {"primary": 2, "secondary": 1}
    assert result.distinct_source_count == 2
    assert result.links_missing_locators == 1
    assert result.locator_coverage == pytest.approx(2 / 3)


def test_claim_evidence_analysis_handles_no_links_and_unknown_claim():
    dataset = HistoricalDataset(
        claims=(HistoricalClaim("empty", "A claim without evidence"),)
    )
    result = analyze_claim_evidence(dataset, "empty")
    assert result.total_links == 0
    assert result.locator_coverage is None
    with pytest.raises(KeyError, match="Unknown claim"):
        analyze_claim_evidence(dataset, "missing")
