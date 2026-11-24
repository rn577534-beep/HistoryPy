"""Orchestrated, provenance-aware historical research workflow.

The pipeline coordinates existing retrieval tools. It does not generate facts,
resolve historical disputes, or treat retrieval relevance as evidence of truth.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.integrations.aggregation import (
    AggregationReport,
    DuplicateCandidateGroup,
    MetadataConflict,
    SearchProvider,
    compare_metadata,
    find_duplicate_candidates,
    search_all,
)
from historypy.integrations.historical_apis import ExternalRecord
from historypy.research.engine import ResearchQuery, execute_research_query
from historypy.research.evidence_analysis import (
    ClaimEvidenceAnalysis,
    analyze_claim_evidence,
)
from historypy.research.query import SearchHit
from historypy.research.semantic import EmbeddingBatch, SemanticSearchHit, SemanticSearchIndex


@dataclass(frozen=True, slots=True)
class ResearchTask:
    """A literal query unit supplied by the researcher."""

    query: str
    ordinal: int


@dataclass(frozen=True, slots=True)
class ResearchTaskResult:
    """Results for one task, retaining each retrieval channel separately."""

    task: ResearchTask
    local_hits: tuple[SearchHit, ...]
    semantic_hits: tuple[SemanticSearchHit, ...]
    external: AggregationReport | None


@dataclass(frozen=True, slots=True)
class ResearchReport:
    """A reproducible collection of retrieval results and documented gaps."""

    query: str
    tasks: tuple[ResearchTaskResult, ...]
    claim_analyses: tuple[ClaimEvidenceAnalysis, ...]
    duplicate_candidates: tuple[DuplicateCandidateGroup, ...]
    metadata_conflicts: tuple[MetadataConflict, ...]
    gaps: tuple[str, ...]

    @property
    def external_records(self) -> tuple[ExternalRecord, ...]:
        return tuple(
            record
            for task in self.tasks if task.external is not None
            for record in task.external.records
        )

    @property
    def provider_failures(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            (result.provider, result.error or "")
            for task in self.tasks if task.external is not None
            for result in task.external.failures
        )


def _make_tasks(query: str) -> tuple[ResearchTask, ...]:
    """Split only explicit semicolon/newline-separated researcher clauses."""
    clauses = tuple(
        part.strip() for line in query.splitlines()
        for part in line.split(";") if part.strip()
    )
    return tuple(ResearchTask(text, index) for index, text in enumerate(clauses, 1))


class ResearchPipeline:
    """Coordinate local, optional semantic, and optional external discovery.

    External calls are opt-in per run. Providers and embedding functions are
    supplied by the caller, so credentials, costs, network access, and data
    handling remain explicit.
    """

    def __init__(
        self,
        dataset: HistoricalDataset,
        *,
        semantic_index: SemanticSearchIndex | None = None,
        embedder: EmbeddingBatch | None = None,
        providers: Sequence[SearchProvider] = (),
        max_workers: int | None = None,
    ) -> None:
        if semantic_index is not None and not isinstance(semantic_index, SemanticSearchIndex):
            raise TypeError("semantic_index must be a SemanticSearchIndex or None")
        if semantic_index is not None and not callable(embedder):
            raise ValueError("An embedder is required when semantic_index is supplied")
        if max_workers is not None and (
            not isinstance(max_workers, int) or isinstance(max_workers, bool)
            or max_workers < 1
        ):
            raise ValueError("max_workers must be a positive integer or None")
        dataset.require_valid()
        self.dataset = dataset
        self.semantic_index = semantic_index
        self.embedder = embedder
        self.providers = tuple(providers)
        self.max_workers = max_workers

    def run(
        self,
        query: str,
        *,
        kinds: tuple[str, ...] | None = None,
        limit: int = 20,
        include_semantic: bool = True,
        include_external: bool = True,
        limit_per_provider: int = 10,
    ) -> ResearchReport:
        """Run each explicit query clause through configured retrieval channels."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query cannot be empty")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        if not isinstance(include_semantic, bool) or not isinstance(include_external, bool):
            raise TypeError("include_semantic and include_external must be bools")
        if include_semantic and self.semantic_index is not None and self.embedder is None:
            raise ValueError("An embedder is required for semantic retrieval")

        tasks: list[ResearchTaskResult] = []
        for task in _make_tasks(query.strip()):
            local = execute_research_query(
                self.dataset,
                ResearchQuery(text=task.query, kinds=kinds, limit=limit),
            ).hits
            semantic: tuple[SemanticSearchHit, ...] = ()
            if include_semantic and self.semantic_index is not None:
                semantic = self.semantic_index.search(
                    task.query, embedder=self.embedder, kinds=kinds, limit=limit
                )
            external = None
            if include_external and self.providers:
                external = search_all(
                    self.providers, task.query, limit_per_provider=limit_per_provider,
                    max_workers=self.max_workers,
                )
            tasks.append(ResearchTaskResult(task, local, semantic, external))

        claim_ids = tuple(dict.fromkeys(
            hit.record_id
            for result in tasks for hit in result.local_hits
            if hit.kind == "claim"
        ))
        claim_analyses = tuple(
            analyze_claim_evidence(self.dataset, claim_id) for claim_id in claim_ids
        )
        external_records = tuple(
            record for result in tasks if result.external is not None
            for record in result.external.records
        )
        gaps: list[str] = []
        if not any(result.local_hits or result.semantic_hits for result in tasks):
            gaps.append("No matching records were found in the local dataset.")
        if include_external and not self.providers:
            gaps.append("External discovery was requested but no providers were configured.")
        if include_external and self.providers and not external_records:
            gaps.append("Configured external providers returned no records.")
        if any(result.external and result.external.failures for result in tasks):
            gaps.append("One or more external providers failed; inspect provider_failures.")
        for analysis in claim_analyses:
            if analysis.assessment_status in {"insufficient", "mixed"}:
                gaps.append(
                    f"Claim {analysis.claim_id} has {analysis.assessment_status} "
                    "recorded evidence; further source review is needed."
                )
        return ResearchReport(
            query=query.strip(),
            tasks=tuple(tasks),
            claim_analyses=claim_analyses,
            duplicate_candidates=find_duplicate_candidates(external_records),
            metadata_conflicts=compare_metadata(external_records),
            gaps=tuple(dict.fromkeys(gaps)),
        )


def render_research_report(report: ResearchReport) -> str:
    """Render a traceable Markdown discovery report without invented citations."""
    if not isinstance(report, ResearchReport):
        raise TypeError("report must be a ResearchReport")
    lines = [f"# Historical research discovery: {report.query}", "",
             "> Discovery output only. Relevance is not proof of historical truth.", ""]
    for result in report.tasks:
        lines.extend((f"## Task {result.task.ordinal}: {result.task.query}", "",
                      "### Local dataset matches", ""))
        if not result.local_hits:
            lines.append("- No lexical matches.")
        for hit in result.local_hits:
            lines.append(f"- [{hit.kind}] `{hit.record_id}` — {hit.label}")
        lines.extend(("", "### Semantic retrieval", ""))
        if not result.semantic_hits:
            lines.append("- No semantic matches (not configured or none returned).")
        for hit in result.semantic_hits:
            lines.append(
                f"- [{hit.kind}] `{hit.record_id}` — {hit.label} "
                f"(cosine similarity: {hit.similarity:.4f}; retrieval signal only)"
            )
        lines.extend(("", "### External discovery", ""))
        if result.external is None:
            lines.append("- External discovery not run.")
        else:
            for provider_result in result.external.results:
                lines.append(f"- **{provider_result.provider}**")
                if provider_result.error:
                    lines.append(f"  - Error: {provider_result.error}")
                for record in provider_result.records:
                    link = f" — {record.url}" if record.url else ""
                    lines.append(
                        f"  - {record.title} (external ID: `{record.external_id}`)"
                        f"{link}; retrieved: {record.retrieved_at}"
                    )
        lines.append("")
    lines.extend(("## Claim evidence review", ""))
    if not report.claim_analyses:
        lines.append("- No locally matched claims were available for evidence analysis.")
    for item in report.claim_analyses:
        lines.append(
            f"- Claim `{item.claim_id}`: **{item.assessment_status}**; "
            f"{item.distinct_source_count} distinct linked sources, "
            f"{item.total_links} evidence links, "
            f"{item.links_missing_locators} links missing locators."
        )
    lines.extend(("", "## Duplicate candidates and metadata conflicts", ""))
    lines.append(f"- Duplicate candidate groups for human review: {len(report.duplicate_candidates)}")
    lines.append(f"- Metadata conflict fields: {len(report.metadata_conflicts)}")
    lines.extend(("", "## Research gaps and cautions", ""))
    if report.gaps:
        lines.extend(f"- {gap}" for gap in report.gaps)
    else:
        lines.append("- No automatic conclusion is drawn; inspect original sources and provenance.")
    lines.extend(("", ("External records are discovery leads, not automatically imported sources. "
                   "Duplicate candidates and metadata conflicts require human review.")))
    return "\n".join(lines)


__all__ = [
    "ResearchPipeline", "ResearchReport", "ResearchTask", "ResearchTaskResult",
    "render_research_report",
]
