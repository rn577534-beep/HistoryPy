"""Federated discovery and provenance-aware review of external records.

Search results remain discovery leads. This module never merges records or
asserts historical truth; researchers explicitly select records for import.
"""
from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

from historypy.core.models import SourceRecord
from historypy.integrations.historical_apis import ExternalRecord


class SearchProvider(Protocol):
    """Minimal interface implemented by HistoryPy search adapters."""

    def search(self, query: str, *, limit: int = 10) -> tuple[ExternalRecord, ...]: ...


@dataclass(frozen=True, slots=True)
class ProviderSearchResult:
    provider: str
    records: tuple[ExternalRecord, ...]
    error: str | None = None


@dataclass(frozen=True, slots=True)
class DuplicateCandidateGroup:
    """Records sharing a conservative exact identifier or normalized title."""

    reason: str
    records: tuple[ExternalRecord, ...]


@dataclass(frozen=True, slots=True)
class MetadataConflict:
    field: str
    values: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class AggregationReport:
    query: str
    results: tuple[ProviderSearchResult, ...]

    @property
    def records(self) -> tuple[ExternalRecord, ...]:
        return tuple(record for result in self.results for record in result.records)

    @property
    def failures(self) -> tuple[ProviderSearchResult, ...]:
        return tuple(result for result in self.results if result.error is not None)

    @property
    def successful_provider_count(self) -> int:
        return sum(result.error is None for result in self.results)


def _search_one(
    provider: SearchProvider, query: str, limit: int
) -> ProviderSearchResult:
    name = type(provider).__name__
    try:
        records = tuple(provider.search(query, limit=limit))
        if any(not isinstance(item, ExternalRecord) for item in records):
            raise TypeError("provider returned a non-ExternalRecord result")
        return ProviderSearchResult(name, records)
    except Exception as exc:  # noqa: BLE001 - isolate failures from independent providers.
        return ProviderSearchResult(name, (), f"{type(exc).__name__}: {exc}")


def search_all(
    providers: Sequence[SearchProvider], query: str, *,
    limit_per_provider: int = 10, max_workers: int | None = None,
) -> AggregationReport:
    """Search independent providers concurrently while preserving input order.

    Worker count is bounded by provider count and eight by default. Set
    max_workers=1 to force sequential execution.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query cannot be empty")
    if not 1 <= limit_per_provider <= 100:
        raise ValueError("limit_per_provider must be between 1 and 100")
    if max_workers is not None and (
        not isinstance(max_workers, int) or isinstance(max_workers, bool)
        or max_workers < 1
    ):
        raise ValueError("max_workers must be a positive integer or None")
    if not providers:
        return AggregationReport(query.strip(), ())
    workers = min(len(providers), max_workers or 8)
    if workers == 1:
        results = tuple(_search_one(provider, query, limit_per_provider) for provider in providers)
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="historypy-search") as pool:
            results = tuple(pool.map(
                lambda provider: _search_one(provider, query, limit_per_provider),
                providers,
            ))
    return AggregationReport(query.strip(), results)


def _normalized_title(record: ExternalRecord) -> str:
    return " ".join(re.findall(r"\w+", record.title.casefold(), flags=re.UNICODE))


def find_duplicate_candidates(
    records: Sequence[ExternalRecord],
) -> tuple[DuplicateCandidateGroup, ...]:
    """Group exact cross-provider identifiers/URLs/titles for human review."""
    buckets: dict[tuple[str, str], list[ExternalRecord]] = defaultdict(list)
    for record in records:
        buckets[("url", record.url.casefold().rstrip("/"))].append(record) if record.url else None
        buckets[("title", _normalized_title(record))].append(record)
    groups = []
    seen: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for (reason, _), items in sorted(buckets.items()):
        unique = {(item.provider, item.external_id): item for item in items}
        if len(unique) < 2:
            continue
        ordered = tuple(sorted(unique.values(), key=lambda item: (item.provider, item.external_id)))
        identity = (reason, tuple((item.provider, item.external_id) for item in ordered))
        if identity not in seen:
            seen.add(identity)
            groups.append(DuplicateCandidateGroup(reason, ordered))
    return tuple(groups)


def compare_metadata(records: Sequence[ExternalRecord]) -> tuple[MetadataConflict, ...]:
    """Report disagreements without deciding which provider is correct."""
    conflicts = []
    for field in ("title", "description", "creator", "date", "language", "license"):
        values = {
            (record.provider, value.strip())
            for record in records
            if (value := getattr(record, field)) is not None and value.strip()
        }
        distinct = {value for _, value in values}
        if len(distinct) > 1:
            conflicts.append(MetadataConflict(field, tuple(sorted(values))))
    return tuple(conflicts)


def to_source_record(
    record: ExternalRecord, *, source_id: str, accessed_on: str | None = None,
    source_type: str = "tertiary", notes: str | None = None,
) -> SourceRecord:
    """Convert one researcher-selected external result to a HistoryPy source."""
    if not source_id.strip():
        raise ValueError("source_id cannot be empty")
    provenance = (
        f"Discovered via {record.provider}; external id={record.external_id}; "
        f"retrieved_at={record.retrieved_at}; rights={record.license or 'unspecified'}."
    )
    combined_notes = " ".join(part for part in (provenance, notes) if part)
    return SourceRecord(
        id=source_id,
        title=record.title,
        source_type=source_type,
        creator=record.creator,
        publisher=record.provider,
        url=record.url,
        accessed_on=accessed_on,
        language=record.language,
        notes=combined_notes,
    )


__all__ = [
    "AggregationReport", "DuplicateCandidateGroup", "MetadataConflict",
    "ProviderSearchResult", "SearchProvider", "compare_metadata",
    "find_duplicate_candidates", "search_all", "to_source_record",
]
