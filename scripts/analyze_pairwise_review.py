from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


DECISIONS = {"prefer_a", "prefer_b", "tie", "cannot_judge"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze blinded pairwise human-review decisions.")
    parser.add_argument("--assignments", required=True, help="pair_assignments_private.json from export_pairwise_review_packet.py")
    parser.add_argument("--decisions", required=True, help="CSV with columns pair_id,decision")
    parser.add_argument("--output", required=True, help="Markdown report output path")
    parser.add_argument("--table-output", default=None, help="Optional CSV summary output path")
    args = parser.parse_args()

    assignments = _load_assignments(Path(args.assignments))
    decisions = _load_decisions(Path(args.decisions))
    rows = _join_decisions(assignments, decisions)
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
    return {row["pair_id"]: row for row in data}


def _load_decisions(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    decisions = {}
    for row in rows:
        decision = _normalize_decision(row["decision"])
        if decision not in DECISIONS:
            raise ValueError(f"unsupported decision for {row['pair_id']}: {row['decision']}")
        decisions[row["pair_id"]] = decision
    return decisions


def _normalize_decision(decision: str) -> str:
    return decision.strip().lower().replace(" ", "_").replace("-", "_")


def _join_decisions(
    assignments: dict[str, dict[str, str]],
    decisions: dict[str, str],
) -> list[dict[str, str]]:
    rows = []
    for pair_id, decision in sorted(decisions.items()):
        assignment = assignments[pair_id]
        winner = _winner(assignment, decision)
        rows.append({**assignment, "decision": decision, "winner": winner})
    return rows


def _winner(assignment: dict[str, str], decision: str) -> str:
    if decision == "prefer_a":
        return assignment["left_system"]
    if decision == "prefer_b":
        return assignment["right_system"]
    return decision


def _summarize(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    system_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0, "ties": 0, "cannot_judge": 0})
    for row in rows:
        left = row["left_system"]
        right = row["right_system"]
        decision = row["decision"]
        if decision == "tie":
            system_counts[left]["ties"] += 1
            system_counts[right]["ties"] += 1
        elif decision == "cannot_judge":
            system_counts[left]["cannot_judge"] += 1
            system_counts[right]["cannot_judge"] += 1
        else:
            winner = row["winner"]
            loser = right if winner == left else left
            system_counts[winner]["wins"] += 1
            system_counts[loser]["losses"] += 1

    summary = []
    for system, counts in sorted(system_counts.items()):
        judged = counts["wins"] + counts["losses"] + counts["ties"]
        win_rate = counts["wins"] / judged if judged else 0.0
        preference_score = (counts["wins"] + 0.5 * counts["ties"]) / judged if judged else 0.0
        summary.append({"system": system, **counts, "judged": judged, "win_rate": win_rate, "preference_score": preference_score})
    return summary


def _render_report(summary: list[dict[str, object]], rows: list[dict[str, str]]) -> str:
    lines = [
        "# Pairwise Human Review Report",
        "",
        f"Completed pairwise decisions: {len(rows)}",
        "",
        "| System | Wins | Losses | Ties | Cannot Judge | Judged | Win Rate | Preference Score |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary:
        lines.append(
            f"| {row['system']} | {row['wins']} | {row['losses']} | {row['ties']} | "
            f"{row['cannot_judge']} | {row['judged']} | {row['win_rate']:.2f} | {row['preference_score']:.2f} |"
        )
    lines.extend(["", "## Decisions", ""])
    for row in rows:
        lines.append(
            f"- {row['pair_id']}: {row['decision']} -> {row['winner']} "
            f"(left={row['left_system']}, right={row['right_system']}, topic={row.get('topic_id')})"
        )
    return "\n".join(lines) + "\n"


def _write_summary_csv(path: Path, summary: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["system", "wins", "losses", "ties", "cannot_judge", "judged", "win_rate", "preference_score"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)


if __name__ == "__main__":
    main()
