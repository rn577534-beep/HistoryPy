"""Seven-part student learning data assembled from sourced historical records."""

# ruff: noqa: I001 - preserve readable public imports
from __future__ import annotations

from typing import Any

from historypy.core.dataset import HistoricalDataset
from historypy.research.timeline import timeline_for_dataset


_PROMPTS = (
    "What changed before this event?",
    "Which recorded factors may help explain it?",
    "Which claims have supporting or contradicting evidence?",
    "What remains uncertain or undocumented?",
)


def learning_experience_data(dataset: HistoricalDataset, event_id: str) -> dict[str, Any]:
    """Compose story, mystery, map, timeline, elsewhere, storyboard and evidence data.

    No causal links or missing facts are inferred. Elsewhere events must have
    explicit overlapping date bounds on the same calendar and distinct places.
    """
    if not isinstance(dataset, HistoricalDataset):
        raise TypeError("dataset must be a HistoricalDataset")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("event_id cannot be empty")
    dataset.require_valid()
    events = {item.id: item for item in dataset.events}
    if event_id not in events:
        raise KeyError(f"Unknown event id: {event_id}")
    event = events[event_id]
    places = {item.id: item for item in dataset.places}
    people = {item.id: item for item in dataset.people}
    sources = {item.id: item for item in dataset.sources}
    claims = [c for c in dataset.claims if event_id in c.event_ids]
    claim_ids = {c.id for c in claims}
    claim_by_id = {c.id: c for c in claims}

    evidence = []
    source_ids = set(event.source_ids)
    for link in dataset.evidence:
        if link.claim_id not in claim_ids or link.source_id not in sources:
            continue
        source = sources[link.source_id]
        source_ids.add(source.id)
        evidence.append({
            "claim_id": link.claim_id,
            "claim": claim_by_id[link.claim_id].statement,
            "relation": link.relation,
            "source_id": source.id,
            "source_title": source.title,
            "source_type": source.source_type,
            "url": source.url,
            "locator": (link.locator or link.page or link.paragraph
                        or link.archive_shelfmark or link.transcription_line
                        or link.timecode or link.url_fragment),
            "quotation": link.quotation,
            "interpretation_note": link.interpretation_note,
        })

    relationships = [
        r for r in dataset.relationships
        if r.subject_id == event_id or r.object_id == event_id
    ]
    person_ids = {
        endpoint for r in relationships for endpoint in (r.subject_id, r.object_id)
        if endpoint in people
    }
    linked_people = [
        {"id": p.id, "name": p.name, "description": p.description}
        for p in dataset.people if p.id in person_ids
    ]
    event_place_ids = set(event.place_ids)
    linked_places = [places[key] for key in event.place_ids if key in places]

    elsewhere = []
    for other in dataset.events:
        if other.id == event_id or not other.place_ids:
            continue
        left, right = event.date, other.date
        if (left.calendar != right.calendar or left.calendar == "unspecified"
                or left.overlaps(right) is not True):
            continue
        if set(other.place_ids) == event_place_ids:
            continue
        elsewhere.append({
            "id": other.id, "title": other.title, "date": other.date.display(),
            "summary": other.summary,
            "places": [places[k].name for k in other.place_ids if k in places],
            "source_ids": list(other.source_ids),
        })

    timeline_result = timeline_for_dataset(
        dataset, kinds=("event",), include_indeterminate=True
    )
    timeline = [{
        "id": entry.record_id, "title": entry.label, "date": entry.date_label,
        "selected": entry.record_id == event_id,
        "source_ids": list(entry.source_ids),
    } for entry in timeline_result.entries]

    map_places = [{
        "id": p.id, "name": p.name, "description": p.description,
        "latitude": p.latitude, "longitude": p.longitude,
        "coordinates_available": p.latitude is not None,
    } for p in linked_places]
    source_catalogue = [{
        "id": key, "title": sources[key].title,
        "source_type": sources[key].source_type, "url": sources[key].url,
        "language": sources[key].language,
    } for key in sorted(source_ids) if key in sources]

    storyboard = [
        {"step": "Background", "content": event.notes or "No separate context note recorded."},
        {"step": "Event", "content": event.summary or "No event summary recorded."},
        {"step": "People and places", "content": linked_people + map_places},
        {"step": "Claims and evidence", "content": {
            "claims": [c.statement for c in claims], "evidence_links": len(evidence)
        }},
        {"step": "Consequences and open questions", "content":
            "Add sourced consequence claims; no causal conclusion is inferred automatically."},
    ]
    return {
        "event_id": event.id, "title": event.title, "date": event.date.display(),
        "story": {"summary": event.summary, "context": event.notes, "tags": list(event.tags)},
        "mystery": {"prompts": list(_PROMPTS), "claims": [
            {"id": c.id, "statement": c.statement, "scope_note": c.scope_note,
             "interpretation_note": c.interpretation_note} for c in claims
        ]},
        "map": {"places": map_places,
                "note": "Recorded coordinates only; not a reconstructed historical boundary."},
        "timeline": {"entries": timeline, "undated_count": timeline_result.undated_count},
        "elsewhere": {"events": elsewhere,
            "note": "Only explicitly overlapping dates on the same calendar and different places are included."},
        "storyboard": storyboard,
        "evidence": {"items": evidence, "sources": source_catalogue,
            "note": "A source link does not by itself authenticate a source or prove a claim."},
        "assessment": {"available": False,
            "message": "No test is included; it requires an explicit learner request."},
    }
