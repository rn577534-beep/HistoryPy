"""External data-provider integrations."""

from historypy.integrations.aggregation import (
    AggregationReport,
    DuplicateCandidateGroup,
    MetadataConflict,
    ProviderSearchResult,
    SearchProvider,
    compare_metadata,
    find_duplicate_candidates,
    search_all,
    to_source_record,
)
from historypy.integrations.historical_apis import (
    EuropeanaSearch,
    ExternalRecord,
    InternetArchiveSearch,
    LibraryOfCongressSearch,
    MediaWikiSearch,
    ProviderError,
    WikidataSearch,
)

__all__ = [
    "AggregationReport",
    "DuplicateCandidateGroup",
    "EuropeanaSearch",
    "ExternalRecord",
    "InternetArchiveSearch",
    "LibraryOfCongressSearch",
    "MediaWikiSearch",
    "MetadataConflict",
    "ProviderError",
    "ProviderSearchResult",
    "SearchProvider",
    "WikidataSearch",
    "compare_metadata",
    "find_duplicate_candidates",
    "search_all",
    "to_source_record",
]
