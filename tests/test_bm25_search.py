import pytest

from historypy import BM25SearchIndex, HistoricalDataset, HistoricalPerson


def test_bm25_ranks_documents_by_term_coverage_and_accent_folds():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(
            id="p1", name="M. Blanc",
            description="Les réformes sont discutées pendant la séance parlementaire.",
        ),
        HistoricalPerson(
            id="p2", name="Budget speaker",
            description="Le budget est discuté au parlement.",
        ),
        HistoricalPerson(
            id="p3", name="Reform writer",
            description="Réformes administratives.",
        ),
    ))
    index = BM25SearchIndex.build(dataset)

    hits = index.search("reformes séance parlementaire", limit=None)

    assert hits[0].record_id == "p1"
    assert {hit.record_id for hit in hits} == {"p1", "p2", "p3"}
    assert "reformes" in hits[0].matched_terms


def test_bm25_supports_kind_filters_limits_and_validation():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="p1", name="Maritime scholar"),
    ))
    index = BM25SearchIndex.build(dataset)

    assert index.search("maritime", kinds=("event",)) == ()
    assert len(index.search("maritime", limit=1)) == 1
    assert index.search("unknown tokens") == ()
    with pytest.raises(TypeError):
        index.search(123)
    with pytest.raises(ValueError, match="k1"):
        BM25SearchIndex.build(dataset, k1=0)
    with pytest.raises(ValueError, match="b"):
        BM25SearchIndex.build(dataset, b=1.5)
