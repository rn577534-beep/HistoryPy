"""Read-only collection metadata adapters for Smithsonian and Harvard Art Museums."""

from __future__ import annotations

import os
from urllib.parse import urlencode

from historypy.integrations.historical_apis import (
    ExternalRecord, _clean, _request_json, _retrieved_at,
)


class SmithsonianSearch:
    """Search Smithsonian Open Access metadata (requires SMITHSONIAN_API_KEY)."""

    endpoint = "https://api.si.edu/openaccess/api/v1.0/search"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SMITHSONIAN_API_KEY")
        if not self.api_key:
            raise ValueError("Set SMITHSONIAN_API_KEY or pass api_key")

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params = urlencode({"q": query, "rows": limit, "api_key": self.api_key})
        payload = _request_json(f"{self.endpoint}?{params}")
        retrieved = _retrieved_at()
        rows = payload.get("response", {}).get("rows", [])
        records = []
        for item in rows:
            content = item.get("content", {}).get("descriptiveNonRepeating", {})
            freetext = item.get("content", {}).get("freetext", {})
            title_values = freetext.get("title", [])
            title = _clean(title_values[0].get("content") if title_values else None)
            identifier = _clean(content.get("record_ID") or item.get("id"))
            if not identifier or not title:
                continue
            online = content.get("online_media", {}).get("media", [])
            media_rights = _clean(online[0].get("usage", {}).get("access") if online else None)
            records.append(ExternalRecord(
                provider="Smithsonian Open Access", external_id=identifier, title=title,
                description=_clean(freetext.get("notes") or freetext.get("physicalDescription")),
                url=_clean(content.get("record_link")), creator=None,
                date=_clean(freetext.get("date", [{}])[0].get("content")
                             if freetext.get("date") else None),
                language=None, license=media_rights or "Check item-level rights and CC0 status",
                retrieved_at=retrieved,
            ))
        return tuple(records)


class HarvardArtMuseumsSearch:
    """Search Harvard Art Museums object metadata (requires HARVARD_ART_MUSEUMS_API_KEY).

    Respect the provider's non-commercial terms, 2,500 requests/day limit, and
    maximum two-week content caching period.
    """

    endpoint = "https://api.harvardartmuseums.org/object"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("HARVARD_ART_MUSEUMS_API_KEY")
        if not self.api_key:
            raise ValueError("Set HARVARD_ART_MUSEUMS_API_KEY or pass api_key")

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        params = urlencode({
            "apikey": self.api_key, "title": query, "size": limit,
            "fields": "objectid,objectnumber,title,dated,people,creditline,url",
        })
        payload = _request_json(f"{self.endpoint}?{params}")
        retrieved = _retrieved_at()
        records = []
        for item in payload.get("records", []):
            identifier = _clean(item.get("objectid") or item.get("objectnumber"))
            title = _clean(item.get("title"))
            if not identifier or not title:
                continue
            people = item.get("people", [])
            creator = _clean("; ".join(
                str(person.get("name")) for person in people if person.get("name")
            ))
            records.append(ExternalRecord(
                provider="Harvard Art Museums", external_id=identifier, title=title,
                description=_clean(item.get("creditline")), url=_clean(item.get("url")),
                creator=creator, date=_clean(item.get("dated")), language="en",
                license="Check object-level rights; API terms apply", retrieved_at=retrieved,
            ))
        return tuple(records)
