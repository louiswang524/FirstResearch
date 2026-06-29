from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Step:
    name: str
    command: list[str]
    requires_env: tuple[str, ...] = ()
    skip_if_missing: tuple[str, ...] = ()


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce paper artifacts from saved outputs or fresh API calls.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--no-api", action="store_true", help="Regenerate reports/audits from saved artifacts only.")
    mode.add_argument("--with-api", action="store_true", help="Run API-backed generation/rescoring stages before audits.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    steps = _no_api_steps()
    if args.with_api:
        steps = _api_steps() + steps

    for step in steps:
        missing_files = [path for path in step.skip_if_missing if not (ROOT / path).exists()]
        if missing_files:
            print(f"\n==> {step.name}")
            print(f"Skipping because optional file(s) are absent: {', '.join(missing_files)}")
            continue
        missing = [name for name in step.requires_env if not os.environ.get(name)]
        if missing:
            raise SystemExit(f"{step.name}: missing required environment variable(s): {', '.join(missing)}")
        print(f"\n==> {step.name}")
        print(" ".join(step.command))
        if not args.dry_run:
            subprocess.run(step.command, cwd=ROOT, check=True)


def _api_steps() -> list[Step]:
    py = sys.executable
    return [
        Step(
            "Run DeepSeek strong-baseline benchmark",
            [py, "scripts/run_benchmark.py", "--config", "configs/deepseek_strong_baselines.yaml"],
            ("DEEPSEEK_API_KEY",),
        ),
        Step(
            "Run DeepSeek one-repeat ablation checkpoint",
            [
                py,
                "scripts/run_benchmark.py",
                "--config",
                "configs/deepseek_ablation_repeated.yaml",
                "--resume",
                "--target-rows",
                "70",
            ],
            ("DEEPSEEK_API_KEY",),
        ),
        Step(
            "Run combination pilot",
            [py, "scripts/run_benchmark.py", "--config", "configs/deepseek_combo_study.yaml", "--resume"],
            ("DEEPSEEK_API_KEY",),
        ),
        Step(
            "Gemini rescore strong-baseline packages",
            [py, "scripts/rescore_packages.py", "--config", "configs/deepseek_strong_baselines_gemini_judge.yaml"],
            ("GEMINI_API_KEY",),
        ),
        Step(
            "Gemini rescore ablation packages",
            [py, "scripts/rescore_packages.py", "--config", "configs/deepseek_ablation_repeated_gemini_judge.yaml"],
            ("GEMINI_API_KEY",),
        ),
    ]


def _no_api_steps() -> list[Step]:
    py = sys.executable
    return [
        Step(
            "Generate strong-baseline report",
            [
                py,
                "scripts/generate_report.py",
                "--results",
                "outputs/reports/deepseek_strong_baselines_10topics.csv",
                "--output",
                "outputs/reports/deepseek_strong_baselines_10topics.md",
                "--table-output",
                "outputs/reports/deepseek_strong_baselines_10topics_table.csv",
            ],
        ),
        Step(
            "Generate strong-baseline Gemini report",
            [
                py,
                "scripts/generate_report.py",
                "--results",
                "outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv",
                "--output",
                "outputs/reports/deepseek_strong_baselines_gemini_judge_report.md",
                "--table-output",
                "outputs/reports/deepseek_strong_baselines_gemini_judge_table.csv",
            ],
        ),
        Step(
            "Analyze strong-baseline judge agreement",
            [
                py,
                "scripts/analyze_judge_agreement.py",
                "--primary-results",
                "outputs/reports/deepseek_strong_baselines_10topics.csv",
                "--secondary-results",
                "outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv",
                "--output",
                "outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.md",
                "--table-output",
                "outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.csv",
            ],
        ),
        Step(
            "Generate ablation checkpoint report",
            [
                py,
                "scripts/generate_report.py",
                "--results",
                "outputs/reports/deepseek_ablation_repeated_results.csv",
                "--output",
                "outputs/reports/deepseek_ablation_repeated_report.md",
                "--table-output",
                "outputs/reports/deepseek_ablation_repeated_table.csv",
                "--max-rows",
                "70",
            ],
        ),
        Step(
            "Generate ablation Gemini report",
            [
                py,
                "scripts/generate_report.py",
                "--results",
                "outputs/reports/deepseek_ablation_repeated_gemini_judge_results.csv",
                "--output",
                "outputs/reports/deepseek_ablation_repeated_gemini_judge_report.md",
                "--table-output",
                "outputs/reports/deepseek_ablation_repeated_gemini_judge_table.csv",
            ],
        ),
        Step(
            "Analyze ablation judge agreement",
            [
                py,
                "scripts/analyze_judge_agreement.py",
                "--primary-results",
                "outputs/reports/deepseek_ablation_repeated_results.csv",
                "--secondary-results",
                "outputs/reports/deepseek_ablation_repeated_gemini_judge_results.csv",
                "--output",
                "outputs/reports/deepseek_ablation_repeated_gemini_judge_agreement.md",
                "--table-output",
                "outputs/reports/deepseek_ablation_repeated_gemini_judge_agreement.csv",
            ],
        ),
        Step(
            "Generate combo report",
            [
                py,
                "scripts/generate_report.py",
                "--results",
                "outputs/reports/deepseek_combo_study_results.csv",
                "--output",
                "outputs/reports/deepseek_combo_study_report.md",
                "--table-output",
                "outputs/reports/deepseek_combo_study_table.csv",
            ],
        ),
        Step(
            "Audit saved package artifacts",
            [
                py,
                "scripts/audit_package_artifacts.py",
                "--results",
                "outputs/reports/deepseek_strong_baselines_10topics.csv",
                "--output",
                "outputs/reports/deepseek_strong_baselines_package_audit.md",
                "--json-output",
                "outputs/reports/deepseek_strong_baselines_package_audit.json",
                "--strict",
            ],
        ),
        Step(
            "Audit manuscript results table",
            [
                py,
                "scripts/audit_results_table.py",
                "--results",
                "outputs/reports/deepseek_strong_baselines_10topics.csv",
                "--manuscript",
                "papers/firstresearch_draft.md",
                "--output",
                "outputs/reports/results_table_audit.md",
                "--json-output",
                "outputs/reports/results_table_audit.json",
                "--strict",
            ],
            skip_if_missing=("papers/firstresearch_draft.md",),
        ),
        Step(
            "Generate baseline fidelity report",
            [
                py,
                "scripts/generate_baseline_fidelity_report.py",
                "--config",
                "configs/deepseek_strong_baselines.yaml",
                "--output",
                "outputs/reports/baseline_fidelity_report.md",
                "--json-output",
                "outputs/reports/baseline_fidelity_report.json",
            ],
        ),
        Step(
            "Audit references",
            [
                py,
                "scripts/audit_references.py",
                "--registry",
                "papers/reference_registry.yaml",
                "--manuscript",
                "papers/firstresearch_draft.md",
                "--output",
                "outputs/reports/reference_audit.md",
                "--json-output",
                "outputs/reports/reference_audit.json",
                "--strict",
            ],
            skip_if_missing=("papers/reference_registry.yaml", "papers/firstresearch_draft.md"),
        ),
        Step(
            "Generate human-review protocol",
            [
                py,
                "scripts/generate_human_review_protocol.py",
                "--output",
                "outputs/reports/human_review_protocol.md",
                "--json-output",
                "outputs/reports/human_review_protocol.json",
            ],
        ),
        Step("Generate artifact manifest", [py, "scripts/generate_artifact_manifest.py"]),
        Step(
            "Audit paper evidence",
            [
                py,
                "scripts/audit_paper_evidence.py",
                "--output",
                "outputs/reports/paper_evidence_audit.md",
                "--json-output",
                "outputs/reports/paper_evidence_audit.json",
                "--strict",
            ],
            skip_if_missing=("papers/firstresearch_draft.md", "papers/claim_evidence_registry.yaml"),
        ),
        Step(
            "Audit claim evidence",
            [
                py,
                "scripts/audit_claim_evidence.py",
                "--registry",
                "papers/claim_evidence_registry.yaml",
                "--evidence-audit",
                "outputs/reports/paper_evidence_audit.json",
                "--manuscript",
                "papers/firstresearch_draft.md",
                "--output",
                "outputs/reports/claim_evidence_audit.md",
                "--json-output",
                "outputs/reports/claim_evidence_audit.json",
                "--strict",
            ],
            skip_if_missing=("papers/claim_evidence_registry.yaml", "papers/firstresearch_draft.md"),
        ),
        Step("Check expected headline numbers", [py, "scripts/check_expected_results.py"]),
        Step(
            "Generate reproducibility appendix",
            [py, "scripts/generate_repro_appendix.py", "--output", "papers/reproducibility_appendix.md"],
            skip_if_missing=("papers",),
        ),
    ]


if __name__ == "__main__":
    main()
