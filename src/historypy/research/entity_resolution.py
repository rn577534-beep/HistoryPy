"""Conservative candidate generation for possible duplicate entities.

Candidates are prompts for human review, never identity decisions. Similar names
can refer to different people or places, and one entity can have many names.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from historypy.core.dataset import HistoricalDataset
from historypy.research.alias_registry import AliasRegistry
from historypy.research.similarity import compare_names


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
    matched_alias_ids: tuple[str, ...] = ()
    matched_languages: tuple[str, ...] = ()
    matched_review_statuses: tuple[str, ...] = ()
    ambiguous_alias: bool = False


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))


def _names_for(
    dataset: HistoricalDataset,
    kind: str,
    *,
    alias_registry: AliasRegistry | None = None,
    include_unverified_aliases: bool = False,
):
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
    registry_by_entity: dict[str, list[tuple[str, str, str, str]]] = {}
    if alias_registry is not None:
        for assertion in alias_registry.assertions:
            if assertion.entity_kind != kind or assertion.review_status == "rejected":
                continue
            if assertion.review_status != "verified" and not include_unverified_aliases:
                continue
            registry_by_entity.setdefault(assertion.entity_id, []).append((
                assertion.alias, assertion.alias_id, assertion.language,
                assertion.review_status,
            ))
    for record in records:
        names = [(record.name, "", "und", "canonical")]
        names.extend(
            (alias, "", "und", "legacy_unverified")
            for alias in getattr(record, "aliases", ())
        )
        names.extend(registry_by_entity.get(record.id, ()))
        yield record.id, record.name, tuple(names)


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
    alias_registry: AliasRegistry | None = None,
    include_unverified_aliases: bool = False,
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

    if not isinstance(include_unverified_aliases, bool):
        raise TypeError("include_unverified_aliases must be a bool")
    if alias_registry is not None:
        if not isinstance(alias_registry, AliasRegistry):
            raise TypeError("alias_registry must be an AliasRegistry")
        if alias_registry.dataset != dataset:
            raise ValueError("alias_registry must belong to the supplied dataset snapshot")

    registry_alias_entities: dict[str, set[str]] = {}
    if alias_registry is not None:
        for assertion in alias_registry.assertions:
            if assertion.review_status == "rejected":
                continue
            if assertion.review_status != "verified" and not include_unverified_aliases:
                continue
            registry_alias_entities.setdefault(_normalize(assertion.alias), set()).add(
                f"{assertion.entity_kind}:{assertion.entity_id}"
            )

    candidates: list[EntityMatchCandidate] = []
    for kind in dict.fromkeys(kinds):
        records = sorted(
            _names_for(
                dataset, kind, alias_registry=alias_registry,
                include_unverified_aliases=include_unverified_aliases,
            ),
            key=lambda item: item[0],
        )
        for index, (left_id, left_label, left_names) in enumerate(records):
            for right_id, right_label, right_names in records[index + 1:]:
                if left_id == right_id:
                    continue
                best = (0.0, "", "", "", "", "und", "und", "", "")
                for left_name in left_names:
                    for right_name in right_names:
                        score = _name_similarity(left_name[0], right_name[0])
                        if score > best[0]:
                            best = (
                                score, left_name[0], right_name[0],
                                left_name[1], right_name[1],
                                left_name[2], right_name[2],
                                left_name[3], right_name[3],
                            )
                if best[0] >= threshold:
                    candidates.append(EntityMatchCandidate(
                        kind=kind,
                        left_id=left_id,
                        right_id=right_id,
                        left_name=left_label,
                        right_name=right_label,
                        similarity=round(best[0], 6),
                        matched_names=(best[1], best[2]),
                        matched_alias_ids=tuple(value for value in (best[3], best[4]) if value),
                        matched_languages=(best[5], best[6]),
                        matched_review_statuses=(best[7], best[8]),
                        ambiguous_alias=(
                            _normalize(best[1]) == _normalize(best[2])
                            and len(registry_alias_entities.get(_normalize(best[1]), ())) > 1
                        ),
                    ))
    candidates.sort(
        key=lambda item: (-item.similarity, item.kind, item.left_id, item.right_id)
    )
    return tuple(candidates[:limit] if limit is not None else candidates)
