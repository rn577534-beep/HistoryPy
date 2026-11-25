import pytest
from dataclasses import replace

from historypy import (
    AliasAssertion,
    AliasRegistry,
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalPerson,
    HistoricalRelationship,
    ResearchPipeline,
    SourceRecord,
    execute_question_plan,
    plan_research_question,
    select_paths_by_temporal_policy,
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
        claims=dataset.claims,
        evidence=dataset.evidence,
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
    assert direct.hops[0].evidence_links[0].locator == "page 4"
    assert direct.hops[0].evidence_links[0].quotation == "Evidence D"
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



def test_question_planner_bounds_endpoint_pair_hypotheses():
    plan = plan_research_question(
        _dataset(),
        "Ada Lovelace, Charles Babbage, and Mary Somerville",
        max_path_queries=2,
    )
    assert len(plan.path_queries) == 2
    assert plan.path_queries_truncated
    assert any("endpoint pairs were omitted" in warning for warning in plan.warnings)



def test_question_planner_rejects_malformed_predicate_lexicon():
    with pytest.raises(TypeError, match="tuple or list"):
        plan_research_question(
            _dataset(),
            "Ada Lovelace and Charles Babbage",
            predicate_lexicon={"collaborated_with": "connected to"},
        )


def test_path_review_surfaces_conflicting_claims_and_missing_locators():
    base = _dataset()
    dataset = HistoricalDataset(
        sources=base.sources,
        people=base.people,
        claims=base.claims,
        evidence=base.evidence + (
            EvidenceLink("c3", "s1", "contradicts", quotation="Counter-evidence"),
        ),
        relationships=base.relationships,
    )
    report = execute_question_plan(
        dataset, plan_research_question(
            dataset, "Ada Lovelace and Mary Somerville", max_hops=2
        )
    )
    direct = next(
        row for row in report.path_reviews
        if row.path.entity_ids == ("p1", "p3")
    )
    assert direct.evidence_status == "conflicting"
    assert direct.conflicting_claim_ids == ("c3",)
    assert direct.hops[0].conflicting_claim_ids == ("c3",)
    assert direct.claims_missing_locators == ("c3",)
    assert any("both supporting and contradicting" in warning for warning in report.warnings)


def test_path_review_does_not_call_contradiction_only_claim_supported():
    base = _dataset()
    evidence = tuple(
        EvidenceLink(
            link.claim_id, link.source_id,
            "contradicts" if link.claim_id == "c3" else link.relation,
            locator=link.locator, quotation=link.quotation,
        )
        for link in base.evidence
    )
    dataset = HistoricalDataset(
        sources=base.sources,
        people=base.people,
        claims=base.claims,
        evidence=evidence,
        relationships=base.relationships,
    )
    report = execute_question_plan(
        dataset, plan_research_question(
            dataset, "Ada Lovelace and Mary Somerville", max_hops=2
        )
    )
    direct = next(
        row for row in report.path_reviews
        if row.path.entity_ids == ("p1", "p3")
    )
    assert direct.evidence_status == "contradicted"
    assert direct.hops[0].contradicted_claim_ids == ("c3",)
    assert direct.unsupported_claim_ids == ("c3",)


def test_path_status_fails_closed_when_one_hop_is_contradicted():
    base = _dataset()
    evidence = tuple(
        EvidenceLink(
            link.claim_id, link.source_id,
            "contradicts" if link.claim_id == "c1" else link.relation,
            locator=link.locator, quotation=link.quotation,
        )
        for link in base.evidence
    )
    dataset = HistoricalDataset(
        sources=base.sources,
        people=base.people,
        claims=base.claims,
        evidence=evidence,
        relationships=base.relationships,
    )
    report = execute_question_plan(
        dataset, plan_research_question(
            dataset, "Ada Lovelace and Mary Somerville", max_hops=2
        )
    )
    indirect = next(
        row for row in report.path_reviews
        if row.path.entity_ids == ("p1", "p2", "p3")
    )
    assert indirect.evidence_status == "contradicted"
    assert indirect.contradicted_claim_ids == ("c1",)
    assert indirect.unsupported_claim_ids == ("c1",)


def test_temporal_policy_requires_explicit_unknown_date_behavior():
    base = _dataset()
    relationships = tuple(
        replace(row, valid_from=None, valid_to=None) if row.id == "r2" else row
        for row in base.relationships
    )
    dataset = HistoricalDataset(
        sources=base.sources,
        people=base.people,
        claims=base.claims,
        evidence=base.evidence,
        relationships=relationships,
    )
    report = execute_question_plan(
        dataset, plan_research_question(
            dataset, "Ada Lovelace and Mary Somerville", max_hops=2
        )
    )
    selection = select_paths_by_temporal_policy(
        report.path_reviews, policy="exclude_incompatible"
    )
    assert len(selection.selected_reviews) == 2
    assert len(selection.excluded_unknown) == 0

    strict = select_paths_by_temporal_policy(
        report.path_reviews, policy="compatible_only"
    )
    assert len(strict.selected_reviews) == 1
    assert len(strict.excluded_unknown) == 1
    assert strict.excluded_unknown[0].temporal_status == "unknown"


def test_temporal_policy_excludes_known_conflicts_but_retains_unknown_by_choice():
    report = execute_question_plan(
        _dataset(), plan_research_question(
            _dataset(), "Ada Lovelace and Mary Somerville", max_hops=2
        )
    )
    selection = select_paths_by_temporal_policy(
        report.path_reviews, policy="exclude_incompatible"
    )
    assert all(row.temporal_status != "incompatible" for row in selection.selected_reviews)
    assert len(selection.excluded_incompatible) == 1
    assert selection.excluded_unknown == ()
