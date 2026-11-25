import pytest

from historypy import HistoricalDataset, HistoricalPerson, HistoricalPlace, SourceRecord
from historypy.research.alias_registry import AliasAssertion, AliasRegistry


def _registry():
    dataset = HistoricalDataset(
        sources=(
            SourceRecord("src-book", "Historical gazetteer", "secondary"),
            SourceRecord("src-archive", "Archival register", "archival"),
        ),
        people=(
            HistoricalPerson("p1", "Jeanne d'Arc"),
            HistoricalPerson("p2", "Joan of Arc"),
        ),
        places=(HistoricalPlace("l1", "Paris"),),
    )
    assertions = (
        AliasAssertion(
            alias_id="a-fr", entity_kind="person", entity_id="p1",
            alias="Jeanne d’Arc", language="fr", alias_type="historical_name",
            source_id="src-book", locator="page 14", license="CC-BY-4.0",
            review_status="verified", reviewer="editor-1", reviewed_at="2026-01-10",
        ),
        AliasAssertion(
            alias_id="a-en", entity_kind="person", entity_id="p2",
            alias="Joan of Arc", language="en", alias_type="spelling_variant",
            source_id="src-archive", locator="folio 2r", license="CC0-1.0",
            review_status="verified", reviewer="editor-2", reviewed_at="2026-01-11",
        ),
        AliasAssertion(
            alias_id="a-candidate", entity_kind="person", entity_id="p1",
            alias="Maid of Orleans", language="en", alias_type="title",
            source_id="src-book", locator="page 15", license="CC-BY-4.0",
            review_status="candidate",
        ),
        AliasAssertion(
            alias_id="a-disputed", entity_kind="person", entity_id="p2",
            alias="Maid of Orleans", language="en", alias_type="title",
            source_id="src-archive", locator="folio 3v", license="CC0-1.0",
            review_status="disputed",
        ),
        AliasAssertion(
            alias_id="a-rejected", entity_kind="place", entity_id="l1",
            alias="Maid of Orleans", language="en", alias_type="other",
            source_id="src-book", locator="page 16", license="CC-BY-4.0",
            review_status="rejected",
        ),
    )
    return dataset, AliasRegistry(
        dataset, assertions, registry_version="aliases-1.0",
        dataset_version="history-dataset-2026-01",
    )


def test_verified_exact_lookup_is_default_and_accent_insensitive():
    _, registry = _registry()
    matches = registry.resolve("JEANNE D'ARC", language="fr")
    assert len(matches) == 1
    assert matches[0].entity_id == "p1"
    assert matches[0].review_status == "verified"
    assert matches[0].source_id == "src-book"
    assert matches[0].locator == "page 14"


def test_unverified_lookup_preserves_ambiguity_and_never_returns_rejected():
    _, registry = _registry()
    assert registry.resolve("Maid of Orleans") == ()
    matches = registry.resolve("Maid of Orleans", include_unverified=True)
    assert {item.alias_id for item in matches} == {"a-candidate", "a-disputed"}
    assert all(item.ambiguous and item.ambiguity_count == 2 for item in matches)


def test_language_filter_and_registry_round_trip():
    dataset, registry = _registry()
    payload = registry.to_dict()
    restored = AliasRegistry.from_dict(dataset, payload)
    assert restored.to_dict() == payload
    assert restored.resolve("Joan of Arc", language="fr") == ()
    assert restored.resolve("Joan of Arc", language="en")[0].entity_id == "p2"


def test_alias_assertions_require_citation_and_verified_review_metadata():
    with pytest.raises(ValueError, match="source_id"):
        AliasAssertion(
            "a1", "person", "p1", "Name", "en", "historical_name",
            "", "page 1", "CC0",
        )
    with pytest.raises(ValueError, match="reviewer"):
        AliasAssertion(
            "a1", "person", "p1", "Name", "en", "historical_name",
            "src", "page 1", "CC0", review_status="verified",
            reviewed_at="2026-01-01",
        )


def test_registry_rejects_unknown_entities_sources_and_schema_fields():
    dataset, registry = _registry()
    payload = registry.to_dict()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="Unknown alias registry field"):
        AliasRegistry.from_dict(dataset, payload)

    with pytest.raises(ValueError, match="Unknown person entity"):
        AliasRegistry(
            dataset,
            (AliasAssertion(
                "bad-entity", "person", "missing", "Name", "en", "other",
                "src-book", "page 1", "CC0",
            ),),
            registry_version="1", dataset_version="1",
        )
    with pytest.raises(ValueError, match="Unknown source id"):
        AliasRegistry(
            dataset,
            (AliasAssertion(
                "bad-source", "person", "p1", "Name", "en", "other",
                "missing", "page 1", "CC0",
            ),),
            registry_version="1", dataset_version="1",
        )
