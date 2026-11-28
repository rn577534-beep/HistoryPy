# Multilingual entity resolution

HistoryPy keeps entity identity separate from spelling similarity. Canonical
names, legacy aliases, and citation-backed AliasAssertion records have
different provenance and review states.

## Verified alias-aware duplicate suggestions

Use AliasRegistry with suggest_entity_matches to include researcher-verified
aliases when comparing two records of the same entity type:

~~~python
from historypy import suggest_entity_matches

candidates = suggest_entity_matches(
    dataset,
    kinds=("person", "place", "organization"),
    threshold=0.88,
    alias_registry=verified_alias_registry,
)
for item in candidates:
    print(item.left_name, item.right_name, item.similarity)
    print(item.matched_names, item.matched_alias_ids, item.matched_languages)
    print(item.matched_review_statuses, item.ambiguous_alias)
~~~

Only verified registry aliases are included by default. Candidate and disputed
aliases can be included for a separate review queue by setting
include_unverified_aliases=True; rejected aliases are always excluded.
The returned candidate records preserve the alias IDs, languages, and review
statuses that produced the best lexical match.

## Ambiguity and transliteration policy

A shared alias can refer to more than one entity. Such suggestions set
ambiguous_alias=True when the matched registry alias is shared by multiple
entity records. Do not interpret that as a duplicate decision.

Cross-script forms such as Bengali transliterations of English or Arabic names
must be added as explicit, sourced alias assertions. HistoryPy does not invent
transliterations or merge entities automatically. Use source IDs, page or
catalogue locators, rights metadata, reviewer identity, and review date for
verified assertions. Keep homonyms as separate records until historical
context establishes whether they refer to the same person or place.

## Benchmarking

benchmarks/benchmark_entity_resolution.py evaluates name-pair similarity
against a researcher-reviewed JSONL gold set with language-specific precision,
recall, F1, and false-positive rate. The labels must be independently
reviewed and split into tuning and held-out sets. A similarity score is not a
probability of identity.

No real-world Bengali-English precision/recall result is published until a
licensed, researcher-reviewed bilingual pair set exists. Unit tests use
synthetic fixtures only and are not evidence of real-world accuracy.
