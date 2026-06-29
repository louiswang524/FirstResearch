from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firstresearch.schemas import ResearchPackage


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit benchmark CSV rows against saved ResearchPackage artifacts.")
    parser.add_argument("--results", required=True, help="Benchmark CSV containing output_path rows.")
    parser.add_argument("--output", required=True)
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if any package row fails the audit.")
    args = parser.parse_args()

    rows = _read_rows(Path(args.results))
    audit_rows = [_audit_row(row) for row in rows]
    summary = _summarize(audit_rows)
    report = _render_report(summary, audit_rows, args.results)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps({"summary": summary, "rows": audit_rows}, indent=2) + "\n", encoding="utf-8")
    print(output)
    if args.strict and summary["failed_rows"] > 0:
        raise SystemExit(1)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _audit_row(row: dict[str, str]) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    package_path = Path(row.get("output_path", ""))
    package = None
    if not row.get("output_path"):
        errors.append("missing output_path")
    elif not package_path.exists():
        errors.append("output_path does not exist")
    else:
        try:
            package = ResearchPackage.model_validate_json(package_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 - report validation error text to artifact audit.
            errors.append(f"package schema validation failed: {exc}")

    if package is not None:
        _check_package_linkage(row, package, errors)
        _check_common_package_fields(package, errors, warnings)
        if row.get("system") == "firstresearch":
            _check_firstresearch_fields(package, errors, warnings)
        else:
            _check_baseline_fields(row, package, errors, warnings)

    return {
        "topic_id": row.get("topic_id", ""),
        "system": row.get("system", ""),
        "replicate": row.get("replicate", ""),
        "output_path": row.get("output_path", ""),
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
    }


def _check_package_linkage(row: dict[str, str], package: ResearchPackage, errors: list[str]) -> None:
    if row.get("topic_id") and package.topic.topic_id != row.get("topic_id"):
        errors.append(f"topic_id mismatch: csv={row.get('topic_id')} package={package.topic.topic_id}")
    if row.get("topic") and package.topic.topic != row.get("topic"):
        errors.append("topic text mismatch")


def _check_common_package_fields(package: ResearchPackage, errors: list[str], warnings: list[str]) -> None:
    if not package.certificates:
        errors.append("missing certificates")
    if not package.gate_decisions:
        errors.append("missing gate decisions")
    if package.review is None:
        errors.append("missing review")
    if package.certificates and not package.certificates[0].minimal_decisive_test.falsifying_observation:
        errors.append("lead certificate missing falsifying observation")
    if package.certificates and not package.certificates[0].failure_update_rule.if_failed:
        errors.append("lead certificate missing failure update rule")
    if package.gate_decisions and not any(decision.passed for decision in package.gate_decisions):
        warnings.append("no passing gate decision")


def _check_firstresearch_fields(package: ResearchPackage, errors: list[str], warnings: list[str]) -> None:
    if package.first_principles_decomposition is None:
        errors.append("firstresearch package missing decomposition")
    if package.mechanism_model is None:
        errors.append("firstresearch package missing mechanism model")
    if not package.tensions:
        errors.append("firstresearch package missing tensions")
    if not package.candidate_questions:
        errors.append("firstresearch package missing candidate questions")
    if not package.experiment_plans:
        errors.append("firstresearch package missing experiment plans")
    if package.self_improvement_update is None:
        warnings.append("firstresearch package missing self-improvement update")


def _check_baseline_fields(
    row: dict[str, str],
    package: ResearchPackage,
    errors: list[str],
    warnings: list[str],
) -> None:
    baseline_name = package.metadata.get("baseline")
    system = row.get("system")
    if baseline_name and baseline_name != system:
        errors.append(f"baseline metadata mismatch: csv={system} package={baseline_name}")
    if not baseline_name:
        warnings.append("baseline package missing baseline metadata")


def _summarize(rows: list[dict[str, object]]) -> dict[str, object]:
    by_system: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_system[str(row["system"])].append(row)
    system_summary = []
    for system, system_rows in sorted(by_system.items()):
        failed = sum(not bool(row["passed"]) for row in system_rows)
        warnings = sum(len(row["warnings"]) for row in system_rows)
        system_summary.append(
            {
                "system": system,
                "rows": len(system_rows),
                "failed_rows": failed,
                "warnings": warnings,
            }
        )
    error_counts = Counter(error for row in rows for error in row["errors"])
    warning_counts = Counter(warning for row in rows for warning in row["warnings"])
    return {
        "total_rows": len(rows),
        "failed_rows": sum(not bool(row["passed"]) for row in rows),
        "warning_count": sum(len(row["warnings"]) for row in rows),
        "system_summary": system_summary,
        "error_counts": dict(error_counts),
        "warning_counts": dict(warning_counts),
    }


def _render_report(summary: dict[str, object], rows: list[dict[str, object]], results_path: str) -> str:
    lines = [
        "# Package Artifact Audit",
        "",
        f"Results CSV: `{results_path}`",
        f"Rows audited: {summary['total_rows']}",
        f"Failed rows: {summary['failed_rows']}",
        f"Warnings: {summary['warning_count']}",
        "",
        "## By System",
        "",
        "| System | Rows | Failed Rows | Warnings |",
        "|---|---:|---:|---:|",
    ]
    for row in summary["system_summary"]:
        lines.append(f"| {row['system']} | {row['rows']} | {row['failed_rows']} | {row['warnings']} |")

    lines.extend(["", "## Errors", ""])
    if summary["error_counts"]:
        for error, count in summary["error_counts"].items():
            lines.append(f"- {error}: {count}")
    else:
        lines.append("- No package artifact errors.")

    lines.extend(["", "## Warnings", ""])
    if summary["warning_counts"]:
        for warning, count in summary["warning_counts"].items():
            lines.append(f"- {warning}: {count}")
    else:
        lines.append("- No package artifact warnings.")

    failed = [row for row in rows if not row["passed"]]
    if failed:
        lines.extend(["", "## Failed Rows", ""])
        for row in failed[:20]:
            lines.append(f"- {row['topic_id']} / {row['system']} / {row['output_path']}: {', '.join(row['errors'])}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
