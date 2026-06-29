from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from pydantic import BaseModel, Field

from firstresearch.orchestrator import ResearchOrchestrator
from firstresearch.schemas import (
    CandidateResearchQuestion,
    ExpectedObservations,
    FailureUpdateRule,
    FirstPrincipleAssumption,
    FirstPrinciplesDecomposition,
    GateDecision,
    Hypothesis,
    MechanismModel,
    MechanismVariable,
    MinimalDecisiveTest,
    PrimitiveDefinition,
    QualityScores,
    ResearchPackage,
    ResearchQuestionCertificate,
    ResearchTopic,
    Review,
    Tension,
)
from firstresearch.utils.llm import MockLLMClient
from firstresearch.utils.llm import LLMClient


class Baseline(ABC):
    name: str

    @abstractmethod
    def run(self, topic: ResearchTopic) -> ResearchPackage:
        raise NotImplementedError


class FirstResearchSystem(Baseline):
    name = "firstresearch"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or MockLLMClient()

    def run(self, topic: ResearchTopic) -> ResearchPackage:
        return ResearchOrchestrator(self.llm_client).run(topic)


class FirstResearchAblation(FirstResearchSystem):
    ablation_name = "unspecified"
    orchestrator_options: dict[str, bool] = {}

    def run(self, topic: ResearchTopic) -> ResearchPackage:
        package = ResearchOrchestrator(self.llm_client, **self.orchestrator_options).run(topic)
        package.metadata["baseline"] = self.name
        package.metadata["ablation"] = self.ablation_name
        return package


class BaselineIdea(BaseModel):
    primitive_definitions: list[PrimitiveDefinition] = Field(min_length=3)
    assumptions: list[FirstPrincipleAssumption] = Field(min_length=2)
    mechanism_summary: str = Field(min_length=1)
    tension: str = Field(min_length=1)
    question: str = Field(min_length=1)
    question_type: Literal["descriptive", "causal", "diagnostic", "benchmark", "algorithmic"]
    hypothesis: str = Field(min_length=1)
    predicted_effect: str = Field(min_length=1)
    experiment: str = Field(min_length=1)
    independent_variables: list[str] = Field(min_length=1)
    dependent_variables: list[str] = Field(min_length=1)
    controls: list[str] = Field(min_length=1)
    falsifying_observation: str = Field(min_length=1)
    expected_support: list[str] = Field(min_length=1)
    expected_reject: list[str] = Field(min_length=1)
    failure_update: str = Field(min_length=1)
    novelty_note: str = Field(min_length=1)
    quality_scores: QualityScores


def _validate_baseline_idea(raw: dict[str, Any]) -> BaselineIdea:
    normalized = dict(raw)
    for key in [
        "independent_variables",
        "dependent_variables",
        "controls",
        "expected_support",
        "expected_reject",
    ]:
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = [value]
    return BaselineIdea.model_validate(normalized)


class CoScientistHypothesis(BaseModel):
    hypothesis_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    hypothesis: str = Field(min_length=1)
    mechanism: str = Field(min_length=1)
    experiment: str = Field(min_length=1)
    novelty_rationale: str = Field(min_length=1)
    risks: list[str] = Field(min_length=1)


class CoScientistHypothesisPool(BaseModel):
    hypotheses: list[CoScientistHypothesis] = Field(min_length=3)


class CoScientistDebateResult(BaseModel):
    critiques: list[str] = Field(min_length=1)
    ranking: list[str] = Field(min_length=1)
    winning_hypothesis_id: str = Field(min_length=1)
    synthesis: str = Field(min_length=1)


class AgentLabLiteraturePlan(BaseModel):
    related_work_claims: list[str] = Field(min_length=2)
    inferred_gap: str = Field(min_length=1)
    closest_baselines: list[str] = Field(min_length=1)


class AgentLabExperimentPlan(BaseModel):
    proposed_question: str = Field(min_length=1)
    proposed_hypothesis: str = Field(min_length=1)
    experiment_design: str = Field(min_length=1)
    implementation_risks: list[str] = Field(min_length=1)


class AgentLabCritique(BaseModel):
    strengths: list[str] = Field(min_length=1)
    weaknesses: list[str] = Field(min_length=1)
    required_revisions: list[str] = Field(min_length=1)


class TreeSearchBranch(BaseModel):
    branch_id: str = Field(min_length=1)
    research_direction: str = Field(min_length=1)
    mechanism_bet: str = Field(min_length=1)
    minimal_experiment: str = Field(min_length=1)
    expected_failure_mode: str = Field(min_length=1)


class TreeSearchBranchSet(BaseModel):
    branches: list[TreeSearchBranch] = Field(min_length=3)


class TreeSearchSelection(BaseModel):
    selected_branch_id: str = Field(min_length=1)
    ranking: list[str] = Field(min_length=1)
    selection_rationale: str = Field(min_length=1)
    expansion_instructions: list[str] = Field(min_length=1)


class PromptDrivenBaseline(Baseline):
    def __init__(self, *, name: str, system_prompt: str, llm_client: LLMClient) -> None:
        self.name = name
        self.system_prompt = system_prompt
        self.llm_client = llm_client

    def run(self, topic: ResearchTopic) -> ResearchPackage:
        raw = self.llm_client.complete_json(
            system_prompt=self.system_prompt + "\n\nReturn strict JSON matching the requested fields.",
            user_payload={
                "_agent": f"Baseline_{self.name}",
                "topic": topic.model_dump(mode="json"),
                "_output_schema": BaselineIdea.model_json_schema(),
            },
        )
        idea = _validate_baseline_idea(raw)
        mechanism = MechanismModel(
            variables=[
                MechanismVariable(name="topic condition", role="input", description="The main condition or task distribution studied by the baseline."),
                MechanismVariable(name="proposed mechanism", role="mediator", description=idea.mechanism_summary),
                MechanismVariable(name="research quality", role="outcome", description="Whether the proposed question is falsifiable and experimentable."),
            ],
            causal_chain=[{"step": idea.mechanism_summary}],
            mechanism_summary=idea.mechanism_summary,
        )
        tension = Tension(
            tension_id=f"{self.name.upper()}-TENSION",
            statement=idea.tension,
            derived_from=[item.name for item in idea.primitive_definitions[:2]],
            why_it_matters=idea.novelty_note,
            what_existing_methods_may_miss="Baseline-generated novelty assessment.",
            testability=min(5, max(0, idea.quality_scores.experimentability)),
        )
        question = CandidateResearchQuestion(
            question=idea.question,
            question_type=idea.question_type,
            source_tension=tension.tension_id,
            expected_contribution=idea.novelty_note,
        )
        certificate = ResearchQuestionCertificate(
            topic=topic.topic,
            primitive_definitions=idea.primitive_definitions,
            first_principle_assumptions=idea.assumptions,
            mechanism_model=mechanism,
            tension_or_contradiction=tension,
            research_question=question,
            hypothesis=Hypothesis(statement=idea.hypothesis, predicted_effect=idea.predicted_effect),
            minimal_decisive_test=MinimalDecisiveTest(
                experiment=idea.experiment,
                independent_variables=idea.independent_variables,
                dependent_variables=idea.dependent_variables,
                controls=idea.controls,
                falsifying_observation=idea.falsifying_observation,
            ),
            expected_observations=ExpectedObservations(
                supports_hypothesis=idea.expected_support,
                rejects_hypothesis=idea.expected_reject,
            ),
            failure_update_rule=FailureUpdateRule(
                if_failed=idea.failure_update,
                assumption_to_revise=idea.assumptions[0].assumption,
                next_question=f"What mechanism explains failure of: {idea.question}",
            ),
            quality_scores=idea.quality_scores,
        )
        gate = GateDecision(
            passed=idea.quality_scores.first_principles_derivation >= 3 and idea.quality_scores.falsifiability >= 3,
            reason="Baseline package scored using its generated certificate fields.",
            scores=idea.quality_scores,
        )
        return ResearchPackage(
            topic=topic,
            topic_summary=f"{self.name} research package for: {topic.topic}",
            first_principles_decomposition=FirstPrinciplesDecomposition(
                primitive_definitions=idea.primitive_definitions,
                assumptions=idea.assumptions,
            ),
            mechanism_model=mechanism,
            tensions=[tension],
            candidate_questions=[question],
            certificates=[certificate],
            gate_decisions=[gate],
            review=Review(
                summary="Baseline output converted to the common FirstResearch evaluation schema.",
                strengths=["Generated by the same LLM backend as FirstResearch"],
                weaknesses=["Not constrained by the full FirstResearch staged derivation process"],
                questions=[],
                missing_baselines=["firstresearch"],
                score=max(1, min(10, round(idea.quality_scores.average() * 2))),
                confidence=3,
                recommendation="borderline" if idea.quality_scores.average() >= 3 else "weak_reject",
            ),
            metadata={"baseline": self.name, "llm_driven": True},
        )


class CoScientistBaseline(Baseline):
    """A strong hypothesis-generation baseline inspired by AI co-scientist systems.

    The baseline uses staged generation, debate/ranking, and evolution, but outputs
    the same ResearchPackage schema as FirstResearch for fair benchmark scoring.
    """

    name = "co_scientist"

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def run(self, topic: ResearchTopic) -> ResearchPackage:
        pool = self._generate(topic)
        debate = self._debate(topic, pool)
        idea = self._evolve(topic, pool, debate)
        return self._idea_to_package(topic, idea, pool, debate)

    def _generate(self, topic: ResearchTopic) -> CoScientistHypothesisPool:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are the Generation agent in a strong AI co-scientist baseline. "
                "Generate diverse, non-overlapping scientific hypotheses for the topic. "
                "Focus on novelty, testability, and concrete experiments. Return strict JSON."
            ),
            user_payload={
                "_agent": "CoScientistGenerate",
                "topic": topic.model_dump(mode="json"),
                "_output_schema": CoScientistHypothesisPool.model_json_schema(),
            },
        )
        return CoScientistHypothesisPool.model_validate(raw)

    def _debate(self, topic: ResearchTopic, pool: CoScientistHypothesisPool) -> CoScientistDebateResult:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are the Reflection, Debate, and Ranking agents in an AI co-scientist baseline. "
                "Critique the hypotheses pairwise for novelty, mechanism clarity, falsifiability, "
                "and experiment feasibility. Rank them and choose the best candidate. Return strict JSON."
            ),
            user_payload={
                "_agent": "CoScientistDebate",
                "topic": topic.model_dump(mode="json"),
                "hypothesis_pool": pool.model_dump(mode="json"),
                "_output_schema": CoScientistDebateResult.model_json_schema(),
            },
        )
        return CoScientistDebateResult.model_validate(raw)

    def _evolve(
        self,
        topic: ResearchTopic,
        pool: CoScientistHypothesisPool,
        debate: CoScientistDebateResult,
    ) -> BaselineIdea:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are the Evolution agent in an AI co-scientist baseline. "
                "Refine the winning hypothesis using the debate feedback. Produce one final "
                "research package idea in the shared evaluation schema. Keep the final question "
                "tightly aligned to the original topic and include a concrete falsifying observation. "
                "Return strict JSON."
            ),
            user_payload={
                "_agent": "CoScientistEvolve",
                "topic": topic.model_dump(mode="json"),
                "hypothesis_pool": pool.model_dump(mode="json"),
                "debate": debate.model_dump(mode="json"),
                "_output_schema": BaselineIdea.model_json_schema(),
            },
        )
        return _validate_baseline_idea(raw)

    def _idea_to_package(
        self,
        topic: ResearchTopic,
        idea: BaselineIdea,
        pool: CoScientistHypothesisPool,
        debate: CoScientistDebateResult,
    ) -> ResearchPackage:
        # Reuse the common conversion logic without another LLM call.
        return _baseline_idea_to_package(
            topic=topic,
            idea=idea,
            name=self.name,
            metadata={
                "baseline": self.name,
                "llm_driven": True,
                "hypothesis_pool": pool.model_dump(mode="json"),
                "debate": debate.model_dump(mode="json"),
            },
        )


class AgentLabBaseline(Baseline):
    """A strong workflow baseline inspired by Agent Laboratory.

    It simulates literature-review, experiment-planning, professor critique, and
    final synthesis agents, then maps the result into the shared package schema.
    """

    name = "agent_lab"

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def run(self, topic: ResearchTopic) -> ResearchPackage:
        literature = self._literature(topic)
        experiment = self._experiment(topic, literature)
        critique = self._critique(topic, literature, experiment)
        idea = self._synthesize(topic, literature, experiment, critique)
        return _baseline_idea_to_package(
            topic=topic,
            idea=idea,
            name=self.name,
            metadata={
                "baseline": self.name,
                "llm_driven": True,
                "literature_plan": literature.model_dump(mode="json"),
                "experiment_plan": experiment.model_dump(mode="json"),
                "critique": critique.model_dump(mode="json"),
            },
        )

    def _literature(self, topic: ResearchTopic) -> AgentLabLiteraturePlan:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are the literature review agent in an Agent Laboratory-style baseline. "
                "Infer the closest related work claims, likely gaps, and baselines for the topic. "
                "Return strict JSON."
            ),
            user_payload={
                "_agent": "AgentLabLiterature",
                "topic": topic.model_dump(mode="json"),
                "_output_schema": AgentLabLiteraturePlan.model_json_schema(),
            },
        )
        return AgentLabLiteraturePlan.model_validate(raw)

    def _experiment(self, topic: ResearchTopic, literature: AgentLabLiteraturePlan) -> AgentLabExperimentPlan:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are the ML engineer and experiment planner in an Agent Laboratory-style baseline. "
                "Turn the literature gap into a concrete question, hypothesis, and runnable experiment. "
                "Return strict JSON."
            ),
            user_payload={
                "_agent": "AgentLabExperiment",
                "topic": topic.model_dump(mode="json"),
                "literature_plan": literature.model_dump(mode="json"),
                "_output_schema": AgentLabExperimentPlan.model_json_schema(),
            },
        )
        return AgentLabExperimentPlan.model_validate(raw)

    def _critique(
        self,
        topic: ResearchTopic,
        literature: AgentLabLiteraturePlan,
        experiment: AgentLabExperimentPlan,
    ) -> AgentLabCritique:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are the professor/reviewer agent in an Agent Laboratory-style baseline. "
                "Critique novelty, soundness, baselines, experiment feasibility, and overclaiming. "
                "Return strict JSON."
            ),
            user_payload={
                "_agent": "AgentLabCritique",
                "topic": topic.model_dump(mode="json"),
                "literature_plan": literature.model_dump(mode="json"),
                "experiment_plan": experiment.model_dump(mode="json"),
                "_output_schema": AgentLabCritique.model_json_schema(),
            },
        )
        return AgentLabCritique.model_validate(raw)

    def _synthesize(
        self,
        topic: ResearchTopic,
        literature: AgentLabLiteraturePlan,
        experiment: AgentLabExperimentPlan,
        critique: AgentLabCritique,
    ) -> BaselineIdea:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are the final synthesis agent in an Agent Laboratory-style baseline. "
                "Revise the research idea using the professor critique and produce one final "
                "package in the shared evaluation schema. Return strict JSON."
            ),
            user_payload={
                "_agent": "AgentLabSynthesize",
                "topic": topic.model_dump(mode="json"),
                "literature_plan": literature.model_dump(mode="json"),
                "experiment_plan": experiment.model_dump(mode="json"),
                "critique": critique.model_dump(mode="json"),
                "_output_schema": BaselineIdea.model_json_schema(),
            },
        )
        return _validate_baseline_idea(raw)


class TreeSearchScientistBaseline(Baseline):
    """An AI Scientist-v2-inspired baseline with branch search and expansion."""

    name = "tree_search_scientist"

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def run(self, topic: ResearchTopic) -> ResearchPackage:
        branches = self._branch(topic)
        selection = self._select(topic, branches)
        idea = self._expand(topic, branches, selection)
        return _baseline_idea_to_package(
            topic=topic,
            idea=idea,
            name=self.name,
            metadata={
                "baseline": self.name,
                "llm_driven": True,
                "branches": branches.model_dump(mode="json"),
                "selection": selection.model_dump(mode="json"),
            },
        )

    def _branch(self, topic: ResearchTopic) -> TreeSearchBranchSet:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are an AI Scientist-v2-style experiment manager. Generate a tree-search frontier "
                "of distinct research branches for the topic. Each branch should make a mechanism bet, "
                "a minimal experiment, and a likely failure mode explicit. Return strict JSON."
            ),
            user_payload={
                "_agent": "TreeSearchBranch",
                "topic": topic.model_dump(mode="json"),
                "_output_schema": TreeSearchBranchSet.model_json_schema(),
            },
        )
        return TreeSearchBranchSet.model_validate(raw)

    def _select(self, topic: ResearchTopic, branches: TreeSearchBranchSet) -> TreeSearchSelection:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are an AI Scientist-v2-style selection agent. Rank branches by novelty, "
                "mechanism clarity, falsifiability, and experiment feasibility. Select one branch "
                "for deeper expansion. Return strict JSON."
            ),
            user_payload={
                "_agent": "TreeSearchSelect",
                "topic": topic.model_dump(mode="json"),
                "branches": branches.model_dump(mode="json"),
                "_output_schema": TreeSearchSelection.model_json_schema(),
            },
        )
        return TreeSearchSelection.model_validate(raw)

    def _expand(
        self,
        topic: ResearchTopic,
        branches: TreeSearchBranchSet,
        selection: TreeSearchSelection,
    ) -> BaselineIdea:
        raw = self.llm_client.complete_json(
            system_prompt=(
                "You are an AI Scientist-v2-style expansion agent. Turn the selected branch into "
                "one polished research package idea in the shared evaluation schema. Prefer a novel "
                "mechanism boundary or threshold and a concrete falsifying observation. Return strict JSON."
            ),
            user_payload={
                "_agent": "TreeSearchExpand",
                "topic": topic.model_dump(mode="json"),
                "branches": branches.model_dump(mode="json"),
                "selection": selection.model_dump(mode="json"),
                "_output_schema": BaselineIdea.model_json_schema(),
            },
        )
        return _validate_baseline_idea(raw)


def _baseline_idea_to_package(
    *,
    topic: ResearchTopic,
    idea: BaselineIdea,
    name: str,
    metadata: dict[str, object],
) -> ResearchPackage:
    mechanism = MechanismModel(
        variables=[
            MechanismVariable(name="topic condition", role="input", description="The main condition or task distribution studied by the baseline."),
            MechanismVariable(name="proposed mechanism", role="mediator", description=idea.mechanism_summary),
            MechanismVariable(name="research quality", role="outcome", description="Whether the proposed question is falsifiable and experimentable."),
        ],
        causal_chain=[{"step": idea.mechanism_summary}],
        mechanism_summary=idea.mechanism_summary,
    )
    tension = Tension(
        tension_id=f"{name.upper()}-TENSION",
        statement=idea.tension,
        derived_from=[item.name for item in idea.primitive_definitions[:2]],
        why_it_matters=idea.novelty_note,
        what_existing_methods_may_miss="Baseline-generated novelty assessment.",
        testability=min(5, max(0, idea.quality_scores.experimentability)),
    )
    question = CandidateResearchQuestion(
        question=idea.question,
        question_type=idea.question_type,
        source_tension=tension.tension_id,
        expected_contribution=idea.novelty_note,
    )
    certificate = ResearchQuestionCertificate(
        topic=topic.topic,
        primitive_definitions=idea.primitive_definitions,
        first_principle_assumptions=idea.assumptions,
        mechanism_model=mechanism,
        tension_or_contradiction=tension,
        research_question=question,
        hypothesis=Hypothesis(statement=idea.hypothesis, predicted_effect=idea.predicted_effect),
        minimal_decisive_test=MinimalDecisiveTest(
            experiment=idea.experiment,
            independent_variables=idea.independent_variables,
            dependent_variables=idea.dependent_variables,
            controls=idea.controls,
            falsifying_observation=idea.falsifying_observation,
        ),
        expected_observations=ExpectedObservations(
            supports_hypothesis=idea.expected_support,
            rejects_hypothesis=idea.expected_reject,
        ),
        failure_update_rule=FailureUpdateRule(
            if_failed=idea.failure_update,
            assumption_to_revise=idea.assumptions[0].assumption,
            next_question=f"What mechanism explains failure of: {idea.question}",
        ),
        quality_scores=idea.quality_scores,
    )
    gate = GateDecision(
        passed=idea.quality_scores.first_principles_derivation >= 3 and idea.quality_scores.falsifiability >= 3,
        reason="Baseline package scored using its generated certificate fields.",
        scores=idea.quality_scores,
    )
    return ResearchPackage(
        topic=topic,
        topic_summary=f"{name} research package for: {topic.topic}",
        first_principles_decomposition=FirstPrinciplesDecomposition(
            primitive_definitions=idea.primitive_definitions,
            assumptions=idea.assumptions,
        ),
        mechanism_model=mechanism,
        tensions=[tension],
        candidate_questions=[question],
        certificates=[certificate],
        gate_decisions=[gate],
        review=Review(
            summary="Baseline output converted to the common FirstResearch evaluation schema.",
            strengths=["Generated by the same LLM backend as FirstResearch"],
            weaknesses=["Not constrained by the full FirstResearch staged derivation process"],
            questions=[],
            missing_baselines=["firstresearch"],
            score=max(1, min(10, round(idea.quality_scores.average() * 2))),
            confidence=3,
            recommendation="borderline" if idea.quality_scores.average() >= 3 else "weak_reject",
        ),
        metadata=metadata,
    )


class SimplePackageBaseline(Baseline):
    name = "simple"
    score_offset = 0
    question_prefix = "How can we improve"
    include_certificate = True

    def run(self, topic: ResearchTopic) -> ResearchPackage:
        decomposition = FirstPrinciplesDecomposition(
            primitive_definitions=[
                PrimitiveDefinition(name="system", definition="The agent or method being studied.", why_primitive="It is the unit of intervention."),
                PrimitiveDefinition(name="task", definition="A problem the system attempts to solve.", why_primitive="Performance is defined over tasks."),
                PrimitiveDefinition(name="metric", definition="A measurement of output quality.", why_primitive="Evaluation requires measurement."),
            ],
            assumptions=[
                FirstPrincipleAssumption(assumption="Better methods improve metrics.", rationale="The baseline frames research as improvement.", possible_failure="Metric gains may not explain mechanisms."),
                FirstPrincipleAssumption(assumption="The topic has an open gap.", rationale="Research ideation assumes missing knowledge.", possible_failure="The gap may be already answered."),
            ],
        )
        mechanism = MechanismModel(
            variables=[
                MechanismVariable(name="method choice", role="input", description="The proposed agent method."),
                MechanismVariable(name="score", role="outcome", description="Measured benchmark outcome."),
            ],
            causal_chain=[{"step": "Method choice changes benchmark score."}],
            mechanism_summary="A generic method-improvement mechanism with limited causal detail.",
        )
        tension = Tension(
            tension_id="BASE-TENSION",
            statement="The topic may need better performance, but the mechanism is under-specified.",
            derived_from=["system", "metric"],
            why_it_matters="Weak mechanisms make experiments less decisive.",
            what_existing_methods_may_miss="They may optimize a metric without explaining failure.",
            testability=3,
        )
        question = CandidateResearchQuestion(
            question=f"{self.question_prefix} {topic.topic.lower()}?",
            question_type="algorithmic",
            source_tension=tension.tension_id,
            expected_contribution="A plausible improvement direction.",
        )
        scores = QualityScores(
            first_principles_derivation=max(0, 2 + self.score_offset),
            falsifiability=max(0, 2 + self.score_offset),
            mechanism_clarity=max(0, 2 + self.score_offset),
            novelty=max(0, 2 + self.score_offset),
            experimentability=max(0, 3 + self.score_offset),
        )
        package = ResearchPackage(
            topic=topic,
            topic_summary=f"Baseline package for: {topic.topic}",
            first_principles_decomposition=decomposition,
            mechanism_model=mechanism,
            tensions=[tension],
            candidate_questions=[question],
            metadata={"baseline": self.name},
        )
        if self.include_certificate:
            certificate = ResearchQuestionCertificate(
                topic=topic.topic,
                primitive_definitions=decomposition.primitive_definitions,
                first_principle_assumptions=decomposition.assumptions,
                mechanism_model=mechanism,
                tension_or_contradiction=tension,
                research_question=question,
                hypothesis=Hypothesis(statement="The proposed improvement increases benchmark score.", predicted_effect="Higher score than a basic baseline."),
                minimal_decisive_test=MinimalDecisiveTest(
                    experiment="Compare the proposed method to a baseline on a small topic set.",
                    independent_variables=["method"],
                    dependent_variables=["benchmark score"],
                    controls=["same evaluator"],
                    falsifying_observation="The proposed method does not improve the benchmark score.",
                ),
                expected_observations=ExpectedObservations(supports_hypothesis=["Higher score"], rejects_hypothesis=["No score gain"]),
                failure_update_rule=FailureUpdateRule(if_failed="Try a different method.", assumption_to_revise="Better methods improve metrics.", next_question="Which metric better captures the topic?"),
                quality_scores=scores,
            )
            package.certificates = [certificate]
            package.gate_decisions = [GateDecision(passed=scores.falsifiability >= 3 and scores.first_principles_derivation >= 3, reason="Baseline deterministic gate.", scores=scores)]
        package.review = Review(
            summary="Baseline output is plausible but less mechanistically grounded.",
            strengths=["Simple", "Runnable"],
            weaknesses=["Weak first-principles trace", "Generic experiment"],
            questions=[],
            missing_baselines=["firstresearch"],
            score=max(1, min(10, int(scores.average() * 2))),
            confidence=3,
            recommendation="borderline" if scores.average() >= 3 else "weak_reject",
        )
        return package


class SinglePromptBaseline(SimplePackageBaseline):
    name = "single_prompt"
    question_prefix = "What is a promising research direction for"


class LiteratureFirstBaseline(SimplePackageBaseline):
    name = "literature_first"
    score_offset = 1
    question_prefix = "What literature gap remains for"


class GenericMultiAgentBaseline(SimplePackageBaseline):
    name = "generic_multi_agent"
    score_offset = 1
    question_prefix = "How should a multi-agent research assistant address"


class NoCertificateAblation(SimplePackageBaseline):
    name = "no_certificate_ablation"
    include_certificate = False


class NoGateRepairAblation(FirstResearchAblation):
    name = "no_gate_repair_ablation"
    ablation_name = "gate_repair_removed"
    orchestrator_options = {"enable_gate_repair": False}


class NoNoveltyBoundaryRepairAblation(FirstResearchAblation):
    name = "no_novelty_boundary_repair_ablation"
    ablation_name = "novelty_boundary_repair_removed"
    orchestrator_options = {"require_novelty_boundary": False}


class NoMechanismModelAblation(FirstResearchAblation):
    name = "no_mechanism_model_ablation"
    ablation_name = "mechanism_builder_removed"
    orchestrator_options = {"enable_mechanism_builder": False}


class CertificateOnlyAblation(FirstResearchAblation):
    name = "certificate_only_ablation"
    ablation_name = "reviewer_and_meta_removed"
    orchestrator_options = {"enable_reviewer": False, "enable_meta_researcher": False}


class NoSelfImprovementAblation(FirstResearchAblation):
    name = "no_self_improvement_ablation"
    ablation_name = "self_improvement_removed"
    orchestrator_options = {"enable_meta_researcher": False}


class FirstResearchDebateCombo(FirstResearchAblation):
    name = "firstresearch_debate_combo"
    ablation_name = "co_scientist_debate_refinement_added"
    orchestrator_options = {"enable_question_debate_refinement": True}


SINGLE_PROMPT_BASELINE_PROMPT = """You are a standard one-shot auto-research assistant.
Given the topic, propose one research question, hypothesis, and minimal experiment.
Do not use a staged first-principles certificate process; answer in the usual direct ideation style."""

LITERATURE_FIRST_BASELINE_PROMPT = """You are a literature-first auto-research assistant.
Start from likely related work, infer a research gap, then propose one research question,
hypothesis, and minimal experiment. The output must still fill the requested JSON fields."""

GENERIC_MULTI_AGENT_BASELINE_PROMPT = """You are simulating a generic multi-agent research pipeline.
Combine perspectives from a planner, literature reviewer, method designer, and critic, then return
one consolidated research question, hypothesis, and minimal experiment."""


def get_baselines(
    names: list[str] | None = None,
    *,
    llm_client: LLMClient | None = None,
    llm_baselines: bool = False,
) -> list[Baseline]:
    registry: dict[str, Baseline] = {
        "firstresearch": FirstResearchSystem(llm_client),
        "single_prompt": SinglePromptBaseline(),
        "literature_first": LiteratureFirstBaseline(),
        "generic_multi_agent": GenericMultiAgentBaseline(),
        "co_scientist": CoScientistBaseline(llm_client or MockLLMClient()),
        "agent_lab": AgentLabBaseline(llm_client or MockLLMClient()),
        "tree_search_scientist": TreeSearchScientistBaseline(llm_client or MockLLMClient()),
        "no_certificate_ablation": NoCertificateAblation(),
        "no_gate_repair_ablation": NoGateRepairAblation(llm_client),
        "no_novelty_boundary_repair_ablation": NoNoveltyBoundaryRepairAblation(llm_client),
        "no_mechanism_model_ablation": NoMechanismModelAblation(llm_client),
        "certificate_only_ablation": CertificateOnlyAblation(llm_client),
        "no_self_improvement_ablation": NoSelfImprovementAblation(llm_client),
        "firstresearch_debate_combo": FirstResearchDebateCombo(llm_client),
    }
    if llm_baselines:
        if llm_client is None:
            llm_client = MockLLMClient()
        registry.update(
            {
                "single_prompt": PromptDrivenBaseline(
                    name="single_prompt",
                    system_prompt=SINGLE_PROMPT_BASELINE_PROMPT,
                    llm_client=llm_client,
                ),
                "literature_first": PromptDrivenBaseline(
                    name="literature_first",
                    system_prompt=LITERATURE_FIRST_BASELINE_PROMPT,
                    llm_client=llm_client,
                ),
                "generic_multi_agent": PromptDrivenBaseline(
                    name="generic_multi_agent",
                    system_prompt=GENERIC_MULTI_AGENT_BASELINE_PROMPT,
                    llm_client=llm_client,
                ),
                "co_scientist": CoScientistBaseline(llm_client),
                "agent_lab": AgentLabBaseline(llm_client),
                "tree_search_scientist": TreeSearchScientistBaseline(llm_client),
            }
        )
    if not names:
        names = ["firstresearch", "single_prompt", "literature_first", "generic_multi_agent"]
    return [registry[name] for name in names]
