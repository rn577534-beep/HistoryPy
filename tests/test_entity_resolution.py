import pytest

from historypy import HistoricalDataset, HistoricalPerson, HistoricalPlace
from historypy.research.entity_resolution import suggest_entity_matches


def test_suggests_alias_matches_without_merging_records():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="p1", name="Alexander III", aliases=("Alexander the Great",)),
        HistoricalPerson(id="p2", name="Alexander the Great"),
        HistoricalPerson(id="p3", name="Aristotle"),
    ))
    candidates = suggest_entity_matches(dataset, kinds=("person",))
    assert len(candidates) == 1
    assert candidates[0].left_id == "p1"
    assert candidates[0].right_id == "p2"
    assert candidates[0].matched_names == ("Alexander the Great", "Alexander the Great")
    assert len(dataset.people) == 3


def test_only_compares_records_within_the_same_kind():
    dataset = HistoricalDataset(
        people=(HistoricalPerson(id="p1", name="Example City"),),
        places=(HistoricalPlace(id="l1", name="Example City"),),
    )
    assert suggest_entity_matches(dataset, kinds=("person", "place")) == ()


def test_short_names_do_not_generate_fuzzy_candidates():
    dataset = HistoricalDataset(people=(
        HistoricalPerson(id="p1", name="Li"),
        HistoricalPerson(id="p2", name="Lu"),
    ))
    assert suggest_entity_matches(dataset, kinds=("person",), threshold=0.1) == ()


def test_threshold_and_limit_validation():
    with pytest.raises(ValueError, match="threshold"):
        suggest_entity_matches(HistoricalDataset(), threshold=1.1)
    with pytest.raises(TypeError, match="threshold"):
        suggest_entity_matches(HistoricalDataset(), threshold=True)
    with pytest.raises(TypeError, match="limit"):
        suggest_entity_matches(HistoricalDataset(), limit=True)
    assert suggest_entity_matches(HistoricalDataset(), limit=0) == ()


def test_candidates_are_deterministically_ordered():
    dataset = HistoricalDataset(places=(
        HistoricalPlace(id="z", name="Example City"),
        HistoricalPlace(id="a", name="Example City"),
        HistoricalPlace(id="b", name="Example City"),
    ))
    results = suggest_entity_matches(dataset, kinds=("place",))
    assert [(item.left_id, item.right_id) for item in results] == [
        ("a", "b"), ("a", "z"), ("b", "z")
    ]


def test_civilization_and_organization_accept_historical_aliases():
    from historypy import HistoricalCivilization, HistoricalOrganization
    from historypy.research.hybrid import EntityAwareSearchIndex

    dataset = HistoricalDataset(
        civilizations=(
            HistoricalCivilization(
                id="c1", name="Byzantine Empire",
                aliases=("Eastern Roman Empire", "Βυζαντινή Αυτοκρατορία"),
            ),
        ),
        organizations=(
            HistoricalOrganization(
                id="o1", name="League of Nations",
                aliases=("Société des Nations", "国際連盟"),
            ),
        ),
    )
    index = EntityAwareSearchIndex.build(dataset)
    byzantium = index.resolve("The Eastern Roman Empire")
    league_french = index.resolve("Société des Nations")
    league_japanese = index.resolve("国際連盟")
    assert [(item.kind, item.record_id) for item in byzantium] == [
        ("civilization", "c1")
    ]
    assert [(item.kind, item.record_id) for item in league_french] == [
        ("organization", "o1")
    ]
    assert [(item.kind, item.record_id) for item in league_japanese] == [
        ("organization", "o1")
    ]
    assert league_french[0].matched_alias == "Société des Nations"
    assert league_japanese[0].matched_alias == "国際連盟"


def test_civilization_and_organization_aliases_are_validated():
    from historypy import HistoricalCivilization, HistoricalOrganization

    with pytest.raises(ValueError, match="aliases"):
        HistoricalCivilization(id="c1", name="Empire", aliases=("",))
    with pytest.raises(ValueError, match="aliases"):
        HistoricalOrganization(id="o1", name="Institution", aliases=("X", "X"))
