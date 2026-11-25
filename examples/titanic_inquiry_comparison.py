"""Run the packaged Titanic source-comparison example from a checkout."""
from historypy.examples.titanic_inquiry_comparison import (
    build_titanic_inquiry_dataset,
)

if __name__ == "__main__":
    from historypy import render_event_source_comparison

    dataset = build_titanic_inquiry_dataset()
    print(render_event_source_comparison(dataset, "titanic_loss_1912"))
