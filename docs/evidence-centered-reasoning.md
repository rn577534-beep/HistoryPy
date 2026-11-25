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
