"""Compare two separately conducted 1912 Titanic inquiry reports.

This is a worked example of source comparison, not a claim that either
inquiry's figures are automatically the final historical truth.
"""
from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    SourceRecord,
    render_event_source_comparison,
)


def build_titanic_inquiry_dataset() -> HistoricalDataset:
    sources = (
        SourceRecord(
            id="us_senate_report_806",
            title="U.S. Senate Report No. 806: Investigation into Loss of S.S. Titanic",
            source_type="primary",
            creator="U.S. Senate Committee on Commerce",
            publication_date="1912-05-28",
            publisher="United States Government Printing Office",
            url="https://www.senate.gov/about/resources/pdf/TitanicReport.pdf",
            language="English",
            archive_reference="62nd Congress, 2nd Session, Senate Report No. 806",
            notes=(
                "Separate U.S. Senate investigation. The report's witness base may "
                "overlap with other inquiries; independence of underlying testimony "
                "must not be assumed."
            ),
        ),
        SourceRecord(
            id="british_court_cd6352",
            title="British Wreck Commissioner's Court: Report on the Loss of Titanic",
            source_type="primary",
            creator="British Wreck Commissioner's Court, Lord Mersey and assessors",
            publication_date="1912-07-30",
            publisher="British Board of Trade",
            url="https://www.titanicinquiry.org/BOTInq/BOTReport/botRepFindings.php",
            language="English",
            archive_reference="British Parliamentary Paper Cd. 6352; Smithsonian call no. VK1225.T617 1912",
            notes=(
                "Separate British formal investigation. This is a distinct inquiry, "
                "not proof of a wholly independent witness or document base."
            ),
        ),
    )
    event = HistoricalEvent(
        id="titanic_loss_1912",
        title="Loss of RMS Titanic",
        date=HistoricalDate(
            earliest="1912-04-15",
            latest="1912-04-15",
            precision="day",
            calendar="gregorian",
        ),
        summary=(
            "The Titanic sank in the North Atlantic after striking an iceberg "
            "during the night of 14–15 April 1912."
        ),
        source_ids=(
            "us_senate_report_806",
            "british_court_cd6352",
        ),
        tags=("maritime-history", "1912", "official-inquiry"),
    )
    claims = (
        HistoricalClaim(
            id="titanic_lifeboat_capacity_1176",
            statement="The Titanic's total lifeboat capacity was 1,176 persons.",
            event_ids=("titanic_loss_1912",),
            interpretation_note=(
                "The two inquiry reports give different totals: 1,176 and 1,178. "
                "Preserve both source statements; do not silently normalize them."
            ),
        ),
        HistoricalClaim(
            id="titanic_survivors_706",
            statement="The number of people saved from the Titanic was 706.",
            event_ids=("titanic_loss_1912",),
            interpretation_note=(
                "The two inquiry reports give different counts: 706 and 712. "
                "Check the original tables and counting definitions before "
                "attempting reconciliation."
            ),
        ),
    )
    evidence = (
        EvidenceLink(
            claim_id="titanic_lifeboat_capacity_1176",
            source_id="us_senate_report_806",
            relation="supports",
            quotation="Total lifeboat capacity, 1,176.",
            page="13",
            locator="CAPACITY OF LIFEBOATS NOT FITTED",
            url_fragment="capacity-of-lifeboats-not-fitted",
            interpretation_note="U.S. Senate report's printed total.",
        ),
        EvidenceLink(
            claim_id="titanic_lifeboat_capacity_1176",
            source_id="british_court_cd6352",
            relation="contradicts",
            quotation="or a total of 1,178",
            paragraph="Findings of the Court, Question 5(d)",
            locator="Findings of the Court — Question 5(d)",
            interpretation_note=(
                "British Court's sum of 80 + 910 + 188 = 1,178."
            ),
        ),
        EvidenceLink(
            claim_id="titanic_survivors_706",
            source_id="us_senate_report_806",
            relation="supports",
            quotation="while but 706 were saved.",
            page="13",
            locator="CAPACITY OF LIFEBOATS NOT FITTED",
            url_fragment="capacity-of-lifeboats-not-fitted",
            interpretation_note="U.S. Senate report's saved-person total.",
        ),
        EvidenceLink(
            claim_id="titanic_survivors_706",
            source_id="british_court_cd6352",
            relation="contradicts",
            quotation="712, rescued by Carpathia from the boats.",
            paragraph="Findings of the Court, Question 21(a)",
            locator="Findings of the Court — Question 21(a)",
            interpretation_note="British Court's rescue count.",
        ),
    )
    return HistoricalDataset(
        sources=sources,
        events=(event,),
        claims=claims,
        evidence=evidence,
    )


if __name__ == "__main__":
    dataset = build_titanic_inquiry_dataset()
    print(render_event_source_comparison(dataset, "titanic_loss_1912"))
