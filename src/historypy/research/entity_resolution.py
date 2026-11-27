"""Conservative candidate generation for possible duplicate entities.

Candidates are prompts for human review, never identity decisions. Similar names
can refer to different people or places, and one entity can have many names.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from historypy.research.similarity import compare_names

from historypy.core.dataset import HistoricalDataset


@dataclass(frozen=True, slots=True)
class EntityMatchCandidate:
    """A pair of records whose names are lexically similar."""

    kind: str
    left_id: str
    right_id: str
    left_name: str
    right_name: str
    similarity: float
    matched_names: tuple[str, str]


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))


def _names_for(dataset: HistoricalDataset, kind: str):
    if kind == "person":
        records = dataset.people
    elif kind == "place":
        records = dataset.places
    elif kind == "civilization":
        records = dataset.civilizations
    elif kind == "organization":
        records = dataset.organizations
    else:
        raise ValueError(f"Unsupported entity kind: {kind}")
    for record in records:
        aliases = getattr(record, "aliases", ())
        yield record.id, record.name, (record.name, *aliases)


def _name_similarity(left: str, right: str) -> float:
    left_norm, right_norm = _normalize(left), _normalize(right)
    if not left_norm or not right_norm:
        return 0.0
    # Very short strings are too collision-prone for fuzzy matching.
    if min(len(left_norm), len(right_norm)) < 4:
        return 0.0
    return compare_names(left, right).combined

def suggest_entity_matches(
    dataset: HistoricalDataset,
    *,
    kinds: Iterable[str] = ("person", "place"),
    threshold: float = 0.82,
    limit: int | None = 100,
) -> tuple[EntityMatchCandidate, ...]:
    """Suggest same-kind name matches for manual review; never merge records.

    The score is lexical similarity, not a probability of shared identity.
    Context, dates, locations, sources, and historical scholarship must be
    examined before deciding whether two records describe the same entity.
    """
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise TypeError("threshold must be a number")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("threshold must be between 0.0 and 1.0")
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int)
    ):
        raise TypeError("limit must be an integer or None")
    if limit is not None and limit <= 0:
        return ()

    candidates: list[EntityMatchCandidate] = []
    for kind in dict.fromkeys(kinds):
        records = sorted(_names_for(dataset, kind), key=lambda item: item[0])
        for index, (left_id, left_label, left_names) in enumerate(records):
            for right_id, right_label, right_names in records[index + 1:]:
                if left_id == right_id:
                    continue
                best = (0.0, "", "")
                for left_name in left_names:
                    for right_name in right_names:
                        score = _name_similarity(left_name, right_name)
                        if score > best[0]:
                            best = (score, left_name, right_name)
                if best[0] >= threshold:
                    candidates.append(EntityMatchCandidate(
                        kind=kind,
                        left_id=left_id,
                        right_id=right_id,
                        left_name=left_label,
                        right_name=right_label,
                        similarity=round(best[0], 6),
                        matched_names=(best[1], best[2]),
                    ))
    candidates.sort(
        key=lambda item: (-item.similarity, item.kind, item.left_id, item.right_id)
    )
    return tuple(candidates[:limit] if limit is not None else candidates)
