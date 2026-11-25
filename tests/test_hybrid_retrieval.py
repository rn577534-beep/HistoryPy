from historypy import (
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    HistoricalPlace,
)
from historypy.research.bm25 import BM25SearchIndex
from historypy.research.hybrid import (
    EntityAwareSearchIndex,
    HybridSearchIndex,
    decompose_research_question,
)
from historypy.research.search_index import DatasetSearchIndex


def dataset():
    return HistoricalDataset(
        people=(HistoricalPerson(
            "p1", "Alexander the Great", aliases=("Alexander III", "Iskandar")
        ),),
        places=(HistoricalPlace(
            "pl1", "Constantinople", aliases=("Byzantium", "Istanbul")
        ),),
        events=(
            HistoricalEvent(
                "e1", "Siege of Tyre",
                HistoricalDate(earliest_year=-332, latest_year=-332, calendar="gregorian"),
                summary="Alexander the Great besieged the Phoenician city of Tyre.",
            ),
            HistoricalEvent(
                "e2", "Fall of Constantinople",
                HistoricalDate(earliest_year=1453, latest_year=1453, calendar="gregorian"),
                summary="Ottoman forces captured Constantinople, also called Byzantium.",
            ),
        ),
    )


def test_question_decomposition_only_splits_clear_multi_hop_patterns():
    result = decompose_research_question(
        "Who was Alexander the Great and when did he besiege Tyre?"
    )
    assert result.parts == (
        "Who was Alexander the Great", "when did he besiege Tyre"
    )
    assert decompose_research_question("Describe the siege of Tyre").parts == (
        "Describe the siege of Tyre",
    )
    assert len(decompose_research_question(
        "Compare Athens versus Sparta; what changed?"
    ).parts) == 3


def test_entity_alias_resolver_finds_canonical_and_historical_names():
    resolver = EntityAwareSearchIndex.build(dataset())
    matches = resolver.resolve("Was Iskandar connected to Byzantium?")
    assert {(item.kind, item.record_id) for item in matches} == {
        ("person", "p1"), ("place", "pl1")
    }
    assert resolver.resolve("Istanbul", kinds=("person",)) == ()


def test_hybrid_rrf_combines_trigram_and_bm25_with_stable_ranks():
    data = dataset()
    index = HybridSearchIndex(
        DatasetSearchIndex.build(data), BM25SearchIndex.build(data)
    )
    hits = index.search("Alexander Tyre", limit=5)
    assert hits[0].record_id == "e1"
    assert hits[0].bm25_rank == 1
    assert hits[0].trigram_rank == 1
    decomposed = index.search(
        "Who was Alexander the Great and when did he besiege Tyre?",
        decompose=True,
    )
    assert decomposed
    assert decomposed[0].record_id == "e1"


def test_hybrid_semantic_rank_is_optional_and_reported():
    from historypy.research.semantic import SemanticSearchIndex

    def embed(texts):
        return [(1.0, 0.0) if "tyre" in text.casefold() else (0.0, 1.0) for text in texts]

    data = dataset()
    semantic = SemanticSearchIndex.build(data, embedder=embed, model_id="fixture")
    index = HybridSearchIndex(
        DatasetSearchIndex.build(data), BM25SearchIndex.build(data), semantic
    )
    hits = index.search("Tyre", embedder=embed)
    assert hits[0].record_id == "e1"
    assert hits[0].semantic_rank == 1
