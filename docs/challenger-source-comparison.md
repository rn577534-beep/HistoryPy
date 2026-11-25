# Source comparison case study: Challenger mission 51-L (1986)

This worked example compares three records about the 28 January 1986 Challenger
mission 51-L accident:

1. **Presidential Commission report**, published 6 June 1986. NASA's official
   NTRS copy is
   https://ntrs.nasa.gov/archive/nasa/casi.ntrs.nasa.gov/19860015255.pdf.
   Chapter V, paragraph 82 states the Commission's conclusion about the launch
   decision.
2. **Presidential Commission hearing transcript**, Volume V, 2 May 1986 session.
   The transcript records Al McDonald's testimony at page 2754:
   https://www.nasa.gov/history/rogersrep/v5part6a.htm.
3. **House Report 99-1016**, a later congressional review:
   https://www.govinfo.gov/content/pkg/GPO-CRPT-99hrpt1016/pdf/GPO-CRPT-99hrpt1016.pdf.

## What the example records

- The Commission report's conclusion that the launch decision was flawed.
- McDonald's testimony that the Center Board briefing described the erosion
  concern only briefly. The stored quotation is an excerpt from his answer; the
  question immediately before it asks whether the temperature concern and
  O-ring erosion problems had been briefed.
- The House report as a separate official review, explicitly marked as derived
  from the Commission report.

## Independence is not assumed

These are three documents, but not three independent evidence streams. The
hearing transcript belongs to the same Presidential Commission record as its
final report. The House report reviews the Commission's work. The example
records those relationships through shared evidence groups and the
derived-from-source field; it must not be counted as three independent
confirmations.

The quotation and locator fields are traceability metadata. They do not by
themselves prove the testimony is complete, unbiased, or factually correct.
Researchers should read the full question-and-answer context and consult the
original documents before drawing conclusions.

Run the example with:

~~~bash
python -c "from historypy import render_event_source_comparison; from historypy.examples.challenger_source_comparison import build_challenger_dataset; d=build_challenger_dataset(); print(render_event_source_comparison(d, 'challenger_51l_1986'))"
~~~
