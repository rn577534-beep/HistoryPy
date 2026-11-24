import io
import json
from urllib.error import HTTPError

import pytest

from historypy.integrations import (
    EuropeanaSearch,
    ExternalRecord,
    InternetArchiveSearch,
    LibraryOfCongressSearch,
    MediaWikiSearch,
    ProviderError,
    WikidataSearch,
    historical_apis,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self.payload


def test_mediawiki_search_normalizes_metadata(monkeypatch):
    monkeypatch.setattr(
        historical_apis,
        "urlopen",
        lambda request, timeout: FakeResponse({
            "query": {"search": [{
                "pageid": 42, "title": "Ancient City",
                "snippet": "A <b>historic</b> settlement",
            }]}
        }),
    )
    result = MediaWikiSearch().search("ancient city")
    assert len(result) == 1
    assert result[0].external_id == "42"
    assert result[0].title == "Ancient City"
    assert result[0].url.endswith("/Ancient_City")


def test_wikidata_search_normalizes_entity(monkeypatch):
    monkeypatch.setattr(
        historical_apis,
        "urlopen",
        lambda request, timeout: FakeResponse({
            "search": [{
                "id": "Q123", "label": "Example",
                "description": "historical entity",
                "concepturi": "https://www.wikidata.org/entity/Q123",
            }]
        }),
    )
    result = WikidataSearch().search("Example")
    assert result[0].external_id == "Q123"
    assert result[0].license.startswith("CC0")


def test_europeana_requires_key(monkeypatch):
    monkeypatch.delenv("EUROPEANA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="EUROPEANA_API_KEY"):
        EuropeanaSearch()


def test_europeana_uses_api_key_header(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["key"] = request.get_header("X-api-key")
        return FakeResponse({
            "items": [{
                "id": "/123/item", "title": ["Manuscript"],
                "guid": "https://www.europeana.eu/item/123",
                "dcCreator": ["Unknown scribe"], "rights": ["CC0"],
            }]
        })

    monkeypatch.setattr(historical_apis, "urlopen", fake_urlopen)
    result = EuropeanaSearch("test-key").search("manuscript")
    assert captured["key"] == "test-key"
    assert result[0].title == "Manuscript"


def test_loc_and_archive_search_providers(monkeypatch):
    payloads = iter([
        {"results": [{"id": "https://loc.gov/item/1", "title": "LOC record"}]},
        {"response": {"docs": [{"identifier": "archive-item", "title": "Archive record"}]}},
    ])
    monkeypatch.setattr(
        historical_apis, "urlopen",
        lambda request, timeout: FakeResponse(next(payloads)),
    )
    assert LibraryOfCongressSearch().search("history")[0].title == "LOC record"
    assert InternetArchiveSearch().search("history")[0].url.endswith("/archive-item")


def test_invalid_query_and_limit_rejected():
    with pytest.raises(ValueError):
        MediaWikiSearch().search(" ")
    with pytest.raises(ValueError):
        WikidataSearch().search("history", limit=51)


def test_external_record_requires_identity():
    with pytest.raises(ValueError):
        ExternalRecord("", "", "", None, None, None, None, None, None, "now")


def test_http_failure_is_wrapped(monkeypatch):
    def fail(request, timeout):
        raise HTTPError(request.full_url, 503, "Unavailable", {}, io.BytesIO())

    monkeypatch.setattr(historical_apis, "urlopen", fail)
    with pytest.raises(ProviderError):
        MediaWikiSearch().search("history")
