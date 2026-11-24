# HistoryPy

An evidence-aware Python toolkit for historical research, chronology, structured datasets, and relationship analysis.

HistoryPy is designed to help researchers represent historical information without flattening uncertainty or disagreement into unsupported certainty. It separates events, claims, sources, evidence, people, places, organizations, and analytical results.

## Principles

- Evidence before assertion: claims can be linked to identifiable sources and specific source locations.
- Preserve disagreement: supporting and contradicting evidence remain separately queryable.
- Represent uncertainty in dates, identities, locations, and interpretations.
- Make transformations and analytical results reproducible and testable.
- Record provenance and respect copyright and dataset licenses.
- Support histories from all regions and periods without assuming one chronology is universal.

## Installation

Requires Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

## Quick start

```python
from historypy import (
    HistoricalDate, HistoricalEvent, HistoricalPerson, HistoricalPlace,
    HistoricalRelationship, HistoricalDataset, RelationshipGraph,
    search_dataset, events_overlapping,
)

person = HistoricalPerson(id="person-001", name="Example historical person")
place = HistoricalPlace(id="place-001", name="Example historical place")
event = HistoricalEvent(
    id="event-001", title="Example event",
    date=HistoricalDate(
        earliest="1947-08-14", latest="1947-08-14",
        precision="day", calendar="gregorian",
    ),
    place_ids=(place.id,),
)
relationship = HistoricalRelationship(
    id="relationship-001", subject_id=person.id,
    predicate="associated_with", object_id=place.id,
)
dataset = HistoricalDataset(
    people=(person,), places=(place,), events=(event,),
    relationships=(relationship,),
)
dataset.require_valid()

graph = RelationshipGraph.from_dataset(dataset)
print(graph.neighbors(person.id))
print(search_dataset(dataset, "historical person"))
period = HistoricalDate(
    earliest="1947-01-01", latest="1947-12-31", calendar="gregorian"
)
print(events_overlapping(dataset, period))
```

## Main capabilities

| Module | Purpose |
|---|---|
| `historypy.core.models` | Historical dates, events, claims, sources, evidence |
| `historypy.core.entities` | People, places, civilizations, organizations, relationships |
| `historypy.core.dataset` | Dataset collections and referential-integrity validation |
| `historypy.chronology` | Date interval comparisons and event timeline utilities |
| `historypy.graph` | Directed relationship graph, neighbors, paths, components |
| `historypy.io` | Versioned JSON and lossless multi-table CSV bundle interchange |
| `historypy.research.evidence` | Claim evidence retrieval and transparent conflict summaries |
| `historypy.research.query` | Lexical dataset search and date-overlap event queries |
| `historypy.research.entity_resolution` | Conservative possible-duplicate suggestions for human review |
| `historypy.research.source_audit` | Bibliographic metadata completeness checks, not credibility scores |\n| `historypy.research.geography` | Great-circle distance and radius search for geocoded places |

## Research queries

`search_dataset(dataset, query)` searches names, aliases, descriptions, titles, tags, claims, and source metadata. Every whitespace-separated query term must appear in the searchable text. Search is case-insensitive and deterministic, but lexical only: it does not perform semantic search or historical inference. `suggest_entity_matches()` can propose same-type person/place/civilization/organization records with similar names. Its similarity is not a probability of identity, and it never merges records; a researcher must review dates, places, sources, and context.

`events_overlapping(dataset, period)` returns events whose bounded dates overlap the requested period. If the calendar or date bounds make comparison indeterminate, those events are excluded by default. Set `include_indeterminate=True` to include them explicitly; this does not mean they are confirmed matches.

```python
from historypy import search_dataset, events_overlapping

hits = search_dataset(dataset, "Alexandria ancient", kinds=("place", "event"))
for hit in hits:
    print(hit.kind, hit.record_id, hit.label, hit.matched_terms)

events = events_overlapping(dataset, period, include_indeterminate=False)
```

## Evidence workflow

A claim and the evidence for it are separate records. An evidence link can be marked as `supports`, `contradicts`, `contextualizes`, or `mentions`. It can also store structured page, paragraph, archive shelfmark, URL fragment, transcription-line, and timecode locators in addition to its free-form locator.

```python
from historypy import summarize_claim_evidence, claims_with_conflicting_evidence

summary = summarize_claim_evidence(dataset, "claim-001")
print(summary.supporting_source_ids)
print(summary.contradicting_source_ids)
print(summary.has_conflicting_evidence)
conflicts = claims_with_conflicting_evidence(dataset)
```

Evidence summaries count linked sources and relationships; they are not automated credibility scores. The library does not independently authenticate sources or decide historical truth. Multiple sources repeating one earlier account are not automatically independent corroboration.

## Source metadata audit

`audit_dataset_sources(dataset)` reports which recommended catalogue fields are present or absent for each source record. It checks creator, publication date, publisher, language, a URL or archival reference, and access date. Missing fields are catalogue gaps, not evidence that a source is unreliable or false.

```python
from historypy import audit_dataset_sources

for audit in audit_dataset_sources(dataset):
    print(audit.source_id, audit.missing_recommended_fields)
```

## Dataset validation

```python
issues = dataset.validate()
for issue in issues:
    print(issue.code, issue.record_id, issue.message)
```

Validation checks identifiers and references, including circular parent/predecessor hierarchies for places, civilizations, and organizations. It does not certify historical accuracy.

## JSON interchange

```python
from historypy import save_dataset, load_dataset, dataset_to_json, dataset_from_json

save_dataset(dataset, "research-dataset.json")
restored = load_dataset("research-dataset.json")
payload = dataset_to_json(dataset)
restored_again = dataset_from_json(payload)
```

The JSON format declares a schema name and version. Unknown schema versions and fields are rejected. Import validates references by default; use `validate=False` only for deliberate repair workflows.

## CSV bundle interchange\n\nCSV is inherently flat, while HistoryPy records contain nested dates, aliases, and references. The CSV bundle therefore stores each record collection in its own CSV table and encodes each cell as JSON, with a manifest carrying schema/version and dataset metadata. This is designed for lossless round-tripping and spreadsheet inspection; it is not a claim that arbitrary CSV files can be imported without a mapping.\n\n```python\nfrom historypy import save_dataset_csv_bundle, load_dataset_csv_bundle\n\nsave_dataset_csv_bundle(dataset, "research-csv-bundle")\nrestored = load_dataset_csv_bundle("research-csv-bundle")\n```\n\n## Geographic queries\n\n```python\nfrom historypy import places_within_radius\n\nnearby = places_within_radius(dataset, 23.7, 90.4, radius_km=50)\nfor place in nearby:\n    print(place.name, place.distance_km)\n```\n\nOnly places with coordinates are returned. Distances use a spherical Earth approximation; they do not express uncertainty in historical place locations.\n\n## Research audit trail

`append_research_action()` returns a new immutable hash-linked sequence. Each action can record before/after content hashes, actor, timestamp, target, and rationale. `verify_research_audit_trail()` detects changed entries and broken links. This is tamper-evident, not a digital signature or proof of author identity.

## Comparative metrics

`MetricObservation` and `compare_metrics()` support transparent, unit-aware comparisons. Missing values stay `None`; observations with different units are kept in separate groups. Supply source IDs with each observation so researchers can trace reported figures.

## Dataset quality and profiling

`assess_dataset_quality()` reports validation errors and research gaps such as claims without linked evidence, events without source IDs, and incomplete source catalogue metadata. `profile_dataset()` counts records and coverage indicators. Neither function scores historical truth or source credibility.

## Reusable search index

Build `DatasetSearchIndex` once for repeated lexical searches. It preserves the substring matching behavior of `search_dataset()`. Rebuild the index after changing the dataset; the index is a snapshot, not a live view.

```python
from historypy import DatasetSearchIndex, assess_dataset_quality, profile_dataset

index = DatasetSearchIndex.build(dataset)
hits = index.search("ancient port", kinds=("place",))
report = assess_dataset_quality(dataset)
profile = profile_dataset(dataset)
```


## External historical and cultural-heritage APIs

HistoryPy includes read-only metadata search adapters for several public providers. These adapters return normalized `ExternalRecord` metadata and short descriptions; they do not copy full articles or automatically declare imported statements to be historically true.

| Provider | Access | Typical material |
|---|---|---|
| Wikipedia / MediaWiki | No API key | Article discovery and short search snippets |
| Wikidata | No API key | Structured entity discovery and identifiers |
| Library of Congress | No API key | Catalogues, photographs, manuscripts, and collection records |
| Internet Archive | No API key | Archive catalogue metadata and item records |
| Europeana | Free account and API key | Cultural heritage objects, digitized books, images, and museum/archive records |

Example:

```python
from historypy import (
    MediaWikiSearch,
    WikidataSearch,
    LibraryOfCongressSearch,
    InternetArchiveSearch,
)

for provider in (
    MediaWikiSearch(language="en"),
    WikidataSearch(),
    LibraryOfCongressSearch(),
    InternetArchiveSearch(),
):
    for item in provider.search("Mughal Empire", limit=5):
        print(item.provider, item.title, item.url, item.retrieved_at)
```

Europeana requires a free API key. Store it outside source code, for example in an environment variable:

```bash
export EUROPEANA_API_KEY="your-key"
```

```python
from historypy import EuropeanaSearch

items = EuropeanaSearch().search("Bengal manuscripts", limit=10)
```

Never commit API keys to Git, notebooks, issue reports, or published examples. Do not place secrets in URLs. The adapter sends the Europeana key in the `X-Api-Key` request header. Follow each provider's current rate limits, terms, attribution rules, and item-level rights metadata. A search result is a discovery lead, not a verified historical claim; researchers should preserve the provider URL, access time, rights statement, and source context before citing it. The adapters deliberately return metadata rather than full copyrighted text.

The adapters use Python's standard library and do not add a mandatory third-party dependency. They use a descriptive User-Agent and a finite request timeout. They do not yet implement persistent caching, automatic retries, or bulk harvesting.


## Federated historical data discovery

Search multiple configured providers with one query. A provider failure is isolated, so successful responses remain available:

```python
from historypy import (
    MediaWikiSearch,
    WikidataSearch,
    LibraryOfCongressSearch,
    InternetArchiveSearch,
    search_all,
    find_duplicate_candidates,
    compare_metadata,
    to_source_record,
)

report = search_all(
    [
        MediaWikiSearch(),
        WikidataSearch(),
        LibraryOfCongressSearch(),
        InternetArchiveSearch(),
    ],
    "Mughal Empire",
    limit_per_provider=5,
)

for provider_result in report.results:
    print(provider_result.provider, provider_result.error)
    for item in provider_result.records:
        print(item.title, item.url, item.license)

# Candidate groups and metadata disagreements are review aids only.
duplicates = find_duplicate_candidates(report.records)
conflicts = compare_metadata(report.records)

# Import only a result selected by a researcher.
selected = report.records[0]
source = to_source_record(selected, source_id="selected-source-001")
```

Six aggregation capabilities are provided: federated search, per-provider failure isolation, conservative exact duplicate candidates, field-level metadata conflict reports, explicit conversion of selected records into `SourceRecord`, and automated tests/documentation. Duplicate candidates are not merged. Similar titles do not prove identity. Conflicting dates or creators are not automatically reconciled. The imported source preserves provider identity, external ID, retrieval timestamp, rights statement, URL, and language in its metadata/notes.

Federated provider requests run concurrently by default (bounded to eight workers) while results retain provider input order and failures remain isolated. Set max_workers=1 for sequential operation. There is no persistent cache or automatic retry; each provider's own public API limits still apply. Respect upstream terms, rate limits, and attribution requirements. Do not bulk harvest unless the provider permits it.

## Chronology notes

- ISO date bounds represent Gregorian calendar dates.
- BCE/year-only dates use astronomical year numbering: 1 CE = 1, 1 BCE = 0, 2 BCE = -1.
- Calendar names are explicit metadata; no implicit calendar conversion is performed.
- Date overlap returns `None` when comparison cannot safely be established.

## Development status

Early development / pre-alpha. APIs may change. This repository does not yet ship a comprehensive historical dataset, a calendar-conversion engine, automatic source authentication, semantic search, entity resolution, or a production research database.

See [architecture](docs/architecture.md) and [contribution guidelines](CONTRIBUTING.md).

## Automated checks

The repository includes tests for chronology, BCE date handling, entities, dataset validation, graph traversal, evidence analysis, JSON interchange, and research queries. GitHub Actions is configured to run pytest and Ruff on Python 3.10–3.13. A configured workflow is not a verified passing run; consult the Actions tab for the latest execution.


## Next research infrastructure milestone (0.3)

### Dataset-wide knowledge graph

`HistoricalKnowledgeGraph.from_dataset(dataset)` projects recorded claims, events, entities, sources, relationships, and evidence links into typed nodes and directed edges. Edges preserve the recorded relation and optional provenance identifiers; they are not automatically authenticated facts.

### Temporal graph views

`temporal_graph(dataset, period)` selects events whose dates are comparable and overlap the requested period. Incomparable dates are excluded by default; `include_indeterminate=True` includes them explicitly. Calendar conversion is never implicit.

### Evidence-based claim assessment

`assess_claim(dataset, claim_id)` reports `supported`, `contradicted`, `mixed`, or `insufficient` according to the labels researchers attached to evidence links. These labels do not establish truth, source reliability, or source independence.

### SQLite dataset storage

`SQLiteDatasetStore("research.sqlite")` stores versioned JSON dataset payloads in a transactional SQLite table. It uses Python's standard-library `sqlite3`, validates datasets before saving, and supports `save`, `load`, `names`, and `delete`.

### Reproducible claim reports

`render_claim_report(dataset, "claim-001")` creates Markdown with the claim, recorded assessment, linked sources, and limitations. It does not invent citations or narrative conclusions.

### Smithsonian and Harvard Art Museums discovery

`SmithsonianSearch` reads Smithsonian Open Access search metadata and `HarvardArtMuseumsSearch` reads Harvard Art Museums object metadata. Both require keys supplied explicitly or through `SMITHSONIAN_API_KEY` and `HARVARD_ART_MUSEUMS_API_KEY`. Do not commit keys. Smithsonian rights and media access are item-specific; Harvard API content is non-commercial, limited to 2,500 requests/day, and may not be cached for more than two weeks without written permission. These adapters have mock-based tests only; live access depends on valid credentials and provider availability.

The two providers' official developer documentation and terms should be reviewed before publishing or redistributing returned material:
- [Smithsonian Open Access developer tools](https://www.si.edu/openaccess/devtools)
- [Harvard Art Museums API documentation](https://github.com/harvardartmuseums/api-docs)

All six capabilities are research infrastructure, not a pre-verified historical knowledgebase. Researchers remain responsible for checking original sources, item-level rights, and competing interpretations.


## Structured research query engine (0.4)

The structured query engine combines transparent lexical search with optional record type, date period, place, source, event-tag, and evidence-status filters. Filters use AND semantics. Results are deterministically ordered and paginated; facets count the complete filtered result set before pagination.

```python
from historypy import (
    HistoricalDate,
    ResearchQuery,
    execute_research_query,
)

query = ResearchQuery(
    text="port treaty",
    kinds=("event", "claim"),
    period=HistoricalDate(
        earliest_year=1200,
        latest_year=1400,
        calendar="gregorian",
    ),
    place_ids=("old-port",),
    source_ids=("archive-source-1",),
    tags=("trade",),
    limit=25,
    offset=0,
)
result = execute_research_query(dataset, query)

for hit in result.hits:
    print(hit.kind, hit.record_id, hit.label)

print("Total:", result.total)
print("Kinds:", result.facets.kind_counts)
print("Evidence:", result.facets.evidence_status_counts)
print("Tags:", result.facets.tag_counts)
```

Supported evidence statuses are `supported`, `contradicted`, `mixed`, and `insufficient`. They reflect only recorded evidence-link labels, not a machine judgment of historical truth or source credibility. Place filters apply to place records and records explicitly linked to those places. Source filters apply to records with recorded source links and claims with linked evidence. Tag filters apply to events. Date filters use explicit calendar compatibility; a person's birth-to-death interval and an institution's founding-to-dissolution interval are considered as ranges. Records with incomparable dates are excluded unless `include_indeterminate=True`.

For repeated text queries, pass a prebuilt `DatasetSearchIndex` using `execute_research_query(dataset, query, index=index)`. The index must have been built from the same unchanged dataset snapshot; rebuild it after edits. Search remains lexical substring retrieval, not semantic or vector search. Facets are descriptive counts, not quality scores. This release adds query composition and result navigation without introducing opaque ranking or automated historical conclusions.


## Unified historical timeline (0.5)

The timeline engine combines dated events with person lifespans, civilization spans, and organization lifespans. It sorts using astronomical year numbering for BCE dates and preserves the original calendar metadata. A period filter uses the existing three-state overlap behavior: true, false, or indeterminate. No calendar conversion is performed.

```python
from historypy import HistoricalDate, timeline_for_dataset

period = HistoricalDate(
    earliest_year=1200, latest_year=1500,
    precision="year", calendar="gregorian",
)
timeline = timeline_for_dataset(dataset, period=period)

for entry in timeline.entries:
    print(entry.kind, entry.label, entry.date_label)
print("Undated records:", timeline.undated_count)
print("Incomparable dates:", timeline.excluded_indeterminate_count)
```

Undated records are omitted by default and counted separately. Set `include_indeterminate=True` to include undated records when no period is specified, or to retain records whose calendars cannot be compared with a requested period. This is an explicit inclusion choice, not a claim that dates match.

## Dataset provenance audit (0.5)

`audit_dataset_provenance(dataset)` summarizes how source records are linked across events, people, places, civilizations, organizations, and relationships. It also identifies unused source records, claims without evidence links, records without source references, and counts each recorded evidence-link relation.

```python
from historypy import audit_dataset_provenance

provenance = audit_dataset_provenance(dataset)
print(provenance.source_usage_counts)
print(provenance.orphan_source_ids)
print(provenance.claims_without_evidence)
print(provenance.evidence_relation_counts)
```

This is a coverage and traceability audit only. A source referenced many times is not necessarily reliable, independent, or correct. Missing links indicate documentation gaps, not that a historical claim is false.


## Normalized SQLite research store (0.6)

For larger collections, `NormalizedSQLiteStore` stores each source, claim, event, person, place, civilization, organization, relationship, and evidence link as an individual database row. Source references are indexed separately. The store uses a versioned SQLite schema and atomic replacement of a named dataset; the earlier JSON-payload `SQLiteDatasetStore` remains available for compatibility.

```python
from historypy import NormalizedSQLiteStore

store = NormalizedSQLiteStore("historypy.sqlite3")
store.save("ancient-world", dataset)

print(store.count_records("ancient-world"))
hits = store.search_records(
    "ancient-world", "Babylon", kind="events", limit=25, offset=0
)
for hit in hits:
    print(hit.kind, hit.record_id, hit.payload)

for usage in store.source_usage("ancient-world"):
    print(usage.source_id, usage.record_links, usage.evidence_links)
```

Search currently uses indexed dataset/kind selection plus case-insensitive substring matching over normalized record text. It is not full-text ranking or semantic/vector search. Pagination is deterministic by record kind and ID. SQLite FTS5 and external embedding providers are not required.


## Normalized research database (0.7)

The normalized SQLite store maintains indexed record and source-reference tables. When the SQLite build provides FTS5, the store maintains a full-text index for phrase search; otherwise it automatically falls back to the dependency-free case-insensitive substring search. FTS5 uses token-based phrase matching, so punctuation and partial-token behavior can differ from the fallback. Search results are deterministically ordered and paginated.

~~~python
from historypy import NormalizedSQLiteStore

store = NormalizedSQLiteStore("history.db")
store.save("project", dataset)

matches = store.search_records(
    "project", "Mughal administration", kind="claims", limit=25
)
period = store.query_year_range(
    "project", 1526, 1707, calendar="gregorian", limit=100
)
~~~

Year-range queries use inclusive overlap and astronomical year numbering (1 CE = 1, 1 BCE = 0, 2 BCE = -1). BCE ranges are supported. Calendar filtering is exact when supplied; HistoryPy never converts calendars implicitly. Open-ended dates can match a range, while records with no normalized year bounds are excluded unless include_undated=True is passed. The store indexes year and calendar columns to accelerate these queries.

FTS5 is an optional SQLite capability, not a mandatory dependency. The fallback remains available on SQLite builds without FTS5. Neither lexical search mode understands meaning or independently verifies historical claims. Query performance depends on dataset size, hardware, SQLite build, and query selectivity; no fixed response-time guarantee is made.


## Semantic retrieval and evidence analysis (0.8)

### Embedding-backed semantic search

HistoryPy supports semantic ranking through a caller-supplied embedding function. It intentionally does not download a model, choose a paid provider, or send research text to an external service automatically. The embedder must return one finite, non-zero vector per input text and use the same model/vector space for indexing and querying.

~~~python
from historypy import SemanticSearchIndex

# embed_texts must return one vector per input string from your chosen model.
index = SemanticSearchIndex.build(
    dataset,
    embedder=embed_texts,
    model_id="provider/model-name@version",
    batch_size=64,
)
hits = index.search(
    "What evidence connects this port to maritime trade?",
    embedder=embed_texts,
    kinds=("event", "claim", "place"),
    limit=20,
    min_similarity=0.25,
)
for hit in hits:
    print(hit.kind, hit.record_id, hit.similarity, hit.label)
~~~

The model identifier is retained with the index so model provenance is visible. Rebuild the index after changing the dataset or embedding model. Similarity is a retrieval signal, not a probability, source-quality score, or measure of historical truth. The quality of results depends on the selected embedding model, its language coverage, domain suitability, and the research corpus. This feature has no mandatory model or network dependency; users control embedding generation, hosting, cost, and privacy.

### Claim evidence coverage analysis

~~~python
from historypy import analyze_claim_evidence

analysis = analyze_claim_evidence(dataset, "claim-001")
print(analysis.assessment_status)
print(analysis.relation_counts)
print(analysis.source_type_counts)
print(analysis.locator_coverage)
~~~

This report summarizes recorded support/contradiction/context/mention links, source-type metadata, and whether source locators were recorded. Source types and locator completeness do not prove reliability or independence. The analysis never resolves disputes automatically.
