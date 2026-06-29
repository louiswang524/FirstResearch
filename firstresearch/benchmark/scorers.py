from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from firstresearch.schemas import BenchmarkResult, QualityScores, ResearchPackage
from firstresearch.utils.llm import LLMClient


class JudgeResult(BaseModel):
    scores: QualityScores
    review_score: int = Field(ge=1, le=10)
    recommendation: Literal["reject", "weak_reject", "borderline", "weak_accept", "accept"]
    rationale: str = Field(min_length=1)


def score_package(
    package: ResearchPackage,
    system: str,
    output_path: str | None = None,
    judge_client: LLMClient | None = None,
    replicate: int | None = None,
    run_id: str | None = None,
) -> BenchmarkResult:
    if judge_client is not None:
        judged = judge_package(package, judge_client)
        scores = judged.scores
        review_score = judged.review_score
        recommendation = judged.recommendation
    elif package.certificates:
        scores = package.certificates[0].quality_scores
        review_score = package.review.score if package.review else None
        recommendation = package.review.recommendation.value if package.review else None
    else:
        scores = QualityScores(
            first_principles_derivation=1,
            falsifiability=1,
            mechanism_clarity=1,
            novelty=2,
            experimentability=2,
        )
        review_score = package.review.score if package.review else None
        recommendation = package.review.recommendation.value if package.review else None
    passed_gate = any(decision.passed for decision in package.gate_decisions)
    return BenchmarkResult(
        run_id=run_id,
        topic_id=package.topic.topic_id,
        topic=package.topic.topic,
        system=system,
        replicate=replicate,
        passed_gate=passed_gate,
        scores=scores,
        review_score=review_score,
        recommendation=recommendation,
        output_path=output_path,
    )


def judge_package(package: ResearchPackage, judge_client: LLMClient) -> JudgeResult:
    scrubbed = package.model_dump(mode="json")
    scrubbed.pop("metadata", None)
    scrubbed["topic_summary"] = "Blinded auto-research output for the supplied topic."
    if scrubbed.get("review"):
        scrubbed["review"]["summary"] = "Blinded internal review summary omitted from judge identity cues."
        scrubbed["review"]["missing_baselines"] = []
    raw = judge_client.complete_json(
        system_prompt=(
            "You are a strict blinded evaluator for auto-research outputs. "
            "Score only the research package quality, not the identity of the system. "
            "Use 0-5 for each rubric metric and 1-10 for review_score. "
            "Return strict JSON matching the supplied schema."
        ),
        user_payload={
            "_agent": "BenchmarkJudge",
            "_output_schema": JudgeResult.model_json_schema(),
            "rubric": {
                "first_principles_derivation": "Does the question trace clearly to primitives, assumptions, and tensions?",
                "falsifiability": "Is there a concrete observation that would reject the hypothesis?",
                "mechanism_clarity": "Are variables and causal/computational links clear?",
                "novelty": "Is the question non-obvious relative to generic gap-finding?",
                "experimentability": "Can the proposed test be run with reasonable resources?",
            },
            "research_package": scrubbed,
        },
    )
    return JudgeResult.model_validate(raw)
