import pytest

from historypy import HistoricalClaim, HistoricalDataset, HistoricalDate, HistoricalRelationship


def _year(value):
    return HistoricalDate(
        earliest_year=value, latest_year=value, calendar="gregorian"
    )


def test_relationship_accepts_distinct_ordered_validity_boundaries():
    relationship = HistoricalRelationship(
        "r1", "entity-a", "related_to", "entity-b",
        valid_from=_year(1800),
        valid_to=_year(1810),
    )
    assert relationship.valid_from.earliest_year == 1800
    assert relationship.valid_to.latest_year == 1810


def test_relationship_rejects_valid_from_after_valid_to():
    with pytest.raises(ValueError, match="valid_from cannot be later"):
        HistoricalRelationship(
            "r1", "entity-a", "related_to", "entity-b",
            valid_from=_year(1810),
            valid_to=_year(1800),
        )


def test_relationship_does_not_compare_incomparable_calendars_as_ordered():
    relationship = HistoricalRelationship(
        "r1", "entity-a", "related_to", "entity-b",
        valid_from=HistoricalDate(
            earliest_year=1800, calendar="julian"
        ),
        valid_to=HistoricalDate(
            earliest_year=1790, calendar="gregorian"
        ),
    )
    assert relationship.valid_from.calendar == "julian"



def test_dataset_rejects_relationship_claim_references_that_do_not_exist():
    dataset = HistoricalDataset(
        people=(),
        claims=(HistoricalClaim("claim-1", "A proposition."),),
        relationships=(
            HistoricalRelationship(
                "r1", "missing-person-a", "related_to", "missing-person-b",
                claim_ids=("missing-claim",),
            ),
        ),
    )
    codes = {issue.code for issue in dataset.validate()}
    assert "missing_relationship_claim" in codes
