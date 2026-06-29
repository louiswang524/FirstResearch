from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator


class ResearchTopic(BaseModel):
    topic: str = Field(min_length=1)
    topic_id: str | None = None
    goal: str | None = None
    domain: str | None = None
    target_venue: str | None = None
    domain_constraints: list[str] = Field(default_factory=list)
    available_compute: str | None = None
    preferred_method: str | None = None


class PrimitiveDefinition(BaseModel):
    name: str = Field(min_length=1)
    definition: str = Field(min_length=1)
    why_primitive: str = Field(min_length=1)


class FirstPrincipleAssumption(BaseModel):
    assumption: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    possible_failure: str = Field(min_length=1)


class CoreTradeoff(BaseModel):
    tradeoff: str = Field(min_length=1)
    variables: list[str] = Field(min_length=1)


class FirstPrinciplesDecomposition(BaseModel):
    primitive_definitions: list[PrimitiveDefinition] = Field(min_length=3)
    assumptions: list[FirstPrincipleAssumption] = Field(min_length=2)
    core_tradeoffs: list[CoreTradeoff] = Field(default_factory=list)


class MechanismVariable(BaseModel):
    name: str = Field(min_length=1)
    role: Literal["input", "mediator", "output", "outcome", "confounder"]
    description: str = Field(min_length=1)


class CausalChainStep(BaseModel):
    step: str | None = None
    source: str | None = None
    relation: str | None = None
    target: str | None = None
    explanation: str | None = None

    @field_validator("step", "source", "relation", "target", "explanation", mode="before")
    @classmethod
    def stringify_values(cls, value: object) -> object:
        if value is None or isinstance(value, str):
            return value
        return str(value)

    @model_validator(mode="after")
    def has_step_or_edge(self) -> "CausalChainStep":
        if self.step or (self.source and self.relation and self.target):
            return self
        raise ValueError("causal chain step needs either step or source/relation/target")


class Bottleneck(BaseModel):
    bottleneck: str = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)


class MechanismModel(BaseModel):
    variables: list[MechanismVariable] = Field(min_length=1)
    causal_chain: list[CausalChainStep] = Field(min_length=1)
    bottlenecks: list[Bottleneck] = Field(default_factory=list)
    mechanism_summary: str = Field(min_length=1)


class Tension(BaseModel):
    tension_id: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    derived_from: list[str] = Field(min_length=1)
    why_it_matters: str = Field(min_length=1)
    what_existing_methods_may_miss: str = Field(default="")
    testability: int = Field(ge=0, le=5)


class QuestionType(str, Enum):
    descriptive = "descriptive"
    causal = "causal"
    diagnostic = "diagnostic"
    benchmark = "benchmark"
    algorithmic = "algorithmic"


class CandidateResearchQuestion(BaseModel):
    question: str = Field(min_length=1)
    question_type: QuestionType
    source_tension: str = Field(min_length=1)
    expected_contribution: str = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def fill_expected_contribution(cls, data: object) -> object:
        if isinstance(data, dict) and not data.get("expected_contribution"):
            question = str(data.get("question", "the generated question"))
            data = {**data, "expected_contribution": f"Tests a mechanism-level claim implied by: {question}"}
        return data


class Hypothesis(BaseModel):
    statement: str = Field(min_length=1)
    predicted_effect: str = Field(min_length=1)


class MinimalDecisiveTest(BaseModel):
    experiment: str = Field(min_length=1)
    independent_variables: list[str] = Field(min_length=1)
    dependent_variables: list[str] = Field(min_length=1)
    controls: list[str] = Field(min_length=1)
    falsifying_observation: str = Field(min_length=1)


class ExpectedObservations(BaseModel):
    supports_hypothesis: list[str] = Field(min_length=1)
    rejects_hypothesis: list[str] = Field(min_length=1)


class FailureUpdateRule(BaseModel):
    if_failed: str = Field(min_length=1)
    assumption_to_revise: str = Field(min_length=1)
    next_question: str = Field(min_length=1)


class QualityScores(BaseModel):
    first_principles_derivation: int = Field(ge=0, le=5)
    falsifiability: int = Field(ge=0, le=5)
    mechanism_clarity: int = Field(ge=0, le=5)
    novelty: int = Field(ge=0, le=5)
    experimentability: int = Field(ge=0, le=5)

    def average(self) -> float:
        return sum(self.model_dump().values()) / 5


class ResearchQuestionCertificate(BaseModel):
    topic: str = Field(min_length=1)
    primitive_definitions: list[PrimitiveDefinition] = Field(min_length=3)
    first_principle_assumptions: list[FirstPrincipleAssumption] = Field(min_length=2)
    mechanism_model: MechanismModel
    tension_or_contradiction: Tension
    research_question: CandidateResearchQuestion
    hypothesis: Hypothesis
    minimal_decisive_test: MinimalDecisiveTest
    expected_observations: ExpectedObservations
    failure_update_rule: FailureUpdateRule
    quality_scores: QualityScores

    @model_validator(mode="after")
    def question_references_tension(self) -> "ResearchQuestionCertificate":
        if self.research_question.source_tension != self.tension_or_contradiction.tension_id:
            raise ValueError("research question must reference the selected source tension")
        return self


class GateDecision(BaseModel):
    passed: bool = Field(alias="pass")
    reason: str
    repair_suggestions: list[str] = Field(default_factory=list)
    scores: QualityScores

    model_config = {"populate_by_name": True}


class BaselineSpec(BaseModel):
    name: str
    description: str


class MetricSpec(BaseModel):
    name: str
    definition: str


class ExperimentPlan(BaseModel):
    hypothesis: str = Field(min_length=1)
    independent_variables: list[str] = Field(min_length=1)
    dependent_variables: list[str] = Field(min_length=1)
    controlled_variables: list[str] = Field(min_length=1)
    baselines: list[BaselineSpec] = Field(min_length=1)
    metrics: list[MetricSpec] = Field(min_length=1)
    expected_result: str = Field(min_length=1)
    falsifying_result: str = Field(min_length=1)
    minimum_viable_experiment: str = Field(min_length=1)
    risks_and_confounds: list[str] = Field(default_factory=list)


class ReviewRecommendation(str, Enum):
    reject = "reject"
    weak_reject = "weak_reject"
    borderline = "borderline"
    weak_accept = "weak_accept"
    accept = "accept"


class Review(BaseModel):
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    questions: list[str] = Field(default_factory=list)
    missing_baselines: list[str] = Field(default_factory=list)
    score: int = Field(ge=1, le=10)
    confidence: int = Field(ge=1, le=5)
    recommendation: ReviewRecommendation


class SelfImprovementRecord(BaseModel):
    failure_type: str
    root_cause: str
    violated_principle: str
    new_or_updated_principle: str
    new_or_updated_skill: str
    regression_test: str


class ResearchPackage(BaseModel):
    topic: ResearchTopic
    topic_summary: str
    first_principles_decomposition: FirstPrinciplesDecomposition | None = None
    mechanism_model: MechanismModel | None = None
    tensions: list[Tension] = Field(default_factory=list)
    candidate_questions: list[CandidateResearchQuestion] = Field(default_factory=list)
    certificates: list[ResearchQuestionCertificate] = Field(default_factory=list)
    gate_decisions: list[GateDecision] = Field(default_factory=list)
    experiment_plans: list[ExperimentPlan] = Field(default_factory=list)
    review: Review | None = None
    self_improvement_update: SelfImprovementRecord | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkResult(BaseModel):
    run_id: str | None = None
    topic_id: str | None
    topic: str
    system: str
    replicate: int | None = None
    passed_gate: bool
    scores: QualityScores
    review_score: int | None = None
    recommendation: str | None = None
    output_path: str | None = None

    @field_validator("system")
    @classmethod
    def no_empty_system(cls, value: str, info: ValidationInfo) -> str:
        if not value.strip():
            raise ValueError("system cannot be empty")
        return value
