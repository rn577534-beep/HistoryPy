# HistoryPy JSON dataset format

## Envelope

Every exported dataset uses a versioned JSON envelope:

- schema: `historypy.dataset`
- schema_version: `1`
- metadata: string-to-string dataset metadata
- collections: arrays of typed records

The version field is mandatory. Readers reject unsupported versions rather than guessing how to interpret an unfamiliar schema.

## Collections

| Collection | Record type | Identifier |
|---|---|---|
| sources | SourceRecord | id |
| claims | HistoricalClaim | id |
| events | HistoricalEvent | id |
| people | HistoricalPerson | id |
| places | HistoricalPlace | id |
| civilizations | HistoricalCivilization | id |
| organizations | HistoricalOrganization | id |
| relationships | HistoricalRelationship | id |
| evidence | EvidenceLink | claim_id + source_id + relation |

Entity IDs must be unique across events, people, places, civilizations, and organizations. Each record's source references must resolve to a source in the same dataset.

## Dates

Dates are JSON objects with explicit fields for normalized bounds, calendar, precision, circa status, and the original expression. Optional date values are represented by null. BCE/year-only bounds use astronomical year numbering; for example, 1 BCE is year 0.

ISO bounds must be canonical YYYY-MM-DD strings. They represent Gregorian dates. The calendar field is never silently converted by the library.

## Evidence

Evidence links connect a claim to a source and use one of four relations:

- supports
- contradicts
- contextualizes
- mentions

The locator should identify a page, folio, inscription line, catalogue number, timestamp, or other reproducible location. Quotations should be brief and comply with source copyright and access conditions.

## Import behavior

JSON parsing rejects unknown dataset fields, unknown record fields, invalid date objects, and unsupported schema versions. By default, referential integrity is checked after parsing. Use validation bypass only when intentionally loading an incomplete dataset for repair.

## Compatibility policy

A future incompatible data-format change must increment schema_version and provide a documented migration path. Never reinterpret old date values or relationship predicates silently.
