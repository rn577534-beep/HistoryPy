"""Conservative import of Wikidata aliases as unverified research candidates.

This importer never verifies aliases or merges entities. A researcher-supplied
QID-to-canonical-entity mapping is required, and all imported assertions remain
in candidate review status until independently checked.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from historypy.core.dataset import HistoricalDataset
from historypy.core.models import SourceRecord
from historypy.research.alias_registry import AliasAssertion, AliasRegistry

_WIKIDATA_ID = re.compile(r"^Q[1-9][0-9]*$")
_ALLOWED_LANGUAGES = {"bn", "en", "fr"}
_SCRIPT_BY_LANGUAGE = {"bn": "Beng", "en": "Latn", "fr": "Latn"}


def _alias_values(raw: Any) -> tuple[str, ...]:
    if isinstance(raw, str):
        values = (raw,)
    elif isinstance(raw, list):
        values = tuple(
            item if isinstance(item, str) else item.get("value")
            for item in raw
            if isinstance(item, str) or isinstance(item, dict)
        )
    else:
        return ()
    return tuple(
        value.strip() for value in values
        if isinstance(value, str) and value.strip()
    )


def import_wikidata_alias_candidates(
    dataset: HistoricalDataset,
    export_data: object,
    entity_mapping: Mapping[str, tuple[str, str]],
    *,
    registry_version: str,
    dataset_version: str,
    languages: tuple[str, ...] = ("bn", "en", "fr"),
) -> tuple[HistoricalDataset, AliasRegistry]:
    """Import a Wikidata JSON export as candidate aliases, never verified.

    Expected export shape is either a list of Wikidata entity objects or a
    dictionary with an entities list. Each entity has id and an aliases mapping
    from language code to a list of strings or value objects. The mapping
    argument explicitly connects each QID to a canonical dataset entity.
    """
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    if not isinstance(entity_mapping, Mapping):
        raise TypeError("entity_mapping must be a mapping")
    if not languages or any(language not in _ALLOWED_LANGUAGES for language in languages):
        raise ValueError("languages must be a non-empty subset of bn, en, and fr")
    if isinstance(export_data, dict):
        entities = export_data.get("entities")
    else:
        entities = export_data
    if not isinstance(entities, list):
        raise TypeError("export_data must be a list or a dictionary with an entities list")

    dataset.require_valid()
    existing_sources = {source.id: source for source in dataset.sources}
    source_additions: dict[str, SourceRecord] = {}
    assertions: dict[str, AliasAssertion] = {}
    allowed_languages = set(languages)

    for qid, target in entity_mapping.items():
        if not isinstance(qid, str) or not _WIKIDATA_ID.fullmatch(qid):
            raise ValueError(f"Invalid Wikidata entity ID: {qid!r}")
        if (
            not isinstance(target, tuple) or len(target) != 2
            or any(not isinstance(value, str) or not value.strip() for value in target)
        ):
            raise TypeError("entity_mapping values must be (entity_kind, entity_id) tuples")

    for item in entities:
        if not isinstance(item, dict):
            raise TypeError("each Wikidata export entity must be a dictionary")
        qid = item.get("id")
        if qid not in entity_mapping:
            continue
        if not isinstance(qid, str) or not _WIKIDATA_ID.fullmatch(qid):
            raise ValueError(f"Invalid Wikidata entity ID: {qid!r}")
        aliases_by_language = item.get("aliases", {})
        if not isinstance(aliases_by_language, dict):
            raise TypeError(f"aliases for {qid} must be a language mapping")
        entity_kind, entity_id = entity_mapping[qid]
        source_id = f"wikidata-{qid.lower()}"
        source_url = f"https://www.wikidata.org/wiki/{qid}"
        source = SourceRecord(
            id=source_id,
            title=f"Wikidata item {qid}",
            source_type="other",
            publisher="Wikimedia Foundation",
            url=source_url,
            notes=(
                "Structured-data alias export; imported as candidate assertions only. "
                "No alias is researcher-verified by this import."
            ),
        )
        if source_id in existing_sources:
            existing = existing_sources[source_id]
            if existing.url != source_url:
                raise ValueError(
                    f"Existing source {source_id} does not match expected Wikidata URL"
                )
        else:
            source_additions[source_id] = source

        for language, raw_aliases in aliases_by_language.items():
            if language not in allowed_languages:
                continue
            for alias in _alias_values(raw_aliases):
                identity = chr(31).join((qid, entity_kind, entity_id, language, alias))
                alias_id = "wd-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
                assertions[alias_id] = AliasAssertion(
                    alias_id=alias_id,
                    entity_kind=entity_kind,
                    entity_id=entity_id,
                    alias=alias,
                    language=language,
                    alias_type="other",
                    source_id=source_id,
                    locator=f"{qid}/aliases/{language}",
                    license="CC0-1.0",
                    review_status="candidate",
                    script=_SCRIPT_BY_LANGUAGE[language],
                    note=(
                        "Imported from Wikidata alias data. Candidate only: verify "
                        "historical usage and entity identity against independent sources."
                    ),
                )

    updated_dataset = replace(
        dataset,
        sources=dataset.sources + tuple(source_additions[key] for key in sorted(source_additions)),
    )
    registry = AliasRegistry(
        updated_dataset,
        tuple(assertions[key] for key in sorted(assertions)),
        registry_version=registry_version,
        dataset_version=dataset_version,
    )
    return updated_dataset, registry


__all__ = ["import_wikidata_alias_candidates"]
