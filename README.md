# HistoryPy

An open, evidence-aware toolkit for historical research and analysis.

HistoryPy is a Python library for representing, organizing, comparing, and analyzing historical information. It is designed around traceable sources, explicit uncertainty, and reproducible research—not around treating unsupported claims as facts.

## Principles

- Evidence before assertion: historical claims should link to identifiable sources and evidence.
- Preserve disagreement: conflicting accounts remain visible.
- Represent uncertainty in dates, identities, locations, and interpretations.
- Make transformations and analytical results reproducible and testable.
- Record provenance and respect copyright and dataset licenses.
- Support histories from all regions and periods without assuming one chronology is universal.

## Initial scope

The first release establishes structured historical dates, event records, bibliographic source records, explicit claim-to-source evidence links, basic chronology comparisons, automated tests, and documentation.

This repository does not yet contain a comprehensive historical dataset and does not automatically determine whether a claim is true.

## Quick start

Requires Python 3.10 or newer.

    python -m pip install -e ".[dev]"
    pytest

Example:

    from historypy import HistoricalDate, HistoricalEvent

    event = HistoricalEvent(
        id="event-example-001",
        title="Example historical event",
        date=HistoricalDate(
            earliest="1947-08-14",
            latest="1947-08-14",
            precision="day",
            calendar="gregorian",
        ),
        summary="An illustrative record; replace with a sourced entry.",
    )
    print(event.title)
    print(event.date.display())

## Development status

Early development. APIs may change before the first stable release.

See docs/architecture.md and CONTRIBUTING.md.