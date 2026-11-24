# HistoryPy architecture

## Mission

HistoryPy is an evidence-aware Python toolkit for organizing and analyzing historical information. It is not an authority that declares historical truth. It keeps historical records, sources, evidence, researcher interpretations, and computational results distinct.

## Architecture layers

1. **Core records** — dates, events, claims, sources, evidence, people, places, civilizations, organizations, and relationships.
2. **Dataset integrity** — in-memory collections with stable identifiers and referential-integrity diagnostics.
3. **Chronology** — bounded dates, BCE/CE astronomical year numbering, calendar labels, event ordering, and overlap detection.
4. **Knowledge graph** — directed, typed relationships, graph traversal, shortest paths, and connected components.
5. **Research tools** — evidence retrieval and transparent summaries of supporting, contradicting, contextualizing, and mentioning sources. These summaries do not assign a truth score.
6. **Interchange** — versioned JSON serialization, validation on import, and UTF-8 file persistence.
7. **Future interfaces and analysis** — source comparison, entity resolution, geographic analysis, network measures, CSV interchange, command-line tools, APIs, notebooks, and visual research interfaces.

## Evidence model

A claim must not be considered verified merely because it appears in multiple records. Capture source identity, source type, date, creator, provenance, relevant passage or archive locator, relationship to the claim, and researcher notes. Independent corroboration must be distinguished from multiple sources repeating one earlier account. Contradictory evidence must remain queryable.

## Chronology model

ISO bounds represent Gregorian calendar dates. BCE and year-only dates can use astronomical year numbering: 1 CE = 1, 1 BCE = 0, 2 BCE = -1. Original expressions and calendar names must be preserved. The current overlap operation returns an indeterminate result when dates are unbounded or calendars are incompatible or unspecified. It never silently converts calendars.

## Entity model

People, places, civilizations, and organizations have stable IDs and source references. Place coordinates are optional and validated when supplied. A civilization is a research category whose boundaries and identity may be debated; records should preserve that uncertainty in descriptions and source links. Relationships are directed and typed by a predicate, may include validity dates, and can retain a confidence estimate as metadata—not as proof.

## Dataset validation

HistoricalDataset.validate() reports duplicate IDs and broken references without modifying or deleting records. require_valid() raises a summarized error for workflows that require referential integrity. Validation checks are structural; they do not establish historical accuracy.

## Graph analysis

RelationshipGraph provides deterministic neighbor lookup, predicate filtering, breadth-first shortest paths, and weakly connected components. It treats relationships as directed unless callers request incoming or bidirectional traversal. Graph construction from a HistoricalDataset requires valid references. The graph layer does not infer missing edges or score historical truth.

## Evidence analysis

The research.evidence module retrieves all evidence links for a claim and summarizes source IDs by relation. It can identify claims with both supporting and contradicting links. These are transparent descriptive summaries, not credibility rankings: source independence, provenance, author expertise, genre, bias, and context still require scholarly assessment.

## Data interchange

The JSON format uses the schema identifier historypy.dataset and a numeric schema version. Import rejects unknown fields and unsupported versions. Referential integrity is checked by default; validation can be bypassed explicitly for repair workflows. Future incompatible changes require a version increment and migration documentation.

## Data governance

Every imported dataset should record its source and maintainer, license and permitted use, retrieval date and version, transformation script, and known coverage gaps or biases. Do not commit copyrighted books, scans, or restricted datasets without permission.

## Current implementation

The early 0.1.x codebase includes dependency-light core records, chronology operations, entity records, dataset validation, relationship graph analysis, evidence summaries, versioned JSON import/export, an example dataset builder, and automated tests. It does not yet include a comprehensive historical dataset, calendar-conversion engine, geospatial index, or automatic source authentication.
