from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INCLUDE_PATTERNS = [
    "ARTIFACT_README.md",
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    ".env.example",
    "configs/*.yaml",
    "data/*.jsonl",
    "firstresearch/**/*.py",
    "firstresearch/prompts/*.md",
    "scripts/*.py",
    "tests/*.py",
    "outputs/reports/deepseek_strong_baselines_10topics.csv",
    "outputs/reports/deepseek_strong_baselines_10topics.jsonl",
    "outputs/reports/deepseek_strong_baselines_10topics_metadata.json",
    "outputs/reports/deepseek_strong_baselines_10topics.md",
    "outputs/reports/deepseek_strong_baselines_10topics_table.csv",
    "outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv",
    "outputs/reports/deepseek_strong_baselines_gemini_judge_results.jsonl",
    "outputs/reports/deepseek_strong_baselines_gemini_judge_metadata.json",
    "outputs/reports/deepseek_strong_baselines_gemini_judge_report.md",
    "outputs/reports/deepseek_strong_baselines_gemini_judge_table.csv",
    "outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.md",
    "outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.csv",
    "outputs/reports/deepseek_packages/*.json",
    "outputs/reports/deepseek_combo_study_results.csv",
    "outputs/reports/deepseek_combo_study_results.jsonl",
    "outputs/reports/deepseek_combo_study_metadata.json",
    "outputs/reports/deepseek_combo_study_report.md",
    "outputs/reports/deepseek_combo_study_table.csv",
    "outputs/reports/deepseek_combo_study_packages/*.json",
    "outputs/reports/deepseek_ablation_repeated_results.csv",
    "outputs/reports/deepseek_ablation_repeated_results.jsonl",
    "outputs/reports/deepseek_ablation_repeated_metadata.json",
    "outputs/reports/deepseek_ablation_repeated_report.md",
    "outputs/reports/deepseek_ablation_repeated_table.csv",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_results.csv",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_results.jsonl",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_metadata.json",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_report.md",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_table.csv",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_agreement.md",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_agreement.csv",
    "outputs/reports/deepseek_ablation_repeated_packages/*.json",
    "outputs/reports/deepseek_strong_baselines_package_audit.md",
    "outputs/reports/deepseek_strong_baselines_package_audit.json",
    "outputs/reports/baseline_fidelity_report.md",
    "outputs/reports/baseline_fidelity_report.json",
    "outputs/reports/human_review_protocol.md",
    "outputs/reports/human_review_protocol.json",
    "outputs/reports/artifact_manifest.md",
    "outputs/reports/artifact_manifest.json",
    "outputs/reports/expected_results_check.json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare a curated anonymous GitHub artifact directory and zip.")
    parser.add_argument("--output-dir", default="outputs/firstresearch_anonymous_github_artifact")
    parser.add_argument("--zip-output", default="outputs/firstresearch_anonymous_github_artifact.zip")
    args = parser.parse_args()

    output_dir = ROOT / args.output_dir
    zip_output = ROOT / args.zip_output
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    copied = 0
    for rel_path in _collect_paths():
        target = output_dir / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel_path, target)
        copied += 1

    (output_dir / ".gitignore").write_text(_artifact_gitignore(), encoding="utf-8")
    (output_dir / "README.md").write_text((ROOT / "ARTIFACT_README.md").read_text(encoding="utf-8"), encoding="utf-8")

    if zip_output.exists():
        zip_output.unlink()
    shutil.make_archive(str(zip_output.with_suffix("")), "zip", output_dir)
    print(f"Copied {copied} files to {output_dir}")
    print(zip_output)


def _collect_paths() -> list[Path]:
    paths: set[Path] = set()
    for pattern in INCLUDE_PATTERNS:
        matches = list(ROOT.glob(pattern))
        if not matches and not any(char in pattern for char in "*?[]"):
            matches = [ROOT / pattern]
        for path in matches:
            if path.is_file():
                paths.add(path.relative_to(ROOT))
    return sorted(paths, key=lambda path: path.as_posix())


def _artifact_gitignore() -> str:
    return "\n".join(
        [
            "__pycache__/",
            "*.py[cod]",
            ".pytest_cache/",
            ".mypy_cache/",
            ".ruff_cache/",
            ".venv/",
            "venv/",
            "env/",
            ".env",
            "*.log",
            "*.aux",
            "*.out",
            "*.blg",
            "outputs/**/*.tmp",
            "",
        ]
    )


if __name__ == "__main__":
    main()
