from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_PATTERNS = [
    "configs/*.yaml",
    "data/*.jsonl",
    "firstresearch/**/*.py",
    "firstresearch/prompts/*.md",
    "scripts/*.py",
    "papers/firstresearch_draft.md",
    "papers/reproducibility_appendix.md",
    "papers/review_response_notes.md",
    "papers/claim_evidence_registry.yaml",
    "papers/reference_registry.yaml",
    "outputs/reports/deepseek_strong_baselines_10topics.csv",
    "outputs/reports/deepseek_strong_baselines_10topics.jsonl",
    "outputs/reports/deepseek_strong_baselines_10topics_metadata.json",
    "outputs/reports/deepseek_strong_baselines_10topics.md",
    "outputs/reports/deepseek_strong_baselines_10topics_table.csv",
    "outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv",
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
    "outputs/reports/deepseek_ablation_repeated_packages/*.json",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_results.csv",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_metadata.json",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_report.md",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_table.csv",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_agreement.md",
    "outputs/reports/deepseek_ablation_repeated_gemini_judge_agreement.csv",
    "outputs/reports/deepseek_strong_baselines_package_audit.md",
    "outputs/reports/deepseek_strong_baselines_package_audit.json",
    "outputs/reports/results_table_audit.md",
    "outputs/reports/results_table_audit.json",
    "outputs/reports/baseline_fidelity_report.md",
    "outputs/reports/baseline_fidelity_report.json",
    "outputs/reports/reference_audit.md",
    "outputs/reports/reference_audit.json",
    "outputs/reports/human_review_protocol.md",
    "outputs/reports/human_review_protocol.json",
    "outputs/reports/paper_evidence_audit.md",
    "outputs/reports/paper_evidence_audit.json",
    "outputs/reports/claim_evidence_audit.md",
    "outputs/reports/claim_evidence_audit.json",
    "outputs/reports/submission_readiness_report.md",
    "outputs/reports/submission_readiness_report.json",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SHA-256 manifest for paper-critical artifacts.")
    parser.add_argument("--output", default="outputs/reports/artifact_manifest.json")
    parser.add_argument("--markdown-output", default="outputs/reports/artifact_manifest.md")
    parser.add_argument("--csv-output", default=None)
    parser.add_argument("--patterns", nargs="*", default=DEFAULT_PATTERNS)
    args = parser.parse_args()

    entries = _collect_entries(args.patterns)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "entry_count": len(entries),
        "entries": entries,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.markdown_output:
        md = Path(args.markdown_output)
        md.parent.mkdir(parents=True, exist_ok=True)
        md.write_text(_render_markdown(manifest), encoding="utf-8")
    if args.csv_output:
        _write_csv(Path(args.csv_output), entries)
    print(output)


def _collect_entries(patterns: list[str]) -> list[dict[str, object]]:
    paths: set[Path] = set()
    for pattern in patterns:
        matches = list(Path().glob(pattern))
        if not matches and not any(char in pattern for char in "*?[]"):
            matches = [Path(pattern)]
        for path in matches:
            if path.is_file():
                paths.add(path)
    return [_entry(path) for path in sorted(paths, key=lambda item: item.as_posix())]


def _entry(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _render_markdown(manifest: dict[str, object]) -> str:
    lines = [
        "# Artifact Manifest",
        "",
        f"Generated at UTC: `{manifest['generated_at_utc']}`",
        "",
        "| Path | Bytes | SHA-256 |",
        "|---|---:|---|",
    ]
    for entry in manifest["entries"]:
        lines.append(f"| `{entry['path']}` | {entry['bytes']} | `{entry['sha256']}` |")
    return "\n".join(lines) + "\n"


def _write_csv(path: Path, entries: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(entries)


if __name__ == "__main__":
    main()
