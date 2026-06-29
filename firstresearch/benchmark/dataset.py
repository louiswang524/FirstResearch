from __future__ import annotations

import json
from pathlib import Path

from firstresearch.schemas import ResearchTopic


def load_topics(path: Path) -> list[ResearchTopic]:
    topics: list[ResearchTopic] = []
    with path.open(encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            data = json.loads(line)
            topics.append(
                ResearchTopic(
                    topic_id=data.get("topic_id") or f"line-{line_number}",
                    topic=data["topic"],
                    domain=data.get("domain"),
                    goal=data.get("goal"),
                )
            )
    return topics
