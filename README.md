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
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    HistoricalPlace,
    HistoricalRelationship,
    HistoricalDataset,
    RelationshipGraph,
)

person = HistoricalPerson(id="person-001", name="Example historical person")
place = HistoricalPlace(id="place-001", name="Example historical place")

event = HistoricalEvent(
    id="event-001",
    title="Example event",
    date=HistoricalDate(
        earliest="1947-08-14",
        latest="1947-08-14",
        precision="day",
        calendar="gregorian",
    ),
    place_ids=(place.id,),
)

relationship = HistoricalRelationship(
    id="relationship-001",
    subject_id=person.id,
    predicate="associated_with",
    object_id=place.id,
)

dataset = HistoricalDataset(
    people=(person,),
    places=(place,),
    events=(event,),
    relationships=(relationship,),
)
dataset.require_valid()

graph = RelationshipGraph(
    entity_ids=(person.id, place.id, event.id),
    relationships=(relationship,),
)
print(graph.neighbors(person.id))
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
| `historypy.research` | Claim evidence retrieval and conflict summaries without truth scoring |

## Evidence workflow

A claim and the evidence for it are separate records. An evidence link can be marked as:

- `supports`
- `contradicts`
- `contextualizes`
- `mentions`

The library stores source metadata and locators, but does not independently authenticate sources or decide historical truth. Multiple sources repeating the same earlier account are not automatically independent corroboration.

Use the evidence analysis helpers to inspect the links without collapsing disagreement:

```python
from historypy import summarize_claim_evidence, claims_with_conflicting_evidence

summary = summarize_claim_evidence(dataset, "claim-001")
print(summary.supporting_source_ids)
print(summary.contradicting_source_ids)
print(summary.has_conflicting_evidence)

conflicts = claims_with_conflicting_evidence(dataset)
```

These summaries count linked sources and relationships; they are not automated credibility scores.

## Dataset validation

```python
issues = dataset.validate()
if issues:
    for issue in issues:
        print(issue.code, issue.record_id, issue.message)
else:
    print("Dataset structure is valid")
```

Validation checks identifiers and references. It does not certify the historical accuracy of a record.

## JSON interchange

```python
from historypy import save_dataset, load_dataset, dataset_to_json, dataset_from_json

save_dataset(dataset, "research-dataset.json")
restored = load_dataset("research-dataset.json")

payload = dataset_to_json(dataset)
restored_again = dataset_from_json(payload)
```

The JSON format declares the schema name and version. Unknown schema versions and unknown record fields are rejected. Import validates references by default; use `validate=False` only when deliberately loading a dataset for repair.

## Chronology notes

- ISO date bounds represent Gregorian calendar dates.
- BCE/year-only dates use astronomical year numbering: 1 CE = 1, 1 BCE = 0, 2 BCE = -1.
- Calendar names are explicit metadata; no implicit calendar conversion is performed.
- Date overlap returns `None` when comparison cannot safely be established.

## Development status

Early development / pre-alpha. APIs may change. This repository does not yet ship a comprehensive historical dataset, a calendar-conversion engine, automatic source authentication, or a production research database.

See [architecture](docs/architecture.md) and [contribution guidelines](CONTRIBUTING.md).


## Automated checks

The repository currently includes 44 test cases covering chronology, BCE date handling, entity validation, dataset references, graph traversal, evidence conflict summaries, and JSON round trips. GitHub Actions is configured to run the test suite and Ruff on Python 3.10–3.13.

A configured workflow is not the same as a verified passing run. Check the Actions tab for the latest execution before treating a commit as release-ready.
