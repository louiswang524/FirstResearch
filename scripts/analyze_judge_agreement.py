from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean, pstdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


DEFAULT_METRICS = ["average_score", "novelty", "mechanism_clarity", "falsifiability", "review_score"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze agreement between two benchmark judge result CSVs.")
    parser.add_argument("--primary-results", required=True)
    parser.add_argument("--secondary-results", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--table-output", default=None)
    parser.add_argument("--metrics", nargs="*", default=DEFAULT_METRICS)
    args = parser.parse_args()

    primary = _read_rows(Path(args.primary_results))
    secondary = _read_rows(Path(args.secondary_results))
    matched = _match_rows(primary, secondary)
    metric_rows = _metric_agreement(matched, args.metrics)
    system_rows = _system_agreement(matched, args.metrics)
    rank_rows = _within_group_rank_agreement(matched, args.metrics)

    report = _render_report(
        metric_rows,
        system_rows,
        rank_rows,
        primary_path=args.primary_results,
        secondary_path=args.secondary_results,
        matched_count=len(matched),
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    if args.table_output:
        _write_table(Path(args.table_output), metric_rows, system_rows, rank_rows)
    print(output)


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _match_rows(
    primary: list[dict[str, str]],
    secondary: list[dict[str, str]],
) -> list[tuple[dict[str, str], dict[str, str]]]:
    secondary_by_key = {_row_key(row): row for row in secondary}
    matched = []
    for row in primary:
        other = secondary_by_key.get(_row_key(row))
        if other is not None:
            matched.append((row, other))
    return matched


def _row_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (row.get("topic_id", ""), row.get("replicate", "") or "1", row.get("system", ""))


def _group_key(row: dict[str, str]) -> tuple[str, str]:
    return (row.get("topic_id", ""), row.get("replicate", "") or "1")


def _metric_agreement(
    matched: list[tuple[dict[str, str], dict[str, str]]],
    metrics: list[str],
) -> list[dict[str, object]]:
    rows = []
    for metric in metrics:
        pairs = _numeric_pairs(matched, metric)
        if not pairs:
            continue
        primary_values = [left for left, _ in pairs]
        secondary_values = [right for _, right in pairs]
        deltas = [right - left for left, right in pairs]
        rows.append(
            {
                "section": "metric",
                "metric": metric,
                "n": len(pairs),
                "primary_mean": mean(primary_values),
                "secondary_mean": mean(secondary_values),
                "mean_delta_secondary_minus_primary": mean(deltas),
                "delta_std": pstdev(deltas) if len(deltas) > 1 else 0.0,
                "pearson": _pearson(primary_values, secondary_values),
                "spearman": _spearman(primary_values, secondary_values),
            }
        )
    return rows


def _system_agreement(
    matched: list[tuple[dict[str, str], dict[str, str]]],
    metrics: list[str],
) -> list[dict[str, object]]:
    by_system: dict[str, list[tuple[dict[str, str], dict[str, str]]]] = defaultdict(list)
    for pair in matched:
        by_system[pair[0].get("system", "")].append(pair)

    rows = []
    for metric in metrics:
        primary_means = {}
        secondary_means = {}
        for system, pairs in by_system.items():
            values = _numeric_pairs(pairs, metric)
            if values:
                primary_means[system] = mean(left for left, _ in values)
                secondary_means[system] = mean(right for _, right in values)
        shared_systems = sorted(set(primary_means) & set(secondary_means))
        if not shared_systems:
            continue
        primary_values = [primary_means[system] for system in shared_systems]
        secondary_values = [secondary_means[system] for system in shared_systems]
        primary_ranks = _rank_values(primary_values)
        secondary_ranks = _rank_values(secondary_values)
        for index, system in enumerate(shared_systems):
            rows.append(
                {
                    "section": "system",
                    "metric": metric,
                    "system": system,
                    "primary_mean": primary_values[index],
                    "secondary_mean": secondary_values[index],
                    "mean_delta_secondary_minus_primary": secondary_values[index] - primary_values[index],
                    "primary_rank": primary_ranks[index],
                    "secondary_rank": secondary_ranks[index],
                    "rank_delta_secondary_minus_primary": secondary_ranks[index] - primary_ranks[index],
                }
            )
    return rows


def _within_group_rank_agreement(
    matched: list[tuple[dict[str, str], dict[str, str]]],
    metrics: list[str],
) -> list[dict[str, object]]:
    by_group: dict[tuple[str, str], list[tuple[dict[str, str], dict[str, str]]]] = defaultdict(list)
    for pair in matched:
        by_group[_group_key(pair[0])].append(pair)

    rows = []
    for metric in metrics:
        correlations = []
        exact_top_matches = 0
        comparable_groups = 0
        for pairs in by_group.values():
            values = _numeric_pairs(pairs, metric)
            if len(values) < 2:
                continue
            primary_values = [left for left, _ in values]
            secondary_values = [right for _, right in values]
            correlations.append(_spearman(primary_values, secondary_values))
            comparable_groups += 1
            if _top_indices(primary_values) & _top_indices(secondary_values):
                exact_top_matches += 1
        if comparable_groups:
            rows.append(
                {
                    "section": "rank",
                    "metric": metric,
                    "groups": comparable_groups,
                    "mean_within_group_spearman": mean(correlations),
                    "top_system_match_rate": exact_top_matches / comparable_groups,
                }
            )
    return rows


def _numeric_pairs(
    matched: list[tuple[dict[str, str], dict[str, str]]],
    metric: str,
) -> list[tuple[float, float]]:
    pairs = []
    for left, right in matched:
        left_value = left.get(metric, "")
        right_value = right.get(metric, "")
        if left_value == "" or right_value == "":
            continue
        pairs.append((float(left_value), float(right_value)))
    return pairs


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        return 0.0
    left_mean = mean(left)
    right_mean = mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    left_denominator = sum((x - left_mean) ** 2 for x in left) ** 0.5
    right_denominator = sum((y - right_mean) ** 2 for y in right) ** 0.5
    denominator = left_denominator * right_denominator
    return numerator / denominator if denominator else 0.0


def _spearman(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(right) < 2:
        return 0.0
    return _pearson(_rank_values(left), _rank_values(right))


def _rank_values(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1], reverse=True)
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position + 1
        while end < len(indexed) and indexed[end][1] == indexed[position][1]:
            end += 1
        average_rank = (position + 1 + end) / 2
        for original_index, _ in indexed[position:end]:
            ranks[original_index] = average_rank
        position = end
    return ranks


def _top_indices(values: list[float]) -> set[int]:
    if not values:
        return set()
    best = max(values)
    return {index for index, value in enumerate(values) if value == best}


def _render_report(
    metric_rows: list[dict[str, object]],
    system_rows: list[dict[str, object]],
    rank_rows: list[dict[str, object]],
    *,
    primary_path: str,
    secondary_path: str,
    matched_count: int,
) -> str:
    lines = [
        "# Judge Agreement Analysis",
        "",
        f"Primary results: `{primary_path}`",
        f"Secondary results: `{secondary_path}`",
        f"Matched package rows: {matched_count}",
        "",
        "## Metric Agreement",
        "",
        "| Metric | N | Primary Mean | Secondary Mean | Delta | Delta Std | Pearson | Spearman |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metric_rows:
        lines.append(
            f"| {row['metric']} | {row['n']} | {float(row['primary_mean']):.3f} | "
            f"{float(row['secondary_mean']):.3f} | {float(row['mean_delta_secondary_minus_primary']):+.3f} | "
            f"{float(row['delta_std']):.3f} | {float(row['pearson']):.3f} | {float(row['spearman']):.3f} |"
        )

    lines.extend(["", "## Within-Topic Rank Stability", ""])
    lines.append("| Metric | Groups | Mean Spearman | Top-System Match Rate |")
    lines.append("|---|---:|---:|---:|")
    for row in rank_rows:
        lines.append(
            f"| {row['metric']} | {row['groups']} | {float(row['mean_within_group_spearman']):.3f} | "
            f"{float(row['top_system_match_rate']):.3f} |"
        )

    lines.extend(["", "## System-Level Means", ""])
    lines.append("| Metric | System | Primary Mean | Secondary Mean | Delta | Primary Rank | Secondary Rank | Rank Delta |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for row in system_rows:
        lines.append(
            f"| {row['metric']} | {row['system']} | {float(row['primary_mean']):.3f} | "
            f"{float(row['secondary_mean']):.3f} | {float(row['mean_delta_secondary_minus_primary']):+.3f} | "
            f"{float(row['primary_rank']):.1f} | {float(row['secondary_rank']):.1f} | "
            f"{float(row['rank_delta_secondary_minus_primary']):+.1f} |"
        )
    return "\n".join(lines) + "\n"


def _write_table(
    path: Path,
    metric_rows: list[dict[str, object]],
    system_rows: list[dict[str, object]],
    rank_rows: list[dict[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [*metric_rows, *rank_rows, *system_rows]
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
