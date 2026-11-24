import pytest

from historypy import HistoricalDataset, SourceRecord
from historypy.research.source_audit import audit_dataset_sources, audit_source_record


def test_source_audit_reports_missing_recommended_metadata():
    source = SourceRecord(id="s1", title="Uncatalogued source", source_type="primary")
    audit = audit_source_record(source)
    assert audit.source_id == "s1"
    assert audit.has_locator is False
    assert "creator" in audit.missing_recommended_fields
    assert "url_or_archive_reference" in audit.missing_recommended_fields


def test_source_audit_accepts_either_url_or_archive_reference():
    source = SourceRecord(
        id="s2", title="Archived source", source_type="archival",
        archive_reference="Archive X, box 4, folio 2",
    )
    audit = audit_source_record(source)
    assert audit.has_locator is True
    assert "url_or_archive_reference" not in audit.missing_recommended_fields


def test_dataset_source_audit_preserves_order_and_empty_result():
    dataset = HistoricalDataset(sources=(
        SourceRecord(id="s1", title="First", source_type="primary"),
        SourceRecord(id="s2", title="Second", source_type="secondary"),
    ))
    assert [item.source_id for item in audit_dataset_sources(dataset)] == ["s1", "s2"]
    assert audit_dataset_sources(HistoricalDataset()) == ()


def test_source_audit_does_not_accept_other_record_types():
    with pytest.raises(TypeError, match="SourceRecord"):
        audit_source_record("not a source")  # type: ignore[arg-type]
