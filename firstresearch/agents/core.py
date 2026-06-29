from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from firstresearch.agents.base import BaseAgent
from firstresearch.schemas import (
    CandidateResearchQuestion,
    ExperimentPlan,
    ExpectedObservations,
    FailureUpdateRule,
    FirstPrinciplesDecomposition,
    GateDecision,
    Hypothesis,
    MechanismModel,
    MinimalDecisiveTest,
    QualityScores,
    ResearchPackage,
    ResearchQuestionCertificate,
    ResearchTopic,
    Review,
    SelfImprovementRecord,
    Tension,
)
from firstresearch.utils.llm import LLMClient

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


class TopicInput(BaseModel):
    topic: ResearchTopic


class MechanismInput(BaseModel):
    topic: ResearchTopic
    decomposition: FirstPrinciplesDecomposition


class TensionInput(BaseModel):
    decomposition: FirstPrinciplesDecomposition
    mechanism_model: MechanismModel


class TensionsOutput(BaseModel):
    tensions: list[Tension] = Field(min_length=1)


class QuestionInput(BaseModel):
    tensions: list[Tension] = Field(min_length=1)
    mechanism_model: MechanismModel


class QuestionDebateInput(BaseModel):
    topic: ResearchTopic
    decomposition: FirstPrinciplesDecomposition
    mechanism_model: MechanismModel
    tensions: list[Tension] = Field(min_length=1)
    candidate_questions: list[CandidateResearchQuestion] = Field(min_length=1)


class QuestionsOutput(BaseModel):
    candidate_questions: list[CandidateResearchQuestion] = Field(min_length=1)


class CertificateInput(BaseModel):
    topic: ResearchTopic
    decomposition: FirstPrinciplesDecomposition
    mechanism_model: MechanismModel
    tension: Tension
    question: CandidateResearchQuestion


class CertificateDetails(BaseModel):
    hypothesis: Hypothesis
    minimal_decisive_test: MinimalDecisiveTest
    expected_observations: ExpectedObservations
    failure_update_rule: FailureUpdateRule
    quality_scores: QualityScores


class CertificateRepairInput(BaseModel):
    topic: ResearchTopic
    certificate: ResearchQuestionCertificate
    gate_decision: GateDecision


class CertificateRepairOutput(BaseModel):
    research_question: CandidateResearchQuestion
    hypothesis: Hypothesis
    minimal_decisive_test: MinimalDecisiveTest
    expected_observations: ExpectedObservations
    failure_update_rule: FailureUpdateRule
    quality_scores: QualityScores


class FirstPrinciplesDecomposer(BaseAgent[TopicInput, FirstPrinciplesDecomposition]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="FirstPrinciplesDecomposer",
            prompt_path=PROMPT_DIR / "decomposer.md",
            input_schema=TopicInput,
            output_schema=FirstPrinciplesDecomposition,
            llm_client=llm_client,
        )


class MechanismBuilder(BaseAgent[MechanismInput, MechanismModel]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="MechanismBuilder",
            prompt_path=PROMPT_DIR / "mechanism_builder.md",
            input_schema=MechanismInput,
            output_schema=MechanismModel,
            llm_client=llm_client,
        )


class TensionFinder(BaseAgent[TensionInput, TensionsOutput]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="TensionFinder",
            prompt_path=PROMPT_DIR / "tension_finder.md",
            input_schema=TensionInput,
            output_schema=TensionsOutput,
            llm_client=llm_client,
        )


class QuestionGenerator(BaseAgent[QuestionInput, QuestionsOutput]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="QuestionGenerator",
            prompt_path=PROMPT_DIR / "question_generator.md",
            input_schema=QuestionInput,
            output_schema=QuestionsOutput,
            llm_client=llm_client,
        )


class QuestionDebateRefiner(BaseAgent[QuestionDebateInput, QuestionsOutput]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="QuestionDebateRefiner",
            prompt_path=PROMPT_DIR / "question_debate_refiner.md",
            input_schema=QuestionDebateInput,
            output_schema=QuestionsOutput,
            llm_client=llm_client,
        )


class CertificateBuilder(BaseAgent[CertificateInput, CertificateDetails]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="CertificateBuilder",
            prompt_path=PROMPT_DIR / "certificate_builder.md",
            input_schema=CertificateInput,
            output_schema=CertificateDetails,
            llm_client=llm_client,
        )

    def build(self, input_obj: CertificateInput) -> ResearchQuestionCertificate:
        details = self.run(input_obj)
        question = input_obj.question
        if question.source_tension != input_obj.tension.tension_id:
            question = question.model_copy(update={"source_tension": input_obj.tension.tension_id})
        return ResearchQuestionCertificate(
            topic=input_obj.topic.topic,
            primitive_definitions=input_obj.decomposition.primitive_definitions,
            first_principle_assumptions=input_obj.decomposition.assumptions,
            mechanism_model=input_obj.mechanism_model,
            tension_or_contradiction=input_obj.tension,
            research_question=question,
            hypothesis=details.hypothesis,
            minimal_decisive_test=details.minimal_decisive_test,
            expected_observations=details.expected_observations,
            failure_update_rule=details.failure_update_rule,
            quality_scores=details.quality_scores,
        )


class CertificateRepairer(BaseAgent[CertificateRepairInput, CertificateRepairOutput]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="CertificateRepairer",
            prompt_path=PROMPT_DIR / "certificate_repairer.md",
            input_schema=CertificateRepairInput,
            output_schema=CertificateRepairOutput,
            llm_client=llm_client,
        )

    def repair(self, input_obj: CertificateRepairInput) -> ResearchQuestionCertificate:
        repaired = self.run(input_obj)
        source_tension = input_obj.certificate.tension_or_contradiction.tension_id
        question = repaired.research_question
        if question.source_tension != source_tension:
            question = question.model_copy(update={"source_tension": source_tension})
        return input_obj.certificate.model_copy(
            update={
                "research_question": question,
                "hypothesis": repaired.hypothesis,
                "minimal_decisive_test": repaired.minimal_decisive_test,
                "expected_observations": repaired.expected_observations,
                "failure_update_rule": repaired.failure_update_rule,
                "quality_scores": repaired.quality_scores,
            }
        )


class GateAgent:
    name = "GateAgent"

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        *,
        require_competitive_novelty: bool = True,
        require_boundary_signal: bool = True,
    ) -> None:
        self.llm_client = llm_client
        self.require_competitive_novelty = require_competitive_novelty
        self.require_boundary_signal = require_boundary_signal

    def run(self, certificate: ResearchQuestionCertificate) -> GateDecision:
        blocking_suggestions: list[str] = []
        improvement_suggestions: list[str] = []
        scores = certificate.quality_scores
        if not certificate.minimal_decisive_test.falsifying_observation.strip():
            blocking_suggestions.append("Add a concrete falsifying observation.")
        if not certificate.mechanism_model.mechanism_summary.strip():
            blocking_suggestions.append("Add a mechanism summary.")
        if scores.first_principles_derivation < 3:
            blocking_suggestions.append("Strengthen primitive-to-question derivation.")
        if scores.falsifiability < 3:
            blocking_suggestions.append("Make the hypothesis and test more falsifiable.")
        if scores.first_principles_derivation < 4:
            improvement_suggestions.append("Improve primitive-to-question traceability to at least 4/5.")
        if scores.mechanism_clarity < 4:
            improvement_suggestions.append("Make the mechanism variables and causal chain more explicit.")
        if self.require_competitive_novelty and scores.novelty < 5:
            improvement_suggestions.append("Increase novelty to a competitive 5/5 by isolating a sharper boundary condition, threshold, phase transition, or mechanism interaction.")
        if self.require_boundary_signal and not _has_mechanism_boundary_signal(certificate.research_question.question, certificate.hypothesis.statement):
            improvement_suggestions.append("State the novel mechanism boundary explicitly, such as a threshold, interaction, failure regime, or nonlinear tradeoff.")
        if scores.experimentability < 4:
            improvement_suggestions.append("Make the minimal experiment more concrete and resource-bounded.")
        if _topic_overlap(certificate.topic, certificate.research_question.question) < 0.25:
            improvement_suggestions.append("Tighten topic adherence; the question should preserve the user's original topic terms.")
        passed = not blocking_suggestions
        return GateDecision(
            passed=passed,
            reason="Passed deterministic gate rules." if passed else "Failed deterministic gate rules.",
            repair_suggestions=blocking_suggestions + improvement_suggestions,
            scores=scores,
        )

    def should_repair(self, decision: GateDecision) -> bool:
        return bool(decision.repair_suggestions)


def _topic_overlap(topic: str, question: str) -> float:
    topic_terms = _content_terms(topic)
    question_terms = _content_terms(question)
    if not topic_terms:
        return 1.0
    return len(topic_terms & question_terms) / len(topic_terms)


def _content_terms(text: str) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "are",
        "can",
        "does",
        "do",
        "how",
        "in",
        "is",
        "of",
        "or",
        "rather",
        "should",
        "than",
        "the",
        "to",
        "what",
        "when",
    }
    terms = set()
    for raw in text.lower().replace("?", "").replace("-", " ").split():
        term = raw.strip(".,:;()[]{}\"'")
        if len(term) <= 2 or term in stopwords:
            continue
        if term.endswith("ing") and len(term) > 5:
            term = term[:-3]
        if term.endswith("s") and len(term) > 3:
            term = term[:-1]
        terms.add(term)
    return terms


def _has_mechanism_boundary_signal(question: str, hypothesis: str) -> bool:
    text = f"{question} {hypothesis}".lower()
    signals = {
        "boundary",
        "threshold",
        "phase",
        "transition",
        "interaction",
        "nonlinear",
        "regime",
        "failure mode",
        "inflection",
        "tradeoff",
        "cost ratio",
        "interference",
    }
    return any(signal in text for signal in signals)


class ExperimentInput(BaseModel):
    certificate: ResearchQuestionCertificate


class ExperimentDesigner(BaseAgent[ExperimentInput, ExperimentPlan]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="ExperimentDesigner",
            prompt_path=PROMPT_DIR / "experiment_designer.md",
            input_schema=ExperimentInput,
            output_schema=ExperimentPlan,
            llm_client=llm_client,
        )


class ReviewerAgent(BaseAgent[ResearchPackage, Review]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="ReviewerAgent",
            prompt_path=PROMPT_DIR / "reviewer.md",
            input_schema=ResearchPackage,
            output_schema=Review,
            llm_client=llm_client,
        )


class MetaResearcher(BaseAgent[ResearchPackage, SelfImprovementRecord]):
    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__(
            name="MetaResearcher",
            prompt_path=PROMPT_DIR / "meta_researcher.md",
            input_schema=ResearchPackage,
            output_schema=SelfImprovementRecord,
            llm_client=llm_client,
        )
