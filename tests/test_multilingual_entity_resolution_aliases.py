from historypy import HistoricalDataset, HistoricalPerson, SourceRecord
from historypy.research import AliasAssertion, AliasRegistry, suggest_entity_matches


def _dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord("source-a", "Catalogue A", "tertiary"),
            SourceRecord("source-b", "Catalogue B", "tertiary"),
        ),
        people=(
            HistoricalPerson("person-a", "Saladin"),
            HistoricalPerson("person-b", "Salah ad-Din"),
        ),
    )


def _registry(dataset, status="verified"):
    return AliasRegistry(
        dataset,
        (
            AliasAssertion(
                alias_id="alias-a",
                entity_kind="person",
                entity_id="person-a",
                alias="সালাহউদ্দিন",
                language="bn",
                alias_type="transliteration",
                source_id="source-a",
                locator="catalogue entry A",
                license="CC0",
                review_status=status,
                reviewer="reviewer-a" if status == "verified" else None,
                reviewed_at="2026-01-01" if status == "verified" else None,
            ),
            AliasAssertion(
                alias_id="alias-b",
                entity_kind="person",
                entity_id="person-b",
                alias="সালাহউদ্দিন",
                language="bn",
                alias_type="transliteration",
                source_id="source-b",
                locator="catalogue entry B",
                license="CC0",
                review_status=status,
                reviewer="reviewer-b" if status == "verified" else None,
                reviewed_at="2026-01-02" if status == "verified" else None,
            ),
        ),
        registry_version="aliases-1",
        dataset_version="dataset-1",
    )


def test_verified_bengali_aliases_are_used_in_duplicate_candidate_generation():
    dataset = _dataset()
    registry = _registry(dataset)

    candidates = suggest_entity_matches(
        dataset, kinds=("person",), threshold=0.99, alias_registry=registry
    )

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate.left_id == "person-a"
    assert candidate.right_id == "person-b"
    assert candidate.matched_names == ("সালাহউদ্দিন", "সালাহউদ্দিন")
    assert candidate.matched_alias_ids == ("alias-a", "alias-b")
    assert candidate.matched_languages == ("bn", "bn")
    assert candidate.matched_review_statuses == ("verified", "verified")
    assert candidate.ambiguous_alias is True
    # Suggestions never merge or delete the underlying entities.
    assert len(dataset.people) == 2


def test_candidate_aliases_are_excluded_until_explicitly_included():
    dataset = _dataset()
    registry = _registry(dataset, status="candidate")

    assert suggest_entity_matches(
        dataset, kinds=("person",), threshold=0.99, alias_registry=registry
    ) == ()

    candidates = suggest_entity_matches(
        dataset,
        kinds=("person",),
        threshold=0.99,
        alias_registry=registry,
        include_unverified_aliases=True,
    )
    assert len(candidates) == 1
    assert candidates[0].matched_review_statuses == ("candidate", "candidate")
    assert candidates[0].ambiguous_alias is True
