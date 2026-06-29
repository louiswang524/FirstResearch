from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


METRICS = [
    "first_principles_derivation",
    "falsifiability",
    "mechanism_clarity",
    "novelty",
    "experimentability",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze scalar blinded human-review scores.")
    parser.add_argument("--assignments", required=True, help="assignments_private.json from export_human_review_packet.py")
    parser.add_argument("--scores", required=True, help="CSV with blind_id plus rubric score columns")
    parser.add_argument("--output", required=True, help="Markdown report output path")
    parser.add_argument("--table-output", default=None, help="Optional CSV summary output path")
    args = parser.parse_args()

    assignments = _load_assignments(Path(args.assignments))
    score_rows = _load_scores(Path(args.scores))
    rows = _join_scores(assignments, score_rows)
    summary = _summarize(rows)
    report = _render_report(summary, rows)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    if args.table_output:
        _write_summary_csv(Path(args.table_output), summary)
    print(output)


def _load_assignments(path: Path) -> dict[str, dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["blind_id"]: row for row in data}


def _load_scores(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _join_scores(
    assignments: dict[str, dict[str, str]],
    score_rows: list[dict[str, str]],
) -> list[dict[str, object]]:
    rows = []
    for score_row in score_rows:
        blind_id = score_row["blind_id"]
        assignment = assignments[blind_id]
        numeric = {metric: _score(score_row, metric) for metric in METRICS}
        numeric["average_score"] = mean(numeric.values())
        review_score = score_row.get("review_score", "")
        numeric["review_score"] = float(review_score) if review_score != "" else None
        rows.append(
            {
                **assignment,
                **numeric,
                "recommendation": score_row.get("recommendation", ""),
                "reviewer_id": score_row.get("reviewer_id", ""),
            }
        )
    return rows


def _score(row: dict[str, str], metric: str) -> float:
    value = row.get(metric, "")
    if value == "":
        raise ValueError(f"missing score for {metric} in {row.get('blind_id')}")
    score = float(value)
    if score < 0 or score > 5:
        raise ValueError(f"{metric} must be in [0, 5], got {score}")
    return score


def _summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["system"])].append(row)

    summary = []
    for system, system_rows in sorted(grouped.items()):
        out: dict[str, object] = {"system": system, "n": len(system_rows)}
        for metric in [*METRICS, "average_score"]:
            values = [float(row[metric]) for row in system_rows]
            out[metric] = mean(values)
            out[f"{metric}_std"] = pstdev(values) if len(values) > 1 else 0.0
        review_values = [row["review_score"] for row in system_rows if row["review_score"] is not None]
        out["review_score"] = mean(review_values) if review_values else None
        out["review_score_std"] = pstdev(review_values) if len(review_values) > 1 else 0.0
        recommendations = Counter(str(row["recommendation"]) for row in system_rows if row["recommendation"])
        out["top_recommendation"] = recommendations.most_common(1)[0][0] if recommendations else ""
        summary.append(out)
    return summary


def _render_report(summary: list[dict[str, object]], rows: list[dict[str, object]]) -> str:
    lines = [
        "# Scalar Human Review Report",
        "",
        f"Completed scalar reviews: {len(rows)}",
        "",
        "| System | N | Derivation | Falsifiability | Mechanism | Novelty | Experimentability | Avg | Avg Std | Review | Top Recommendation |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in summary:
        review = "" if row["review_score"] is None else f"{row['review_score']:.2f}"
        lines.append(
            f"| {row['system']} | {row['n']} | {row['first_principles_derivation']:.2f} | "
            f"{row['falsifiability']:.2f} | {row['mechanism_clarity']:.2f} | {row['novelty']:.2f} | "
            f"{row['experimentability']:.2f} | {row['average_score']:.2f} | {row['average_score_std']:.2f} | "
            f"{review} | {row['top_recommendation']} |"
        )
    return "\n".join(lines) + "\n"


def _write_summary_csv(path: Path, summary: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    metric_fields = []
    for metric in [*METRICS, "average_score"]:
        metric_fields.extend([metric, f"{metric}_std"])
    fieldnames = ["system", "n", *metric_fields, "review_score", "review_score_std", "top_recommendation"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)


if __name__ == "__main__":
    main()
