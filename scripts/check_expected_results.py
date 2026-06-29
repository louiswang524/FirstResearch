from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path


EXPECTED_STRONG_DEEPSEEK = {
    "firstresearch": 4.76,
    "tree_search_scientist": 4.32,
    "co_scientist": 4.18,
    "agent_lab": 4.12,
}

EXPECTED_STRONG_GEMINI = {
    "firstresearch": 4.86,
    "tree_search_scientist": 4.38,
    "co_scientist": 4.28,
    "agent_lab": 4.16,
}

EXPECTED_ABLATION_DEEPSEEK = {
    "certificate_only_ablation": 4.90,
    "firstresearch": 4.80,
    "no_self_improvement_ablation": 4.76,
    "no_novelty_boundary_repair_ablation": 4.44,
    "no_gate_repair_ablation": 4.30,
    "no_mechanism_model_ablation": 3.78,
    "no_certificate_ablation": 0.92,
}

EXPECTED_ABLATION_GEMINI = {
    "certificate_only_ablation": 4.88,
    "firstresearch": 4.74,
    "no_certificate_ablation": 0.89,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Check paper headline numbers against saved result artifacts.")
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument("--json-output", default="outputs/reports/expected_results_check.json")
    args = parser.parse_args()

    checks: list[dict[str, object]] = []
    checks.extend(
        _check_system_means(
            "strong_deepseek",
            Path("outputs/reports/deepseek_strong_baselines_10topics.csv"),
            EXPECTED_STRONG_DEEPSEEK,
            args.tolerance,
        )
    )
    checks.extend(
        _check_system_means(
            "strong_gemini",
            Path("outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv"),
            EXPECTED_STRONG_GEMINI,
            args.tolerance,
        )
    )
    checks.extend(
        _check_table_means(
            "ablation_deepseek",
            Path("outputs/reports/deepseek_ablation_repeated_table.csv"),
            EXPECTED_ABLATION_DEEPSEEK,
            args.tolerance,
        )
    )
    checks.extend(
        _check_table_means(
            "ablation_gemini",
            Path("outputs/reports/deepseek_ablation_repeated_gemini_judge_table.csv"),
            EXPECTED_ABLATION_GEMINI,
            args.tolerance,
        )
    )
    checks.extend(_check_agreement_report(Path("outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.md")))

    passed = all(check["passed"] for check in checks)
    for check in checks:
        status = "PASS" if check["passed"] else "FAIL"
        print(f"{status} {check['id']}: {check['detail']}")

    output = Path(args.json_output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"passed": passed, "checks": checks}, indent=2) + "\n", encoding="utf-8")
    if not passed:
        raise SystemExit(1)


def _check_system_means(
    prefix: str,
    path: Path,
    expected: dict[str, float],
    tolerance: float,
    replicate: int | None = None,
) -> list[dict[str, object]]:
    rows = _read_rows(path)
    if replicate is not None:
        rows = [row for row in rows if _as_optional_int(row.get("replicate")) == replicate]
    actual = _mean_by_system(rows)
    checks = []
    for system, expected_value in expected.items():
        actual_value = actual.get(system)
        passed = actual_value is not None and math.isclose(actual_value, expected_value, abs_tol=tolerance)
        checks.append(
            {
                "id": f"{prefix}:{system}",
                "passed": passed,
                "expected": expected_value,
                "actual": actual_value,
                "detail": f"expected {expected_value:.2f}, actual {actual_value:.2f}" if actual_value is not None else "missing",
            }
        )
    return checks


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _check_table_means(
    prefix: str,
    path: Path,
    expected: dict[str, float],
    tolerance: float,
) -> list[dict[str, object]]:
    rows = _read_rows(path)
    actual = {row.get("system", ""): round(float(row["average_score"]), 2) for row in rows if row.get("system")}
    checks = []
    for system, expected_value in expected.items():
        actual_value = actual.get(system)
        passed = actual_value is not None and math.isclose(actual_value, expected_value, abs_tol=tolerance)
        checks.append(
            {
                "id": f"{prefix}:{system}",
                "passed": passed,
                "expected": expected_value,
                "actual": actual_value,
                "detail": f"expected {expected_value:.2f}, actual {actual_value:.2f}" if actual_value is not None else "missing",
            }
        )
    return checks


def _mean_by_system(rows: list[dict[str, str]]) -> dict[str, float]:
    scores: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        system = row.get("system", "")
        if not system:
            continue
        scores[system].append(float(row["average_score"]))
    return {system: round(sum(values) / len(values), 2) for system, values in scores.items() if values}


def _check_agreement_report(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return [{"id": "strong_agreement:exists", "passed": False, "detail": "missing agreement report"}]
    text = path.read_text(encoding="utf-8")
    checks = []
    for label, expected in [
        ("matched_rows", "Matched package rows: 40"),
        ("pearson_average", "0.865"),
        ("spearman_average", "0.894"),
        ("top_match_rate", "0.800"),
    ]:
        passed = expected in text
        checks.append({"id": f"strong_agreement:{label}", "passed": passed, "detail": f"contains {expected}"})
    return checks


def _as_optional_int(value: str | None) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


if __name__ == "__main__":
    main()
