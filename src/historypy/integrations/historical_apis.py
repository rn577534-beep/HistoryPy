"""Read-only adapters for public historical and cultural-heritage APIs.

Only metadata and short descriptions are normalized. Full copyrighted texts are
not downloaded or copied. API credentials are read from environment variables.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ProviderError(RuntimeError):
    """An upstream provider request failed or returned an invalid response."""


@dataclass(frozen=True, slots=True)
class ExternalRecord:
    provider: str
    external_id: str
    title: str
    description: str | None
    url: str | None
    creator: str | None
    date: str | None
    language: str | None
    license: str | None
    retrieved_at: str

    def __post_init__(self) -> None:
        if not self.provider.strip() or not self.external_id.strip() or not self.title.strip():
            raise ValueError("provider, external_id, and title cannot be empty")


def _request_json(url: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    request_headers = {
        "Accept": "application/json",
        "User-Agent": "HistoryPy/0.2 (historical research; contact repository maintainers)",
    }
    if headers:
        request_headers.update(headers)
    request = Request(url, headers=request_headers)
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Historical data provider request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise ProviderError("Provider returned a non-object JSON response")
    return payload


def _retrieved_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        value = "; ".join(str(item) for item in value if item)
    if isinstance(value, dict):
        value = value.get("value") or value.get("label")
    text = str(value).strip()
    return text or None


class MediaWikiSearch:
    """Search Wikipedia or another MediaWiki site; no API key required."""

    def __init__(self, language: str = "en", project: str = "wikipedia") -> None:
        if not language.isalpha() or not project.isalpha():
            raise ValueError("language and project must contain letters only")
        self.endpoint = f"https://{language}.{project}.org/w/api.php"
        self.provider = f"{language}.{project}"

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        params = urlencode({
            "action": "query", "list": "search", "srsearch": query,
            "srlimit": limit, "format": "json", "utf8": 1,
        })
        payload = _request_json(f"{self.endpoint}?{params}")
        results = payload.get("query", {}).get("search", [])
        retrieved = _retrieved_at()
        return tuple(
            ExternalRecord(
                provider=self.provider,
                external_id=str(item.get("pageid", item.get("title", ""))),
                title=str(item.get("title", "Untitled")),
                description=_clean(item.get("snippet")),
                url=f"https://{self.provider}.org/wiki/{str(item.get('title', '')).replace(' ', '_')}",
                creator=None, date=None, language=self.endpoint.split("//")[1].split(".")[0],
                license="Wikipedia content license; verify page-specific attribution",
                retrieved_at=retrieved,
            )
            for item in results if item.get("title")
        )


class WikidataSearch:
    """Search Wikidata entities using its public Action API; no key required."""

    endpoint = "https://www.wikidata.org/w/api.php"

    def search(self, query: str, *, limit: int = 10, language: str = "en") -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        params = urlencode({
            "action": "wbsearchentities", "search": query, "language": language,
            "uselang": language, "limit": limit, "format": "json",
        })
        payload = _request_json(f"{self.endpoint}?{params}")
        retrieved = _retrieved_at()
        return tuple(
            ExternalRecord(
                provider="Wikidata",
                external_id=str(item.get("id", "")),
                title=str(item.get("label") or item.get("id") or "Untitled"),
                description=_clean(item.get("description")),
                url=_clean(item.get("concepturi")),
                creator=None, date=None, language=language, license="CC0 (Wikidata structured data)",
                retrieved_at=retrieved,
            )
            for item in payload.get("search", []) if item.get("id")
        )


class EuropeanaSearch:
    """Search Europeana cultural-heritage records; requires a free API key.

    Set EUROPEANA_API_KEY in the environment or pass api_key explicitly.
    """

    endpoint = "https://api.europeana.eu/record/v2/search.json"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("EUROPEANA_API_KEY")
        if not self.api_key:
            raise ValueError("Set EUROPEANA_API_KEY or pass api_key")

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params = urlencode({"query": query, "rows": limit, "profile": "minimal"})
        payload = _request_json(
            f"{self.endpoint}?{params}",
            headers={"X-Api-Key": self.api_key},
        )
        retrieved = _retrieved_at()
        return tuple(
            ExternalRecord(
                provider="Europeana",
                external_id=str(item.get("id", "")),
                title=_clean(item.get("title")) or "Untitled",
                description=_clean(item.get("dcDescription")),
                url=_clean(item.get guid := "guid") if False else _clean(item.get("guid")),
                creator=_clean(item.get("dcCreator")),
                date=_clean(item.get("year")),
                language=_clean(item.get("language")),
                license=_clean(item.get("rights")),
                retrieved_at=retrieved,
            )
            for item in payload.get("items", []) if item.get("id")
        )


class LibraryOfCongressSearch:
    """Search the Library of Congress JSON API; no API key required."""

    endpoint = "https://www.loc.gov/search/"

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params = urlencode({"q": query, "fo": "json", "c": limit})
        payload = _request_json(f"{self.endpoint}?{params}")
        retrieved = _retrieved_at()
        return tuple(
            ExternalRecord(
                provider="Library of Congress",
                external_id=str(item.get("id") or item.get("url") or ""),
                title=_clean(item.get("title")) or "Untitled",
                description=_clean(item.get("description")),
                url=_clean(item.get("url")),
                creator=_clean(item.get("contributor")),
                date=_clean(item.get("date")),
                language=_clean(item.get("language")),
                license=_clean(item.get("rights")),
                retrieved_at=retrieved,
            )
            for item in payload.get("results", []) if item.get("id") or item.get("url")
        )


class InternetArchiveSearch:
    """Search Internet Archive metadata; no API key required."""

    endpoint = "https://archive.org/advancedsearch.php"

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params = urlencode([
            ("q", query), ("fl[]", "identifier"), ("fl[]", "title"),
            ("fl[]", "description"), ("fl[]", "date"), ("fl[]", "creator"),
            ("rows", str(limit)), ("page", "1"), ("output", "json"),
        ])
        payload = _request_json(f"{self.endpoint}?{params}")
        docs = payload.get("response", {}).get("docs", [])
        retrieved = _retrieved_at()
        return tuple(
            ExternalRecord(
                provider="Internet Archive",
                external_id=str(item.get("identifier", "")),
                title=_clean(item.get("title")) or str(item.get("identifier", "Untitled")),
                description=_clean(item.get("description")),
                url=f"https://archive.org/details/{item.get('identifier')}",
                creator=_clean(item.get("creator")),
                date=_clean(item.get("date")),
                language=None, license=None, retrieved_at=retrieved,
            )
            for item in docs if item.get("identifier")
        )


__all__ = [
    "EuropeanaSearch", "ExternalRecord", "InternetArchiveSearch",
    "LibraryOfCongressSearch", "MediaWikiSearch", "ProviderError", "WikidataSearch",
]
