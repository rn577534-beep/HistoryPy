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

### Install directly from GitHub

The current development version can be installed without cloning the repository:

```bash
python -m pip install "git+https://github.com/rn577534-beep/HistoryPy.git@feat/evidence-centered-reasoning"
```

This requires Git to be installed and available on your PATH. To verify the installation:

```bash
python -c "import historypy; print(historypy.__version__)"
```

### Install from a local clone (contributors)

```bash
git clone --branch feat/evidence-centered-reasoning --single-branch https://github.com/rn577534-beep/HistoryPy.git
cd HistoryPy
python -m pip install -e ".[dev]"
pytest
ruff check .
```

### Optional semantic-search dependencies

Install the optional embedding-model dependencies from a local clone with:

```bash
python -m pip install ".[semantic]"
```

The semantic extra installs `sentence-transformers`; the base installation does not download an embedding model automatically.

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
| `historypy.research.evidence_analysis` | Evidence relation counts, source-type coverage, and locator completeness |
| `historypy.research.semantic` | Embedding-backed semantic retrieval using an explicitly supplied model |
| `historypy.research.query` | Lexical dataset search and date-overlap event queries |
| `historypy.research.entity_resolution` | Conservative possible-duplicate suggestions for human review |
| `historypy.research.source_audit` | Bibliographic metadata completeness checks, not credibility scores |
| `historypy.research.geography` | Great-circle distance and radius search for geocoded places |

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

## Source independence audit

HistoryPy can now group evidence sources that have **recorded** common origins. The audit follows direct and transitive `derived_from_source_ids` links and shared `shared_evidence_group_ids`. It also retains intermediate source records as bridge nodes when they connect two sources cited for the same claim.

```python
from historypy import analyze_claim_source_independence, audit_source_independence

claim_report = analyze_claim_source_independence(dataset, "claim-001")
print(claim_report.status)
print(claim_report.dependent_clusters)
print(claim_report.unknown_source_ids)

dataset_report = audit_source_independence(dataset)
print(dataset_report.claims_with_known_dependence)
print(dataset_report.claims_with_unknown_dependence)
```

Statuses distinguish `known_dependence`, `known_dependence_and_unknown`, `dependence_unknown`, `single_source_dependence_unknown`, and `no_evidence`. A source without a documented dependency path is **unknown**, not independent. The audit does not infer independence from different publishers, URLs, titles, or source types. Record shared witnesses, syndicated dispatches, and common archival documents in the source genealogy metadata; otherwise the relationship cannot be detected. This report is a provenance aid, not a source-credibility or historical-truth score.

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

## CSV bundle interchange

CSV is inherently flat, while HistoryPy records contain nested dates, aliases, and references. The CSV bundle therefore stores each record collection in its own CSV table and encodes each cell as JSON, with a manifest carrying schema/version and dataset metadata. This is designed for lossless round-tripping and spreadsheet inspection; it is not a claim that arbitrary CSV files can be imported without a mapping.

```python
from historypy import save_dataset_csv_bundle, load_dataset_csv_bundle

save_dataset_csv_bundle(dataset, "research-csv-bundle")
restored = load_dataset_csv_bundle("research-csv-bundle")
```

## Geographic queries

```python
from historypy import places_within_radius

nearby = places_within_radius(dataset, 23.7, 90.4, radius_km=50)
for place in nearby:
    print(place.name, place.distance_km)
```

Only places with coordinates are returned. Distances use a spherical Earth approximation; they do not express uncertainty in historical place locations.

## Research audit trail

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

Early development / pre-alpha. APIs may change. This repository does not yet ship a comprehensive historical dataset, a calendar-conversion engine, automatic source authentication, a bundled embedding model, or a production hosted research service. Semantic retrieval is available through a caller-supplied embedding model; entity matching remains a human-reviewed suggestion workflow.

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

HistoryPy supports semantic ranking through a caller-supplied embedding function. The core package intentionally does not download a model, choose a paid provider, or send research text to an external service automatically. An optional benchmark adapter is provided for a public multilingual Sentence Transformers model. The embedder must return one finite, non-zero vector per input text and use the same model/vector space for indexing and querying.

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


## Intelligent historical research pipeline (0.9)

The orchestration layer combines local lexical search, optional caller-supplied semantic retrieval, and opt-in federated provider discovery. Query clauses are split only where the researcher explicitly enters semicolons or new lines; HistoryPy does not invent subquestions or entities.

```python
from historypy import (
    HistoricalDataset, ResearchPipeline, render_research_report,
    MediaWikiSearch, WikidataSearch, LibraryOfCongressSearch,
)

pipeline = ResearchPipeline(
    dataset,
    providers=(MediaWikiSearch(), WikidataSearch(), LibraryOfCongressSearch()),
)
report = pipeline.run(
    "Mughal Empire; Bengal trade",
    include_semantic=False,  # set up a SemanticSearchIndex/embedder to enable it
    include_external=True,
)
print(render_research_report(report))
print(report.gaps)
print(report.provider_failures)
```

The pipeline retains local, semantic, and external results as separate channels. It reports evidence coverage for locally matched claims, provider failures, duplicate candidates, metadata conflicts, and research gaps. Markdown reports include local record IDs and external URLs/retrieval timestamps where available. External records remain discovery leads and are not automatically imported. The pipeline does not synthesize historical narratives, infer source independence, or rank sources by credibility. Semantic retrieval requires the same caller-supplied embedding model used to build the index. External API calls are opt-in and subject to provider terms, rate limits, network availability, and credentials.

The automated tests use fixture providers and do not constitute live provider validation or a benchmark of historical accuracy. Query speed and research completeness depend on the dataset, embedding model, providers, and environment; no fixed performance or accuracy guarantee is made.

## Research infrastructure milestone (1.0)

Version 1.0 consolidates the research workflow and adds a reproducible synthetic
benchmark for lexical retrieval. It compares the baseline scan with the reusable
trigram index, verifies that both return identical ordered record IDs, and
reports median timings, index build cost, Python/runtime details, and corpus
size as JSON.

Run it from the repository root:

```bash
python benchmarks/benchmark_search.py --records 10000 --repeat 7
```

The benchmark uses generated fixture records, not a representative historical
corpus. Its timings depend on hardware, Python, corpus shape, and query
selectivity. They must not be interpreted as historical accuracy, source
reliability, or a fixed latency promise. The smoke test in CI checks that the
benchmark runs; it does not enforce machine-dependent speed thresholds.

### Current release boundaries

- HistoryPy is research infrastructure, not a populated or independently
  verified global history knowledgebase.
- Semantic search requires an explicitly supplied embedder; an optional
  multilingual Sentence Transformers adapter is available for reproducible
  evaluation, but the core package does not send corpus text to a provider
  automatically.
- External API adapters are tested with fixtures; live availability,
  credentials, rights, and rate limits remain provider-dependent.
- Search ranking is retrieval relevance only. It is not a truth or credibility
  score, and human source review remains necessary.
- The package remains pre-alpha while schemas, provider integrations, and
  research workflows continue to evolve.


### Large-corpus scale and memory benchmark

The opt-in GitHub Actions workflow `.github/workflows/scale-benchmarks.yml`
tests synthetic corpora of 100,000 and 1,000,000 records. It measures index
build time, additional Python allocations during index construction and query
execution, linear/indexed query time, and exact ordered result parity for a
selective query. Run locally with:

```bash
python benchmarks/benchmark_scale.py --records 100000 --repeat 1
python benchmarks/benchmark_scale.py --records 1000000 --repeat 1
```

Memory values use Python `tracemalloc`: they exclude the already-created
dataset, native allocations, and total process RSS. The benchmark deliberately
uses a selective synthetic query; it does not establish performance for broad
queries, real historical corpora, retrieval relevance, or historical accuracy.
The workflow is separate from the required fast test matrix because the
million-record case is resource-intensive.


## Comparing sources for the same event

`compare_event_sources(dataset, event_id)` places the event's directly linked
sources beside the quotations and evidence links attached to claims that name
that event. Each excerpt retains its relation label and exact citation locator
(page, paragraph, archive shelfmark, URL fragment, transcription line, or
timecode). Sources linked to the event without a quotation are still listed so
missing evidence can be identified.

```python
from historypy import compare_event_sources

comparison = compare_event_sources(dataset, "event-001")
for source in comparison.sources:
    print(source.title, source.source_type, source.url)
    for excerpt in source.evidence:
        print(excerpt.relation, excerpt.quotation, excerpt.page, excerpt.locator)

print("Evidence without locators:", comparison.evidence_missing_locators)
print("Recorded support/contradiction labels:",
      comparison.has_recorded_support_contradiction)
```

This is a side-by-side provenance view, not automatic source adjudication.
Conflicting labels are only those entered by a researcher; repeated accounts
may depend on one another. HistoryPy does not infer source independence or
decide which account is correct. Quotations and locators must be checked
against the original source and its rights conditions.


## BM25 ranked historical search

For queries where every word should not be required to appear literally, use the
BM25 index. It ranks partial-term matches and folds common accent differences:

~~~python
from historypy import BM25SearchIndex

bm25 = BM25SearchIndex.build(dataset)
for hit in bm25.search("réformes parlementaires", limit=10):
    print(hit.score, hit.label, hit.record_id, hit.matched_terms)
~~~

BM25 scores are relative retrieval scores, not confidence estimates or
historical-truth assessments. See docs/research-benchmarks.md for the measured
comparison against the existing trigram search and the real historical corpus.


To render a source-by-source evidence report with quotations and exact
citation positions:

~~~python
from historypy import render_event_source_comparison

print(render_event_source_comparison(dataset, "event-001"))
~~~

The report keeps researcher-entered support/contradiction labels and clearly
flags missing citation locations; it does not decide which source is correct.


## BM25 and real-corpus relevance evaluation

For natural-language queries where exact substring matching is too strict,
`BM25SearchIndex` provides accent-insensitive tokenization, OR-term retrieval,
document-length normalization, and deterministic score ordering. A BM25 score
is a ranking signal, not a probability or confidence estimate.

```python
from historypy import BM25SearchIndex

bm25 = BM25SearchIndex.build(dataset)
for hit in bm25.search("réformes parlement séance", kinds=("event",), limit=10):
    print(hit.record_id, hit.score, hit.matched_terms)
```

The reproducible HistoriQA-ThirdRepublic evaluation is documented in
`docs/research-benchmarks.md`. In the pinned 3,386-document / 1,782-question
benchmark run (Python 3.12), BM25 achieved Recall@10 **0.5564** and MRR@10
**0.4889**, compared with **0.0022** and **0.0015** for the strict all-terms
trigram substring baseline. BM25 Recall@10 was 0.8239 for single-hop questions,
but 0.2839 for comparative multi-hop questions and 0.2829 for bridge-entity
multi-hop questions. This is promising retrieval evidence, not proof of
historical correctness or general performance across languages and periods.

For comparing accounts of a specific event, use
`compare_event_sources(dataset, event_id)` or
`render_event_source_comparison(dataset, event_id)`. These group event-linked
sources and claim quotations by source, preserving researcher-entered support
or contradiction labels and exact page/paragraph/archive/timecode locators.
They do not automatically determine whether sources are independent or which
account is true.


## Hybrid and entity-aware retrieval

HistoryPy now provides conservative multi-hop query decomposition, exact
canonical-name/alias lookup for people and places, and reciprocal-rank fusion
across trigram and BM25 indexes with optional caller-supplied semantic vectors.
See [the retrieval guide](docs/hybrid-retrieval.md). Retrieval ranking is not
historical truth, and alias matches never automatically merge entities.


## Source comparison case study

See [the Titanic inquiry comparison](docs/source-comparison-case-study.md) for a worked example preserving two official reports' differing lifeboat-capacity and survivor totals with citation locators. The example deliberately does not adjudicate which figure is historically final.


## Held-out French and English multi-hop retrieval

The HistoriQA-ThirdRepublic benchmark now uses a deterministic, question-type-
stratified 80/20 held-out question split (seed 2026). It reports Trigram,
BM25, lexical RRF, and decomposed RRF separately on held-out questions. The
split is a question evaluation split, not a model-training split.

An English HotpotQA adapter is also included:

~~~bash
python benchmarks/benchmark_hotpotqa_retrieval.py --data hotpot_dev_distractor_v1.json --top-k 10
~~~

The GitHub Actions workflow downloads a pinned copy and verifies its checksum.
HotpotQA is a general English Wikipedia multi-hop dataset, not a history-only
corpus; its metrics are reported separately from the French historical corpus.
See docs/hybrid-retrieval.md and docs/research-benchmarks.md.

## Entity aliases, ambiguity, and cautious spelling suggestions

Researcher-supplied aliases support historical names and transliterations.
Fuzzy suggestions only surface possible spelling variants for human review;
they never merge records or assert identity.

~~~python
from historypy import EntityAwareSearchIndex

entities = EntityAwareSearchIndex.build(dataset)
exact_matches = entities.resolve("Alexandre")
review_candidates = entities.suggest("Alexandre", threshold=0.88)

for candidate in review_candidates:
    print(candidate.canonical_name, candidate.matched_alias,
          candidate.similarity, candidate.ambiguous)
~~~

When used in hybrid retrieval, pass an explicit threshold to opt in to fuzzy
entity candidates. Ambiguous aliases return every matching entity with an
ambiguity count; do not treat a name match as proof that two records refer to
the same person or place.

## Citation completeness and source dependence

Each SourceRecord can optionally record researcher-known source dependencies
and shared evidence groups:

~~~python
SourceRecord(
    id="later_report",
    title="Later report",
    source_type="secondary",
    derived_from_source_ids=("original_report",),
    shared_evidence_group_ids=("witness-interview-17",),
)
~~~

The provenance audit reports direct and transitive derivation plus shared-evidence pairs.
Unrecorded dependencies remain unknown; the audit does not infer independence.

~~~python
from historypy import audit_citation_completeness, audit_dataset_provenance

citations = audit_citation_completeness(dataset)
print(citations.complete_citation_coverage)
print(citations.missing_locator_indices)
print(citations.missing_quotation_indices)
print(citations.missing_source_url_indices)

provenance = audit_dataset_provenance(dataset)
print(provenance.potential_source_dependency_pairs)
~~~

Citation completeness requires a locator, quotation, and source URL for an
evidence link. It is a traceability measure, not a guarantee that the quotation
is authentic or that the source is reliable.

## SQLite WAL and durability diagnostics

The normalized SQLite store supports opt-in WAL mode, concurrent writers,
explicit WAL checkpoints, and database integrity checks:

~~~python
from historypy import NormalizedSQLiteStore

store = NormalizedSQLiteStore("history.sqlite", journal_mode="WAL")
store.save("research", dataset)
print(store.checkpoint_wal(mode="PASSIVE"))
print(store.integrity_check())

# Operational maintenance and a verified online backup:
print(store.maintenance_stats())
store.optimize()
store.backup_to("history-backup.sqlite")
~~~

The scale workflow tests DELETE and WAL modes at 100k and 1m synthetic records,
including reopen parity and broad/selective query timings. The online backup
uses SQLite's backup API and verifies the copied database with
`integrity_check`. Page/freelist statistics help monitor file growth and
reclaimable space. These tools do not replace off-site backup retention,
physical power-loss testing, or filesystem fault-injection testing.

## Optional real semantic model benchmark

Install the optional dependency and run the multilingual semantic benchmark:

~~~bash
python -m pip install ".[semantic]"
python benchmarks/benchmark_hybrid_retrieval.py \
  --corpus corpus_dataset.jsonl \
  --questions question_dataset.jsonl \
  --semantic-embedder benchmark_semantic_embedder:embed_texts \
  --semantic-model-id sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
~~~

The adapter uses CPU execution and loads the model lazily. The model is an
evaluation choice, not a historical source-quality or truth estimator. The
semantic workflow stores a machine-readable report as a GitHub Actions
artifact; report metrics, not the mere presence of the model, determine whether
semantic fusion is useful.


### Source independence inside claim analysis

The normal claim evidence analysis now includes the conservative source-genealogy report:

```python
from historypy import analyze_claim_evidence

analysis = analyze_claim_evidence(dataset, "claim-001")
print(analysis.assessment_status)  # support/contradiction coverage only
print(analysis.source_independence.status)
print(analysis.source_independence.dependent_clusters)
print(analysis.source_independence.unknown_source_ids)
```

A cluster means the cited sources have a recorded shared origin or derivation path.
Sources without a recorded relationship remain **unknown**, not independent.
Research reports show these groups and add a caution when dependence is known or
unknown; this does not change the claim's evidence status or assign a truth score.


### Versioned multilingual alias registry

For citation-backed aliases with researcher review metadata, use the separate
registry rather than treating every legacy string alias as verified:

```python
from historypy import AliasAssertion, AliasRegistry

registry = AliasRegistry(
    dataset,
    [AliasAssertion(
        alias_id="alias-001",
        entity_kind="person",
        entity_id="person-001",
        alias="Jeanne d’Arc",
        language="fr",
        alias_type="historical_name",
        source_id="source-001",
        locator="page 14",
        license="CC-BY-4.0",
        review_status="verified",
        reviewer="researcher-id",
        reviewed_at="2026-01-10",
    )],
    registry_version="aliases-1.0",
    dataset_version="dataset-2026-01",
)
print(registry.resolve("Jeanne d'Arc", language="fr"))
```

Verified aliases are returned by default. Candidate and disputed aliases require
an explicit opt-in, rejected aliases are excluded, and homonyms remain ambiguous.
Every alias assertion retains its source, locator, license, language, and review
status. The registry never merges entity records.


### Bounded multi-hop relationship paths

When the researcher already knows the canonical endpoint IDs, HistoryPy can
enumerate sourced relationship paths without guessing entities from prose:

```python
from historypy import RelationshipPathQuery, find_relationship_paths

report = find_relationship_paths(
    dataset,
    RelationshipPathQuery(
        "person-001", "place-001",
        max_hops=3,
        predicates=("member_of", None, "located_in"),
    ),
)
for path in report.paths:
    print(path.entity_ids, path.source_ids)
    print(path.relationships_missing_sources)
```

Each step retains its relationship ID, predicate, original direction, source
IDs, and validity dates. Unsourced edges are flagged. Paths are structural
hypotheses, not automatic historical conclusions; time-window compatibility
and free-text question planning are available as review-only workflows.


### Compare decomposition on French and English multi-hop retrieval

A paired held-out benchmark compares full-query hybrid retrieval against
decomposition-enabled hybrid retrieval on French HistoriQA and English
HotpotQA. It reports Recall@10 and MRR@10 before and after decomposition, with
per-language deltas and an equal-weight language macro-average.

```bash
python benchmarks/benchmark_multilingual_decomposition.py \
  --french-corpus path/to/french_corpus.jsonl \
  --french-questions path/to/french_questions.jsonl \
  --english-hotpotqa path/to/hotpotqa.json \
  --top-k 10 \
  --output multilingual_decomposition_report.json
```

No benchmark numbers are hard-coded: run it with the actual corpus files.


### Reviewable free-text multi-hop question workflow

```python
from historypy import ResearchPipeline

report = ResearchPipeline(dataset).run_question(
    "How was Ada Lovelace connected to Charles Babbage?",
    alias_registry=verified_alias_registry,  # optional
    predicate_lexicon={"collaborated_with": ("connected to", "worked with")},
    max_hops=3,
    direction="both",
    max_path_queries=40,
    max_explored_states=10000,
)
for review in report.path_reviews:
    print(review.path.entity_ids)
    print(review.temporal_status, review.source_independence.status)
    for hop in review.hops:
        print(hop.relationship_id, hop.predicate, hop.source_records)
        print(hop.claim_ids, hop.evidence_links, hop.claim_analyses)
```

Only exact canonical names and researcher-verified aliases become entity
candidates. Ambiguity, per-hop source records, path-wide source dependence,
and temporal compatibility are exposed for review. Predicate phrases are
candidate slots; path search remains unfiltered until the researcher confirms
the intended relation sequence. A path is not proof of historical truth.


Relationship records may link to claim records with `claim_ids=(...)`.
The multi-hop workflow then reports claim-level evidence coverage for each
hop. Missing claim links remain visible evidence gaps; source IDs alone are
not a substitute for locators, quotations, and claim-level evidence review.


Verified aliases can also participate in hybrid entity retrieval without
losing provenance:

```python
entity_index = EntityAwareSearchIndex.build(
    dataset, alias_registry=verified_alias_registry
)
hybrid = HybridSearchIndex(
    DatasetSearchIndex.build(dataset),
    BM25SearchIndex.build(dataset),
    entity_index=entity_index,
)
for hit in hybrid.search("Augusta Ada", entity_language="en"):
    print(hit.matched_entity_evidence)
```

Legacy aliases remain unverified; only reviewed registry assertions carry
verified status, alias IDs, source references, and citation locators.


Use `entity_language="fr"`, `"en"`, or another valid language tag to scope
verified registry aliases while keeping canonical entity-name matching.


Multi-hop question reviews also report claim-level contradictions, unsupported claims, missing locators, and a conservative path evidence status (`conflicting`, `contradicted`, `supported`, or `insufficient`). A contradicted hop cannot be masked by support on another hop; these labels summarize recorded evidence links and are not historical truth verdicts.


### Researcher-reviewed source genealogy

Use `SourceDependencyRegistry` to store cited, versioned dependency assertions for derivation, shared witnesses, shared archival records, syndication, and shared datasets. Only `verified` assertions affect independence analysis; candidate, disputed, and rejected assertions remain inert.

```python
registry = SourceDependencyRegistry(
    dataset,
    [SourceDependencyAssertion(
        assertion_id="genealogy-001",
        source_id="report-2",
        related_source_id="witness-1",
        dependency_type="derived_from",
        evidence_source_id="catalogue-1",
        locator="entry 42",
        license="CC-BY-4.0",
        review_status="verified",
        reviewer="researcher-1",
        reviewed_at="2026-11-25",
    )],
    registry_version="genealogy-1",
    dataset_version="dataset-1",
)
report = registry.audit_source_set(["report-2", "witness-1"])
```

The registry keeps the citation and review history separate from the applied dataset snapshot. It does not assign source credibility or determine historical truth.

### Multilingual alias candidate imports

`import_wikidata_alias_candidates` accepts a Wikidata JSON export plus an explicit QID-to-canonical-entity mapping. It imports Bengali, English, and French aliases as `candidate` assertions only, with CC0 metadata and revision-pinned locators when `lastrevid` is available. Human review against appropriate independent sources is required before verification.
