from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firstresearch.schemas import ResearchPackage


RUBRIC = [
    ("first_principles_derivation", "Does the question trace clearly to primitives, assumptions, and tensions?"),
    ("falsifiability", "Is there a concrete observation that would reject the hypothesis?"),
    ("mechanism_clarity", "Are variables and causal or computational links clear?"),
    ("novelty", "Is the question non-obvious relative to generic gap-finding?"),
    ("experimentability", "Can the proposed test be run with reasonable resources?"),
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export blinded research packages for human review.")
    parser.add_argument("--results", required=True, help="Benchmark CSV containing output_path rows.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--max-items", type=int, default=None)
    args = parser.parse_args()

    rows = _read_rows(Path(args.results))
    rng = random.Random(args.seed)
    rng.shuffle(rows)
    if args.max_items is not None:
        rows = rows[: args.max_items]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    assignments = []
    for index, row in enumerate(rows, start=1):
        blind_id = f"HR{index:04d}"
        package_path = Path(row["output_path"])
        package = ResearchPackage.model_validate_json(package_path.read_text(encoding="utf-8"))
        review_path = output_dir / f"{blind_id}.md"
        review_path.write_text(_render_review_item(blind_id, package), encoding="utf-8")
        assignments.append(
            {
                "blind_id": blind_id,
                "topic_id": row.get("topic_id"),
                "system": row.get("system"),
                "replicate": row.get("replicate") or None,
                "source_package": str(package_path),
                "review_file": str(review_path),
            }
        )

    (output_dir / "assignments_private.json").write_text(
        json.dumps(assignments, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "rubric.md").write_text(_render_rubric(), encoding="utf-8")
    print(output_dir)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _render_rubric() -> str:
    lines = [
        "# Human Review Rubric",
        "",
        "Score each dimension from 0 to 5. Use half-points only if necessary.",
        "Do not try to identify the system that generated the package.",
        "",
        "| Dimension | Question | Score | Notes |",
        "|---|---|---:|---|",
    ]
    for name, question in RUBRIC:
        lines.append(f"| {name} | {question} |  |  |")
    lines.extend(
        [
            "",
            "Reviewer-style score: 1-10",
            "",
            "Recommendation: reject / weak_reject / borderline / weak_accept / accept",
            "",
            "Pairwise preference, when reviewing matched items for the same topic: prefer A / prefer B / tie / cannot judge.",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_review_item(blind_id: str, package: ResearchPackage) -> str:
    certificate = package.certificates[0] if package.certificates else None
    question = certificate.research_question.question if certificate else _first_question(package)
    hypothesis = certificate.hypothesis.statement if certificate else "No structured certificate hypothesis supplied."
    test = certificate.minimal_decisive_test.experiment if certificate else "No structured certificate test supplied."
    falsifier = certificate.minimal_decisive_test.falsifying_observation if certificate else "No structured falsifying observation supplied."
    mechanism = package.mechanism_model.mechanism_summary if package.mechanism_model else "No mechanism model supplied."
    tension = certificate.tension_or_contradiction.statement if certificate else _first_tension(package)

    lines = [
        f"# Blinded Review Item {blind_id}",
        "",
        "## Topic",
        "",
        package.topic.topic,
        "",
        "## Proposed Research Question",
        "",
        question,
        "",
        "## Mechanism Summary",
        "",
        mechanism,
        "",
        "## Tension or Contradiction",
        "",
        tension,
        "",
        "## Hypothesis",
        "",
        hypothesis,
        "",
        "## Minimal Decisive Test",
        "",
        test,
        "",
        "## Falsifying Observation",
        "",
        falsifier,
        "",
        "## Reviewer Scores",
        "",
        "| Dimension | Score 0-5 | Notes |",
        "|---|---:|---|",
    ]
    for name, _ in RUBRIC:
        lines.append(f"| {name} |  |  |")
    lines.extend(
        [
            "",
            "Reviewer-style score 1-10:",
            "",
            "Recommendation:",
            "",
            "Free-form comments:",
        ]
    )
    return "\n".join(lines) + "\n"


def _first_question(package: ResearchPackage) -> str:
    if package.candidate_questions:
        return package.candidate_questions[0].question
    return "No research question supplied."


def _first_tension(package: ResearchPackage) -> str:
    if package.tensions:
        return package.tensions[0].statement
    return "No tension supplied."


if __name__ == "__main__":
    main()
