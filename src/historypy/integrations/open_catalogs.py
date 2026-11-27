"""Free/open book-catalog and news discovery adapters.

These adapters retrieve bibliographic/article metadata and discovery links.
They do not bulk-download or redistribute copyrighted book/news content.
"""
from __future__ import annotations

import os
import time
from collections.abc import Iterator
from urllib.parse import urlencode

from historypy.integrations.historical_apis import (
    ExternalRecord,
    _clean,
    _request_json,
    _retrieved_at,
)


class OpenLibrarySearch:
    """Search Open Library's book metadata API; no API key required.

    Identified clients should set HISTORYPY_CONTACT_EMAIL and send requests
    conservatively. Open Library asks API users to cache results and not use
    the live API as a bulk metadata backend; use its monthly data dumps for
    bulk research datasets instead.
    """

    endpoint = "https://openlibrary.org/search.json"

    def __init__(self, contact_email: str | None = None) -> None:
        self.contact_email = contact_email or os.getenv("HISTORYPY_CONTACT_EMAIL")

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params = urlencode({
            "q": query, "limit": limit,
            "fields": "key,title,author_name,first_publish_year,subject,language,isbn",
        })
        headers = {}
        if self.contact_email:
            headers["User-Agent"] = f"HistoryPy/1.1 ({self.contact_email})"
        payload = _request_json(f"{self.endpoint}?{params}", headers=headers)
        retrieved = _retrieved_at()
        records = []
        for item in payload.get("docs", []):
            key = _clean(item.get("key"))
            title = _clean(item.get("title"))
            if not key or not title:
                continue
            subjects = item.get("subject", [])[:8]
            authors = item.get("author_name", [])[:8]
            description = "; ".join(
                part for part in (
                    "Authors: " + ", ".join(authors) if authors else "",
                    "Subjects: " + ", ".join(subjects) if subjects else "",
                ) if part
            ) or None
            records.append(ExternalRecord(
                provider="Open Library",
                external_id=key,
                title=title,
                description=description,
                url=f"https://openlibrary.org{key}",
                creator=_clean(authors),
                date=str(item["first_publish_year"]) if item.get("first_publish_year") else None,
                language=_clean(item.get("language")),
                license="Bibliographic metadata; access and rights vary by edition",
                retrieved_at=retrieved,
            ))
        return tuple(records)


class GutendexSearch:
    """Search Project Gutenberg's public-domain ebook catalog via Gutendex.

    search() returns one API page (up to 32 records). iter_search() explicitly
    follows pagination, with a caller-selected upper bound. Only metadata and
    ebook landing-page links are returned; full text is never downloaded.
    """

    endpoint = "https://gutendex.com/books/"

    @staticmethod
    def _record(item: dict, retrieved: str) -> ExternalRecord | None:
        identifier = item.get("id")
        title = _clean(item.get("title"))
        if identifier is None or not title:
            return None
        authors = [
            author.get("name", "") for author in item.get("authors", [])
            if author.get("name")
        ]
        subjects = item.get("subjects", [])[:8]
        shelves = item.get("bookshelves", [])[:5]
        detail = "; ".join(
            part for part in (
                "Subjects: " + ", ".join(subjects) if subjects else "",
                "Bookshelves: " + ", ".join(shelves) if shelves else "",
                "Languages: " + ", ".join(item.get("languages", [])) if item.get("languages") else "",
            ) if part
        ) or None
        return ExternalRecord(
            provider="Project Gutenberg (Gutendex)",
            external_id=str(identifier),
            title=title,
            description=detail,
            url=f"https://www.gutenberg.org/ebooks/{identifier}",
            creator=_clean([author for author in authors]),
            date=None,
            language=_clean(item.get("languages")),
            license="Project Gutenberg public-domain collection; verify item and country-specific rights",
            retrieved_at=retrieved,
        )

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 32:
            raise ValueError("limit must be between 1 and 32 for one Gutendex page")
        payload = _request_json(f"{self.endpoint}?{urlencode({'search': query})}")
        retrieved = _retrieved_at()
        records = (self._record(item, retrieved) for item in payload.get("results", []))
        return tuple(record for record in records if record is not None)[:limit]

    def iter_search(
        self,
        query: str,
        *,
        max_records: int = 1000,
        max_pages: int = 100,
        page_delay: float = 0.25,
    ) -> Iterator[ExternalRecord]:
        """Iterate a bounded number of catalog records through API pagination."""
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= max_records <= 10000:
            raise ValueError("max_records must be between 1 and 10000")
        if not 1 <= max_pages <= 500:
            raise ValueError("max_pages must be between 1 and 500")
        if not isinstance(page_delay, (int, float)) or isinstance(page_delay, bool) or page_delay < 0:
            raise ValueError("page_delay must be a non-negative number")
        url = f"{self.endpoint}?{urlencode({'search': query})}"
        pages = yielded = 0
        while url and pages < max_pages and yielded < max_records:
            payload = _request_json(url)
            retrieved = _retrieved_at()
            pages += 1
            for item in payload.get("results", []):
                record = self._record(item, retrieved)
                if record is not None:
                    yield record
                    yielded += 1
                    if yielded >= max_records:
                        return
            url = payload.get("next")
            if url and pages < max_pages and yielded < max_records and page_delay:
                time.sleep(page_delay)


class GDELTNewsSearch:
    """Search recent worldwide news metadata with GDELT DOC 2.0; no key required.

    GDELT's article-list search covers a rolling recent-news window (currently
    about three months). Article text remains with the original publisher.
    """

    endpoint = "https://api.gdeltproject.org/api/v2/doc/doc"

    def search(
        self,
        query: str,
        *,
        limit: int = 10,
        timespan: str = "30d",
        language: str | None = None,
    ) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 250:
            raise ValueError("limit must be between 1 and 250")
        if not timespan or len(timespan) > 12:
            raise ValueError("timespan must be a short GDELT duration such as 7d or 30d")
        search_query = query
        if language:
            if not language.isalpha() or len(language) not in {2, 3}:
                raise ValueError("language must be a 2- or 3-letter code")
            search_query = f"({query}) sourcelang:{language}"
        params = urlencode({
            "query": search_query,
            "mode": "ArtList",
            "format": "json",
            "maxrecords": limit,
            "timespan": timespan,
            "sort": "DateDesc",
        })
        payload = _request_json(f"{self.endpoint}?{params}")
        retrieved = _retrieved_at()
        records = []
        for item in payload.get("articles", []):
            url = _clean(item.get("url"))
            title = _clean(item.get("title"))
            if not url or not title:
                continue
            domain = _clean(item.get("domain"))
            detail = "; ".join(
                part for part in (
                    f"Source country: {item.get('sourceCountry')}" if item.get("sourceCountry") else "",
                    f"Language: {item.get('language')}" if item.get("language") else "",
                    f"Seen: {item.get('seendate')}" if item.get("seendate") else "",
                ) if part
            ) or None
            records.append(ExternalRecord(
                provider="GDELT DOC 2.0",
                external_id=url,
                title=title,
                description=detail,
                url=url,
                creator=domain,
                date=_clean(item.get("seendate")),
                language=_clean(item.get("language")),
                license="Article metadata only; article copyright and reuse terms belong to publisher",
                retrieved_at=retrieved,
            ))
        return tuple(records)


class GuardianNewsSearch:
    """Search Guardian article metadata using a free developer key.

    The free developer tier is non-commercial and rate/quota limited. HistoryPy
    stores only article metadata and a short trail text, never the full article.
    """

    endpoint = "https://content.guardianapis.com/search"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("GUARDIAN_API_KEY")
        if not self.api_key:
            raise ValueError("Set GUARDIAN_API_KEY or pass api_key")

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 50:
            raise ValueError("limit must be between 1 and 50")
        params = urlencode({
            "api-key": self.api_key,
            "q": query,
            "page-size": limit,
            "show-fields": "trailText,byline",
            "order-by": "newest",
        })
        payload = _request_json(f"{self.endpoint}?{params}")
        retrieved = _retrieved_at()
        response = payload.get("response", {})
        records = []
        for item in response.get("results", []):
            url = _clean(item.get("webUrl"))
            title = _clean(item.get("webTitle"))
            if not url or not title:
                continue
            fields = item.get("fields", {})
            records.append(ExternalRecord(
                provider="The Guardian Open Platform",
                external_id=url,
                title=title,
                description=_clean(fields.get("trailText")),
                url=url,
                creator=_clean(fields.get("byline")) or _clean(item.get("sectionName")),
                date=_clean(item.get("webPublicationDate")),
                language="en",
                license="Non-commercial developer tier; article copyright remains with The Guardian",
                retrieved_at=retrieved,
            ))
        return tuple(records)


__all__ = [
    "GDELTNewsSearch",
    "GuardianNewsSearch",
    "GutendexSearch",
    "OpenLibrarySearch",
]
