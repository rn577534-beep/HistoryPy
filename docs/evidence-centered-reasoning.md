# Evidence-centered historical reasoning

This design extends the existing retrieval, entity-resolution, graph, and provenance layers. It does not replace them.

> A good search result is not proof of historical truth.

## 1. Reasoning model: entity and relationship paths

A multi-hop question is represented as a sequence of typed slots:

- **Entity slot**: canonical entity ID, candidate IDs, mention text, language, ambiguity state.
- **Relationship slot**: predicate, direction, temporal scope, expected endpoint type.
- **Evidence obligation**: claim(s) and source evidence needed to support or contradict this hop.

A plan must retain the original question and expose every generated sub-question. Each hop is retrieved independently. The final path is assembled only when endpoint IDs and predicates are compatible. Missing or ambiguous hops remain explicit; the engine must not fill them by guesswork.

Every returned path component carries its claim IDs, evidence-link IDs, source IDs, citation locators, retrieval method/rank, and contradiction state. A retrieval score is never promoted to a truth probability.

## 2. Multilingual alias records

Existing string aliases remain useful for lightweight lookup, but a research-grade alias corpus needs a separately versioned record:

| Field | Meaning |
|---|---|
| alias_id | Stable identifier for this alias assertion |
| entity_kind / entity_id | Typed canonical entity reference |
| alias | Exact attested name form |
| language / script | BCP-47 language tag and writing system |
| alias_type | Transliteration, historical name, exonym/endonym, title, spelling variant, or other |
| source_id / locator | Traceable source and exact location supporting this alias |
| valid_from / valid_to | Optional period in which the form is attested |
| review_status | candidate, verified, rejected, or disputed |
| reviewer / reviewed_at | Human review provenance |
| dataset_version / license | Reproducibility and rights metadata |

Only a researcher-reviewed, citation-backed record may enter the verified alias index. Candidate generation and fuzzy matching must remain separate. Shared aliases can resolve to multiple entities; the system must preserve ambiguity and never auto-merge records.

Initial language coverage: Bengali, English, and French. Language coverage is not a quality claim: each alias needs evidence and review metadata.

## 3. Evidence independence

The existing `derived_from_source_ids` and `shared_evidence_group_ids` fields are the starting point. Extend source genealogy to represent relationships such as:

- copied or paraphrased from another publication;
- syndicated from the same wire-service dispatch;
- based on the same witness, interview, testimony, or oral account;
- reproducing the same archival document or dataset;
- independently created records (only when documented, not inferred from different publishers).

For a claim, evidence should be grouped by known shared origin before corroboration is summarized. A dependency family is not a credibility score and does not imply that every member says the same thing.

**Unknown is not independent.** If no dependency has been documented, report the dependency status as unknown. Do not treat unlinked sources as separate independent confirmations.

Reports should expose:
- total evidence links and unique cited sources;
- known dependency families and their recorded rationale;
- source IDs with unresolved/unknown dependence;
- supporting and contradicting evidence separately;
- locator and quotation completeness;
- any conflicts or missing evidence obligations.

Do not produce a single numerical historical-truth score.

## 4. Evaluation

### Multi-hop retrieval

Use identical held-out question IDs, corpus snapshots, tokenization, and top-k for baseline and decomposed/entity-aware runs. Report Recall@10 and MRR@10 overall and by language, hop count, and question type. Keep the original question as a retrieval anchor. Publish confidence intervals or per-question paired differences where sample size permits.

A decomposition rule is retained only when held-out results justify it; a better score on a training/development subset is not enough.

### Entity resolution

Evaluate exact and transliterated alias lookup against a reviewed gold set. Report precision, recall, ambiguity preservation, and false-merge count (the required false-merge count is zero because automatic merging is prohibited). Keep candidate and verified alias evaluation separate.

### Independence

Use adversarial fixtures:
1. several outlets repeating one wire-service report;
2. several books citing the same witness;
3. a primary document quoted by multiple secondary works;
4. distinct primary records with documented independent creation;
5. sources whose relationship is not known.

The expected result for case 5 is **unknown**, not independent corroboration.

## 5. Delivery sequence

1. Add explicit evidence-family analysis to the existing provenance audit, including unknown-dependence reporting.
2. Add versioned, citation-backed multilingual alias records and import/review tooling.
3. Add entity/relationship question plans and per-hop evidence obligations.
4. Add path assembly and contradiction-aware reports.
5. Run paired French and English held-out benchmarks and adversarial provenance tests.
6. Publish benchmark artifacts, dataset versions, model identifiers, and limitations.

## 6. Non-goals and safeguards

- No automatic historical identity merges.
- No automatic source credibility or truth scores.
- No inference that separate URLs, publishers, or article titles imply independent evidence.
- No claim that an LLM-generated sub-question is itself evidence.
- No silently resolved contradictions or missing hops.
- No bulk alias ingestion without source, license, and attribution review.

## 7. Implemented first slice: conservative source-independence audit

The feature branch now includes `historypy.research.source_independence` with:

- `analyze_claim_source_independence(dataset, claim_id)` for claim-level analysis;
- `audit_source_independence(dataset)` for deterministic dataset-wide summaries;
- typed reports for dependency clusters, source edges, bridge sources, and unknown sources;
- direct and transitive `derived_from_source_ids` detection;
- shared-evidence-group detection;
- explicit unknown statuses when dependency metadata is absent;
- adversarial tests for syndicated reports, transitive witness/document chains, mixed known/unknown dependencies, and claims without evidence.

The implementation deliberately does not infer independence. It only reports known dependence when a recorded genealogy path exists. A single source is also marked as dependence-unknown because it cannot corroborate itself.

Run the repository CI commands locally or through GitHub Actions before merging:

```bash
python -m pip install -e ".[dev]"
pytest
ruff check .
```

At this stage, the code and tests have been committed to the feature branch, but a passing CI result has not yet been observed.


## 8. Integrated claim and report analysis

The claim-level evidence analyzer now attaches a
`ClaimSourceIndependenceReport` as `ClaimEvidenceAnalysis.source_independence`.
The research pipeline's Markdown renderer prints known dependency clusters,
bridge context through the structured report, and unresolved source IDs. It
also adds explicit research-gap warnings for both known dependence and unknown
dependence. These warnings do not alter the claim's support/contradiction status
and do not convert retrieval or source counts into truth scores.

Example:

```python
from historypy.research import analyze_claim_evidence

analysis = analyze_claim_evidence(dataset, "claim-1")
print(analysis.source_independence.status)
print(analysis.source_independence.dependent_clusters)
print(analysis.source_independence.unknown_source_ids)
```

The integration test uses two reports in one shared-evidence group and a third
source with no genealogy metadata. The expected result is one known dependent
cluster plus one unknown source—not three independent confirmations.


## 9. Implemented multilingual alias registry slice

`historypy.research.alias_registry` adds a separate, versioned registry without
silently rewriting legacy entity aliases:

- `AliasAssertion` records typed entity IDs, exact alias text, BCP-47-style
  language tags, optional ISO 15924 script codes, alias type, source ID,
  locator, license, optional validity dates, and review provenance.
- Verified assertions require a reviewer and review date.
- Every assertion requires a source record, exact locator, and license.
- `AliasRegistry` checks entity/source references against the dataset and
  rejects duplicate alias assertion IDs.
- Exact lookup returns verified assertions by default. Candidate and disputed
  records are opt-in; rejected records are never returned.
- Homonyms remain separate results with an explicit ambiguity count.
- Versioned `to_dict` / `from_dict` interchange rejects unknown schema fields.
- No fuzzy match, identity merge, or automatic promotion to verified status.

Example:

```python
from historypy import AliasAssertion, AliasRegistry

registry = AliasRegistry(
    dataset,
    [AliasAssertion(
        alias_id="alias-fr-001",
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
matches = registry.resolve("Jeanne d'Arc", language="fr")
```

The registry is intentionally separate from the lightweight legacy alias
index. Integration into retrieval will preserve each alias assertion's review
state and citation rather than flattening verified, candidate, and disputed
forms into one undifferentiated string list.


## 10. Implemented entity/relationship multi-hop path planner

`historypy.research.relationship_paths` adds a bounded path engine over
canonical entity IDs and typed `HistoricalRelationship` records:

- Explicit start/end entity IDs; no guessed entity resolution from raw text.
- Per-hop predicate constraints, optional wildcard hops, and outgoing,
  incoming, or bidirectional traversal.
- Bounded simple paths (1–12 hops) and result limits (1–500).
- Every path step retains the original relationship ID, subject, predicate,
  object, traversal direction, source IDs, and validity dates.
- Relationships without source IDs are surfaced as evidence gaps.
- Search reports include explored-state counts and a truncation flag.
- Reverse traversal never rewrites the original subject/object direction.

Example:

```python
from historypy import RelationshipPathQuery, find_relationship_paths

report = find_relationship_paths(
    dataset,
    RelationshipPathQuery(
        start_entity_id="person-001",
        end_entity_id="place-001",
        max_hops=3,
        predicates=("member_of", None, "located_in"),
        direction="outgoing",
    ),
)
for path in report.paths:
    print(path.entity_ids, path.source_ids)
    print(path.relationships_missing_sources)
```

This is a structural path hypothesis, not proof that all edges are true,
temporally compatible, or causally connected. Validity intervals are retained
for downstream temporal review; the initial path planner does not yet enforce
a shared time window or automatically attach claim-level evidence obligations.
Free-text question parsing into entity and predicate slots remains a separate,
reviewable planning step.


## 11. Paired multilingual decomposition benchmark

`benchmarks/benchmark_multilingual_decomposition.py` now compares full-query
hybrid retrieval with decomposition-enabled hybrid retrieval on paired held-out
questions in:

- French: HistoriQA-ThirdRepublic.
- English: HotpotQA.

Both methods use the same per-language corpus, same deterministic
question-type-stratified held-out rows, same trigram + BM25 RRF index, and the
same top-k. The report contains Recall@10, MRR@10, success@10, and the absolute
decomposed-minus-baseline delta for each language, plus an unweighted language
macro-average.

Run:

```bash
python benchmarks/benchmark_multilingual_decomposition.py \
  --french-corpus path/to/french_corpus.jsonl \
  --french-questions path/to/french_questions.jsonl \
  --english-hotpotqa path/to/hotpotqa.json \
  --top-k 10 \
  --output multilingual_decomposition_report.json
```

The benchmark does not treat HotpotQA as a historical corpus, and it does not
treat gold document relevance labels as historical truth. French and English
datasets differ in domain and annotation; the macro-average weights each
language equally. No external semantic model is silently selected. A report
must be generated with the actual corpus files before any numerical performance
claim is made.


## 12. Reviewable free-text multi-hop question planning

`historypy.research.question_planner` connects free-text questions to the
existing entity, relationship, source-genealogy, and temporal models without
pretending that extraction is historical adjudication.

```python
from historypy import AliasRegistry, ResearchPipeline

pipeline = ResearchPipeline(dataset)

# Optional: pass a citation-backed registry. Only verified aliases are used.
plan_report = pipeline.run_question(
    "How was Ada Lovelace connected to Charles Babbage?",
    alias_registry=alias_registry,
    predicate_lexicon={
        "collaborated_with": ("connected to", "worked with"),
    },
    max_hops=3,
    limit=10,
    direction="both",
    max_path_queries=40,
    max_explored_states=10000,
)

for review in plan_report.path_reviews:
    print(review.path.entity_ids)
    print(review.temporal_status, review.temporal_note)
    print(review.source_independence.status)
    for hop in review.hops:
        print(hop.relationship_id, hop.predicate)
        print([source.id for source in hop.source_records])
        print(hop.source_independence.status)
```

The planner uses exact canonical entity names and exact **verified** alias
assertions only. Candidate, disputed, and rejected aliases are not promoted.
Homonyms remain separate candidates and are explicitly marked ambiguous.
Predicate lexicons are researcher-supplied; detected predicate phrases are
candidate slots, not automatic ontology assertions. Endpoint pairs generate
bounded path hypotheses (40 by default, configurable up to 200), and a hard
exploration budget per endpoint pair (10,000 states by default, configurable
up to 100,000). Truncated searches are explicitly flagged. Path searches remain
unfiltered until the researcher confirms the predicate sequence.

Each returned path includes:
- Per-hop source records, merged from relationship source IDs and linked
  claim-evidence source IDs, with source-genealogy audits.
- Exact `EvidenceLink` records (locator, quotation, relation, and source ID).
- Explicit `HistoricalRelationship.claim_ids` links to claim records.
- Per-hop `ClaimEvidenceAnalysis`, including support/contradiction coverage,
  source genealogy, and locator completeness.
- A path-wide source-genealogy audit, so dependencies crossing hop boundaries
  are not missed.
- A temporal intersection review: `compatible`, `incompatible`, or
  `unknown`. Missing dates or incomparable calendars remain unknown.
- Explicit warnings for ambiguous entities, missing source references,
  unknown source dependence, truncated searches, and temporal gaps.

Example output paths are structural hypotheses only. This workflow does not
write a historical answer, infer causality, or treat a connected path as proof.


### Claim-level evidence obligations for relationship hops

A relationship can now carry `claim_ids` in addition to `source_ids`. The
dataset validator checks these references. During multi-hop review, HistoryPy
loads the linked claims and runs the existing claim evidence analysis for each
hop. This exposes the underlying evidence links, source genealogy, and locator
coverage instead of treating a relationship's source list as a complete
citation. Relationships without linked claims are explicitly reported as
evidence gaps; legacy relationship records remain valid with an empty
`claim_ids` tuple.


### Verified aliases in entity-aware hybrid retrieval

The citation-backed registry can now be supplied when building
`EntityAwareSearchIndex`. Only verified registry assertions are promoted to
verified alias matches; legacy entity `aliases` remain marked unverified.
The provenance travels with the hybrid hit:

```python
from historypy import (
    BM25SearchIndex,
    DatasetSearchIndex,
    EntityAwareSearchIndex,
    HybridSearchIndex,
)

entity_index = EntityAwareSearchIndex.build(
    dataset,
    alias_registry=alias_registry,
)
hybrid = HybridSearchIndex(
    DatasetSearchIndex.build(dataset),
    BM25SearchIndex.build(dataset),
    entity_index=entity_index,
)
for hit in hybrid.search("Augusta Ada", entity_language="en"):
    for alias in hit.matched_entity_evidence:
        print(alias.review_status, alias.alias_id, alias.source_id, alias.locator)
```

The optional `entity_language` filter scopes verified aliases by language
tag while retaining canonical-name matches. This keeps the alias assertion ID,
review state, language, source ID, and locator available after retrieval. Fuzzy suggestions remain review-only and
are never silently promoted into verified alias assertions.


### Contradiction and missing-evidence diagnostics

Multi-hop reviews expose conservative diagnostics derived only from the recorded `EvidenceLink.relation` values:

- `hop.conflicting_claim_ids`: claims with both `supports` and `contradicts` links.
- `hop.contradicted_claim_ids`: claims with contradicting links and no supporting link.
- `hop.unsupported_claim_ids`: claims with no supporting link (including contextualizing-only and mentioning-only evidence).
- `hop.claims_missing_locators`: claims with no evidence links or at least one evidence link without a structured/free-form locator.
- `path.evidence_status`: `conflicting`, `contradicted`, `supported`, or `insufficient`, aggregated conservatively across all hops.
- `path.conflicting_claim_ids`, `path.unsupported_claim_ids`, and `path.claims_missing_locators` provide path-wide identifiers.

The aggregation fails closed: a contradicted hop cannot be hidden by a different supported hop. A mixed claim is labeled conflicting rather than resolved automatically. These statuses describe the dataset's recorded links; they do not establish whether the claim is historically true. Missing relationship-to-claim links remain an explicit gap, not implicit support.

```python
for review in plan_report.path_reviews:
    print(review.evidence_status)
    print(review.conflicting_claim_ids)
    print(review.unsupported_claim_ids)
    print(review.claims_missing_locators)
    for hop in review.hops:
        print(hop.contradicted_claim_ids, hop.missing_claim_link)
```


### Explicit temporal filtering policies

Temporal review remains non-destructive by default: execution reports retain every candidate path. Researchers can apply an explicit policy afterward with `select_paths_by_temporal_policy`:

```python
from historypy import select_paths_by_temporal_policy

# Remove only known-incompatible paths; unknown-date paths remain included.
selection = select_paths_by_temporal_policy(
    plan_report.path_reviews,
    policy="exclude_incompatible",
)

# Strict mode: keep only paths whose recorded intervals are compatible.
strict = select_paths_by_temporal_policy(
    plan_report.path_reviews,
    policy="compatible_only",
)
print(len(strict.excluded_unknown))  # unknown paths are reported, not hidden
```

The policy is mandatory. `all` retains every path; `exclude_incompatible` removes only known conflicts and retains unknown dates; `compatible_only` excludes both incompatible and unknown paths. Excluded records remain available in `TemporalPathSelection`, so the caller can audit what was filtered. No policy converts unknown into compatible.


## 13. Importing multilingual alias candidates without auto-verification

The Wikidata alias importer provides a reproducible way to seed Bengali, English, and French review queues. It requires an explicit QID-to-canonical-entity mapping supplied by the researcher. It imports alias strings only, preserves the Wikidata item URL and language/script metadata, and marks every row as `candidate` with CC0-1.0 metadata. It never marks an alias verified and never merges entities.

```python
from historypy import import_wikidata_alias_candidates

export_data = {
    "entities": [
        {
            "id": "Q7186",
            "aliases": {
                "bn": [{"value": "মারি কুরি"}],
                "en": [{"value": "Madame Curie"}],
                "fr": [{"value": "Marie Skłodowska"}],
            },
        }
    ]
}

updated_dataset, candidates = import_wikidata_alias_candidates(
    dataset,
    export_data,
    {"Q7186": ("person", "person-marie-curie")},
    registry_version="wikidata-candidates-1",
    dataset_version="history-dataset-1",
)

# Candidate rows are review-only; default resolve() will not return them.
print(candidates.resolve("Madame Curie"))
print(candidates.resolve("Madame Curie", include_unverified=True))
```

The importer's mapping is the identity boundary: unmatched QIDs are ignored, and a mapped target must already exist in the dataset. The source locator points to the Wikidata item's language-specific alias section. When the export contains a valid lastrevid, the importer pins the source URL, source ID, and locator to that exact revision; otherwise it labels the source as current so the snapshot limitation remains visible. Wikidata data is useful for candidate discovery, not sufficient by itself to establish historical usage or a disputed identity. A researcher must verify each candidate against suitable independent authority, scholarly, or primary sources before changing its review status.


## 14. Researcher-reviewed source genealogy assertions

Source genealogy can now be curated in a separate, versioned registry instead of writing unreviewed dependency metadata directly into source records. Each assertion records the two related source IDs, dependency type, a citation source ID and locator, license, review state, and optional reviewer/date. Supported types include direct derivation, shared witness, shared archive record, syndication, and shared dataset.

```python
from historypy import (
    SourceDependencyAssertion,
    SourceDependencyRegistry,
    analyze_source_set_independence,
)

registry = SourceDependencyRegistry(
    dataset,
    [SourceDependencyAssertion(
        assertion_id="genealogy-001",
        source_id="report-2",
        related_source_id="witness-1",
        dependency_type="derived_from",
        evidence_source_id="archive-catalogue",
        locator="entry 42",
        license="CC-BY-4.0",
        review_status="verified",
        reviewer="historian-1",
        reviewed_at="2026-11-25",
    )],
    registry_version="genealogy-1",
    dataset_version="history-dataset-1",
)

# Only verified assertions change the derived dataset.
report = registry.audit_source_set(["report-2", "witness-1"])

# Or inspect the annotated snapshot explicitly:
annotated_dataset = registry.apply_verified()
```

Shared-witness, shared-archive, syndication, and shared-dataset assertions require an explicit shared group ID. Candidate, disputed, and rejected assertions remain review data and are not applied. The original dataset is never mutated. Keep the registry alongside the dataset so reviewers can inspect the citation and decision behind every applied dependency edge. This metadata audit identifies recorded dependence; it does not rate credibility or determine historical truth.
