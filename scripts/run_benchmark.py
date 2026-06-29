from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firstresearch.benchmark.runners import run_benchmark
from firstresearch.utils.llm import build_llm_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FirstResearch benchmark.")
    parser.add_argument("--topics", default=None)
    parser.add_argument("--config", default="configs/benchmark.yaml")
    parser.add_argument("--output", default=None)
    parser.add_argument("--output-jsonl", default=None)
    parser.add_argument("--package-dir", default=None)
    parser.add_argument("--metadata-output", default=None)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--systems", nargs="*")
    parser.add_argument("--llm", choices=["mock", "deepseek", "gemini", "openai_compatible"], default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=None)
    parser.add_argument("--max-tokens", type=int, default=None)
    parser.add_argument("--llm-baselines", action="store_true")
    parser.add_argument("--judge-with-llm", action="store_true")
    parser.add_argument("--judge-llm", choices=["mock", "deepseek", "gemini", "openai_compatible"], default=None)
    parser.add_argument("--judge-model", default=None)
    parser.add_argument("--judge-temperature", type=float, default=None)
    parser.add_argument("--judge-max-tokens", type=int, default=None)
    parser.add_argument("--max-topics", type=int, default=None)
    parser.add_argument("--repeats", type=int, default=None)
    parser.add_argument("--resume", action="store_true", help="Resume from existing result rows and package JSON files.")
    parser.add_argument("--target-rows", type=int, default=None, help="Stop once the output CSV has this many rows.")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    llm_provider = args.llm or config.get("llm", "mock")
    temperature = args.temperature if args.temperature is not None else config.get("temperature", 0.2)
    max_tokens = args.max_tokens if args.max_tokens is not None else config.get("max_tokens", 4096)
    llm_client = build_llm_client(
        llm_provider,
        model=args.model or config.get("model"),
        temperature=temperature,
        max_tokens=max_tokens,
    )
    topics = Path(args.topics or config.get("topics", "data/topics_eval.jsonl"))
    output_csv = Path(args.output or config.get("output_csv", "outputs/reports/benchmark_results.csv"))
    output_jsonl = Path(args.output_jsonl or config.get("output_jsonl", output_csv.with_suffix(".jsonl")))
    systems = args.systems or config.get("systems")
    package_dir = Path(args.package_dir or config.get("package_dir", output_csv.parent / "packages"))
    metadata_output = Path(args.metadata_output or config.get("metadata_output", output_csv.with_name(output_csv.stem + "_metadata.json")))
    llm_baselines = args.llm_baselines or bool(config.get("llm_baselines", llm_provider != "mock"))
    judge_with_llm = args.judge_with_llm or bool(config.get("judge_with_llm", False))
    judge_provider = args.judge_llm or config.get("judge_llm") or llm_provider
    judge_temperature = (
        args.judge_temperature
        if args.judge_temperature is not None
        else config.get("judge_temperature", temperature)
    )
    judge_max_tokens = (
        args.judge_max_tokens
        if args.judge_max_tokens is not None
        else config.get("judge_max_tokens", max_tokens)
    )
    judge_client = None
    if judge_with_llm:
        judge_client = build_llm_client(
            judge_provider,
            model=args.judge_model or config.get("judge_model") or args.model or config.get("model"),
            temperature=judge_temperature,
            max_tokens=judge_max_tokens,
        )
    max_topics = args.max_topics if args.max_topics is not None else config.get("max_topics")
    repeats = args.repeats if args.repeats is not None else config.get("repeats", 1)
    resume = args.resume or bool(config.get("resume", False))
    target_rows = args.target_rows if args.target_rows is not None else config.get("target_rows")
    run_benchmark(
        topics_path=topics,
        output_csv=output_csv,
        output_jsonl=output_jsonl,
        systems=systems,
        package_dir=package_dir,
        llm_client=llm_client,
        llm_baselines=llm_baselines,
        max_topics=max_topics,
        judge_client=judge_client,
        repeats=repeats,
        run_id=args.run_id or config.get("run_id"),
        metadata_path=metadata_output,
        resume=resume,
        target_rows=target_rows,
        run_metadata={
            "config": str(config_path) if config_path.exists() else None,
            "llm": llm_provider,
            "model": args.model or config.get("model"),
            "temperature": temperature,
            "max_tokens": max_tokens,
            "judge_llm": judge_provider if judge_with_llm else None,
            "judge_model": (args.judge_model or config.get("judge_model") or args.model or config.get("model")) if judge_with_llm else None,
            "judge_temperature": judge_temperature if judge_with_llm else None,
            "judge_max_tokens": judge_max_tokens if judge_with_llm else None,
        },
    )
    print(output_csv)


if __name__ == "__main__":
    main()
