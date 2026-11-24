"""Build and validate a small illustrative HistoryPy dataset.

The records below are synthetic examples, not historical assertions.
"""

from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    HistoricalPlace,
    SourceRecord,
    dataset_to_json,
)

source = SourceRecord(
    id="source-example-001",
    title="Example archival catalogue",
    source_type="archival",
    creator="Example archive",
    language="en",
    notes="Synthetic demonstration record; replace with a real citation.",
)

person = HistoricalPerson(
    id="person-example-001",
    name="Example historical person",
    source_ids=(source.id,),
)

place = HistoricalPlace(
    id="place-example-001",
    name="Example historical place",
    place_type="city",
)

event = HistoricalEvent(
    id="event-example-001",
    title="Example historical event",
    date=HistoricalDate(
        earliest="1947-08-14",
        latest="1947-08-14",
        precision="day",
        calendar="gregorian",
    ),
    place_ids=(place.id,),
    source_ids=(source.id,),
)

claim = HistoricalClaim(
    id="claim-example-001",
    statement="An illustrative proposition that requires source assessment.",
    subject_ids=(person.id,),
    event_ids=(event.id,),
)

evidence = EvidenceLink(
    claim_id=claim.id,
    source_id=source.id,
    relation="contextualizes",
    locator="catalogue record 001",
    interpretation_note="Demonstration only; this does not establish the claim.",
)

dataset = HistoricalDataset(
    sources=(source,),
    claims=(claim,),
    events=(event,),
    people=(person,),
    places=(place,),
    evidence=(evidence,),
    metadata={
        "title": "HistoryPy example dataset",
        "status": "synthetic demonstration",
    },
)

dataset.require_valid()
print(dataset_to_json(dataset))
