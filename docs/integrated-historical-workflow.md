# Integrated historical research workflow

HistoryPy now has an end-to-end coordinator that joins existing local search,
optional semantic retrieval, book/news/archive APIs, multi-hop question review,
source URL/quotation checks, and the stepwise historical dossier renderer.

## Python use

```python
from historypy import (
    HistoricalResearchWorkflow,
    ResearchQueryVariant,
    render_integrated_research_report,
    save_dataset,
)
from historypy.io import load_dataset

dataset = load_dataset("research.json")
workflow = HistoricalResearchWorkflow(dataset)  # constructs public API adapters; no request yet
report = workflow.run(
    "What events led to the historical transition?",
    query_variants=(
        ResearchQueryVariant("ঐতিহাসিক পরিবর্তনের পেছনে কী ঘটনা ছিল?", "bn"),
        ResearchQueryVariant("events leading to the transition", "en", "keyword"),
    ),
    dossier_title="Historical transition research",
    scope_note="Define the region, period, and research boundaries here.",
    include_external=True,
    verify_sources=True,
)
markdown = render_integrated_research_report(report)
with open("research-report.md", "w", encoding="utf-8") as handle:
    handle.write(markdown)
```

The default provider factory constructs adapters for Open Library, Gutendex /
Project Gutenberg metadata, GDELT news metadata, English and Bengali
MediaWiki, Library of Congress, Internet Archive, and Wikidata. Guardian
News is added only when GUARDIAN_API_KEY is configured. Constructing adapters
does not make network calls; run() does. Pass providers=() to disable the
default provider set and inject only providers you have selected.

## CLI

```bash
historypy research research.json "What happened in this period?" \
  --variant "bn=এই সময়ে কী ঘটেছিল?" \
  --variant "en=events during this period" \
  --title "Research dossier" \
  --scope-note "Region and date boundaries" \
  --output research-report.md
```

Use `--no-external` to skip catalog/news requests and `--no-source-check` to
skip live URL checks. Add `--format json` for a structured session export.
For an offline smoke test, use both flags.

## Multilingual retrieval policy

- The original question is always retained as the anchor query.
- Translations, transliterations, historical aliases, and keyword variants
  are explicitly supplied by the researcher using ResearchQueryVariant or
  repeated CLI --variant LANG=TEXT arguments.
- HistoryPy does not pretend to translate text automatically. Translation
  errors can change historical names and meanings.
- Cross-lingual semantic search works only when the caller supplies a
  multilingual embedding model and builds the semantic index in the same
  embedding space. Similarity is a retrieval signal, not a truth score.
- Verified aliases can be supplied through AliasRegistry. Unreviewed names
  are not silently merged.

## Discovery candidates and source selection

External API results remain discovery candidates. They are deduplicated and
metadata disagreements are surfaced, but are not automatically inserted into
the dataset or linked to claims. To import selected catalogue results:

```python
from historypy import select_external_sources

updated_dataset = select_external_sources(
    dataset,
    report,
    selections=(
        ("Open Library", "/works/OL...W"),
        ("Project Gutenberg (Gutendex)", "12345"),
    ),
)
```

Selection adds bibliographic SourceRecord entries only. It does not create
EvidenceLink objects, claim support, or independence assertions. Inspect the
original work, establish the correct edition and rights, then manually add
claim-specific evidence with page, paragraph, or archival locators. Source
genealogy must be reviewed before counting sources as independent.

## Verification semantics and limitations

- Existing evidence-linked source URLs are checked with HistoryPy's bounded
  HTTP(S) verifier. Exact quotation matching is case-folded and whitespace
  normalized; a match does not authenticate the source or prove context.
- A URL reachability failure does not mean a source is false; a reachable page
  does not mean its content is reliable.
- Newly discovered metadata candidates are not fetched as full text and are
  not quotation-verified by this workflow. Attach them to a claim with a
  locator after researcher inspection, then run verification again.
- The multi-hop question planner reviews only relationships and verified
  aliases already present in the local dataset. External discovery results
  do not silently become graph edges.
- The final dossier is assembled from the curated dataset. Search results,
  missing evidence, conflicts, uncertain dates, and provider failures remain
  separate and visible.

The workflow never copies full copyrighted books or news articles. It uses
catalogue metadata and original publisher/archive links, subject to each
provider's terms, rate limits, and item-level rights.
