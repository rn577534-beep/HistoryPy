# Student-facing visual history learning

HistoryPy can compose a researcher-curated dataset into a seven-part learning
view for one recorded event:

1. **Story** — the event summary, recorded context, and tags.
2. **Historical mystery** — inquiry prompts plus claims explicitly linked to the event.
3. **Map** — only places explicitly linked to the event; coordinates are labelled
   as recorded coordinates, not reconstructed historical borders.
4. **Timeline** — event chronology that preserves date precision, calendar, and
   uncertainty.
5. **What happened elsewhere?** — other events are included only when their
   explicit date intervals overlap, their calendars match, and they have distinct
   recorded places. An empty result is not evidence that nothing else happened.
6. **Complete visual storyboard** — background, event, recorded people and places,
   claims/evidence counts, and open research questions.
7. **Evidence explorer** — linked claims, support/contradiction relations, source
   metadata, and locators or quotations when recorded.

The builder does not infer causal relationships, consequences, event links, or
missing dates. Researchers must add sourced claims and explicit relationships.
A source link is not proof of authenticity or truth.

## Python API

```python
from historypy import (
    load_dataset,
    learning_experience_data,
    render_learning_experience_html,
)

dataset = load_dataset("research-dataset.json")
view = learning_experience_data(dataset, event_id="event-001")
html = render_learning_experience_html(dataset, event_id="event-001")
```

The HTML is self-contained and can be saved by the calling application as a
standalone learning page. The data builder is also suitable for a custom
frontend, mobile app, or classroom platform.

## Assessment is intentionally separate

This seven-part learning view contains no quiz, score, grading, or test control.
An assessment experience should only be initiated after the learner explicitly
asks to be tested. This release does not silently start or insert a test.

## Limitations

- "Elsewhere" is constrained to events in the same dataset and comparable,
  explicitly bounded intervals on the same named calendar.
- Place views require coordinates in the dataset. No geocoding or map tiles are
  silently fetched.
- The storyboard is a structured visual outline, not an automatically verified
  historical reconstruction.
- Historical interpretations remain subject to source criticism and human review.
