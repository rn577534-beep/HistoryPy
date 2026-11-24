from threading import Barrier

import pytest

from historypy.integrations import (
    ExternalRecord,
    compare_metadata,
    find_duplicate_candidates,
    search_all,
    to_source_record,
)


def record(provider, external_id, title, **kwargs):
    values = {
        "provider": provider,
        "external_id": external_id,
        "title": title,
        "description": None,
        "url": None,
        "creator": None,
        "date": None,
        "language": None,
        "license": None,
        "retrieved_at": "2026-11-24T00:00:00+00:00",
    }
    values.update(kwargs)
    return ExternalRecord(**values)


class GoodProvider:
    def search(self, query, *, limit=10):
        return (record("A", "1", "Ancient Bengal"),)


class BrokenProvider:
    def search(self, query, *, limit=10):
        raise RuntimeError("temporary outage")


def test_search_all_preserves_success_when_provider_fails():
    report = search_all([GoodProvider(), BrokenProvider()], "Bengal")
    assert len(report.records) == 1
    assert report.successful_provider_count == 1
    assert report.failures[0].provider == "BrokenProvider"


def test_duplicate_candidates_require_exact_normalized_match():
    items = [
        record("A", "1", "Ancient Bengal"),
        record("B", "2", "Ancient-Bengal"),
        record("C", "3", "Different title"),
    ]
    groups = find_duplicate_candidates(items)
    assert len(groups) == 1
    assert groups[0].reason == "title"
    assert len(groups[0].records) == 2


def test_duplicate_urls_are_grouped_for_review():
    items = [
        record("A", "1", "First title", url="https://example.org/item/1"),
        record("B", "2", "Second title", url="https://example.org/item/1/"),
    ]
    groups = find_duplicate_candidates(items)
    assert len(groups) == 1
    assert groups[0].reason == "url"


def test_metadata_conflicts_are_reported_not_resolved():
    items = [
        record("A", "1", "Title A", creator="Author A", date="1200"),
        record("B", "2", "Title B", creator="Author B", date="1250"),
    ]
    conflicts = compare_metadata(items)
    assert {item.field for item in conflicts} == {"title", "creator", "date"}


def test_selected_record_converts_to_source_with_provenance():
    item = record(
        "Wikidata", "Q1", "Historical figure",
        url="https://www.wikidata.org/entity/Q1",
        license="CC0", language="en",
    )
    source = to_source_record(item, source_id="wikidata-q1")
    assert source.id == "wikidata-q1"
    assert source.publisher == "Wikidata"
    assert "external id=Q1" in source.notes
    assert "CC0" in source.notes


def test_aggregation_rejects_invalid_query_and_limit():
    with pytest.raises(ValueError):
        search_all([GoodProvider()], " ")
    with pytest.raises(ValueError):
        search_all([GoodProvider()], "Bengal", limit_per_provider=0)


def test_search_all_runs_independent_providers_concurrently():
    barrier = Barrier(2)

    class CoordinatedProvider:
        def search(self, query, *, limit=10):
            barrier.wait(timeout=2)
            return (record("parallel", query, "Parallel result"),)

    report = search_all(
        [CoordinatedProvider(), CoordinatedProvider()], "history", max_workers=2
    )
    assert len(report.records) == 2
    assert report.failures == ()
