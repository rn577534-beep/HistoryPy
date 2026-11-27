from historypy import HistoricalDataset, HistoricalDate, HistoricalEvent, HistoricalPlace
from historypy.cli import main
from historypy.io import save_dataset


def sample_dataset():
    return HistoricalDataset(
        events=(HistoricalEvent(
            "event-1", "Example event",
            HistoricalDate(earliest_year=1900, latest_year=1900, calendar="gregorian"),
            place_ids=("place-1",),
        ),),
        places=(HistoricalPlace(
            "place-1", "Example place", latitude=23.7, longitude=90.4,
        ),),
    )


def test_cli_validate_and_export_geojson(tmp_path, capsys):
    dataset_path = tmp_path / "dataset.json"
    save_dataset(sample_dataset(), dataset_path)

    assert main(["validate", str(dataset_path)]) == 0
    assert "valid" in capsys.readouterr().out

    output = tmp_path / "places.geojson"
    assert main([
        "export", str(dataset_path), "--format", "geojson", "--output", str(output)
    ]) == 0
    assert '"FeatureCollection"' in output.read_text(encoding="utf-8")


def test_cli_export_html_and_audit(tmp_path):
    dataset_path = tmp_path / "dataset.json"
    save_dataset(sample_dataset(), dataset_path)

    html_path = tmp_path / "report.html"
    assert main([
        "export", str(dataset_path), "--format", "html", "--output", str(html_path)
    ]) == 0
    assert "<!doctype html>" in html_path.read_text(encoding="utf-8")

    audit_path = tmp_path / "audit.json"
    assert main(["audit", str(dataset_path), "--output", str(audit_path)]) == 0
    assert '"total_evidence_links": 0' in audit_path.read_text(encoding="utf-8")


def test_cli_invalid_file_returns_error_code(tmp_path, capsys):
    missing = tmp_path / "missing.json"
    assert main(["validate", str(missing)]) == 2
    assert "error" in capsys.readouterr().err
