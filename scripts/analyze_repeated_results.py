from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


DEFAULT_METRICS = ["average_score", "novelty", "mechanism_clarity", "falsifiability"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze repeated benchmark results with paired deltas and bootstrap CIs.")
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--table-output", default=None)
    parser.add_argument("--reference-system", default="firstresearch")
    parser.add_argument("--metrics", nargs="*", default=DEFAULT_METRICS)
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=19)
    args = parser.parse_args()

    rows = _read_rows(Path(args.results))
    analysis = analyze_rows(
        rows,
        reference_system=args.reference_system,
        metrics=args.metrics,
        bootstrap_samples=args.bootstrap_samples,
        seed=args.seed,
    )
    report = render_report(analysis, args.reference_system, args.metrics)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    if args.table_output:
        write_table(Path(args.table_output), analysis)
    print(output)


def analyze_rows(
    rows: list[dict[str, str]],
    *,
    reference_system: str,
    metrics: list[str],
    bootstrap_samples: int,
    seed: int,
) -> list[dict[str, object]]:
    by_system: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_key_system: dict[tuple[str, str], dict[str, str]] = {}
    for row in rows:
        by_system[row["system"]].append(row)
        by_key_system[(_pair_key(row), row["system"])] = row

    rng = random.Random(seed)
    summaries: list[dict[str, object]] = []
    for system in sorted(by_system):
        system_rows = by_system[system]
        summary: dict[str, object] = {
            "system": system,
            "n": len(system_rows),
            "replicates": _replicate_count(system_rows),
        }
        for metric in metrics:
            values = [float(row[metric]) for row in system_rows]
            summary[f"{metric}_mean"] = mean(values)
            summary[f"{metric}_std"] = pstdev(values) if len(values) > 1 else 0.0

            paired = _paired_deltas(system_rows, by_key_system, reference_system, system, metric)
            if paired:
                deltas = [delta for _, delta in paired]
                low, high = _bootstrap_ci(deltas, rng, bootstrap_samples)
                summary[f"{metric}_paired_n"] = len(deltas)
                summary[f"{metric}_delta_vs_{reference_system}"] = mean(deltas)
                summary[f"{metric}_delta_ci_low"] = low
                summary[f"{metric}_delta_ci_high"] = high
                summary[f"{metric}_wins"] = sum(delta > 0 for delta in deltas)
                summary[f"{metric}_ties"] = sum(delta == 0 for delta in deltas)
                summary[f"{metric}_losses"] = sum(delta < 0 for delta in deltas)
            else:
                summary[f"{metric}_paired_n"] = 0
                summary[f"{metric}_delta_vs_{reference_system}"] = 0.0
                summary[f"{metric}_delta_ci_low"] = 0.0
                summary[f"{metric}_delta_ci_high"] = 0.0
                summary[f"{metric}_wins"] = 0
                summary[f"{metric}_ties"] = 0
                summary[f"{metric}_losses"] = 0
        summaries.append(summary)
    return summaries


def render_report(analysis: list[dict[str, object]], reference_system: str, metrics: list[str]) -> str:
    primary = metrics[0]
    lines = [
        "# Repeated Benchmark Stability Analysis",
        "",
        f"Reference system: `{reference_system}`",
        "",
        "Positive deltas mean the row system scores higher than the reference on matched topic/replicate pairs.",
        "",
        f"## Primary Metric: `{primary}`",
        "",
        "| System | N | Repeats | Mean | Std | Paired N | Delta vs Reference | 95% Bootstrap CI | W/T/L |",
        "|---|---:|---:|---:|---:|---:|---:|---|---:|",
    ]
    for row in analysis:
        lines.append(
            f"| {row['system']} | {row['n']} | {row['replicates']} | "
            f"{float(row[f'{primary}_mean']):.3f} | {float(row[f'{primary}_std']):.3f} | "
            f"{row[f'{primary}_paired_n']} | {float(row[f'{primary}_delta_vs_{reference_system}']):+.3f} | "
            f"[{float(row[f'{primary}_delta_ci_low']):+.3f}, {float(row[f'{primary}_delta_ci_high']):+.3f}] | "
            f"{row[f'{primary}_wins']}/{row[f'{primary}_ties']}/{row[f'{primary}_losses']} |"
        )

    lines.extend(["", "## Metric Details", ""])
    for metric in metrics:
        lines.append(f"### `{metric}`")
        lines.append("")
        lines.append("| System | Mean | Std | Delta vs Reference | 95% Bootstrap CI |")
        lines.append("|---|---:|---:|---:|---|")
        for row in analysis:
            lines.append(
                f"| {row['system']} | {float(row[f'{metric}_mean']):.3f} | "
                f"{float(row[f'{metric}_std']):.3f} | "
                f"{float(row[f'{metric}_delta_vs_{reference_system}']):+.3f} | "
                f"[{float(row[f'{metric}_delta_ci_low']):+.3f}, {float(row[f'{metric}_delta_ci_high']):+.3f}] |"
            )
        lines.append("")
    return "\n".join(lines)


def write_table(path: Path, analysis: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    for row in analysis:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(analysis)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _pair_key(row: dict[str, str]) -> str:
    replicate = row.get("replicate") or "1"
    return f"{row.get('topic_id', '')}::r{replicate}"


def _replicate_count(rows: list[dict[str, str]]) -> int:
    replicates = {row.get("replicate") or "1" for row in rows}
    return len(replicates)


def _paired_deltas(
    rows: list[dict[str, str]],
    by_key_system: dict[tuple[str, str], dict[str, str]],
    reference_system: str,
    system: str,
    metric: str,
) -> list[tuple[str, float]]:
    paired = []
    for row in rows:
        key = _pair_key(row)
        reference = by_key_system.get((key, reference_system))
        if reference is None:
            continue
        paired.append((key, float(row[metric]) - float(reference[metric])))
    return paired


def _bootstrap_ci(values: list[float], rng: random.Random, samples: int) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1 or samples <= 0:
        value = mean(values)
        return value, value
    means = []
    for _ in range(samples):
        draw = [values[rng.randrange(len(values))] for _ in values]
        means.append(mean(draw))
    means.sort()
    low_index = int(0.025 * (len(means) - 1))
    high_index = int(0.975 * (len(means) - 1))
    return means[low_index], means[high_index]


if __name__ == "__main__":
    main()
