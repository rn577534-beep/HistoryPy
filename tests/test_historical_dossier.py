from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalOrganization,
    HistoricalPerson,
    HistoricalPlace,
    HistoricalRelationship,
    SourceRecord,
    build_historical_dossier,
    render_historical_dossier,
)


def _dataset():
    source = SourceRecord(
        "archive-1", "Independence archive", "primary",
        creator="National archive", url="https://example.org/archive",
    )
    place = HistoricalPlace(
        "dhaka", "Dhaka", place_type="city", source_ids=("archive-1",)
    )
    person = HistoricalPerson(
        "actor-1", "A historical actor", source_ids=("archive-1",)
    )
    organization = HistoricalOrganization(
        "org-1", "A political organization", place_ids=("dhaka",),
        source_ids=("archive-1",),
    )
    event = HistoricalEvent(
        "event-1", "A public declaration",
        HistoricalDate(
            earliest="1971-03-26", latest="1971-03-26",
            precision="day", calendar="Gregorian",
        ),
        summary="A researcher-entered event summary.",
        place_ids=("dhaka",), source_ids=("archive-1",),
    )
    claim = HistoricalClaim(
        "claim-1", "The declaration was made on this date.",
        event_ids=("event-1",),
    )
    unassigned = HistoricalClaim("claim-2", "A broader contextual claim.")
    relationship = HistoricalRelationship(
        "rel-1", "event-1", "involved", "actor-1",
        source_ids=("archive-1",), claim_ids=("claim-1",),
    )
    return HistoricalDataset(
        sources=(source,), claims=(claim, unassigned), events=(event,),
        people=(person,), places=(place,), organizations=(organization,),
        relationships=(relationship,),
        evidence=(
            EvidenceLink("claim-1", "archive-1", "supports", page="12"),
            EvidenceLink("claim-2", "archive-1", "contradicts", locator="chapter 2"),
        ),
    )


def test_dossier_builds_chronological_chapter_and_keeps_explicit_links():
    dossier = build_historical_dossier(
        _dataset(), title="A sample history", scope_note="A bounded research scope."
    )
    assert dossier.title == "A sample history"
    assert len(dossier.chapters) == 1
    chapter = dossier.chapters[0]
    assert chapter.event.id == "event-1"
    assert [item.claim.id for item in chapter.claims] == ["claim-1"]
    assert chapter.places[0].name == "Dhaka"
    assert chapter.organizations[0].name == "A political organization"
    assert dossier.unassigned_claims[0].claim.id == "claim-2"
    assert dossier.validation_issues == ()


def test_dossier_render_contains_traceable_sources_and_review_protocol():
    rendered = render_historical_dossier(build_historical_dossier(_dataset()))
    assert "# Historical dossier" in rendered
    assert "1971-03-26" in rendered
    assert "Independence archive" in rendered
    assert "locator: 12" in rendered
    assert "not assigned to an event" in rendered
    assert "Check source genealogy" in rendered
    assert "not an automated verdict" in rendered


def test_dossier_does_not_promote_retrieval_or_evidence_to_truth():
    dataset = _dataset()
    dossier = build_historical_dossier(dataset)
    review = dossier.chapters[0].claims[0]
    assert review.assessment.status == "supported"
    # The status describes recorded link direction only; it is not a truth score.
    assert "not an automated verdict" in render_historical_dossier(dossier)
