from __future__ import annotations

import argparse
import json
from pathlib import Path


PROTOCOL = {
    "title": "Blinded Human Review Protocol for FirstResearch Research-Package Evaluation",
    "purpose": (
        "Assess whether human reviewers agree that FirstResearch packages are stronger than matched "
        "prompt-level baseline and ablation packages on derivation, falsifiability, mechanism clarity, novelty, "
        "and experimentability."
    ),
    "minimum_reviewers": 2,
    "target_reviewers": 3,
    "reviewer_profile": [
        "ML, NLP, AI-agent, or research-methodology background",
        "able to judge whether a research question is mechanistic, falsifiable, and experimentable",
        "not involved in generating the packages being reviewed",
    ],
    "inputs": {
        "scalar_results_csv": "outputs/reports/deepseek_ablation_repeated_results.csv",
        "scalar_packet_dir": "outputs/human_review/deepseek_ablation_repeated",
        "pairwise_packet_dir": "outputs/human_review/deepseek_ablation_repeated_pairwise",
    },
    "blinding": [
        "Review files use generated IDs such as HR0001 and PW0001.",
        "System names and source package paths are kept only in private assignment JSON files.",
        "Pairwise package order is randomized independently for each pair.",
        "Reviewers are instructed not to infer or identify the generating system.",
    ],
    "scalar_fields": [
        "blind_id",
        "reviewer_id",
        "first_principles_derivation",
        "falsifiability",
        "mechanism_clarity",
        "novelty",
        "experimentability",
        "review_score",
        "recommendation",
    ],
    "pairwise_fields": ["pair_id", "decision"],
    "pairwise_decisions": ["prefer_a", "prefer_b", "tie", "cannot_judge"],
    "analysis_plan": [
        "Compute per-system scalar means and standard deviations for the five rubric dimensions and average score.",
        "Report reviewer-style score and top recommendation by system.",
        "Compute pairwise wins, losses, ties, win rate, and tie-aware preference score.",
        "Treat pairwise preference as the primary human-validity signal because scalar ratings may compress strong packages.",
        "Do not upgrade paper claims from preliminary to supported by humans until completed scalar and pairwise reports exist.",
    ],
    "ethics": [
        "No human-subject behavioral experiment is conducted; reviewers evaluate generated research-package text.",
        "No private or sensitive participant data are collected by the repository scripts.",
        "Reviewer identities should be stored outside public artifacts unless reviewers consent to attribution.",
    ],
    "commands": [
        "python scripts/export_human_review_packet.py --results outputs/reports/deepseek_ablation_repeated_results.csv --output-dir outputs/human_review/deepseek_ablation_repeated --seed 13",
        "python scripts/analyze_human_review.py --assignments outputs/human_review/deepseek_ablation_repeated/assignments_private.json --scores outputs/human_review/deepseek_ablation_repeated/human_scores.csv --output outputs/human_review/deepseek_ablation_repeated/human_review_report.md --table-output outputs/human_review/deepseek_ablation_repeated/human_review_summary.csv",
        "python scripts/export_pairwise_review_packet.py --results outputs/reports/deepseek_ablation_repeated_results.csv --output-dir outputs/human_review/deepseek_ablation_repeated_pairwise --reference-system firstresearch --seed 17",
        "python scripts/analyze_pairwise_review.py --assignments outputs/human_review/deepseek_ablation_repeated_pairwise/pair_assignments_private.json --decisions outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_decisions.csv --output outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_report.md --table-output outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_summary.csv",
    ],
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the preregistered human-review protocol artifact.")
    parser.add_argument("--output", default="outputs/reports/human_review_protocol.md")
    parser.add_argument("--json-output", default="outputs/reports/human_review_protocol.json")
    args = parser.parse_args()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(PROTOCOL), encoding="utf-8")
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(PROTOCOL, indent=2) + "\n", encoding="utf-8")
    print(output)


def render_markdown(protocol: dict[str, object]) -> str:
    lines = [
        f"# {protocol['title']}",
        "",
        "## Purpose",
        "",
        str(protocol["purpose"]),
        "",
        "## Reviewer Plan",
        "",
        f"- Minimum reviewers: {protocol['minimum_reviewers']}",
        f"- Target reviewers: {protocol['target_reviewers']}",
        "",
        "Reviewer profile:",
    ]
    lines.extend(f"- {item}" for item in protocol["reviewer_profile"])
    lines.extend(["", "## Inputs", ""])
    for key, value in protocol["inputs"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Blinding", ""])
    lines.extend(f"- {item}" for item in protocol["blinding"])
    lines.extend(["", "## Scalar Score CSV", "", "Required columns:"])
    lines.extend(f"- `{field}`" for field in protocol["scalar_fields"])
    lines.extend(["", "## Pairwise Decision CSV", "", "Required columns:"])
    lines.extend(f"- `{field}`" for field in protocol["pairwise_fields"])
    lines.extend(["", "Allowed decisions:"])
    lines.extend(f"- `{decision}`" for decision in protocol["pairwise_decisions"])
    lines.extend(["", "## Analysis Plan", ""])
    lines.extend(f"- {item}" for item in protocol["analysis_plan"])
    lines.extend(["", "## Ethics and Data Handling", ""])
    lines.extend(f"- {item}" for item in protocol["ethics"])
    lines.extend(["", "## Commands", "", "```bash"])
    lines.extend(str(command) for command in protocol["commands"])
    lines.extend(["```", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    main()
