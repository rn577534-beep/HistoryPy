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
| `historypy.io` | Versioned JSON import/export and file persistence |
| `historypy.research.evidence` | Claim evidence retrieval and transparent conflict summaries |
| `historypy.research.query` | Lexical dataset search and date-overlap event queries |
| `historypy.research.entity_resolution` | Conservative possible-duplicate suggestions for human review |
| `historypy.research.source_audit` | Bibliographic metadata completeness checks, not credibility scores |

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

A claim and the evidence for it are separate records. An evidence link can be marked as `supports`, `contradicts`, `contextualizes`, or `mentions`.

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
