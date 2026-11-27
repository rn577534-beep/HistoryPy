"""Information-theoretic summaries for recorded evidence categories.

Entropy describes category diversity, not truth or source credibility.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import log2
from typing import Mapping

from historypy.core.dataset import HistoricalDataset


@dataclass(frozen=True, slots=True)
class EntropyReport:
    counts: tuple[tuple[str, int], ...]
    total: int
    entropy_bits: float
    normalized_entropy: float | None
    interpretation: str = (
        "Category diversity only; not historical truth, source reliability, or evidence quality."
    )


def shannon_entropy(counts: Mapping[str, int]) -> EntropyReport:
    """Compute Shannon entropy in bits for non-negative integer counts."""
    if not isinstance(counts, Mapping):
        raise TypeError("counts must be a mapping")
    normalized: dict[str, int] = {}
    for key, value in counts.items():
        if not isinstance(key, str) or not key:
            raise ValueError("category names must be non-empty strings")
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("category counts must be non-negative integers")
        if value:
            normalized[key] = value
    total = sum(normalized.values())
    if total == 0:
        return EntropyReport((), 0, 0.0, None)
    entropy = -sum(
        (value / total) * log2(value / total)
        for value in normalized.values()
    )
    normalized_entropy = entropy / log2(len(normalized)) if len(normalized) > 1 else 0.0
    return EntropyReport(
        tuple(sorted(normalized.items())), total,
        round(entropy, 12), round(normalized_entropy, 12),
    )


def evidence_relation_entropy(
    dataset: HistoricalDataset, *, claim_id: str | None = None
) -> EntropyReport:
    """Summarize the distribution of recorded evidence relations."""
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    if claim_id is not None and claim_id not in {item.id for item in dataset.claims}:
        raise KeyError(f"Unknown claim id: {claim_id}")
    links = (
        link for link in dataset.evidence
        if claim_id is None or link.claim_id == claim_id
    )
    return shannon_entropy(Counter(link.relation for link in links))


def source_type_entropy(
    dataset: HistoricalDataset, *, claim_id: str | None = None
) -> EntropyReport:
    """Summarize source-type diversity among sources linked to evidence."""
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    if claim_id is not None and claim_id not in {item.id for item in dataset.claims}:
        raise KeyError(f"Unknown claim id: {claim_id}")
    source_map = {item.id: item for item in dataset.sources}
    source_ids = {
        link.source_id for link in dataset.evidence
        if claim_id is None or link.claim_id == claim_id
    }
    return shannon_entropy(Counter(
        source_map[source_id].source_type
        for source_id in source_ids if source_id in source_map
    ))
