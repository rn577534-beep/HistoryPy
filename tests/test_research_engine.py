import pytest

from historypy import (
    DatasetSearchIndex,
    EvidenceLink,
    HistoricalClaim,
    HistoricalDate,
    HistoricalDataset,
    HistoricalEvent,
    HistoricalPerson,
    HistoricalPlace,
    ResearchQuery,
    SourceRecord,
    execute_research_query,
)


def build_dataset():
    sources = (
        SourceRecord(id="s1", title="Chronicle", source_type="primary"),
        SourceRecord(id="s2", title="Modern study", source_type="secondary"),
    )
    people = (
        HistoricalPerson(
            id="p1", name="Amina", birth_date=HistoricalDate(
                earliest_year=100, latest_year=100, calendar="gregorian"
            ), death_date=HistoricalDate(
                earliest_year=160, latest_year=160, calendar="gregorian"
            ), source_ids=("s1",),
        ),
        HistoricalPerson(id="p2", name="Rahim"),
    )
    places = (
        HistoricalPlace(id="pl1", name="Old port", place_type="city", source_ids=("s1",)),
        HistoricalPlace(id="pl2", name="Hill fort", place_type="site", source_ids=("s2",)),
    )
    events = (
        HistoricalEvent(
            id="e1", title="Port treaty",
            date=HistoricalDate(
                earliest_year=130, latest_year=130, calendar="gregorian"
            ),
            place_ids=("pl1",), source_ids=("s1",), tags=("diplomacy", "trade"),
        ),
        HistoricalEvent(
            id="e2", title="Fort excavation",
            date=HistoricalDate(
                earliest_year=180, latest_year=180, calendar="gregorian"
            ),
            place_ids=("pl2",), source_ids=("s2",), tags=("archaeology",),
        ),
    )
    claims = (
        HistoricalClaim(id="c1", statement="The treaty was signed at the port."),
        HistoricalClaim(id="c2", statement="The fort was occupied in antiquity."),
    )
    evidence = (
        EvidenceLink("c1", "s1", "supports"),
        EvidenceLink("c1", "s2", "contradicts"),
        EvidenceLink("c2", "s2", "mentions"),
    )
    return HistoricalDataset(
        sources=sources, people=people, places=places, events=events,
        claims=claims, evidence=evidence,
    )


def test_text_and_kind_filters_are_combined():
    result = execute_research_query(
        build_dataset(), ResearchQuery(text="port", kinds=("event", "place"))
    )
    assert [(hit.kind, hit.record_id) for hit in result.hits] == [
        ("event", "e1"), ("place", "pl1")
    ]
    assert result.total == 2


def test_period_query_matches_lifespan_between_birth_and_death():
    period = HistoricalDate(
        earliest_year=120, latest_year=140, calendar="gregorian"
    )
    result = execute_research_query(
        build_dataset(), ResearchQuery(period=period, kinds=("person",))
    )
    assert [hit.record_id for hit in result.hits] == ["p1"]


def test_place_source_and_tag_filters_intersect():
    result = execute_research_query(
        build_dataset(),
        ResearchQuery(
            kinds=("event",), place_ids=("pl1",), source_ids=("s1",),
            tags=("trade",),
        ),
    )
    assert [hit.record_id for hit in result.hits] == ["e1"]


def test_evidence_status_filter_and_facets_are_transparent():
    result = execute_research_query(
        build_dataset(), ResearchQuery(kinds=("claim",), evidence_status="mixed")
    )
    assert [hit.record_id for hit in result.hits] == ["c1"]
    assert result.facets.evidence_status_counts == (("mixed", 1),)


def test_context_only_claim_is_insufficient():
    result = execute_research_query(
        build_dataset(), ResearchQuery(kinds=("claim",), evidence_status="insufficient")
    )
    assert [hit.record_id for hit in result.hits] == ["c2"]


def test_facets_count_full_filtered_results_before_pagination():
    result = execute_research_query(
        build_dataset(), ResearchQuery(kinds=("event",), limit=1)
    )
    assert len(result.hits) == 1
    assert result.total == 2
    assert result.facets.kind_counts == (("event", 2),)
    assert result.facets.tag_counts == (
        ("archaeology", 1), ("diplomacy", 1), ("trade", 1)
    )


def test_offset_and_limit_are_deterministic():
    result = execute_research_query(
        build_dataset(), ResearchQuery(kinds=("event",), limit=1, offset=1)
    )
    assert [hit.record_id for hit in result.hits] == ["e2"]


def test_invalid_query_filters_are_rejected():
    with pytest.raises(ValueError, match="Unsupported record kind"):
        ResearchQuery(kinds=("spaceship",))
    with pytest.raises(ValueError, match="Unsupported evidence status"):
        ResearchQuery(evidence_status="probably_true")
    with pytest.raises(ValueError, match="offset"):
        ResearchQuery(offset=-1)



def test_structured_query_can_reuse_trigram_index():
    dataset = build_dataset()
    query = ResearchQuery(text="port treaty", kinds=("event", "claim"))
    indexed = execute_research_query(
        dataset, query, index=DatasetSearchIndex.build(dataset)
    )
    direct = execute_research_query(dataset, query)
    assert indexed.hits == direct.hits
    assert indexed.total == direct.total
