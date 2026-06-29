from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Stage:
    id: str
    description: str
    command: list[str] | None = None
    outputs: tuple[Path, ...] = ()
    required_inputs: tuple[Path, ...] = ()
    credential_env: tuple[str, ...] = ()
    forceable: bool = False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the paper evidence workflow for ablations, cross-judge checks, human-review packets, and audit artifacts."
    )
    parser.add_argument("--dry-run", action="store_true", help="Plan stages without executing commands.")
    parser.add_argument(
        "--skip-credentialed",
        action="store_true",
        help="Skip stages that require external API credentials even if credentials are present.",
    )
    parser.add_argument("--force", action="store_true", help="Rerun forceable stages even when outputs already exist.")
    parser.add_argument("--output-status", default="outputs/reports/paper_evidence_pipeline_status.json")
    args = parser.parse_args()

    statuses: list[dict[str, object]] = []
    for stage in _stages():
        status = _run_stage(stage, dry_run=args.dry_run, skip_credentialed=args.skip_credentialed, force=args.force)
        statuses.append(status)
        print(f"{status['stage']}: {status['status']} - {status['detail']}")

    output_status = ROOT / args.output_status
    output_status.parent.mkdir(parents=True, exist_ok=True)
    output_status.write_text(
        json.dumps(
            {
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "dry_run": args.dry_run,
                "skip_credentialed": args.skip_credentialed,
                "force": args.force,
                "statuses": statuses,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(_display_path(output_status))

    failed = [status for status in statuses if status["status"] == "failed"]
    if failed:
        raise SystemExit(1)


def _stages() -> list[Stage]:
    python = sys.executable
    return [
        Stage(
            id="repro_appendix",
            description="Regenerate the reproducibility appendix from current configs and prompts.",
            command=[python, "scripts/generate_repro_appendix.py", "--output", "papers/reproducibility_appendix.md"],
            outputs=(Path("papers/reproducibility_appendix.md"),),
        ),
        Stage(
            id="repeated_ablation",
            description="Run the three-replicate ten-topic ablation benchmark.",
            command=[python, "scripts/run_benchmark.py", "--config", "configs/deepseek_ablation_repeated.yaml", "--resume"],
            outputs=(Path("outputs/reports/deepseek_ablation_repeated_results.csv"),),
            credential_env=("DEEPSEEK_API_KEY",),
            forceable=True,
        ),
        Stage(
            id="repeated_ablation_report",
            description="Generate the repeated-ablation Markdown report and paper table.",
            command=[
                python,
                "scripts/generate_report.py",
                "--results",
                "outputs/reports/deepseek_ablation_repeated_results.csv",
                "--output",
                "outputs/reports/deepseek_ablation_repeated_report.md",
                "--table-output",
                "outputs/reports/deepseek_ablation_repeated_table.csv",
            ],
            outputs=(
                Path("outputs/reports/deepseek_ablation_repeated_report.md"),
                Path("outputs/reports/deepseek_ablation_repeated_table.csv"),
            ),
            required_inputs=(Path("outputs/reports/deepseek_ablation_repeated_results.csv"),),
        ),
        Stage(
            id="repeated_ablation_stability",
            description="Analyze repeated-ablation stability with paired deltas and bootstrap CIs.",
            command=[
                python,
                "scripts/analyze_repeated_results.py",
                "--results",
                "outputs/reports/deepseek_ablation_repeated_results.csv",
                "--output",
                "outputs/reports/deepseek_ablation_repeated_stability.md",
                "--table-output",
                "outputs/reports/deepseek_ablation_repeated_stability.csv",
                "--reference-system",
                "firstresearch",
            ],
            outputs=(
                Path("outputs/reports/deepseek_ablation_repeated_stability.md"),
                Path("outputs/reports/deepseek_ablation_repeated_stability.csv"),
            ),
            required_inputs=(Path("outputs/reports/deepseek_ablation_repeated_results.csv"),),
        ),
        Stage(
            id="crossjudge_rescore",
            description="Rescore ablation packages with an independent OpenAI-compatible judge.",
            command=[
                python,
                "scripts/rescore_packages.py",
                "--config",
                "configs/deepseek_ablation_repeated_crossjudge.yaml",
            ],
            outputs=(Path("outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv"),),
            required_inputs=(Path("outputs/reports/deepseek_ablation_repeated_results.csv"),),
            credential_env=("OPENAI_COMPAT_API_KEY", "OPENAI_COMPAT_BASE_URL"),
            forceable=True,
        ),
        Stage(
            id="crossjudge_report",
            description="Generate the independent-judge Markdown report and paper table.",
            command=[
                python,
                "scripts/generate_report.py",
                "--results",
                "outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv",
                "--output",
                "outputs/reports/deepseek_ablation_repeated_crossjudge_report.md",
                "--table-output",
                "outputs/reports/deepseek_ablation_repeated_crossjudge_table.csv",
            ],
            outputs=(
                Path("outputs/reports/deepseek_ablation_repeated_crossjudge_report.md"),
                Path("outputs/reports/deepseek_ablation_repeated_crossjudge_table.csv"),
            ),
            required_inputs=(Path("outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv"),),
        ),
        Stage(
            id="crossjudge_agreement",
            description="Analyze agreement and rank stability between the primary and independent judges.",
            command=[
                python,
                "scripts/analyze_judge_agreement.py",
                "--primary-results",
                "outputs/reports/deepseek_ablation_repeated_results.csv",
                "--secondary-results",
                "outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv",
                "--output",
                "outputs/reports/deepseek_ablation_repeated_judge_agreement.md",
                "--table-output",
                "outputs/reports/deepseek_ablation_repeated_judge_agreement.csv",
            ],
            outputs=(
                Path("outputs/reports/deepseek_ablation_repeated_judge_agreement.md"),
                Path("outputs/reports/deepseek_ablation_repeated_judge_agreement.csv"),
            ),
            required_inputs=(
                Path("outputs/reports/deepseek_ablation_repeated_results.csv"),
                Path("outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv"),
            ),
        ),
        Stage(
            id="human_scalar_packet",
            description="Export blinded scalar human-review packets.",
            command=[
                python,
                "scripts/export_human_review_packet.py",
                "--results",
                "outputs/reports/deepseek_ablation_repeated_results.csv",
                "--output-dir",
                "outputs/human_review/deepseek_ablation_repeated",
                "--seed",
                "13",
            ],
            outputs=(
                Path("outputs/human_review/deepseek_ablation_repeated/rubric.md"),
                Path("outputs/human_review/deepseek_ablation_repeated/assignments_private.json"),
            ),
            required_inputs=(Path("outputs/reports/deepseek_ablation_repeated_results.csv"),),
        ),
        Stage(
            id="human_scalar_analysis",
            description="Analyze scalar human-review scores if reviewers have completed the CSV.",
            command=[
                python,
                "scripts/analyze_human_review.py",
                "--assignments",
                "outputs/human_review/deepseek_ablation_repeated/assignments_private.json",
                "--scores",
                "outputs/human_review/deepseek_ablation_repeated/human_scores.csv",
                "--output",
                "outputs/human_review/deepseek_ablation_repeated/human_review_report.md",
                "--table-output",
                "outputs/human_review/deepseek_ablation_repeated/human_review_summary.csv",
            ],
            outputs=(Path("outputs/human_review/deepseek_ablation_repeated/human_review_report.md"),),
            required_inputs=(
                Path("outputs/human_review/deepseek_ablation_repeated/assignments_private.json"),
                Path("outputs/human_review/deepseek_ablation_repeated/human_scores.csv"),
            ),
        ),
        Stage(
            id="human_pairwise_packet",
            description="Export blinded pairwise human-review packets.",
            command=[
                python,
                "scripts/export_pairwise_review_packet.py",
                "--results",
                "outputs/reports/deepseek_ablation_repeated_results.csv",
                "--output-dir",
                "outputs/human_review/deepseek_ablation_repeated_pairwise",
                "--reference-system",
                "firstresearch",
                "--seed",
                "17",
            ],
            outputs=(
                Path("outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_instructions.md"),
                Path("outputs/human_review/deepseek_ablation_repeated_pairwise/pair_assignments_private.json"),
            ),
            required_inputs=(Path("outputs/reports/deepseek_ablation_repeated_results.csv"),),
        ),
        Stage(
            id="human_pairwise_analysis",
            description="Analyze pairwise human-review decisions if reviewers have completed the CSV.",
            command=[
                python,
                "scripts/analyze_pairwise_review.py",
                "--assignments",
                "outputs/human_review/deepseek_ablation_repeated_pairwise/pair_assignments_private.json",
                "--decisions",
                "outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_decisions.csv",
                "--output",
                "outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_report.md",
                "--table-output",
                "outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_summary.csv",
            ],
            outputs=(Path("outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_report.md"),),
            required_inputs=(
                Path("outputs/human_review/deepseek_ablation_repeated_pairwise/pair_assignments_private.json"),
                Path("outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_decisions.csv"),
            ),
        ),
        Stage(
            id="human_review_protocol",
            description="Generate the preregistered human-review protocol artifact.",
            command=[
                python,
                "scripts/generate_human_review_protocol.py",
                "--output",
                "outputs/reports/human_review_protocol.md",
                "--json-output",
                "outputs/reports/human_review_protocol.json",
            ],
            outputs=(Path("outputs/reports/human_review_protocol.md"), Path("outputs/reports/human_review_protocol.json")),
        ),
        Stage(
            id="stress_generalization",
            description="Run the cross-domain stress benchmark against strong prompt-level baselines.",
            command=[python, "scripts/run_benchmark.py", "--config", "configs/deepseek_stress_generalization.yaml", "--resume"],
            outputs=(Path("outputs/reports/deepseek_stress_generalization_results.csv"),),
            credential_env=("DEEPSEEK_API_KEY",),
            forceable=True,
        ),
        Stage(
            id="stress_generalization_report",
            description="Generate the cross-domain stress benchmark report and paper table.",
            command=[
                python,
                "scripts/generate_report.py",
                "--results",
                "outputs/reports/deepseek_stress_generalization_results.csv",
                "--output",
                "outputs/reports/deepseek_stress_generalization_report.md",
                "--table-output",
                "outputs/reports/deepseek_stress_generalization_table.csv",
            ],
            outputs=(
                Path("outputs/reports/deepseek_stress_generalization_report.md"),
                Path("outputs/reports/deepseek_stress_generalization_table.csv"),
            ),
            required_inputs=(Path("outputs/reports/deepseek_stress_generalization_results.csv"),),
        ),
        Stage(
            id="strong_baseline_package_audit",
            description="Validate saved strong-baseline package artifacts against the reported CSV rows.",
            command=[
                python,
                "scripts/audit_package_artifacts.py",
                "--results",
                "outputs/reports/deepseek_strong_baselines_10topics.csv",
                "--output",
                "outputs/reports/deepseek_strong_baselines_package_audit.md",
                "--json-output",
                "outputs/reports/deepseek_strong_baselines_package_audit.json",
                "--strict",
            ],
            outputs=(
                Path("outputs/reports/deepseek_strong_baselines_package_audit.md"),
                Path("outputs/reports/deepseek_strong_baselines_package_audit.json"),
            ),
            required_inputs=(Path("outputs/reports/deepseek_strong_baselines_10topics.csv"),),
        ),
        Stage(
            id="results_table_audit",
            description="Check the manuscript strong-baseline table against the benchmark CSV.",
            command=[
                python,
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
            outputs=(Path("outputs/reports/results_table_audit.md"), Path("outputs/reports/results_table_audit.json")),
            required_inputs=(
                Path("outputs/reports/deepseek_strong_baselines_10topics.csv"),
                Path("papers/firstresearch_draft.md"),
            ),
        ),
        Stage(
            id="baseline_fidelity_report",
            description="Document what each prompt-level baseline approximation captures and omits.",
            command=[
                python,
                "scripts/generate_baseline_fidelity_report.py",
                "--config",
                "configs/deepseek_strong_baselines.yaml",
                "--output",
                "outputs/reports/baseline_fidelity_report.md",
                "--json-output",
                "outputs/reports/baseline_fidelity_report.json",
            ],
            outputs=(
                Path("outputs/reports/baseline_fidelity_report.md"),
                Path("outputs/reports/baseline_fidelity_report.json"),
            ),
            required_inputs=(Path("configs/deepseek_strong_baselines.yaml"),),
        ),
        Stage(
            id="reference_audit",
            description="Check manuscript references against the verified local reference registry.",
            command=[
                python,
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
            outputs=(Path("outputs/reports/reference_audit.md"), Path("outputs/reports/reference_audit.json")),
            required_inputs=(Path("papers/reference_registry.yaml"), Path("papers/firstresearch_draft.md")),
        ),
        Stage(
            id="artifact_manifest",
            description="Regenerate the SHA-256 artifact manifest.",
            command=[
                python,
                "scripts/generate_artifact_manifest.py",
                "--output",
                "outputs/reports/artifact_manifest.json",
                "--markdown-output",
                "outputs/reports/artifact_manifest.md",
            ],
            outputs=(Path("outputs/reports/artifact_manifest.json"), Path("outputs/reports/artifact_manifest.md")),
        ),
        Stage(
            id="paper_evidence_audit",
            description="Regenerate the paper evidence audit.",
            command=[
                python,
                "scripts/audit_paper_evidence.py",
                "--output",
                "outputs/reports/paper_evidence_audit.md",
                "--json-output",
                "outputs/reports/paper_evidence_audit.json",
                "--strict",
            ],
            outputs=(Path("outputs/reports/paper_evidence_audit.md"), Path("outputs/reports/paper_evidence_audit.json")),
            required_inputs=(Path("outputs/reports/artifact_manifest.json"),),
        ),
        Stage(
            id="claim_evidence_audit",
            description="Check manuscript claims against available evidence artifacts.",
            command=[
                python,
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
            outputs=(Path("outputs/reports/claim_evidence_audit.md"), Path("outputs/reports/claim_evidence_audit.json")),
            required_inputs=(Path("outputs/reports/paper_evidence_audit.json"), Path("papers/claim_evidence_registry.yaml")),
        ),
        Stage(
            id="submission_readiness_report",
            description="Summarize which draft and submission-readiness evidence gates are still open.",
            command=[
                python,
                "scripts/generate_submission_readiness_report.py",
                "--evidence-audit",
                "outputs/reports/paper_evidence_audit.json",
                "--claim-audit",
                "outputs/reports/claim_evidence_audit.json",
                "--pipeline-status",
                "outputs/reports/paper_evidence_pipeline_status.json",
                "--output",
                "outputs/reports/submission_readiness_report.md",
                "--json-output",
                "outputs/reports/submission_readiness_report.json",
            ],
            outputs=(
                Path("outputs/reports/submission_readiness_report.md"),
                Path("outputs/reports/submission_readiness_report.json"),
            ),
            required_inputs=(
                Path("outputs/reports/paper_evidence_audit.json"),
                Path("outputs/reports/claim_evidence_audit.json"),
            ),
        ),
        Stage(
            id="final_artifact_manifest",
            description="Refresh the SHA-256 artifact manifest after readiness artifacts are generated.",
            command=[
                python,
                "scripts/generate_artifact_manifest.py",
                "--output",
                "outputs/reports/artifact_manifest.json",
                "--markdown-output",
                "outputs/reports/artifact_manifest.md",
            ],
            outputs=(Path("outputs/reports/artifact_manifest.json"), Path("outputs/reports/artifact_manifest.md")),
            required_inputs=(Path("outputs/reports/submission_readiness_report.md"),),
        ),
    ]


def _run_stage(stage: Stage, *, dry_run: bool, skip_credentialed: bool, force: bool) -> dict[str, object]:
    missing_inputs = [path.as_posix() for path in stage.required_inputs if not (ROOT / path).exists()]
    missing_credentials = [name for name in stage.credential_env if not os.environ.get(name)]
    outputs_exist = bool(stage.outputs) and all((ROOT / path).exists() for path in stage.outputs)

    base = {
        "stage": stage.id,
        "description": stage.description,
        "command": stage.command,
        "outputs": [path.as_posix() for path in stage.outputs],
        "required_inputs": [path.as_posix() for path in stage.required_inputs],
    }

    if missing_inputs:
        return base | {"status": "skipped", "detail": f"missing inputs: {', '.join(missing_inputs)}"}
    if stage.credential_env and skip_credentialed:
        return base | {"status": "skipped", "detail": "credentialed stage skipped by --skip-credentialed"}
    if missing_credentials:
        return base | {"status": "skipped", "detail": f"missing credentials: {', '.join(missing_credentials)}"}
    if outputs_exist and not force:
        return base | {"status": "skipped", "detail": "outputs already exist"}
    if dry_run:
        return base | {"status": "would_run", "detail": "dry run"}
    if not stage.command:
        return base | {"status": "skipped", "detail": "no command"}

    try:
        completed = subprocess.run(stage.command, cwd=ROOT, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        return base | {
            "status": "failed",
            "detail": f"exit {exc.returncode}",
            "stdout": exc.stdout,
            "stderr": exc.stderr,
        }
    return base | {
        "status": "ran",
        "detail": "completed",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


if __name__ == "__main__":
    main()
