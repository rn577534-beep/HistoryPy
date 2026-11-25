from historypy import (
    AliasAssertion,
    AliasRegistry,
    EvidenceLink,
    HistoricalClaim,
    HistoricalDate,
    HistoricalDataset,
    HistoricalPerson,
    HistoricalRelationship,
    ResearchPipeline,
    SourceRecord,
    execute_question_plan,
    plan_research_question,
)
from historypy.research.source_independence import analyze_source_set_independence


def _date(start, end):
    return HistoricalDate(
        earliest_year=start, latest_year=end, calendar="gregorian"
    )


def _dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord("s1", "Archival register", "archival"),
            SourceRecord(
                "s2", "Later transcription", "secondary",
                derived_from_source_ids=("s1",),
            ),
            SourceRecord("s3", "Independent catalogue", "primary"),
        ),
        people=(
            HistoricalPerson("p1", "Ada Lovelace"),
            HistoricalPerson("p2", "Charles Babbage"),
            HistoricalPerson("p3", "Mary Somerville"),
            HistoricalPerson("p4", "Alex Morgan"),
        ),
        claims=(
            HistoricalClaim("c1", "Ada Lovelace collaborated with Charles Babbage."),
            HistoricalClaim("c2", "Charles Babbage corresponded with Mary Somerville."),
            HistoricalClaim("c3", "Ada Lovelace influenced Mary Somerville."),
        ),
        evidence=(
            EvidenceLink("c1", "s1", "supports", locator="page 1", quotation="Evidence A"),
            EvidenceLink("c1", "s2", "supports", locator="page 2", quotation="Evidence B"),
            EvidenceLink("c2", "s3", "supports", locator="page 3", quotation="Evidence C"),
            EvidenceLink("c3", "s3", "supports", locator="page 4", quotation="Evidence D"),
        ),
        relationships=(
            HistoricalRelationship(
                "r1", "p1", "collaborated_with", "p2",
                source_ids=("s1", "s2"),
                valid_from=_date(1840, 1842),
                valid_to=_date(1844, 1846),
                claim_ids=("c1",),
            ),
            HistoricalRelationship(
                "r2", "p2", "corresponded_with", "p3",
                source_ids=("s3",),
                valid_from=_date(1850, 1851),
                valid_to=_date(1852, 1853),
                claim_ids=("c2",),
            ),
            HistoricalRelationship(
                "r3", "p1", "influenced", "p3",
                source_ids=("s3",),
                valid_from=_date(1840, 1841),
                valid_to=_date(1843, 1844),
                claim_ids=("c3",),
            ),
        ),
    )


def test_question_planner_extracts_exact_names_and_preserves_predicate_candidates():
    dataset = _dataset()
    plan = plan_research_question(
        dataset,
        "How was Ada Lovelace connected to Charles Babbage?",
        predicate_lexicon={"collaborated_with": ("connected to",)},
        max_hops=3,
    )
    assert {(row.entity_id, row.canonical_name) for row in plan.entity_mentions} == {
        ("p1", "Ada Lovelace"),
        ("p2", "Charles Babbage"),
    }
    assert plan.predicate_candidates[0].predicate == "collaborated_with"
    assert len(plan.path_queries) == 2
    assert any("remain unfiltered" in warning for warning in plan.warnings)


def test_verified_alias_is_accepted_but_candidate_alias_is_not():
    dataset = _dataset()
    registry = AliasRegistry(
        dataset,
        [
            AliasAssertion(
                "a1", "person", "p1", "Augusta Ada", "en",
                "historical_name", "s1", "folio 2", "public-domain",
                review_status="verified", reviewer="researcher-1",
                reviewed_at="2026-01-02",
            ),
            AliasAssertion(
                "a2", "person", "p2", "Charles B.", "en",
                "spelling_variant", "s1", "folio 3", "public-domain",
                review_status="candidate",
            ),
        ],
        registry_version="1.0.0",
        dataset_version="fixture-1",
    )
    plan = plan_research_question(
        dataset, "Augusta Ada and Charles B.", alias_registry=registry
    )
    assert {row.entity_id for row in plan.entity_mentions} == {"p1"}
    match = plan.entity_mentions[0]
    assert match.match_type == "verified_alias"
    assert match.source_id == "s1"
    assert match.locator == "folio 2"


def test_ambiguous_canonical_names_are_not_collapsed():
    dataset = _dataset()
    duplicate = HistoricalPerson("p5", "Alex Morgan")
    dataset = HistoricalDataset(
        sources=dataset.sources,
        people=dataset.people + (duplicate,),
        relationships=dataset.relationships,
    )
    plan = plan_research_question(dataset, "Alex Morgan")
    matches = [row for row in plan.entity_mentions if row.matched_text == "Alex Morgan"]
    assert {row.entity_id for row in matches} == {"p4", "p5"}
    assert all(row.ambiguous for row in matches)
    assert plan.path_queries == ()


def test_execution_attaches_per_hop_sources_and_temporal_conflict():
    dataset = _dataset()
    plan = plan_research_question(
        dataset, "Ada Lovelace and Mary Somerville", max_hops=2
    )
    report = execute_question_plan(dataset, plan)
    assert report.path_reviews
    direct = next(
        row for row in report.path_reviews
        if row.path.entity_ids == ("p1", "p3")
    )
    assert direct.temporal_status == "compatible"
    assert direct.hops[0].source_records[0].id == "s3"
    assert direct.hops[0].claim_ids == ("c3",)
    assert direct.hops[0].claim_analyses[0].locator_coverage == 1.0

    indirect = next(
        row for row in report.path_reviews
        if row.path.entity_ids == ("p1", "p2", "p3")
    )
    assert indirect.temporal_status == "incompatible"
    assert indirect.hops[0].source_independence.status == "known_dependence"
    assert indirect.hops[0].claim_analyses[0].assessment_status == "supported"
    assert indirect.hops[0].claim_analyses[0].locator_coverage == 1.0
    assert indirect.hops[0].source_independence.dependent_clusters[0].evidence_source_ids == (
        "s1", "s2"
    )
    assert indirect.source_independence.status == "known_dependence_and_unknown"
    assert indirect.source_independence.unknown_source_ids == ("s3",)


def test_source_set_audit_never_infers_independence_from_missing_metadata():
    report = analyze_source_set_independence(_dataset(), ["s1", "s3"])
    assert report.status == "dependence_unknown"
    assert report.unknown_source_ids == ("s1", "s3")



def test_research_pipeline_exposes_integrated_multi_hop_question_workflow():
    report = ResearchPipeline(_dataset()).run_question(
        "Ada Lovelace and Mary Somerville", max_hops=2
    )
    assert report.plan.question == "Ada Lovelace and Mary Somerville"
    assert report.path_reviews
