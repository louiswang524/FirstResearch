from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from datetime import datetime, timezone

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firstresearch.benchmark.runners import write_results_csv, write_results_jsonl, write_run_metadata
from firstresearch.benchmark.scorers import score_package
from firstresearch.schemas import ResearchPackage
from firstresearch.utils.llm import build_llm_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Rescore existing research packages with a blinded LLM judge.")
    parser.add_argument("--config", default=None)
    parser.add_argument("--input-results", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--output-jsonl", default=None)
    parser.add_argument("--metadata-output", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--llm", choices=["mock", "deepseek", "gemini", "openai_compatible"], default="deepseek")
    parser.add_argument("--model", default=None)
    parser.add_argument("--judge-llm", choices=["mock", "deepseek", "gemini", "openai_compatible"], default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--judge-temperature", type=float, default=None)
    parser.add_argument("--judge-max-tokens", type=int, default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    args = parser.parse_args()

    config = {}
    if args.config:
        config_path = Path(args.config)
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    input_results = args.input_results or config.get("input_results")
    output = args.output or config.get("output_csv")
    if not input_results or not output:
        raise SystemExit("--input-results/--output or config input_results/output_csv are required")
    run_id = args.run_id or config.get("run_id") or "rescore-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    judge = build_llm_client(
        args.judge_llm or config.get("judge_llm") or args.llm or config.get("llm", "deepseek"),
        model=args.judge_model or config.get("judge_model") or args.model or config.get("model"),
        temperature=(
            args.judge_temperature
            if args.judge_temperature is not None
            else config.get("judge_temperature", args.temperature)
        ),
        max_tokens=(
            args.judge_max_tokens
            if args.judge_max_tokens is not None
            else config.get("judge_max_tokens", args.max_tokens)
        ),
    )
    results = []
    with Path(input_results).open(encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            package_path = Path(row["output_path"])
            package = ResearchPackage.model_validate_json(package_path.read_text(encoding="utf-8"))
            replicate = int(row["replicate"]) if row.get("replicate") else None
            results.append(
                score_package(
                    package,
                    row["system"],
                    str(package_path),
                    judge_client=judge,
                    replicate=replicate,
                    run_id=run_id,
                )
            )
    write_results_csv(Path(output), results)
    output_jsonl = args.output_jsonl or config.get("output_jsonl")
    if output_jsonl:
        write_results_jsonl(Path(output_jsonl), results)
    metadata_output = args.metadata_output or config.get("metadata_output")
    if metadata_output:
        write_run_metadata(
            Path(metadata_output),
            {
                "run_id": run_id,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "input_results": str(input_results),
                "output_csv": str(output),
                "output_jsonl": str(output_jsonl) if output_jsonl else None,
                "config": str(args.config) if args.config else None,
                "judge_llm": args.judge_llm or config.get("judge_llm") or args.llm or config.get("llm", "deepseek"),
                "judge_model": args.judge_model or config.get("judge_model") or args.model or config.get("model"),
            },
        )
    print(output)


if __name__ == "__main__":
    main()
