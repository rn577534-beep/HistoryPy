"""Source-comparison example for the 1986 Challenger investigation.

This example intentionally models relationships among an official commission
report, hearing testimony, and a later congressional review. They are three
documents, not three independent evidence streams.
"""
from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    SourceRecord,
)


def build_challenger_dataset() -> HistoricalDataset:
    sources = (
        SourceRecord(
            id="rogers_commission_report",
            title="Report of the Presidential Commission on the Space Shuttle Challenger Accident",
            source_type="primary",
            creator="Presidential Commission on the Space Shuttle Challenger Accident",
            publication_date="1986-06-06",
            publisher="U.S. Government",
            url="https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19860015255.pdf",
            language="English",
            archive_reference="NASA NTRS Document ID 19860015255; Chapter V, paragraph 82",
            shared_evidence_group_ids=("presidential-commission-record",),
            notes=(
                "Official commission report. Its findings synthesize testimony, "
                "technical records, and investigative work from the same inquiry."
            ),
        ),
        SourceRecord(
            id="challenger_hearing_volume_v",
            title="Hearings of the Presidential Commission on the Space Shuttle Challenger Accident, Volume V, May 2 session",
            source_type="primary",
            creator="Presidential Commission on the Space Shuttle Challenger Accident",
            publication_date="1986-05-02",
            publisher="Presidential Commission",
            url="https://www.nasa.gov/history/rogersrep/v5part6a.htm",
            language="English",
            archive_reference="Volume V, May 2, 1986 session; transcript page 2754",
            shared_evidence_group_ids=("presidential-commission-record",),
            notes=(
                "Hearing transcript containing testimony by Al McDonald and "
                "Roger Boisjoly. It belongs to the same commission record as "
                "the final report, so it is not an independent investigation."
            ),
        ),
        SourceRecord(
            id="house_report_99_1016",
            title="Investigation of the Challenger Accident, House Report 99-1016",
            source_type="primary",
            creator="U.S. House Committee on Science and Technology",
            publisher="U.S. Government Publishing Office",
            url="https://www.govinfo.gov/content/pkg/GPO-CRPT-99hrpt1016/pdf/GPO-CRPT-99hrpt1016.pdf",
            language="English",
            archive_reference="99th Congress, House Report 99-1016; GPO-CRPT-99hrpt1016",
            derived_from_source_ids=("rogers_commission_report",),
            notes=(
                "A separate congressional review that explicitly examines the "
                "Presidential Commission's work; recorded as dependent on that report."
            ),
        ),
    )
    event = HistoricalEvent(
        id="challenger_51l_1986",
        title="Space Shuttle Challenger mission 51-L accident",
        date=HistoricalDate(
            earliest="1986-01-28",
            latest="1986-01-28",
            precision="day",
            calendar="gregorian",
        ),
        summary=(
            "The Space Shuttle Challenger mission 51-L accident on 28 January "
            "1986, investigated by the Presidential Commission and Congress."
        ),
        source_ids=tuple(source.id for source in sources),
        tags=("space-history", "1986", "investigation", "source-comparison"),
    )
    claims = (
        HistoricalClaim(
            id="challenger_launch_decision_flawed",
            statement="The Rogers Commission concluded that the decision to launch Challenger was flawed.",
            event_ids=("challenger_51l_1986",),
            interpretation_note=(
                "This records the Commission's stated conclusion, not an "
                "independent assessment by HistoryPy."
            ),
        ),
        HistoricalClaim(
            id="challenger_center_board_briefing_testimony",
            statement="Al McDonald testified that the Center Board briefing summarized the erosion concern only briefly.",
            event_ids=("challenger_51l_1986",),
            interpretation_note=(
                "The preceding question asks whether the temperature concern and "
                "O-ring erosion problems were briefed. This is testimony about "
                "what McDonald recalled, not a verbatim copy of the briefing."
            ),
        ),
    )
    evidence = (
        EvidenceLink(
            claim_id="challenger_launch_decision_flawed",
            source_id="rogers_commission_report",
            relation="supports",
            quotation="The decision to launch the Challenger was flawed.",
            paragraph="Chapter V, paragraph 82",
            locator="Chapter V: The Contributing Cause of the Accident",
            url_fragment="v1ch5",
            interpretation_note="Commission's explicit conclusion about the launch decision.",
        ),
        EvidenceLink(
            claim_id="challenger_center_board_briefing_testimony",
            source_id="challenger_hearing_volume_v",
            relation="supports",
            quotation="No, it wasn't. It was kind of a one-liner",
            page="2754",
            locator="May 2, 1986 session, Al McDonald testimony",
            interpretation_note=(
                "Answer to a question about whether the temperature concern "
                "and O-ring erosion problems had been presented at the Center Board."
            ),
        ),
    )
    return HistoricalDataset(
        sources=sources,
        events=(event,),
        claims=claims,
        evidence=evidence,
    )
