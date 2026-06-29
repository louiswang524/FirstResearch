from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firstresearch.schemas import ResearchPackage


def main() -> None:
    parser = argparse.ArgumentParser(description="Export blinded pairwise preference packets from benchmark results.")
    parser.add_argument("--results", required=True, help="Benchmark CSV containing output_path rows.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--reference-system", default="firstresearch")
    parser.add_argument("--comparison-systems", nargs="*", default=None)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--max-pairs", type=int, default=None)
    args = parser.parse_args()

    rows = _read_rows(Path(args.results))
    pairs = _make_pairs(rows, args.reference_system, args.comparison_systems)
    rng = random.Random(args.seed)
    rng.shuffle(pairs)
    if args.max_pairs is not None:
        pairs = pairs[: args.max_pairs]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    assignments = []
    for index, (reference, comparison) in enumerate(pairs, start=1):
        pair_id = f"PW{index:04d}"
        left, right = reference, comparison
        if rng.random() < 0.5:
            left, right = right, left

        left_package = _load_package(left)
        right_package = _load_package(right)
        pair_path = output_dir / f"{pair_id}.md"
        pair_path.write_text(_render_pair(pair_id, left_package, right_package), encoding="utf-8")
        assignments.append(
            {
                "pair_id": pair_id,
                "topic_id": reference.get("topic_id"),
                "replicate": reference.get("replicate") or None,
                "left_system": left.get("system"),
                "right_system": right.get("system"),
                "left_package": left.get("output_path"),
                "right_package": right.get("output_path"),
                "review_file": str(pair_path),
            }
        )

    (output_dir / "pair_assignments_private.json").write_text(
        json.dumps(assignments, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "pairwise_instructions.md").write_text(_render_instructions(), encoding="utf-8")
    print(output_dir)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _make_pairs(
    rows: list[dict[str, str]],
    reference_system: str,
    comparison_systems: list[str] | None,
) -> list[tuple[dict[str, str], dict[str, str]]]:
    grouped: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in rows:
        key = (row.get("topic_id", ""), row.get("replicate", ""))
        grouped[key][row["system"]] = row

    pairs = []
    for systems_by_name in grouped.values():
        reference = systems_by_name.get(reference_system)
        if reference is None:
            continue
        names = comparison_systems or [name for name in systems_by_name if name != reference_system]
        for name in names:
            comparison = systems_by_name.get(name)
            if comparison is not None:
                pairs.append((reference, comparison))
    return pairs


def _load_package(row: dict[str, str]) -> ResearchPackage:
    package_path = Path(row["output_path"])
    return ResearchPackage.model_validate_json(package_path.read_text(encoding="utf-8"))


def _render_instructions() -> str:
    return "\n".join(
        [
            "# Pairwise Review Instructions",
            "",
            "Each file contains two blinded research packages for the same topic.",
            "Choose which package forms the stronger research proposal, or mark a tie/cannot judge.",
            "Do not try to identify the generating system.",
            "",
            "Decision options: prefer A / prefer B / tie / cannot judge.",
            "",
            "Consider mechanistic derivation, falsifiability, novelty, experimentability, and clarity.",
        ]
    ) + "\n"


def _render_pair(pair_id: str, left: ResearchPackage, right: ResearchPackage) -> str:
    lines = [
        f"# Pairwise Review Item {pair_id}",
        "",
        "## Topic",
        "",
        left.topic.topic,
        "",
        "## Package A",
        "",
        _render_package(left),
        "",
        "## Package B",
        "",
        _render_package(right),
        "",
        "## Preference",
        "",
        "Decision: prefer A / prefer B / tie / cannot judge",
        "",
        "Rationale:",
    ]
    return "\n".join(lines) + "\n"


def _render_package(package: ResearchPackage) -> str:
    certificate = package.certificates[0] if package.certificates else None
    question = certificate.research_question.question if certificate else _first_question(package)
    mechanism = package.mechanism_model.mechanism_summary if package.mechanism_model else "No mechanism model supplied."
    hypothesis = certificate.hypothesis.statement if certificate else "No structured certificate hypothesis supplied."
    test = certificate.minimal_decisive_test.experiment if certificate else "No structured certificate test supplied."
    falsifier = certificate.minimal_decisive_test.falsifying_observation if certificate else "No structured falsifying observation supplied."
    return "\n".join(
        [
            f"Research question: {question}",
            "",
            f"Mechanism: {mechanism}",
            "",
            f"Hypothesis: {hypothesis}",
            "",
            f"Minimal decisive test: {test}",
            "",
            f"Falsifying observation: {falsifier}",
        ]
    )


def _first_question(package: ResearchPackage) -> str:
    if package.candidate_questions:
        return package.candidate_questions[0].question
    return "No research question supplied."


if __name__ == "__main__":
    main()
