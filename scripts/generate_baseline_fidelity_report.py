from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


BASELINE_CARDS = [
    {
        "system": "co_scientist",
        "source_pattern": "AI co-scientist-style hypothesis generation",
        "implemented_elements": [
            "diverse hypothesis generation",
            "reflection/debate/ranking over generated hypotheses",
            "evolution/refinement of the selected hypothesis",
            "shared ResearchPackage output schema for scoring",
        ],
        "omitted_elements": [
            "no reproduction of the original system code or proprietary orchestration",
            "no large-scale asynchronous agent pool",
            "no external biomedical or literature-tool integration",
            "no full published-system search budget",
        ],
        "fairness_controls": [
            "same topic inputs as FirstResearch",
            "same generation model family in configured DeepSeek runs",
            "same output schema before scoring",
            "same LLM-judge rubric and benchmark CSV format",
        ],
    },
    {
        "system": "agent_lab",
        "source_pattern": "Agent Laboratory-style staged research assistant",
        "implemented_elements": [
            "literature-plan stage",
            "experiment-plan stage",
            "professor/reviewer critique stage",
            "final synthesis stage",
            "shared ResearchPackage output schema for scoring",
        ],
        "omitted_elements": [
            "no execution of the public Agent Laboratory codebase",
            "no full paper-writing pipeline",
            "no human-in-the-loop protocol",
            "no experiment execution environment",
        ],
        "fairness_controls": [
            "same topics and model configuration as FirstResearch",
            "same final package schema",
            "same judge prompt and metrics",
            "same artifact storage convention",
        ],
    },
    {
        "system": "tree_search_scientist",
        "source_pattern": "AI Scientist-v2-style branch search",
        "implemented_elements": [
            "frontier generation of multiple research branches",
            "branch ranking by novelty, mechanism clarity, falsifiability, and feasibility",
            "selected-branch expansion into one package",
            "shared ResearchPackage output schema for scoring",
        ],
        "omitted_elements": [
            "no reproduction of AI Scientist-v2 code",
            "no workshop-paper generation pipeline",
            "no code execution or experiment-running loop",
            "no full tree-search compute budget",
        ],
        "fairness_controls": [
            "same topic set",
            "same configured model backend",
            "same final scoring rubric",
            "same CSV/report machinery",
        ],
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a baseline fidelity report for prompt-level comparison systems.")
    parser.add_argument("--config", default="configs/deepseek_strong_baselines.yaml")
    parser.add_argument("--output", default="outputs/reports/baseline_fidelity_report.md")
    parser.add_argument("--json-output", default="outputs/reports/baseline_fidelity_report.json")
    args = parser.parse_args()

    config = _load_config(Path(args.config))
    report_data = _build_report(config, args.config)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(_render_markdown(report_data), encoding="utf-8")
    if args.json_output:
        json_output = Path(args.json_output)
        json_output.parent.mkdir(parents=True, exist_ok=True)
        json_output.write_text(json.dumps(report_data, indent=2) + "\n", encoding="utf-8")
    print(output)


def _load_config(path: Path) -> dict[str, object]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def _build_report(config: dict[str, object], config_path: str) -> dict[str, object]:
    configured_systems = [str(system) for system in config.get("systems", [])]
    cards = [card for card in BASELINE_CARDS if card["system"] in configured_systems]
    return {
        "config": config_path,
        "topics": config.get("topics"),
        "model": config.get("model"),
        "llm": config.get("llm"),
        "judge_with_llm": bool(config.get("judge_with_llm")),
        "llm_baselines": bool(config.get("llm_baselines")),
        "systems": configured_systems,
        "baseline_cards": cards,
        "scope_statement": (
            "These are controlled prompt-level workflow approximations. They test whether FirstResearch "
            "outperforms strong ideation patterns under a shared model, schema, and judge protocol; they do not "
            "claim to reproduce the full published systems."
        ),
    }


def _render_markdown(data: dict[str, object]) -> str:
    lines = [
        "# Baseline Fidelity Report",
        "",
        str(data["scope_statement"]),
        "",
        "## Configuration",
        "",
        f"- Config: `{data['config']}`",
        f"- Topics: `{data['topics']}`",
        f"- LLM backend: `{data['llm']}`",
        f"- Model: `{data['model']}`",
        f"- LLM baselines: `{str(data['llm_baselines']).lower()}`",
        f"- LLM judge: `{str(data['judge_with_llm']).lower()}`",
        f"- Systems: {', '.join(str(system) for system in data['systems'])}",
        "",
        "## Fidelity Cards",
        "",
    ]
    for card in data["baseline_cards"]:
        lines.extend(
            [
                f"### `{card['system']}`",
                "",
                f"Source pattern: {card['source_pattern']}",
                "",
                "Implemented elements:",
            ]
        )
        lines.extend(f"- {item}" for item in card["implemented_elements"])
        lines.extend(["", "Omitted elements:"])
        lines.extend(f"- {item}" for item in card["omitted_elements"])
        lines.extend(["", "Fairness controls:"])
        lines.extend(f"- {item}" for item in card["fairness_controls"])
        lines.append("")

    lines.extend(
        [
            "## Interpretation Boundary",
            "",
            "The resulting table should be described as a controlled comparison against strong prompt-level baseline patterns, not as a claim of superiority over the complete published systems.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
