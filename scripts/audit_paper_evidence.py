from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


CHECKS = [
    {
        "id": "strong_baseline_csv",
        "description": "Ten-topic strong-baseline CSV exists.",
        "path": "outputs/reports/deepseek_strong_baselines_10topics.csv",
        "required": True,
        "kind": "csv_min_rows",
        "min_rows": 40,
    },
    {
        "id": "strong_baseline_report",
        "description": "Ten-topic strong-baseline Markdown report exists.",
        "path": "outputs/reports/deepseek_strong_baselines_10topics.md",
        "required": True,
        "kind": "exists",
    },
    {
        "id": "strong_baseline_metadata",
        "description": "Ten-topic strong-baseline run metadata exists.",
        "path": "outputs/reports/deepseek_strong_baselines_10topics_metadata.json",
        "required": True,
        "kind": "json_has_key",
        "key": "run_id",
    },
    {
        "id": "strong_baseline_gemini_csv",
        "description": "Gemini independent-judge rescore of strong-baseline packages exists.",
        "path": "outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv",
        "required": True,
        "kind": "csv_min_rows",
        "min_rows": 40,
    },
    {
        "id": "strong_baseline_gemini_agreement_report",
        "description": "DeepSeek-vs-Gemini strong-baseline judge agreement report exists.",
        "path": "outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.md",
        "required": True,
        "kind": "contains",
        "contains": ["Judge Agreement Analysis", "Matched package rows: 40", "average_score"],
    },
    {
        "id": "strong_baseline_package_audit",
        "description": "Saved strong-baseline packages validate against reported CSV rows.",
        "path": "outputs/reports/deepseek_strong_baselines_package_audit.md",
        "required": True,
        "kind": "contains",
        "contains": ["Package Artifact Audit", "Failed rows: 0"],
    },
    {
        "id": "results_table_audit",
        "description": "Manuscript strong-baseline table matches the result CSV.",
        "path": "outputs/reports/results_table_audit.md",
        "required": True,
        "kind": "contains",
        "contains": ["Results Table Audit", "Failures: 0"],
    },
    {
        "id": "strong_baseline_config",
        "description": "Exact strong-baseline config exists.",
        "path": "configs/deepseek_strong_baselines.yaml",
        "required": True,
        "kind": "exists",
    },
    {
        "id": "baseline_fidelity_report",
        "description": "Baseline approximation scope and omissions are documented.",
        "path": "outputs/reports/baseline_fidelity_report.md",
        "required": True,
        "kind": "contains",
        "contains": ["Baseline Fidelity Report", "controlled prompt-level workflow approximations", "Omitted elements"],
    },
    {
        "id": "reference_audit",
        "description": "Registered manuscript references are present and source-checked.",
        "path": "outputs/reports/reference_audit.md",
        "required": True,
        "kind": "contains",
        "contains": ["Reference Audit", "PASS", "primary arXiv records"],
    },
    {
        "id": "human_review_protocol",
        "description": "Preregistered human-review protocol exists.",
        "path": "outputs/reports/human_review_protocol.md",
        "required": True,
        "kind": "contains",
        "contains": ["Blinded Human Review Protocol", "Pairwise Decision CSV", "Do not upgrade paper claims"],
    },
    {
        "id": "repro_appendix",
        "description": "Generated reproducibility appendix exists.",
        "path": "papers/reproducibility_appendix.md",
        "required": True,
        "kind": "contains",
        "contains": ["configs/deepseek_strong_baselines.yaml", "configs/deepseek_ablation_repeated.yaml"],
    },
    {
        "id": "artifact_manifest",
        "description": "SHA-256 artifact manifest exists.",
        "path": "outputs/reports/artifact_manifest.json",
        "required": True,
        "kind": "json_min_entries",
        "min_entries": 10,
    },
    {
        "id": "claim_evidence_registry",
        "description": "Claim-evidence registry exists.",
        "path": "papers/claim_evidence_registry.yaml",
        "required": True,
        "kind": "exists",
    },
    {
        "id": "repeated_ablation_csv",
        "description": "Credentialed repeated ablation CSV exists.",
        "path": "outputs/reports/deepseek_ablation_repeated_results.csv",
        "required": False,
        "kind": "csv_min_rows",
        "min_rows": 210,
    },
    {
        "id": "ablation_checkpoint_csv",
        "description": "Credentialed one-repeat ablation checkpoint CSV exists.",
        "path": "outputs/reports/deepseek_ablation_repeated_results.csv",
        "required": True,
        "kind": "csv_min_rows",
        "min_rows": 70,
    },
    {
        "id": "ablation_checkpoint_report",
        "description": "One-repeat ablation checkpoint report exists.",
        "path": "outputs/reports/deepseek_ablation_repeated_report.md",
        "required": True,
        "kind": "contains",
        "contains": ["Comparison Table", "certificate_only_ablation", "no_certificate_ablation"],
    },
    {
        "id": "crossjudge_csv",
        "description": "Independent-judge rescore CSV exists.",
        "path": "outputs/reports/deepseek_ablation_repeated_gemini_judge_results.csv",
        "required": True,
        "kind": "csv_min_rows",
        "min_rows": 70,
    },
    {
        "id": "crossjudge_agreement_report",
        "description": "Primary-vs-independent judge agreement report exists.",
        "path": "outputs/reports/deepseek_ablation_repeated_gemini_judge_agreement.md",
        "required": True,
        "kind": "contains",
        "contains": ["Judge Agreement Analysis", "Within-Topic Rank Stability"],
    },
    {
        "id": "repeated_stability_report",
        "description": "Repeated-run stability analysis with paired deltas exists.",
        "path": "outputs/reports/deepseek_ablation_repeated_stability.md",
        "required": False,
        "kind": "contains",
        "contains": ["Repeated Benchmark Stability Analysis", "95% Bootstrap CI"],
    },
    {
        "id": "stress_generalization_csv",
        "description": "Cross-domain stress benchmark CSV exists.",
        "path": "outputs/reports/deepseek_stress_generalization_results.csv",
        "required": False,
        "kind": "csv_min_rows",
        "min_rows": 40,
    },
    {
        "id": "stress_generalization_report",
        "description": "Cross-domain stress benchmark report exists.",
        "path": "outputs/reports/deepseek_stress_generalization_report.md",
        "required": False,
        "kind": "exists",
    },
    {
        "id": "human_scalar_report",
        "description": "Scalar human-review report exists.",
        "path": "outputs/human_review/deepseek_ablation_repeated/human_review_report.md",
        "required": False,
        "kind": "exists",
    },
    {
        "id": "human_pairwise_report",
        "description": "Pairwise human-review report exists.",
        "path": "outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_report.md",
        "required": False,
        "kind": "exists",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit paper-critical evidence artifacts.")
    parser.add_argument("--output", default="outputs/reports/paper_evidence_audit.md")
    parser.add_argument("--json-output", default=None)
    parser.add_argument("--strict", action="store_true", help="Exit nonzero if any required check fails.")
    parser.add_argument(
        "--require-optional",
        action="store_true",
        help="Exit nonzero if planned strengthening evidence is missing; use this as the submission-readiness gate.",
    )
    args = parser.parse_args()

    results = [_run_check(check) for check in CHECKS]
    report = _render_report(results)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(output)
    if args.strict and any(not result["passed"] for result in results if result["required"]):
        raise SystemExit(1)
    if args.require_optional and any(not result["passed"] for result in results):
        raise SystemExit(1)


def _run_check(check: dict[str, object]) -> dict[str, object]:
    path = Path(str(check["path"]))
    passed = False
    detail = ""
    if not path.exists():
        detail = "missing"
    elif check["kind"] == "exists":
        passed = True
        detail = f"exists ({path.stat().st_size} bytes)"
    elif check["kind"] == "contains":
        text = path.read_text(encoding="utf-8")
        missing = [needle for needle in check["contains"] if str(needle) not in text]
        passed = not missing
        detail = "contains required strings" if passed else f"missing strings: {', '.join(map(str, missing))}"
    elif check["kind"] == "csv_min_rows":
        with path.open(encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        min_rows = int(check["min_rows"])
        passed = len(rows) >= min_rows
        detail = f"{len(rows)} rows; expected at least {min_rows}"
    elif check["kind"] == "json_min_entries":
        data = json.loads(path.read_text(encoding="utf-8"))
        count = len(data.get("entries", []))
        min_entries = int(check["min_entries"])
        passed = count >= min_entries
        detail = f"{count} entries; expected at least {min_entries}"
    elif check["kind"] == "json_has_key":
        data = json.loads(path.read_text(encoding="utf-8"))
        key = str(check["key"])
        passed = key in data and bool(data[key])
        detail = f"{key}={data.get(key)}" if passed else f"missing key: {key}"
    else:
        detail = f"unknown check kind: {check['kind']}"
    return {
        "id": check["id"],
        "description": check["description"],
        "path": str(path),
        "required": bool(check["required"]),
        "passed": passed,
        "detail": detail,
    }


def _render_report(results: list[dict[str, object]]) -> str:
    lines = [
        "# Paper Evidence Audit",
        "",
        "| Check | Required | Status | Detail | Path |",
        "|---|---:|---|---|---|",
    ]
    for result in results:
        status = "PASS" if result["passed"] else "MISSING"
        lines.append(
            f"| {result['id']} | {str(result['required']).lower()} | {status} | "
            f"{result['detail']} | `{result['path']}` |"
        )
    lines.extend(
        [
            "",
            "Required checks cover evidence already claimed in the draft.",
            "Optional checks cover planned evidence needed to strengthen the paper before submission.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
