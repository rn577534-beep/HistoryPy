"""Allen interval algebra for bounded historical dates.

Relations require complete comparable bounds in one explicit calendar.
No calendar conversion is attempted.
"""
from __future__ import annotations

from typing import Literal

from historypy.core.models import HistoricalDate

AllenRelation = Literal[
    "before", "meets", "overlaps", "starts", "during", "finishes", "equals",
    "finished_by", "contains", "started_by", "overlapped_by", "met_by", "after",
]


def allen_interval_relation(
    first: HistoricalDate, second: HistoricalDate
) -> AllenRelation | None:
    """Return the directed Allen relation of first relative to second.

    Returns None when either interval lacks complete bounds or calendars are
    unspecified/incompatible. Only stored normalized bounds are compared.
    """
    if not isinstance(first, HistoricalDate) or not isinstance(second, HistoricalDate):
        raise TypeError("first and second must be HistoricalDate instances")
    if (
        first.calendar == "unspecified"
        or second.calendar == "unspecified"
        or first.calendar != second.calendar
    ):
        return None
    a, b = first._comparison_bounds()
    c, d = second._comparison_bounds()
    if any(value is None for value in (a, b, c, d)):
        return None
    if a > b or c > d:
        return None
    if b < c:
        return "before"
    if b == c:
        return "meets"
    if a < c < b < d:
        return "overlaps"
    if a == c and b < d:
        return "starts"
    if c < a and b < d:
        return "during"
    if c < a and b == d:
        return "finishes"
    if a == c and b == d:
        return "equals"
    if a == c and d < b:
        return "started_by"
    if a < c and d < b:
        return "contains"
    if a < c and b == d:
        return "finished_by"
    if c < a < d < b:
        return "overlapped_by"
    if d == a:
        return "met_by"
    if a > d:
        return "after"
    return None
