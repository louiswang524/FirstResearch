from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from firstresearch.orchestrator import ResearchOrchestrator
from firstresearch.schemas import ResearchTopic
from firstresearch.utils.json import write_json
from firstresearch.utils.llm import build_llm_client


def main() -> None:
    parser = argparse.ArgumentParser(description="Run FirstResearch on one topic.")
    parser.add_argument("--topic", required=True)
    parser.add_argument("--goal")
    parser.add_argument("--domain")
    parser.add_argument("--output", default="outputs/runs/single_topic.json")
    parser.add_argument("--llm", choices=["mock", "deepseek"], default="mock")
    parser.add_argument("--model", default=None)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=4096)
    args = parser.parse_args()

    topic = ResearchTopic(topic=args.topic, goal=args.goal, domain=args.domain)
    llm_client = build_llm_client(
        args.llm,
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
    )
    package = ResearchOrchestrator(llm_client).run(topic)
    output_path = Path(args.output)
    write_json(output_path, package.model_dump(mode="json"))
    print(output_path)


if __name__ == "__main__":
    main()
