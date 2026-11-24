# HistoryPy architecture

## Design goals

HistoryPy is a research toolkit, not an authority that declares historical truth. Keep separate:

- a historical event or claim;
- a source that reports or discusses it;
- evidence extracted from that source;
- a researcher's interpretation;
- an analytical result produced by software.

## Planned layers

1. Core models: identifiers and typed records for events, people, places, sources, claims, and evidence.
2. Chronology: date intervals, calendar metadata, periodization, and documented conversion rules.
3. Knowledge base: versioned datasets with provenance and licensing metadata.
4. Research engines: source comparison, entity resolution, chronology checks, geographic and network analysis.
5. Interfaces: Python API first; command-line, web API, and visual research tools later.

## Evidence model

A claim must not be considered verified merely because it appears in multiple records. Capture source identity, source type, date, creator, provenance, relevant passage or archive locator, relationship to the claim, and researcher notes.

Independent corroboration must be distinguished from multiple sources repeating one earlier account. Contradictory evidence must remain queryable.

## Chronology model

Normalized ISO dates are useful for computation but insufficient for every historical calendar or uncertain date. Records therefore retain calendar metadata and an original date expression. Calendar conversion must be an explicit, tested operation; this release does not silently convert calendars.

## Data governance

Every imported dataset should record its source and maintainer, license and permitted use, retrieval date and version, transformation script, and known coverage gaps or biases. Do not commit copyrighted books, scans, or restricted datasets without permission.

## Current implementation

Version 0.1.0 contains dependency-free core dataclasses for historical dates, events, source records, and evidence links, plus basic interval overlap behavior and tests.

## Next milestones

- Add claims as first-class records.
- Add people, places, organizations, and relationships.
- Add calendar-aware chronology adapters.
- Add source catalog import/export.
- Add validation rules and dataset quality reports.
- Establish benchmark datasets with documented ground truth and known ambiguity.
