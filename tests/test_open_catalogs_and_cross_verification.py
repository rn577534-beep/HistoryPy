from historypy import (
    CrossVerificationReport,
    GDELTNewsSearch,
    GuardianNewsSearch,
    GutendexSearch,
    HistoricalClaim,
    HistoricalDataset,
    OpenLibrarySearch,
    cross_verify_claim,
)
from historypy.integrations import open_catalogs
from historypy.integrations.historical_apis import ExternalRecord


def test_open_library_maps_bibliographic_metadata(monkeypatch):
    monkeypatch.setattr(open_catalogs, "_request_json", lambda *a, **k: {
        "docs": [{
            "key": "/works/OL1W",
            "title": "History of an Empire",
            "author_name": ["A. Historian"],
            "first_publish_year": 1901,
            "subject": ["history", "empire"],
            "language": ["eng"],
        }]
    })
    result = OpenLibrarySearch().search("empire", limit=5)
    assert result[0].provider == "Open Library"
    assert result[0].external_id == "/works/OL1W"
    assert result[0].creator == "A. Historian"
    assert "history" in result[0].description
    assert result[0].url == "https://openlibrary.org/works/OL1W"


def test_gutendex_search_maps_public_domain_catalog_metadata(monkeypatch):
    monkeypatch.setattr(open_catalogs, "_request_json", lambda *a, **k: {
        "results": [{
            "id": 123,
            "title": "A Public Domain Book",
            "authors": [{"name": "Writer"}],
            "subjects": ["History"],
            "bookshelves": ["History"],
            "languages": ["en"],
        }]
    })
    result = GutendexSearch().search("history", limit=2)
    assert result[0].external_id == "123"
    assert result[0].creator == "Writer"
    assert "public-domain" in result[0].license.lower()


def test_gutendex_iter_search_is_bounded_and_paginates(monkeypatch):
    pages = iter([
        {"results": [{"id": 1, "title": "One"}], "next": "https://gutendex.com/books/?page=2"},
        {"results": [{"id": 2, "title": "Two"}], "next": None},
    ])
    monkeypatch.setattr(open_catalogs, "_request_json", lambda *a, **k: next(pages))
    monkeypatch.setattr(open_catalogs.time, "sleep", lambda *_: None)
    result = list(GutendexSearch().iter_search("history", max_records=2))
    assert [item.external_id for item in result] == ["1", "2"]


def test_gdelt_news_maps_article_metadata_without_article_text(monkeypatch):
    seen = {}

    def fake_request(url, **kwargs):
        seen["url"] = url
        return {"articles": [{
            "url": "https://news.example/article",
            "title": "Historical discovery reported",
            "domain": "news.example",
            "language": "English",
            "sourceCountry": "United States",
            "seendate": "20261127T120000Z",
        }]}

    monkeypatch.setattr(open_catalogs, "_request_json", fake_request)
    result = GDELTNewsSearch().search("historical discovery", timespan="7d")
    assert result[0].provider == "GDELT DOC 2.0"
    assert result[0].url == "https://news.example/article"
    assert "copyright" in result[0].license.lower()
    assert "maxrecords=10" in seen["url"]


def test_guardian_requires_key_and_returns_short_metadata(monkeypatch):
    import pytest

    with pytest.raises(ValueError, match="GUARDIAN_API_KEY"):
        GuardianNewsSearch()
    monkeypatch.setattr(open_catalogs, "_request_json", lambda *a, **k: {
        "response": {"results": [{
            "webUrl": "https://theguardian.com/article",
            "webTitle": "A news report",
            "webPublicationDate": "2026-11-27T10:00:00Z",
            "sectionName": "History",
            "fields": {"trailText": "A short trail text", "byline": "Reporter"},
        }]}
    })
    result = GuardianNewsSearch("test-key").search("history")
    assert result[0].creator == "Reporter"
    assert result[0].description == "A short trail text"
    assert "Non-commercial" in result[0].license


class FakeProvider:
    def __init__(self, name, title, url):
        self.name = name
        self.title = title
        self.url = url

    def search(self, query, *, limit=10):
        return (ExternalRecord(
            provider=self.name,
            external_id=self.url,
            title=self.title,
            description="metadata only",
            url=self.url,
            creator=None,
            date=None,
            language="en",
            license="metadata only",
            retrieved_at="2026-11-27T00:00:00+00:00",
        ),)


def test_cross_verify_claim_searches_providers_and_does_not_auto_import():
    dataset = HistoricalDataset(
        claims=(HistoricalClaim("c1", "A historic event"),),
    )
    report = cross_verify_claim(dataset, "c1", [
        FakeProvider("catalog-a", "A historic event", "https://a.example/1"),
        FakeProvider("catalog-b", "A historic event", "https://b.example/2"),
    ])
    assert isinstance(report, CrossVerificationReport)
    assert report.candidate_count == 2
    assert report.successful_provider_count == 2
    assert len(report.duplicate_candidates) == 1
    assert any("not automatically" in note for note in report.notes)


def test_cross_verify_rejects_unknown_claim():
    import pytest

    with pytest.raises(KeyError, match="Unknown claim"):
        cross_verify_claim(HistoricalDataset(), "missing", [])
