import pytest

from historypy import HistoricalDataset, SourceRecord
from historypy.research.source_dependency_registry import (
    SourceDependencyAssertion,
    SourceDependencyRegistry,
)
from historypy.research.source_independence import analyze_source_set_independence


def _dataset():
    return HistoricalDataset(
        sources=(
            SourceRecord("s1", "Original witness statement", "primary"),
            SourceRecord("s2", "Syndicated report", "secondary"),
            SourceRecord("s3", "Research catalogue", "tertiary"),
        )
    )


def test_verified_genealogy_assertions_apply_but_candidates_do_not():
    dataset = _dataset()
    registry = SourceDependencyRegistry(
        dataset,
        (
            SourceDependencyAssertion(
                "a1", "s2", "s1", "derived_from", "s3",
                "entry 12", "CC-BY-4.0",
                review_status="verified", reviewer="reviewer-1",
                reviewed_at="2026-11-25",
            ),
            SourceDependencyAssertion(
                "a2", "s1", "s3", "shared_witness", "s3",
                "entry 13", "CC-BY-4.0",
                review_status="verified", shared_group_id="witness:archive-12",
                reviewer="reviewer-1", reviewed_at="2026-11-25",
            ),
            SourceDependencyAssertion(
                "a3", "s2", "s3", "syndicated_from", "s3",
                "entry 14", "CC-BY-4.0",
                review_status="candidate", shared_group_id="wire:dispatch-4",
            ),
        ),
        registry_version="genealogy-1",
        dataset_version="fixture-1",
    )

    applied = registry.apply_verified()
    source_map = {source.id: source for source in applied.sources}
    assert source_map["s2"].derived_from_source_ids == ("s1",)
    assert source_map["s1"].shared_evidence_group_ids == ("witness:archive-12",)
    assert source_map["s3"].shared_evidence_group_ids == ("witness:archive-12",)
    assert source_map["s2"].shared_evidence_group_ids == ()
    assert dataset.sources[1].derived_from_source_ids == ()

    report = analyze_source_set_independence(applied, ["s2", "s3"])
    assert report.status == "known_dependence"
    assert report.dependent_clusters[0].bridge_source_ids == ("s1",)


def test_registry_round_trip_and_only_verified_assertions_are_applied():
    dataset = _dataset()
    registry = SourceDependencyRegistry(
        dataset,
        (
            SourceDependencyAssertion(
                "a1", "s2", "s1", "derived_from", "s3",
                "page 4", "CC0-1.0", review_status="disputed",
            ),
        ),
        registry_version="v1",
        dataset_version="d1",
    )
    restored = SourceDependencyRegistry.from_dict(dataset, registry.to_dict())
    assert restored.to_dict() == registry.to_dict()
    assert restored.verified_assertions == ()
    assert restored.apply_verified() == dataset


def test_shared_dependency_requires_group_and_verified_requires_review_metadata():
    with pytest.raises(ValueError, match="shared_group_id"):
        SourceDependencyAssertion(
            "a1", "s1", "s2", "shared_witness", "s3",
            "page 1", "CC0",
        )
    with pytest.raises(ValueError, match="reviewer"):
        SourceDependencyAssertion(
            "a2", "s1", "s2", "derived_from", "s3",
            "page 1", "CC0", review_status="verified",
            reviewed_at="2026-11-25",
        )
    with pytest.raises(ValueError, match="reviewed_at"):
        SourceDependencyAssertion(
            "a3", "s1", "s2", "derived_from", "s3",
            "page 1", "CC0", review_status="verified",
            reviewer="reviewer-1",
        )


def test_registry_rejects_missing_sources_and_unknown_fields():
    dataset = _dataset()
    with pytest.raises(ValueError, match="Unknown source id"):
        SourceDependencyRegistry(
            dataset,
            (
                SourceDependencyAssertion(
                    "a1", "s1", "missing", "derived_from", "s3",
                    "page 1", "CC0",
                ),
            ),
            registry_version="v1",
            dataset_version="d1",
        )

    payload = SourceDependencyRegistry(
        dataset, (), registry_version="v1", dataset_version="d1"
    ).to_dict()
    payload["unexpected"] = True
    with pytest.raises(ValueError, match="Unknown registry field"):
        SourceDependencyRegistry.from_dict(dataset, payload)


def test_shared_group_metadata_is_required_only_for_shared_dependency_types():
    assertion = SourceDependencyAssertion(
        "a1", "s2", "s1", "derived_from", "s3",
        "page 1", "CC0",
    )
    assert assertion.shared_group_id is None
