from historypy.examples.titanic_inquiry_comparison import build_titanic_inquiry_dataset
from historypy import render_event_source_comparison


def test_titanic_inquiry_comparison_preserves_both_reported_totals_and_locators():
    dataset = build_titanic_inquiry_dataset()
    report = render_event_source_comparison(dataset, "titanic_loss_1912")

    assert "U.S. Senate Report No. 806" in report
    assert "British Wreck Commissioner's Court" in report
    assert "Total lifeboat capacity, 1,176." in report
    assert "or a total of 1,178" in report
    assert "while but 706 were saved." in report
    assert "712, rescued by" in report
    assert "page: 13" in report
    assert "Question 21(a)" in report
    assert "do not establish source independence" in report
    assert "do not" in report
