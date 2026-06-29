from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


METRICS = [
    ("first_principles_derivation", "Derivation"),
    ("falsifiability", "Falsifiability"),
    ("mechanism_clarity", "Mechanism"),
    ("novelty", "Novelty"),
    ("experimentability", "Experimentability"),
    ("average_score", "Avg"),
    ("review_score", "Review"),
]

DISPLAY_TO_SYSTEM = {
    "FirstResearch": "firstresearch",
    "TreeSearchScientist": "tree_search_scientist",
    "CoScientist": "co_scientist",
    "AgentLab": "agent_lab",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the manuscript strong-baseline table against benchmark CSV results.")
    parser.add_argument("--results", default="outputs/reports/deepseek_strong_baselines_10topics.csv")
    parser.add_argument("--manuscript", default="papers/firstresearch_draft.md")
    parser.add_argument("--output", default="outputs/reports/results_table_audit.md")
    parser.add_argument("--json-output", default="outputs/reports/results_table_audit.json")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    expected = _summarize_results(Path(args.results))
    observed = _parse_manuscript_table(Path(args.manuscript))
    rows = _compare(expected, observed)
    report = _render_report(rows, args.results, args.manuscript)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    print(output)
    if args.strict and any(not row["passed"] for row in rows):
        raise SystemExit(1)


def _summarize_results(path: Path) -> dict[str, dict[str, float]]:
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["system"]].append(row)
    summaries = {}
    for system, system_rows in grouped.items():
        summary = {}
        for metric, _ in METRICS:
            values = [float(row[metric]) for row in system_rows if row.get(metric, "") != ""]
            summary[metric] = round(mean(values), 2) if values else 0.0
        summaries[system] = summary
    return summaries


def _parse_manuscript_table(path: Path) -> dict[str, dict[str, float]]:
    text = path.read_text(encoding="utf-8")
    table_match = re.search(
        r"\*\*Table \d+: Strong-baseline comparison.*?\n\n(?P<table>\| System \|.*?)(?:\n\n|$)",
        text,
        flags=re.DOTALL,
    )
    if not table_match:
        raise ValueError("Could not find strong-baseline comparison table in manuscript")
    table = table_match.group("table")
    observed: dict[str, dict[str, float]] = {}
    for line in table.splitlines():
        if not line.startswith("| ") or line.startswith("| System ") or line.startswith("|---"):
            continue
        cells = [cell.strip().replace("**", "") for cell in line.strip("|").split("|")]
        if len(cells) != 8:
            continue
        display_name = cells[0]
        system = DISPLAY_TO_SYSTEM.get(display_name)
        if not system:
            continue
        observed[system] = {
            "first_principles_derivation": float(cells[1]),
            "falsifiability": float(cells[2]),
            "mechanism_clarity": float(cells[3]),
            "novelty": float(cells[4]),
            "experimentability": float(cells[5]),
            "average_score": float(cells[6]),
            "review_score": float(cells[7]),
        }
    return observed


def _compare(
    expected: dict[str, dict[str, float]],
    observed: dict[str, dict[str, float]],
) -> list[dict[str, object]]:
    rows = []
    for display_name, system in DISPLAY_TO_SYSTEM.items():
        expected_metrics = expected.get(system)
        observed_metrics = observed.get(system)
        if expected_metrics is None or observed_metrics is None:
            rows.append(
                {
                    "system": system,
                    "display_name": display_name,
                    "metric": "__row__",
                    "expected": expected_metrics,
                    "observed": observed_metrics,
                    "passed": False,
                }
            )
            continue
        for metric, _ in METRICS:
            expected_value = expected_metrics[metric]
            observed_value = observed_metrics[metric]
            rows.append(
                {
                    "system": system,
                    "display_name": display_name,
                    "metric": metric,
                    "expected": expected_value,
                    "observed": observed_value,
                    "passed": abs(expected_value - observed_value) < 0.005,
                }
            )
    return rows


def _render_report(rows: list[dict[str, object]], results_path: str, manuscript_path: str) -> str:
    failures = [row for row in rows if not row["passed"]]
    lines = [
        "# Results Table Audit",
        "",
        f"Results CSV: `{results_path}`",
        f"Manuscript: `{manuscript_path}`",
        f"Values checked: {len(rows)}",
        f"Failures: {len(failures)}",
        "",
        "| System | Metric | Expected | Observed | Status |",
        "|---|---|---:|---:|---|",
    ]
    for row in rows:
        status = "PASS" if row["passed"] else "FAIL"
        lines.append(
            f"| {row['display_name']} | {row['metric']} | {row['expected']} | {row['observed']} | {status} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
