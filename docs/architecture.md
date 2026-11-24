# HistoryPy architecture

## Mission

HistoryPy is an evidence-aware Python toolkit for organizing and analyzing historical information. It is not an authority that declares historical truth. It keeps historical records, sources, evidence, researcher interpretations, and computational results distinct.

## Architecture layers

1. **Core records** — dates, events, claims, sources, evidence, people, places, civilizations, organizations, and relationships.
2. **Dataset integrity** — in-memory collections with stable identifiers and referential-integrity diagnostics.
3. **Chronology** — bounded dates, BCE/CE astronomical year numbering, calendar labels, and overlap detection.
4. **Knowledge graph** — directed, typed relationships, graph traversal, shortest paths, and connected components.
5. **Research tools** — evidence retrieval, conflict summaries, lexical search, and event/date overlap queries.
6. **Interchange** — versioned JSON serialization, validation on import, and UTF-8 file persistence.
7. **Future interfaces and analysis** — source comparison, entity resolution, geographic analysis, network measures, CSV interchange, command-line tools, APIs, notebooks, and visual research interfaces.

## Evidence model

A claim must not be considered verified merely because it appears in multiple records. Capture source identity, source type, date, creator, provenance, relevant passage or archive locator, relationship to the claim, and researcher notes. Independent corroboration must be distinguished from multiple sources repeating one earlier account. Contradictory evidence must remain queryable.

## Chronology model

ISO bounds represent Gregorian calendar dates. BCE and year-only dates can use astronomical year numbering: 1 CE = 1, 1 BCE = 0, 2 BCE = -1. Original expressions and calendar names must be preserved. Date overlap returns an indeterminate result when dates are unbounded or calendars are incompatible or unspecified. The library never silently converts calendars.

## Entity and graph model

People, places, civilizations, and organizations have stable IDs and source references. A civilization is a research category whose boundaries and identity may be debated. Relationships are directed and typed by a predicate, may include validity dates, and can retain a confidence estimate as metadata—not as proof. Graph traversal does not infer missing edges or score historical truth.

## Dataset validation

`HistoricalDataset.validate()` reports duplicate IDs and broken references without modifying or deleting records. `require_valid()` raises a summarized error for workflows that require referential integrity. Validation is structural, not a verification of historical accuracy.

## Research queries

`search_dataset()` performs deterministic, case-insensitive lexical retrieval. All query terms must appear in the combined searchable fields. It is not semantic search and does not resolve entities. `events_overlapping()` uses the date model's three-valued overlap result: true, false, or indeterminate. Indeterminate events are omitted unless explicitly requested.

## Evidence analysis

The `research.evidence` module retrieves evidence links for a claim and summarizes source IDs by relation. It can identify claims with both supporting and contradicting links. These are descriptive summaries, not credibility rankings; source independence, provenance, author expertise, genre, bias, and context require scholarly assessment.

## Data interchange

The JSON format uses schema identifier `historypy.dataset` and a numeric schema version. Import rejects unknown fields and unsupported versions. Referential integrity is checked by default; validation can be bypassed explicitly for repair workflows. Future incompatible changes require a version increment and migration documentation.

## Data governance

Every imported dataset should record its source and maintainer, license and permitted use, retrieval date and version, transformation script, and known coverage gaps or biases. Do not commit copyrighted books, scans, or restricted datasets without permission.

## Current implementation

The early 0.1.x codebase includes dependency-light core records, chronology operations, entity records, dataset validation, relationship graph analysis, evidence summaries, lexical and temporal research queries, versioned JSON import/export, and automated tests. It does not include a comprehensive historical dataset, calendar-conversion engine, geospatial index, semantic search, automatic source authentication, or entity resolution.
