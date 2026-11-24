from historypy import EvidenceLink, HistoricalClaim, HistoricalDataset, SourceRecord
from historypy.io.json import dataset_from_json, dataset_to_json


def test_evidence_link_structured_locators_round_trip():
    dataset = HistoricalDataset(
        sources=(SourceRecord(id="s1", title="Source", source_type="archival"),),
        claims=(HistoricalClaim(id="c1", statement="Claim"),),
        evidence=(EvidenceLink(
            claim_id="c1", source_id="s1", relation="supports",
            locator="folio 12", page="12r", paragraph="4",
            archive_shelfmark="MS-42", url_fragment="section-3",
            transcription_line="88", timecode="00:12:34",
        ),),
    )
    restored = dataset_from_json(dataset_to_json(dataset))
    assert restored == dataset
    assert restored.evidence[0].archive_shelfmark == "MS-42"
