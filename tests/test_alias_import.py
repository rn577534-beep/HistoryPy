import pytest

from historypy import HistoricalDataset, HistoricalPerson
from historypy.research.alias_import import import_wikidata_alias_candidates


def _dataset():
    return HistoricalDataset(
        people=(HistoricalPerson("p1", "Marie Curie"),),
    )


def test_wikidata_alias_import_creates_only_candidate_assertions():
    dataset, registry = import_wikidata_alias_candidates(
        _dataset(),
        {
            "entities": [
                {
                    "id": "Q7186",
                    "aliases": {
                        "bn": [{"value": "মারি কুরি"}],
                        "en": [{"value": "Madame Curie"}],
                        "fr": [{"value": "Marie Skłodowska"}],
                        "de": [{"value": "Maria Skłodowska"}],
                    },
                },
                {
                    "id": "Q999999",
                    "aliases": {"en": ["Unmapped person"]},
                },
            ]
        },
        {"Q7186": ("person", "p1")},
        registry_version="wikidata-candidates-1",
        dataset_version="history-fixture-1",
    )

    assert len(dataset.sources) == 1
    source = dataset.sources[0]
    assert source.id == "wikidata-q7186-current"
    assert source.url == "https://www.wikidata.org/wiki/Q7186"
    assert len(registry.assertions) == 3
    assert {row.language for row in registry.assertions} == {"bn", "en", "fr"}
    assert all(row.review_status == "candidate" for row in registry.assertions)
    assert all(row.license == "CC0-1.0" for row in registry.assertions)
    assert registry.resolve("Madame Curie") == ()
    matches = registry.resolve("Madame Curie", include_unverified=True, language="en")
    assert len(matches) == 1
    assert matches[0].entity_id == "p1"
    assert matches[0].review_status == "candidate"


def test_import_is_deterministic_and_preserves_bengali_script_metadata():
    kwargs = {
        "registry_version": "v1",
        "dataset_version": "d1",
    }
    export = [{"id": "Q7186", "aliases": {"bn": ["মারি কুরি"]}}]
    mapping = {"Q7186": ("person", "p1")}
    _, first = import_wikidata_alias_candidates(_dataset(), export, mapping, **kwargs)
    _, second = import_wikidata_alias_candidates(_dataset(), export, mapping, **kwargs)

    assert first.to_dict() == second.to_dict()
    assertion = first.assertions[0]
    assert assertion.script == "Beng"
    assert assertion.locator == "Q7186/current/aliases/bn"
    assert assertion.reviewer is None
    assert assertion.reviewed_at is None


def test_import_rejects_bad_mapping_and_unsupported_languages():
    with pytest.raises(ValueError, match="Invalid Wikidata entity ID"):
        import_wikidata_alias_candidates(
            _dataset(), [], {"not-a-qid": ("person", "p1")},
            registry_version="v1", dataset_version="d1",
        )
    with pytest.raises(ValueError, match="subset of bn, en, and fr"):
        import_wikidata_alias_candidates(
            _dataset(), [], {"Q7186": ("person", "p1")},
            registry_version="v1", dataset_version="d1", languages=("de",),
        )


def test_import_requires_explicit_mapping_and_validates_canonical_target():
    _, registry = import_wikidata_alias_candidates(
        _dataset(),
        [{"id": "Q7186", "aliases": {"en": ["Madame Curie"]}}],
        {},
        registry_version="v1",
        dataset_version="d1",
    )
    assert registry.assertions == ()

    with pytest.raises(ValueError, match="Unknown person entity id"):
        import_wikidata_alias_candidates(
            _dataset(),
            [{"id": "Q7186", "aliases": {"en": ["Madame Curie"]}}],
            {"Q7186": ("person", "missing")},
            registry_version="v1",
            dataset_version="d1",
        )


def test_import_pins_alias_source_to_wikidata_revision_when_available():
    dataset, registry = import_wikidata_alias_candidates(
        _dataset(),
        [{
            "id": "Q7186",
            "lastrevid": 123456,
            "aliases": {"en": ["Madame Curie"]},
        }],
        {"Q7186": ("person", "p1")},
        registry_version="v1",
        dataset_version="d1",
    )
    source = dataset.sources[0]
    assert source.id == "wikidata-q7186-r123456"
    assert source.url == "https://www.wikidata.org/w/index.php?title=Q7186&oldid=123456"
    assert registry.assertions[0].locator == "Q7186/r123456/aliases/en"


def test_import_rejects_invalid_wikidata_revision_identifier():
    with pytest.raises(ValueError, match="lastrevid"):
        import_wikidata_alias_candidates(
            _dataset(),
            [{
                "id": "Q7186",
                "lastrevid": True,
                "aliases": {"en": ["Madame Curie"]},
            }],
            {"Q7186": ("person", "p1")},
            registry_version="v1",
            dataset_version="d1",
        )
