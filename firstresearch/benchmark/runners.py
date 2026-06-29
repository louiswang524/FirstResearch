from __future__ import annotations

import csv
import json
from pathlib import Path
from datetime import datetime, timezone

from firstresearch.benchmark.baselines import get_baselines
from firstresearch.benchmark.dataset import load_topics
from firstresearch.benchmark.scorers import score_package
from firstresearch.schemas import BenchmarkResult, QualityScores, ResearchPackage
from firstresearch.utils.json import write_json
from firstresearch.utils.llm import LLMClient


def run_benchmark(
    *,
    topics_path: Path,
    output_csv: Path,
    output_jsonl: Path | None = None,
    systems: list[str] | None = None,
    package_dir: Path | None = None,
    llm_client: LLMClient | None = None,
    llm_baselines: bool = False,
    max_topics: int | None = None,
    judge_client: LLMClient | None = None,
    repeats: int = 1,
    run_id: str | None = None,
    metadata_path: Path | None = None,
    run_metadata: dict[str, object] | None = None,
    resume: bool = False,
    target_rows: int | None = None,
) -> list[BenchmarkResult]:
    if repeats < 1:
        raise ValueError("repeats must be at least 1")
    run_id = run_id or _default_run_id()
    topics = load_topics(topics_path)
    if max_topics is not None:
        topics = topics[:max_topics]
    baselines = get_baselines(systems, llm_client=llm_client, llm_baselines=llm_baselines)
    package_dir = package_dir or output_csv.parent / "packages"
    results: list[BenchmarkResult] = _read_results_csv(output_csv) if resume and output_csv.exists() else []
    completed = {_result_key(result) for result in results}
    if target_rows is None or len(results) < target_rows:
        for replicate in range(1, repeats + 1):
            for topic in topics:
                for baseline in baselines:
                    if target_rows is not None and len(results) >= target_rows:
                        break
                    result_replicate = replicate if repeats > 1 else None
                    key = (topic.topic_id, baseline.name, result_replicate)
                    if key in completed:
                        continue
                    package_path = _package_path(package_dir, topic.topic_id, baseline.name, replicate, repeats)
                    if resume and package_path.exists():
                        package = _read_package(package_path)
                    else:
                        package = baseline.run(topic)
                    package.metadata["replicate"] = replicate
                    package.metadata["run_id"] = run_id
                    write_json(package_path, package.model_dump(mode="json"))
                    results.append(
                        score_package(
                            package,
                            baseline.name,
                            str(package_path),
                            judge_client=judge_client,
                            replicate=result_replicate,
                            run_id=run_id,
                        )
                    )
                    completed.add(key)
                    write_results_csv(output_csv, results)
                    if output_jsonl:
                        write_results_jsonl(output_jsonl, results)
                if target_rows is not None and len(results) >= target_rows:
                    break
            if target_rows is not None and len(results) >= target_rows:
                break
    write_results_csv(output_csv, results)
    if output_jsonl:
        write_results_jsonl(output_jsonl, results)
    if metadata_path:
        write_run_metadata(
            metadata_path,
            {
                "run_id": run_id,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "topics_path": str(topics_path),
                "output_csv": str(output_csv),
                "output_jsonl": str(output_jsonl) if output_jsonl else None,
                "package_dir": str(package_dir),
                "systems": [baseline.name for baseline in baselines],
                "topic_count": len(topics),
                "repeats": repeats,
                "llm_baselines": llm_baselines,
                "judge_with_llm": judge_client is not None,
                "resume": resume,
                "target_rows": target_rows,
                **(run_metadata or {}),
            },
        )
    return results


def write_results_csv(path: Path, results: list[BenchmarkResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "run_id",
        "topic_id",
        "topic",
        "system",
        "replicate",
        "passed_gate",
        "first_principles_derivation",
        "falsifiability",
        "mechanism_clarity",
        "novelty",
        "experimentability",
        "average_score",
        "review_score",
        "recommendation",
        "output_path",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            row = result.model_dump(mode="json")
            scores = row.pop("scores")
            row.update(scores)
            row["average_score"] = sum(scores.values()) / len(scores)
            writer.writerow(row)


def write_results_jsonl(path: Path, results: list[BenchmarkResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result.model_dump(mode="json"), ensure_ascii=False) + "\n")


def _read_results_csv(path: Path) -> list[BenchmarkResult]:
    results: list[BenchmarkResult] = []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            scores = {
                "first_principles_derivation": int(float(row["first_principles_derivation"])),
                "falsifiability": int(float(row["falsifiability"])),
                "mechanism_clarity": int(float(row["mechanism_clarity"])),
                "novelty": int(float(row["novelty"])),
                "experimentability": int(float(row["experimentability"])),
            }
            results.append(
                BenchmarkResult(
                    run_id=row.get("run_id") or None,
                    topic_id=row.get("topic_id") or None,
                    topic=row["topic"],
                    system=row["system"],
                    replicate=int(row["replicate"]) if row.get("replicate") else None,
                    passed_gate=str(row["passed_gate"]).lower() == "true",
                    scores=QualityScores(**scores),
                    review_score=int(float(row["review_score"])) if row.get("review_score") else None,
                    recommendation=row.get("recommendation") or None,
                    output_path=row.get("output_path") or None,
                )
            )
    return results


def _read_package(path: Path) -> ResearchPackage:
    return ResearchPackage.model_validate_json(path.read_text(encoding="utf-8"))


def _result_key(result: BenchmarkResult) -> tuple[str | None, str, int | None]:
    return (result.topic_id, result.system, result.replicate)


def write_run_metadata(path: Path, metadata: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _package_path(package_dir: Path, topic_id: str | None, system: str, replicate: int, repeats: int) -> Path:
    topic_part = topic_id or "topic"
    if repeats == 1:
        return package_dir / f"{topic_part}_{system}.json"
    return package_dir / f"r{replicate:02d}_{topic_part}_{system}.json"


def _default_run_id() -> str:
    return "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
