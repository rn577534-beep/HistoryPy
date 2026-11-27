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
from historypy.integrations.collection_apis import (
    HarvardArtMuseumsSearch,
    SmithsonianSearch,
)
from historypy.integrations.cross_verification import (
    CrossVerificationReport,
    cross_verify_claim,
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
from historypy.integrations.open_catalogs import (
    GDELTNewsSearch,
    GuardianNewsSearch,
    GutendexSearch,
    OpenLibrarySearch,
)

__all__ = [  # noqa: RUF022 - preserve public API grouping
    "AggregationReport",
    "CrossVerificationReport",
    "DuplicateCandidateGroup",
    "EuropeanaSearch",
    "ExternalRecord",
    "GDELTNewsSearch",
    "GuardianNewsSearch",
    "GutendexSearch",
    "HarvardArtMuseumsSearch",
    "InternetArchiveSearch",
    "LibraryOfCongressSearch",
    "MediaWikiSearch",
    "MetadataConflict",
    "OpenLibrarySearch",
    "ProviderError",
    "ProviderSearchResult",
    "SearchProvider",
    "SmithsonianSearch",
    "WikidataSearch",
    "compare_metadata",
    "cross_verify_claim",
    "find_duplicate_candidates",
    "search_all",
    "to_source_record",
]
