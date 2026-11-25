from historypy import (
    EvidenceLink,
    HistoricalClaim,
    HistoricalDataset,
    HistoricalDate,
    HistoricalEvent,
    HistoricalPerson,
    SourceRecord,
    audit_dataset_provenance,
    timeline_for_dataset,
)


def day(value: str, calendar: str = "gregorian") -> HistoricalDate:
    return HistoricalDate(earliest=value, latest=value, precision="day", calendar=calendar)


def test_timeline_sorts_bce_before_ce_and_combines_record_types():
    dataset = HistoricalDataset(
        events=(
            HistoricalEvent("e2", "Later", HistoricalDate(
                earliest_year=10, latest_year=10, precision="year", calendar="gregorian"
            )),
            HistoricalEvent("e1", "Earlier", HistoricalDate(
                earliest_year=-20, latest_year=-20, precision="year", calendar="gregorian"
            )),
        ),
        people=(HistoricalPerson("p1", "Person", birth_date=HistoricalDate(
            earliest_year=-5, latest_year=-5, precision="year", calendar="gregorian"
        )),),
    )
    result = timeline_for_dataset(dataset)
    assert [entry.record_id for entry in result.entries] == ["e1", "p1", "e2"]


def test_timeline_period_includes_overlapping_lifespans():
    dataset = HistoricalDataset(people=(HistoricalPerson(
        "p1", "Person", birth_date=day("1900-01-01"), death_date=day("1980-01-01"),
    ),))
    result = timeline_for_dataset(dataset, period=day("1950-01-01"))
    assert [entry.record_id for entry in result.entries] == ["p1"]


def test_timeline_excludes_incomparable_calendar_by_default():
    dataset = HistoricalDataset(events=(
        HistoricalEvent("e1", "Event", day("1900-01-01", "julian")),
    ))
    result = timeline_for_dataset(dataset, period=day("1900-01-01"))
    assert result.entries == ()
    assert result.excluded_indeterminate_count == 1
    included = timeline_for_dataset(
        dataset, period=day("1900-01-01"), include_indeterminate=True
    )
    assert len(included.entries) == 1
    assert included.excluded_indeterminate_count == 0


def test_timeline_counts_undated_records_and_can_include_them():
    dataset = HistoricalDataset(events=(HistoricalEvent(
        "e1", "Undated", HistoricalDate(original_expression="sometime in antiquity")
    ),))
    assert timeline_for_dataset(dataset).undated_count == 1
    assert timeline_for_dataset(dataset, include_indeterminate=True).entries[0].record_id == "e1"


def test_provenance_reports_source_usage_orphans_and_unlinked_claims():
    dataset = HistoricalDataset(
        sources=(
            SourceRecord("s1", "Archive", "archival"),
            SourceRecord("s2", "Unused", "other"),
        ),
        claims=(HistoricalClaim("c1", "A proposition"),),
        events=(HistoricalEvent("e1", "Event", day("1900-01-01"), source_ids=("s1",)),),
        evidence=(EvidenceLink("c1", "s1", "supports"),),
    )
    report = audit_dataset_provenance(dataset)
    assert report.source_usage_counts == (("s1", 2), ("s2", 0))
    assert report.orphan_source_ids == ("s2",)
    assert report.claims_without_evidence == ()
    assert report.total_source_links == 2
    assert dict(report.evidence_relation_counts)["supports"] == 1


def test_provenance_counts_sources_used_only_by_evidence():
    dataset = HistoricalDataset(
        sources=(SourceRecord("s1", "Archive", "archival"),),
        claims=(HistoricalClaim("c1", "A proposition"),),
        evidence=(EvidenceLink("c1", "s1", "contradicts"),),
    )
    report = audit_dataset_provenance(dataset)
    assert report.source_usage_counts == (("s1", 1),)
    assert report.orphan_source_ids == ()
    assert report.linked_source_count == 1


def test_provenance_flags_explicit_source_derivation_and_shared_evidence():
    dataset = HistoricalDataset(sources=(
        SourceRecord(
            "s1", "Original archive", "archival",
            shared_evidence_group_ids=("witness-17",),
        ),
        SourceRecord(
            "s2", "Later newspaper", "secondary",
            derived_from_source_ids=("s1",),
            shared_evidence_group_ids=("witness-17",),
        ),
        SourceRecord("s3", "Independent archive", "archival"),
    ))
    report = audit_dataset_provenance(dataset)
    assert report.potential_source_dependency_pairs == (
        ("s1", "s2", "derived_from"),
        ("s1", "s2", "shared_evidence_group:witness-17"),
    )


def test_dataset_rejects_missing_or_circular_source_derivation():
    import pytest

    missing = HistoricalDataset(sources=(
        SourceRecord("s1", "Source", "primary", derived_from_source_ids=("missing",)),
    ))
    assert "missing_derived_source" in {issue.code for issue in missing.validate()}

    circular = HistoricalDataset(sources=(
        SourceRecord("s1", "Source one", "primary", derived_from_source_ids=("s2",)),
        SourceRecord("s2", "Source two", "secondary", derived_from_source_ids=("s1",)),
    ))
    assert "source_derivation_cycle" in {
        issue.code for issue in circular.validate()
    }
    with pytest.raises(ValueError, match="source_derivation_cycle"):
        circular.require_valid()
