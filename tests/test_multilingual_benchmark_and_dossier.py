from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    SourceRecord,
)
from historypy.research import (
    AliasAssertion,
    AliasRegistry,
    EntityAwareSearchIndex,
    build_historical_dossier,
    render_historical_dossier,
    run_retrieval_benchmark,
)
from historypy.research.semantic import SemanticSearchIndex


def _dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord(
                "source-a", "Chronicle A", "secondary",
                shared_evidence_group_ids=("same-origin",),
            ),
            SourceRecord(
                "source-b", "Chronicle B", "secondary",
                shared_evidence_group_ids=("same-origin",),
            ),
        ),
        claims=(HistoricalClaim(
            "claim-1", "The city changed hands.", event_ids=("event-1",)
        ),),
        evidence=(
            EvidenceLink("claim-1", "source-a", "supports", page="12"),
            EvidenceLink("claim-1", "source-b", "contradicts", page="14"),
        ),
        events=(HistoricalEvent(
            "event-1", "A disputed transition",
            HistoricalDate(
                earliest_year=1200, latest_year=1210, precision="decade",
                calendar="julian", circa=True, original_expression="around the early 13th century",
            ),
        ),),
        people=(HistoricalPerson("person-1", "Saladin"),),
    )


def test_semantic_benchmark_compares_all_four_systems_on_same_judgments():
    dataset = _dataset()

    def embedder(texts):
        return tuple((1.0, 0.0) if "city" in text.lower() else (0.0, 1.0) for text in texts)

    semantic_index = SemanticSearchIndex.build(
        dataset, embedder=embedder, model_id="test-multilingual-model"
    )
    report = run_retrieval_benchmark(
        dataset,
        [{"id": "q1", "query": "city transition", "relevant": ["event:event-1"]}],
        cutoff=5,
        bootstrap_samples=200,
        semantic_index=semantic_index,
        embedder=embedder,
    )
    assert {item.system for item in report.systems} == {
        "trigram", "bm25", "semantic", "hybrid_rrf"
    }
    assert all(item.query_count == 1 for item in report.systems)
    assert all(item.mean_latency_ms is not None for item in report.systems)
    assert all(
        item.intervals["recall_at_k"].samples == 200 for item in report.systems
    )


def test_semantic_benchmark_requires_index_and_embedder_together():
    import pytest

    with pytest.raises(ValueError, match="supplied together"):
        run_retrieval_benchmark(
            _dataset(),
            [{"id": "q1", "query": "city", "relevant": ["event:event-1"]}],
            embedder=lambda texts: tuple((1.0, 0.0) for _ in texts),
        )


def test_dossier_reports_evidence_balance_source_dependence_and_date_uncertainty():
    rendered = render_historical_dossier(build_historical_dossier(_dataset()))
    assert "1 supporting, 1 contradicting" in rendered
    assert "Source independence: `known_dependence`" in rendered
    assert "Dependent evidence sources: source-a, source-b" in rendered
    assert "Date uncertainty: precision: decade; approximate date" in rendered
    assert "source wording: around the early 13th century" in rendered


def test_verified_bengali_alias_resolves_to_canonical_english_entity_without_merging():
    dataset = _dataset()
    registry = AliasRegistry(
        dataset,
        (AliasAssertion(
            alias_id="saladin-bn",
            entity_kind="person",
            entity_id="person-1",
            alias="সালাহউদ্দিন আইয়ুবী",
            language="bn",
            alias_type="transliteration",
            source_id="source-a",
            locator="page 3",
            license="CC0",
            review_status="verified",
            reviewer="historian-1",
            reviewed_at="2026-01-01",
        ),),
        registry_version="1",
        dataset_version="dataset-1",
    )
    index = EntityAwareSearchIndex.build(dataset, alias_registry=registry)
    matches = index.resolve("সালাহউদ্দিন আইয়ুবী", language="bn")
    assert len(matches) == 1
    assert matches[0].canonical_name == "Saladin"
    assert matches[0].review_status == "verified"
    assert matches[0].source_id == "source-a"
    assert len(dataset.people) == 1
