from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from statistics import pstdev


METRICS = [
    "first_principles_derivation",
    "falsifiability",
    "mechanism_clarity",
    "novelty",
    "experimentability",
    "average_score",
]


def generate_report(results_csv: Path, output_md: Path, table_csv: Path | None = None) -> str:
    rows = _read_rows(results_csv)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["system"]].append(row)

    summary_rows = []
    for system, system_rows in sorted(grouped.items()):
        summary = {"system": system, "n": len(system_rows)}
        for metric in METRICS:
            values = [float(row[metric]) for row in system_rows]
            summary[metric] = sum(values) / len(values)
            summary[f"{metric}_std"] = pstdev(values) if len(values) > 1 else 0.0
        summary["pass_rate"] = sum(row["passed_gate"].lower() == "true" for row in system_rows) / len(system_rows)
        replicate_ids = {row.get("replicate", "") for row in system_rows if row.get("replicate", "")}
        summary["replicates"] = len(replicate_ids) if replicate_ids else 1
        summary_rows.append(summary)

    lines = ["# FirstResearch Benchmark Report", ""]
    lines.append("## Average Scores")
    lines.append("")
    lines.append("| System | N | Repeats | Derivation | Falsifiability | Mechanism | Novelty | Experimentability | Avg | Avg Std | Pass Rate |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for row in summary_rows:
        lines.append(
            f"| {row['system']} | {row['n']} | {row['replicates']} | {row['first_principles_derivation']:.2f} | "
            f"{row['falsifiability']:.2f} | {row['mechanism_clarity']:.2f} | {row['novelty']:.2f} | "
            f"{row['experimentability']:.2f} | {row['average_score']:.2f} | {row['average_score_std']:.2f} | {row['pass_rate']:.2f} |"
        )

    lines.extend(["", "## Top Examples", ""])
    top_rows = sorted(rows, key=lambda row: float(row["average_score"]), reverse=True)[:5]
    for row in top_rows:
        lines.append(f"- {row['system']} on {row['topic_id']}: avg={float(row['average_score']):.2f}, output={row['output_path']}")

    lines.extend(["", "## Failure Types", ""])
    failed = [row for row in rows if row["passed_gate"].lower() != "true"]
    if failed:
        for row in failed[:10]:
            lines.append(f"- {row['system']} on {row['topic_id']}: did not pass certificate gate")
    else:
        lines.append("- No gate failures recorded.")

    lines.extend(["", "## Comparison Table", ""])
    comparison_rows = [
        row
        for row in summary_rows
        if row["system"] == "firstresearch" or "ablation" in row["system"] or "combo" in row["system"]
    ]
    if comparison_rows:
        full = next((row for row in comparison_rows if row["system"] == "firstresearch"), None)
        full_average = float(full["average_score"]) if full else None
        lines.append("| System | Average Score | Delta vs Full | Pass Rate |")
        lines.append("|---|---:|---:|---:|")
        for row in comparison_rows:
            delta = float(row["average_score"]) - full_average if full_average is not None else 0.0
            lines.append(f"| {row['system']} | {row['average_score']:.2f} | {delta:+.2f} | {row['pass_rate']:.2f} |")
    else:
        lines.append("- No comparison systems included in this run.")

    text = "\n".join(lines) + "\n"
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(text, encoding="utf-8")
    if table_csv:
        _write_summary_csv(table_csv, summary_rows)
    return text


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_summary_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_fields = []
    for metric in METRICS:
        metric_fields.extend([metric, f"{metric}_std"])
    fieldnames = ["system", "n", "replicates", *metric_fields, "pass_rate"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
