# Stepwise historical dossier engine

HistoryPy can turn an already curated `HistoricalDataset` into a structured,
reviewable historical dossier. The engine is deliberately deterministic: it
organizes records and provenance but does not invent facts, causal explanations,
or historical conclusions.

## Workflow

1. **Scope** — give the dossier a title and scope note.
2. **Chronology** — order event records by their stored date intervals. Calendar
   metadata and uncertain or missing dates remain visible.
3. **Event chapters** — create one chapter per event.
4. **Entities and geography** — attach places from each event's explicit
   `place_ids`; attach organizations and civilizations only through their
   recorded place references. People are attached only through explicit
   relationships to the event.
5. **Claims** — attach a claim to an event only when its `event_ids` contains
   that event ID. Claims without event links remain in a separate section.
6. **Evidence** — preserve each evidence relation, source ID, quotation and
   locator. Supporting and contradicting links remain separate.
7. **Source catalogue** — include event and claim sources with available
   bibliographic metadata.
8. **Quality and gaps** — expose dataset validation issues, quality warnings,
   undated events and claims with insufficient or mixed recorded evidence.
9. **Interpretation protocol** — remind the researcher to inspect original
   sources, source genealogy, conflicting accounts and uncertain dates.

No relationship is inferred from similar names, co-occurrence, geographic
proximity or overlapping dates. An event's summary is displayed exactly as
entered by the researcher.

## Python example

```python
from historypy import (
    HistoricalDataset,
    build_historical_dossier,
    render_historical_dossier,
    load_dataset,
)

dataset = load_dataset("research.json")
dossier = build_historical_dossier(
    dataset,
    title="A study of a historical period",
    scope_note="Geographic and chronological boundaries of this study.",
)
markdown = render_historical_dossier(dossier)

with open("historical-dossier.md", "w", encoding="utf-8") as handle:
    handle.write(markdown)
```

## Output contract

The structured `HistoricalDossier` contains:

- `timeline` and chronological `chapters`;
- each chapter's event, explicitly linked claims, people, places, organizations,
  civilizations and sources;
- `unassigned_claims` that have not been attached to an event;
- dataset `quality` findings and `validation_issues`;
- global entity and source catalogues;
- `research_gaps` that need researcher attention.

Claim assessment values such as `supported`, `contradicted`, `mixed`, and
`insufficient` describe only the direction of evidence links currently stored
in the dataset. They are not probabilities and are not verdicts on truth.
Likewise, the quality report measures documentation and structural completeness,
not historical accuracy.

The engine is only as complete as its input dataset. It does not search the web,
download books, authenticate archival material, translate source texts, or
write a causal narrative. Those are separate research steps; results should be
reviewed and entered as sourced records before dossier assembly.

## Command-line use

After installing HistoryPy, build the same report without writing Python code:

```bash
historypy dossier research.json \
  --title "A study of a historical period" \
  --scope-note "Geographic and chronological boundaries." \
  --output historical-dossier.md
```

By default, events with indeterminate dates remain included and are identified
as such. Add `--exclude-indeterminate-dates` to omit them from the chronological
chapters; the report still counts them as a research gap. Omit `--output` to
write Markdown to standard output.
