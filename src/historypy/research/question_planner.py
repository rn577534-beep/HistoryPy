"""Reviewable free-text planning and evidence review for multi-hop questions.

This module deliberately separates candidate extraction from historical
adjudication. Only exact canonical names and researcher-verified aliases are
used as entity mentions. Ambiguity is preserved; no entity is auto-merged.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Literal

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import EvidenceLink, HistoricalDate, SourceRecord
from historypy.research.alias_registry import AliasRegistry
from historypy.research.evidence_analysis import ClaimEvidenceAnalysis, analyze_claim_evidence
from historypy.research.hybrid import DecomposedQuery, decompose_research_question
from historypy.research.relationship_paths import (
    RelationshipPath,
    RelationshipPathQuery,
    RelationshipPathSearchReport,
    find_relationship_paths,
)
from historypy.research.source_independence import (
    SourceSetIndependenceReport,
    analyze_source_set_independence,
)

TemporalStatus = Literal["compatible", "incompatible", "unknown"]


def _normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value.casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    return " ".join(re.findall(r"[^\W_]+", plain, flags=re.UNICODE))


def _contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    return re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


@dataclass(frozen=True, slots=True)
class EntityMentionCandidate:
    """An exact entity mention, with the assertion provenance retained."""

    entity_kind: str
    entity_id: str
    canonical_name: str
    matched_text: str
    match_type: Literal["canonical_name", "verified_alias"]
    alias_id: str | None = None
    language: str | None = None
    source_id: str | None = None
    locator: str | None = None
    ambiguity_count: int = 1

    @property
    def ambiguous(self) -> bool:
        return self.ambiguity_count > 1


@dataclass(frozen=True, slots=True)
class PredicateCandidate:
    """A relation term found by exact match against an explicit researcher lexicon."""

    predicate: str
    matched_term: str


@dataclass(frozen=True, slots=True)
class QuestionPlan:
    """Candidate entity/predicate slots and bounded endpoint path hypotheses."""

    question: str
    decomposition: DecomposedQuery
    entity_mentions: tuple[EntityMentionCandidate, ...]
    predicate_candidates: tuple[PredicateCandidate, ...]
    path_queries: tuple[RelationshipPathQuery, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class HopEvidenceReview:
    """Source metadata and conservative source-genealogy review for one hop."""

    relationship_id: str
    predicate: str
    evidence_source_ids: tuple[str, ...]
    source_records: tuple[SourceRecord, ...]
    source_independence: SourceSetIndependenceReport
    claim_ids: tuple[str, ...]
    evidence_links: tuple[EvidenceLink, ...]
    claim_analyses: tuple[ClaimEvidenceAnalysis, ...]
    missing_source_reference: bool


@dataclass(frozen=True, slots=True)
class QuestionPathReview:
    """A candidate path with hop/path genealogy and temporal compatibility."""

    path: RelationshipPath
    hops: tuple[HopEvidenceReview, ...]
    evidence_source_ids: tuple[str, ...]
    source_independence: SourceSetIndependenceReport
    temporal_status: TemporalStatus
    temporal_note: str


@dataclass(frozen=True, slots=True)
class QuestionExecutionReport:
    """Results of executing every reviewable endpoint hypothesis."""

    plan: QuestionPlan
    searches: tuple[RelationshipPathSearchReport, ...]
    path_reviews: tuple[QuestionPathReview, ...]
    warnings: tuple[str, ...]


def _entity_records(dataset: HistoricalDataset):
    return (
        ("person", dataset.people),
        ("place", dataset.places),
        ("civilization", dataset.civilizations),
        ("organization", dataset.organizations),
    )


def plan_research_question(
    dataset: HistoricalDataset,
    question: str,
    *,
    alias_registry: AliasRegistry | None = None,
    predicate_lexicon: Mapping[str, tuple[str, ...]] | None = None,
    max_hops: int = 3,
    limit: int = 10,
    direction: Literal["outgoing", "incoming", "both"] = "both",
) -> QuestionPlan:
    """Extract exact entity mentions and propose paths without asserting intent.

    Canonical names are matched exactly after Unicode normalization. Alias
    matches are restricted to researcher-verified registry assertions. Predicate
    terms are matched only when supplied in predicate_lexicon; raw language is
    never silently converted into an ontology predicate.
    """
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question cannot be empty")
    if alias_registry is not None and alias_registry.dataset is not dataset:
        raise ValueError("alias_registry must be built for the same dataset instance")
    if not isinstance(max_hops, int) or isinstance(max_hops, bool) or not 1 <= max_hops <= 12:
        raise ValueError("max_hops must be an integer between 1 and 12")
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 500:
        raise ValueError("limit must be an integer between 1 and 500")
    if direction not in {"outgoing", "incoming", "both"}:
        raise ValueError("direction must be outgoing, incoming, or both")

    dataset.require_valid()
    normalized_question = _normalize(question)
    candidates: dict[tuple[str, str, str, str], EntityMentionCandidate] = {}
    raw_mentions: list[tuple[str, str, str, str, str | None, str | None, str | None]] = []

    for kind, records in _entity_records(dataset):
        for entity in records:
            phrase = _normalize(entity.name)
            if _contains_phrase(normalized_question, phrase):
                raw_mentions.append((
                    kind, entity.id, entity.name, entity.name,
                    "canonical_name", None, None,
                ))

    if alias_registry is not None:
        for assertion in alias_registry.assertions:
            if assertion.review_status != "verified":
                continue
            phrase = _normalize(assertion.alias)
            if _contains_phrase(normalized_question, phrase):
                matches = alias_registry.resolve(assertion.alias)
                for match in matches:
                    raw_mentions.append((
                        match.entity_kind, match.entity_id, match.canonical_name,
                        match.alias, "verified_alias", match.alias_id,
                        match.source_id,
                    ))

    for kind, entity_id, canonical, matched, match_type, alias_id, source_id in raw_mentions:
        language = None
        locator = None
        if alias_id is not None and alias_registry is not None:
            assertion = next(
                item for item in alias_registry.assertions if item.alias_id == alias_id
            )
            language = assertion.language
            locator = assertion.locator
        key = (kind, entity_id, _normalize(matched), match_type)
        candidates[key] = EntityMentionCandidate(
            entity_kind=kind,
            entity_id=entity_id,
            canonical_name=canonical,
            matched_text=matched,
            match_type=match_type,
            alias_id=alias_id,
            language=language,
            source_id=source_id,
            locator=locator,
        )

    ambiguity: dict[str, int] = {}
    for candidate in candidates.values():
        ambiguity[_normalize(candidate.matched_text)] = len({
            (row.entity_kind, row.entity_id)
            for row in candidates.values()
            if row.matched_text.casefold() == candidate.matched_text.casefold()
        })
    mentions = tuple(sorted(
        (
            replace(
                candidate,
                ambiguity_count=ambiguity[candidate.matched_text.casefold()],
            )
            for candidate in candidates.values()
        ),
        key=lambda row: (
            row.matched_text.casefold(), row.entity_kind, row.entity_id,
            row.match_type,
        ),
    ))

    known_predicates = {row.predicate for row in dataset.relationships}
    predicate_candidates: list[PredicateCandidate] = []
    if predicate_lexicon is not None:
        for predicate, terms in predicate_lexicon.items():
            if predicate not in known_predicates:
                continue
            for term in terms:
                normalized_term = _normalize(term)
                if normalized_term and _contains_phrase(normalized_question, normalized_term):
                    predicate_candidates.append(PredicateCandidate(predicate, term))
    predicate_candidates = sorted(
        set(predicate_candidates), key=lambda row: (row.predicate, row.matched_term)
    )

    entity_ids = sorted({(row.entity_kind, row.entity_id) for row in mentions})
    ambiguous_entity_pairs = {
        frozenset(
            (row.entity_kind, row.entity_id)
            for row in mentions
            if _normalize(row.matched_text) == phrase
        )
        for phrase in {
            _normalize(row.matched_text) for row in mentions if row.ambiguous
        }
    }
    path_queries = tuple(
        RelationshipPathQuery(
            start_entity_id=start_id,
            end_entity_id=end_id,
            max_hops=max_hops,
            direction=direction,
            limit=limit,
        )
        for start_kind, start_id in entity_ids
        for end_kind, end_id in entity_ids
        if (start_kind, start_id) != (end_kind, end_id)
        and frozenset(((start_kind, start_id), (end_kind, end_id)))
        not in ambiguous_entity_pairs
    )
    warnings: list[str] = [
        (
            "Predicate matches are reviewable candidates only; endpoint path searches "
            "remain unfiltered until a researcher confirms the relation sequence."
        )
    ]
    if not mentions:
        warnings.append(
            "No exact canonical entity name or researcher-verified alias was found; "
            "entity resolution needs researcher input."
        )
    if any(row.ambiguous for row in mentions):
        warnings.append(
            "One or more exact name/alias matches are ambiguous; all candidates are retained."
        )
    if len(entity_ids) < 2:
        warnings.append("At least two distinct entity candidates are needed to propose a path.")
    if not predicate_candidates:
        warnings.append(
            "No predicate slot was grounded by the supplied predicate lexicon; "
            "path searches are unfiltered structural hypotheses."
        )
    if not path_queries and len(entity_ids) >= 2:
        warnings.append("No distinct endpoint pair could be generated.")
    return QuestionPlan(
        question=question.strip(),
        decomposition=decompose_research_question(question),
        entity_mentions=mentions,
        predicate_candidates=tuple(predicate_candidates),
        path_queries=path_queries,
        warnings=tuple(warnings),
    )


def _date_boundary(value: HistoricalDate, *, lower: bool):
    start, end = value._comparison_bounds()
    return (start or end) if lower else (end or start)


def _temporal_review(
    path: RelationshipPath,
) -> tuple[TemporalStatus, str]:
    """Intersect all hop validity intervals; missing/incomparable dates stay unknown."""
    if not path.steps:
        return "unknown", "The path contains no relationship steps."
    intervals = []
    calendars = set()
    incomplete = False
    for step in path.steps:
        if step.valid_from is None or step.valid_to is None:
            incomplete = True
            continue
        if (
            step.valid_from.calendar == "unspecified"
            or step.valid_to.calendar == "unspecified"
            or step.valid_from.calendar != step.valid_to.calendar
        ):
            incomplete = True
            continue
        calendars.add(step.valid_from.calendar)
        lower = _date_boundary(step.valid_from, lower=True)
        upper = _date_boundary(step.valid_to, lower=False)
        if lower is None or upper is None:
            incomplete = True
            continue
        if lower > upper:
            return "incompatible", (
                f"Relationship {step.relationship_id} has a validity start after its end."
            )
        intervals.append((lower, upper, step.relationship_id))
    if len(calendars) > 1:
        return "unknown", "Relationship validity dates use different calendars."
    if not intervals:
        return "unknown", "No complete, comparable validity interval is recorded."
    latest_start = max(item[0] for item in intervals)
    earliest_end = min(item[1] for item in intervals)
    if latest_start > earliest_end:
        return "incompatible", (
            "The recorded relationship validity intervals have no shared time window."
        )
    if incomplete:
        return "unknown", (
            "Known intervals do not conflict, but at least one hop has missing or "
            "incomparable validity metadata."
        )
    return "compatible", "All recorded hop validity intervals share a common time window."


def execute_question_plan(
    dataset: HistoricalDataset,
    plan: QuestionPlan,
) -> QuestionExecutionReport:
    """Run bounded path hypotheses and attach per-hop sources/dependence/date review."""
    if not isinstance(plan, QuestionPlan):
        raise TypeError("plan must be a QuestionPlan")
    dataset.require_valid()
    source_index = {source.id: source for source in dataset.sources}
    relationship_index = {edge.id: edge for edge in dataset.relationships}
    searches = tuple(
        find_relationship_paths(dataset, query) for query in plan.path_queries
    )
    reviews: list[QuestionPathReview] = []
    warnings = list(plan.warnings)
    for search in searches:
        if search.truncated:
            warnings.append(
                f"Path search from {search.query.start_entity_id} to "
                f"{search.query.end_entity_id} was truncated at its result limit."
            )
        for path in search.paths:
            hop_reviews = []
            for step in path.steps:
                relationship = relationship_index[step.relationship_id]
                claim_ids = tuple(relationship.claim_ids)
                evidence_links = tuple(
                    link for link in dataset.evidence if link.claim_id in claim_ids
                )
                evidence_source_ids = tuple(sorted(
                    set(step.source_ids) | {link.source_id for link in evidence_links}
                ))
                records = tuple(
                    source_index[source_id]
                    for source_id in evidence_source_ids if source_id in source_index
                )
                claim_analyses = tuple(
                    analyze_claim_evidence(dataset, claim_id)
                    for claim_id in claim_ids
                )
                hop_reviews.append(HopEvidenceReview(
                    relationship_id=step.relationship_id,
                    predicate=step.predicate,
                    evidence_source_ids=evidence_source_ids,
                    source_records=records,
                    source_independence=analyze_source_set_independence(
                        dataset, evidence_source_ids
                    ),
                    claim_ids=claim_ids,
                    evidence_links=evidence_links,
                    claim_analyses=claim_analyses,
                    missing_source_reference=not bool(evidence_source_ids),
                ))
            path_evidence_source_ids = tuple(sorted({
                source_id for hop in hop_reviews for source_id in hop.evidence_source_ids
            }))
            path_independence = analyze_source_set_independence(
                dataset, path_evidence_source_ids
            )
            temporal_status, temporal_note = _temporal_review(path)
            reviews.append(QuestionPathReview(
                path=path,
                hops=tuple(hop_reviews),
                evidence_source_ids=path_evidence_source_ids,
                source_independence=path_independence,
                temporal_status=temporal_status,
                temporal_note=temporal_note,
            ))
    if not reviews:
        warnings.append("No relationship path was found for the proposed endpoint pairs.")
    if any(
        review.source_independence.status in {
            "known_dependence", "known_dependence_and_unknown"
        }
        for review in reviews
    ):
        warnings.append(
            "At least one complete path contains source records with known shared "
            "genealogy; do not count them as independent corroboration."
        )
    if any(
        review.source_independence.status in {
            "dependence_unknown", "single_source_dependence_unknown",
            "known_dependence_and_unknown",
        }
        for review in reviews
    ):
        warnings.append(
            "At least one complete path has unknown source dependence; the path's "
            "source count is not an independence count."
        )
    if any(review.temporal_status == "incompatible" for review in reviews):
        warnings.append(
            "At least one path has mutually incompatible relationship validity intervals."
        )
    if any(review.temporal_status == "unknown" for review in reviews):
        warnings.append(
            "At least one path has unknown temporal compatibility; do not assume "
            "its relationships were contemporaneous."
        )
    if any(hop.missing_source_reference for review in reviews for hop in review.hops):
        warnings.append("At least one path hop has no linked source record.")
    if any(not hop.claim_analyses for review in reviews for hop in review.hops):
        warnings.append(
            "At least one path hop has no explicitly linked claim-level evidence; "
            "source metadata alone does not provide a quotation or locator."
        )
    if any(
        hop.source_independence.status in {
            "dependence_unknown", "single_source_dependence_unknown",
            "known_dependence_and_unknown",
        }
        for review in reviews for hop in review.hops
    ):
        warnings.append(
            "At least one hop has unknown source dependence; missing genealogy "
            "metadata is not evidence of independence."
        )
    return QuestionExecutionReport(
        plan=plan,
        searches=searches,
        path_reviews=tuple(reviews),
        warnings=tuple(dict.fromkeys(warnings)),
    )


__all__ = [
    "EntityMentionCandidate",
    "HopEvidenceReview",
    "PredicateCandidate",
    "QuestionExecutionReport",
    "QuestionPathReview",
    "QuestionPlan",
    "execute_question_plan",
    "plan_research_question",
]
