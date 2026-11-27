"""Command-line tools for validating and exporting HistoryPy datasets."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from historypy.io import load_dataset
from historypy.research import (
    audit_citation_completeness,
    build_historical_dossier,
    render_historical_dossier,
    run_retrieval_benchmark,
)
from historypy.research.visualization import (
    render_visualization_html,
    timeline_visualization_data,
    to_geojson,
    to_graphviz_dot,
)


def _write_output(content: str, output: Path | None) -> None:
    if output is None:
        sys.stdout.write(content)
        if not content.endswith("\n"):
            sys.stdout.write("\n")
    else:
        output.write_text(content + ("" if content.endswith("\n") else "\n"), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="historypy",
        description="Validate, audit, and export evidence-aware historical datasets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate a dataset JSON file")
    validate.add_argument("dataset", type=Path)

    audit = subparsers.add_parser("audit", help="audit citation traceability")
    audit.add_argument("dataset", type=Path)
    audit.add_argument("--output", type=Path)

    dossier = subparsers.add_parser("dossier", help="organize a dataset into a stepwise historical dossier")
    dossier.add_argument("dataset", type=Path)
    dossier.add_argument("--title", default="Historical dossier")
    dossier.add_argument("--scope-note", default="")
    dossier.add_argument("--exclude-indeterminate-dates", action="store_true")
    dossier.add_argument("--format", choices=("markdown", "json"), default="markdown")
    dossier.add_argument("--output", type=Path)

    evaluate = subparsers.add_parser("evaluate", help="compare retrieval methods on reviewed relevance judgments")
    evaluate.add_argument("dataset", type=Path)
    evaluate.add_argument("cases", type=Path, help="JSON file containing reviewed query cases")
    evaluate.add_argument("--top-k", type=int, default=10)
    evaluate.add_argument("--bootstrap-samples", type=int, default=2000)
    evaluate.add_argument("--seed", type=int, default=2026)
    evaluate.add_argument("--output", type=Path, required=True)

    export = subparsers.add_parser("export", help="export a visualization artifact")
    export.add_argument("dataset", type=Path)
    export.add_argument("--format", choices=("geojson", "graphviz", "timeline", "html"), required=True)
    export.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; return 0 on success and 2 for invalid input or failed validation."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        dataset = load_dataset(args.dataset, validate=False)
        if args.command == "validate":
            dataset.require_valid()
            print("HistoryPy dataset is valid.")
            return 0
        if args.command == "audit":
            report = audit_citation_completeness(dataset)
            _write_output(json.dumps(asdict(report), indent=2, sort_keys=True), args.output)
            return 0
        if args.command == "dossier":
            dossier = build_historical_dossier(
                dataset,
                title=args.title,
                scope_note=args.scope_note,
                include_indeterminate_dates=not args.exclude_indeterminate_dates,
            )
            rendered = (
                json.dumps(asdict(dossier), ensure_ascii=False, indent=2, sort_keys=True)
                if args.format == "json"
                else render_historical_dossier(dossier)
            )
            _write_output(rendered, args.output)
            return 0
        if args.command == "evaluate":
            cases = json.loads(args.cases.read_text(encoding="utf-8"))
            if not isinstance(cases, list):
                raise ValueError("benchmark cases file must contain a JSON array")
            report = run_retrieval_benchmark(
                dataset,
                cases,
                cutoff=args.top_k,
                bootstrap_samples=args.bootstrap_samples,
                seed=args.seed,
            )
            _write_output(json.dumps(asdict(report), ensure_ascii=False, indent=2), args.output)
            return 0
        if args.format == "geojson":
            rendered = json.dumps(to_geojson(dataset), ensure_ascii=False, indent=2, sort_keys=True)
        elif args.format == "graphviz":
            rendered = to_graphviz_dot(dataset)
        elif args.format == "timeline":
            rendered = json.dumps(
                timeline_visualization_data(dataset),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        else:
            rendered = render_visualization_html(dataset)
        _write_output(rendered, args.output)
        return 0
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(f"historypy: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
