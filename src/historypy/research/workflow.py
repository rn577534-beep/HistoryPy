"""Integrated multilingual historical research workflow."""
from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import SourceRecord
from historypy.integrations.aggregation import (
    DuplicateCandidateGroup,
    MetadataConflict,
    SearchProvider,
    compare_metadata,
    find_duplicate_candidates,
    to_source_record,
)
from historypy.integrations.historical_apis import (
    ExternalRecord,
    InternetArchiveSearch,
    LibraryOfCongressSearch,
    MediaWikiSearch,
    WikidataSearch,
)
from historypy.integrations.open_catalogs import (
    GDELTNewsSearch,
    GuardianNewsSearch,
    GutendexSearch,
    OpenLibrarySearch,
)
from historypy.research.alias_registry import AliasRegistry
from historypy.research.dossier import (
    HistoricalDossier,
    build_historical_dossier,
    render_historical_dossier,
)
from historypy.research.pipeline import (
    ResearchPipeline,
    ResearchReport,
    render_research_report,
)
from historypy.research.question_planner import QuestionExecutionReport
from historypy.research.semantic import EmbeddingBatch, SemanticSearchIndex
from historypy.research.source_verification import (
    SourceVerificationReport,
    verify_source_urls,
)


@dataclass(frozen=True, slots=True)
class ResearchQueryVariant:
    """A researcher-supplied translation, transliteration, alias, or keyword."""
    text: str
    language: str
    variant_type: str = "translation"

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("query variant text cannot be empty")
        if not isinstance(self.language, str) or not re.fullmatch(
            r"[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*", self.language
        ):
            raise ValueError("language must be a valid language tag")
        if self.variant_type not in {"translation", "transliteration", "alias", "keyword"}:
            raise ValueError("unsupported query variant type")


@dataclass(frozen=True, slots=True)
class QueryDiscovery:
    query: str
    language: str
    variant_type: str
    report: ResearchReport


@dataclass(frozen=True, slots=True)
class IntegratedResearchReport:
    question: str
    discoveries: tuple[QueryDiscovery, ...]
    dossier: HistoricalDossier
    question_execution: QuestionExecutionReport
    source_verification: SourceVerificationReport | None
    duplicate_candidates: tuple[DuplicateCandidateGroup, ...]
    metadata_conflicts: tuple[MetadataConflict, ...]
    gaps: tuple[str, ...]

    @property
    def external_records(self) -> tuple[ExternalRecord, ...]:
        return tuple(r for d in self.discoveries for r in d.report.external_records)

    @property
    def provider_failures(self) -> tuple[tuple[str, str], ...]:
        return tuple(f for d in self.discoveries for f in d.report.provider_failures)


def default_historical_providers() -> tuple[SearchProvider, ...]:
    """Create public book, archive, news, and knowledge API adapters; no calls yet."""
    providers: list[SearchProvider] = [
        OpenLibrarySearch(), GutendexSearch(), GDELTNewsSearch(),
        MediaWikiSearch("en"), MediaWikiSearch("bn"),
        LibraryOfCongressSearch(), InternetArchiveSearch(), WikidataSearch(),
    ]
    if os.getenv("GUARDIAN_API_KEY"):
        providers.append(GuardianNewsSearch())
    return tuple(providers)


class HistoricalResearchWorkflow:
    """Coordinate query variants, retrieval, source checks, and dossier assembly.

    Translation variants are supplied by the researcher, not machine-invented.
    Cross-lingual semantic retrieval requires a multilingual embedding model.
    """

    def __init__(
        self, dataset: HistoricalDataset, *,
        providers: Sequence[SearchProvider] | None = None,
        semantic_index: SemanticSearchIndex | None = None,
        embedder: EmbeddingBatch | None = None,
        max_workers: int | None = 4,
    ) -> None:
        dataset.require_valid()
        self.dataset = dataset
        self.providers = tuple(default_historical_providers() if providers is None else providers)
        self.pipeline = ResearchPipeline(
            dataset, semantic_index=semantic_index, embedder=embedder,
            providers=self.providers, max_workers=max_workers,
        )

    def run(
        self, question: str, *,
        query_variants: Sequence[ResearchQueryVariant] = (),
        alias_registry: AliasRegistry | None = None,
        predicate_lexicon: Mapping[str, tuple[str, ...]] | None = None,
        include_semantic: bool = True, include_external: bool = True,
        verify_sources: bool = True, limit: int = 20,
        limit_per_provider: int = 10,
        dossier_title: str = "Historical research dossier",
        scope_note: str = "", max_hops: int = 3,
    ) -> IntegratedResearchReport:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("question cannot be empty")
        if not isinstance(query_variants, Sequence) or isinstance(query_variants, (str, bytes)):
            raise TypeError("query_variants must be a sequence of ResearchQueryVariant")
        if any(not isinstance(v, ResearchQueryVariant) for v in query_variants):
            raise TypeError("query_variants must contain only ResearchQueryVariant values")
        if not isinstance(verify_sources, bool):
            raise TypeError("verify_sources must be bool")
        variants = (ResearchQueryVariant(question.strip(), "und", "keyword"), *query_variants)
        unique: dict[str, ResearchQueryVariant] = {}
        for variant in variants:
            unique.setdefault(" ".join(variant.text.casefold().split()), variant)
        discoveries = tuple(
            QueryDiscovery(
                v.text, v.language, v.variant_type,
                self.pipeline.run(
                    v.text, include_semantic=include_semantic,
                    include_external=include_external, limit=limit,
                    limit_per_provider=limit_per_provider,
                ),
            ) for v in unique.values()
        )
        question_execution = self.pipeline.run_question(
            question, alias_registry=alias_registry,
            predicate_lexicon=predicate_lexicon, max_hops=max_hops,
        )
        dossier = build_historical_dossier(
            self.dataset, title=dossier_title, scope_note=scope_note,
        )
        verification = verify_source_urls(self.dataset) if verify_sources else None
        records = tuple(r for d in discoveries for r in d.report.external_records)
        gaps = [g for d in discoveries for g in d.report.gaps]
        gaps.extend(question_execution.warnings)
        gaps.extend(dossier.research_gaps)
        if verification is not None:
            if verification.failed_count:
                gaps.append(f"{verification.failed_count} evidence-linked source URL(s) could not be verified.")
            if verification.results and not verification.quotation_match_count:
                gaps.append("No recorded quotation was confirmed by exact text matching.")
        if records:
            gaps.append(f"{len(records)} external results remain candidates; none was auto-imported as evidence.")
        if not include_external:
            gaps.append("External discovery was disabled.")
        return IntegratedResearchReport(
            question.strip(), discoveries, dossier, question_execution, verification,
            find_duplicate_candidates(records), compare_metadata(records),
            tuple(dict.fromkeys(gaps)),
        )


def select_external_sources(
    dataset: HistoricalDataset, report: IntegratedResearchReport,
    selections: Sequence[tuple[str, str]], *,
    source_type: str = "tertiary", accessed_on: str | None = None,
) -> HistoricalDataset:
    """Import explicitly selected catalog records as sources, never as claim evidence."""
    if not isinstance(dataset, HistoricalDataset) or not isinstance(report, IntegratedResearchReport):
        raise TypeError("dataset and report must be HistoryPy research objects")
    if source_type not in {
        "primary", "secondary", "tertiary", "archaeological", "oral",
        "epigraphic", "numismatic", "archival", "other",
    }:
        raise ValueError("unsupported source_type")
    if not isinstance(selections, Sequence) or isinstance(selections, (str, bytes)):
        raise TypeError("selections must be a sequence of pairs")
    available = {(r.provider, r.external_id): r for r in report.external_records}
    existing = {s.id: s for s in dataset.sources}
    additions: list[SourceRecord] = []
    seen: set[tuple[str, str]] = set()
    for key in selections:
        if not isinstance(key, tuple) or len(key) != 2 or any(
            not isinstance(v, str) or not v.strip() for v in key
        ):
            raise ValueError("each selection must be a non-empty (provider, external_id) tuple")
        if key in seen:
            continue
        seen.add(key)
        record = available.get(key)
        if record is None:
            raise KeyError(f"External candidate not found: {key!r}")
        digest = hashlib.sha256(f"{record.provider}\0{record.external_id}".encode()).hexdigest()[:20]
        source = to_source_record(
            record, source_id=f"external-{digest}", accessed_on=accessed_on,
            source_type=source_type,
            notes="Researcher-selected discovery candidate; not claim evidence.",
        )
        old = existing.get(source.id)
        if old is not None and old != source:
            raise ValueError(f"Generated source ID conflicts: {source.id}")
        if old is None:
            additions.append(source)
            existing[source.id] = source
    updated = replace(dataset, sources=(*dataset.sources, *additions))
    updated.require_valid()
    return updated


def render_integrated_research_report(report: IntegratedResearchReport) -> str:
    """Render discovery, verification, and the structured dossier as Markdown."""
    if not isinstance(report, IntegratedResearchReport):
        raise TypeError("report must be an IntegratedResearchReport")
    lines = [
        f"# Integrated historical research: {report.question}", "",
        "> Search relevance and URL reachability are not verdicts on historical truth.",
        "", "## 1. Multilingual discovery", "",
    ]
    for i, item in enumerate(report.discoveries, 1):
        lines.extend((
            f"### {i}. [{item.language}] {item.query}",
            f"Variant type: {item.variant_type}", "",
            render_research_report(item.report), "",
        ))
    lines.extend(("", "## 2. Multi-hop question review", ""))
    if report.question_execution.path_reviews:
        for review in report.question_execution.path_reviews:
            lines.append(
                f"- Candidate path {review.path.path_id}: evidence {review.evidence_status}; "
                f"temporal status {review.temporal_status}."
            )
    else:
        lines.append("- No supported relationship path was found in the current dataset.")
    lines.extend(("", "## 3. Source URL and quotation checks", ""))
    if report.source_verification is None:
        lines.append("- Live source verification was not run.")
    elif not report.source_verification.results:
        lines.append("- No evidence-linked source URLs were available.")
    else:
        for item in report.source_verification.results:
            lines.append(f"- {item.source_id}: {item.status}; quotation: {item.quotation_status}.")
    lines.extend(("", "## 4. Duplicate and metadata review", ""))
    lines.append(f"- Duplicate candidate groups: {len(report.duplicate_candidates)}")
    lines.append(f"- Metadata conflicts: {len(report.metadata_conflicts)}")
    lines.extend(("", "## 5. Research gaps", ""))
    lines.extend(f"- {gap}" for gap in report.gaps) if report.gaps else lines.append("- No automatic gap flags.")
    lines.extend(("", "## 6. Historical dossier", "", render_historical_dossier(report.dossier), ""))
    lines.extend((
        "## 7. Researcher review required", "",
        "1. Inspect original books, archival items, articles, or artefacts.",
        "2. Confirm author, date, edition, rights, and provenance.",
        "3. Select source candidates explicitly; provider count does not establish independence.",
        "4. Attach selected sources to claims with page or archival locators.",
        "5. Preserve supporting, contradicting, and unresolved evidence separately.",
    ))
    return "\n".join(lines)


__all__ = [
    "HistoricalResearchWorkflow", "IntegratedResearchReport", "QueryDiscovery",
    "ResearchQueryVariant", "default_historical_providers",
    "render_integrated_research_report", "select_external_sources",
]
