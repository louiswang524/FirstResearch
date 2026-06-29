from __future__ import annotations

import argparse
import json
from pathlib import Path


NEXT_ACTIONS = {
    "repeated_ablation_csv": "Set DEEPSEEK_API_KEY, then run `python scripts/run_paper_evidence_pipeline.py --force`.",
    "repeated_stability_report": "Run `python scripts/analyze_repeated_results.py --results outputs/reports/deepseek_ablation_repeated_results.csv --output outputs/reports/deepseek_ablation_repeated_stability.md --table-output outputs/reports/deepseek_ablation_repeated_stability.csv --reference-system firstresearch` after repeated ablation results exist.",
    "crossjudge_csv": "Set GEMINI_API_KEY, then run `python scripts/rescore_packages.py --config configs/deepseek_ablation_repeated_gemini_judge.yaml`; or set OPENAI_COMPAT_API_KEY, OPENAI_COMPAT_BASE_URL, and OPENAI_COMPAT_MODEL, then run `python scripts/rescore_packages.py --config configs/deepseek_ablation_repeated_crossjudge.yaml`.",
    "crossjudge_agreement_report": "Run `python scripts/analyze_judge_agreement.py --primary-results outputs/reports/deepseek_ablation_repeated_results.csv --secondary-results outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv --output outputs/reports/deepseek_ablation_repeated_judge_agreement.md --table-output outputs/reports/deepseek_ablation_repeated_judge_agreement.csv` after both judge CSVs exist.",
    "stress_generalization_csv": "Set DEEPSEEK_API_KEY, then run `python scripts/run_benchmark.py --config configs/deepseek_stress_generalization.yaml`.",
    "stress_generalization_report": "Run `python scripts/generate_report.py --results outputs/reports/deepseek_stress_generalization_results.csv --output outputs/reports/deepseek_stress_generalization_report.md --table-output outputs/reports/deepseek_stress_generalization_table.csv` after stress results exist.",
    "human_scalar_report": "Collect blinded reviewer `human_scores.csv`, then run `python scripts/analyze_human_review.py --assignments outputs/human_review/deepseek_ablation_repeated/assignments_private.json --scores outputs/human_review/deepseek_ablation_repeated/human_scores.csv --output outputs/human_review/deepseek_ablation_repeated/human_review_report.md --table-output outputs/human_review/deepseek_ablation_repeated/human_review_summary.csv`.",
    "human_pairwise_report": "Collect blinded reviewer `pairwise_decisions.csv`, then run `python scripts/analyze_pairwise_review.py --assignments outputs/human_review/deepseek_ablation_repeated_pairwise/pair_assignments_private.json --decisions outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_decisions.csv --output outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_report.md --table-output outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_summary.csv`.",
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize whether the paper evidence package is submission-ready.")
    parser.add_argument("--evidence-audit", default="outputs/reports/paper_evidence_audit.json")
    parser.add_argument("--claim-audit", default="outputs/reports/claim_evidence_audit.json")
    parser.add_argument("--pipeline-status", default="outputs/reports/paper_evidence_pipeline_status.json")
    parser.add_argument("--output", default="outputs/reports/submission_readiness_report.md")
    parser.add_argument("--json-output", default="outputs/reports/submission_readiness_report.json")
    args = parser.parse_args()

    evidence = _load_json(Path(args.evidence_audit), [])
    claims = _load_json(Path(args.claim_audit), [])
    pipeline = _load_json(Path(args.pipeline_status), {})
    summary = build_summary(evidence=evidence, claims=claims, pipeline=pipeline)
    summary["inputs"] = {
        "evidence_audit": args.evidence_audit,
        "claim_audit": args.claim_audit,
        "pipeline_status": args.pipeline_status,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(summary), encoding="utf-8")
    json_output = Path(args.json_output)
    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(output)


def build_summary(
    *,
    evidence: list[dict[str, object]],
    claims: list[dict[str, object]],
    pipeline: dict[str, object],
) -> dict[str, object]:
    required = [row for row in evidence if row.get("required")]
    optional = [row for row in evidence if not row.get("required")]
    required_missing = [row for row in required if not row.get("passed")]
    optional_missing = [row for row in optional if not row.get("passed")]
    claim_failures = [row for row in claims if not row.get("passed")]
    statuses = list(pipeline.get("statuses", [])) if isinstance(pipeline, dict) else []
    pipeline_failures = [row for row in statuses if row.get("status") == "failed"]

    submission_ready = not required_missing and not optional_missing and not claim_failures and not pipeline_failures
    return {
        "submission_ready": submission_ready,
        "required_checks": len(required),
        "required_missing": [_evidence_brief(row) for row in required_missing],
        "optional_checks": len(optional),
        "optional_missing": [_evidence_brief(row) for row in optional_missing],
        "claim_checks": len(claims),
        "claim_failures": [_claim_brief(row) for row in claim_failures],
        "pipeline_status_counts": _status_counts(statuses),
        "pipeline_failures": [_stage_brief(row) for row in pipeline_failures],
        "next_actions": _next_actions(required_missing + optional_missing, claim_failures, pipeline_failures),
    }


def render_markdown(summary: dict[str, object]) -> str:
    ready = "true" if summary["submission_ready"] else "false"
    lines = [
        "# Submission Readiness Report",
        "",
        f"Submission ready: `{ready}`",
        "",
        "This report distinguishes current draft evidence from submission-level evidence. A paper can pass required draft checks while still failing submission readiness if repeated, cross-judge, stress, or human-review evidence is missing.",
        "",
        "## Evidence Gate",
        "",
        f"Required checks: {summary['required_checks']}; missing: {len(summary['required_missing'])}",
        f"Submission-strengthening checks: {summary['optional_checks']}; missing: {len(summary['optional_missing'])}",
        "",
    ]
    lines.extend(_table("Missing required evidence", summary["required_missing"]))
    lines.extend(_table("Missing submission evidence", summary["optional_missing"]))
    lines.extend(
        [
            "## Claim Gate",
            "",
            f"Claim checks: {summary['claim_checks']}; failures: {len(summary['claim_failures'])}",
            "",
        ]
    )
    lines.extend(_table("Claim failures", summary["claim_failures"]))
    lines.extend(["## Pipeline Status", ""])
    counts = summary["pipeline_status_counts"]
    if counts:
        lines.extend(["| Status | Count |", "|---|---:|"])
        for key in sorted(counts):
            lines.append(f"| {key} | {counts[key]} |")
        lines.append("")
    else:
        lines.extend(["No pipeline status file was available.", ""])
    lines.extend(_table("Pipeline failures", summary["pipeline_failures"]))
    lines.extend(["## Next Actions", ""])
    actions = summary["next_actions"]
    if actions:
        for action in actions:
            lines.append(f"- {action}")
    else:
        lines.append("- No blocking next actions detected.")
    return "\n".join(lines) + "\n"


def _load_json(path: Path, fallback: object) -> object:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence_brief(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": row.get("id", ""),
        "detail": row.get("detail", ""),
        "path": row.get("path", ""),
    }


def _claim_brief(row: dict[str, object]) -> dict[str, object]:
    missing = row.get("missing_evidence", [])
    return {
        "id": row.get("id", ""),
        "detail": ", ".join(missing) if isinstance(missing, list) else str(missing),
        "path": "",
    }


def _stage_brief(row: dict[str, object]) -> dict[str, object]:
    return {
        "id": row.get("stage", ""),
        "detail": row.get("detail", ""),
        "path": "",
    }


def _status_counts(statuses: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in statuses:
        status = str(row.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    return counts


def _next_actions(
    missing_evidence: list[dict[str, object]],
    claim_failures: list[dict[str, object]],
    pipeline_failures: list[dict[str, object]],
) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()
    for row in missing_evidence:
        check_id = str(row.get("id", ""))
        action = NEXT_ACTIONS.get(check_id, f"Resolve `{check_id}`: {row.get('detail', '')}")
        if action not in seen:
            actions.append(action)
            seen.add(action)
    if claim_failures:
        action = "After new evidence lands, rerun `python scripts/audit_claim_evidence.py --registry papers/claim_evidence_registry.yaml --evidence-audit outputs/reports/paper_evidence_audit.json --manuscript papers/firstresearch_draft.md --output outputs/reports/claim_evidence_audit.md --json-output outputs/reports/claim_evidence_audit.json --strict` and only then upgrade paper claims."
        actions.append(action)
    for row in pipeline_failures:
        actions.append(f"Fix failed pipeline stage `{row.get('stage', '')}`: {row.get('detail', '')}")
    if actions:
        actions.append("Regenerate this report with `python scripts/generate_submission_readiness_report.py`.")
    return actions


def _table(title: str, rows: object) -> list[str]:
    typed_rows = list(rows) if isinstance(rows, list) else []
    lines = [f"### {title}", ""]
    if not typed_rows:
        lines.extend(["None.", ""])
        return lines
    lines.extend(["| ID | Detail | Path |", "|---|---|---|"])
    for row in typed_rows:
        lines.append(f"| {row.get('id', '')} | {row.get('detail', '')} | `{row.get('path', '')}` |")
    lines.append("")
    return lines


if __name__ == "__main__":
    main()
