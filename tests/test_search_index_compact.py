import pytest

from historypy import DatasetSearchIndex, HistoricalDataset, HistoricalPerson, search_dataset


def test_compact_search_index_matches_linear_search_for_queries_and_filters():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="p1", name="Bengal maritime scholar"),
        HistoricalPerson(id="p2", name="Bengal maritime merchant"),
        HistoricalPerson(id="p3", name="Bengal administrator"),
    ))
    index = DatasetSearchIndex.build(dataset)

    for query in ("Bengal maritime", "scholar", "ar", "missing phrase", ""):
        for kinds in (None, ("person",), ("event",)):
            assert index.search(query, kinds=kinds, limit=None) == search_dataset(
                dataset, query, kinds=kinds, limit=None
            )


def test_compact_search_index_postings_are_read_only():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="p1", name="Maritime archive"),
    ))
    index = DatasetSearchIndex.build(dataset)

    posting = index.postings["mar"]
    assert posting.readonly is True
    with pytest.raises(TypeError):
        posting[0] = 10
    with pytest.raises(TypeError):
        index.postings["mar"] = ()
