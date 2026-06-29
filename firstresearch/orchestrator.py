from __future__ import annotations

from firstresearch.agents.core import (
    CertificateBuilder,
    CertificateInput,
    CertificateRepairer,
    CertificateRepairInput,
    ExperimentDesigner,
    ExperimentInput,
    FirstPrinciplesDecomposer,
    GateAgent,
    MechanismBuilder,
    MechanismInput,
    MetaResearcher,
    QuestionDebateInput,
    QuestionDebateRefiner,
    QuestionGenerator,
    QuestionInput,
    ReviewerAgent,
    TensionFinder,
    TensionInput,
    TopicInput,
)
from firstresearch.schemas import ResearchPackage, ResearchTopic
from firstresearch.schemas import MechanismModel, MechanismVariable, Tension
from firstresearch.utils.llm import LLMClient, MockLLMClient


class ResearchOrchestrator:
    def __init__(
        self,
        llm_client: LLMClient | None = None,
        *,
        enable_gate_repair: bool = True,
        require_novelty_boundary: bool = True,
        enable_mechanism_builder: bool = True,
        enable_reviewer: bool = True,
        enable_meta_researcher: bool = True,
        enable_question_debate_refinement: bool = False,
    ) -> None:
        self.llm_client = llm_client or MockLLMClient()
        self.enable_gate_repair = enable_gate_repair
        self.enable_mechanism_builder = enable_mechanism_builder
        self.enable_reviewer = enable_reviewer
        self.enable_meta_researcher = enable_meta_researcher
        self.enable_question_debate_refinement = enable_question_debate_refinement
        self.decomposer = FirstPrinciplesDecomposer(self.llm_client)
        self.mechanism_builder = MechanismBuilder(self.llm_client)
        self.tension_finder = TensionFinder(self.llm_client)
        self.question_generator = QuestionGenerator(self.llm_client)
        self.question_debate_refiner = QuestionDebateRefiner(self.llm_client)
        self.certificate_builder = CertificateBuilder(self.llm_client)
        self.certificate_repairer = CertificateRepairer(self.llm_client)
        self.gate = GateAgent(
            self.llm_client,
            require_competitive_novelty=require_novelty_boundary,
            require_boundary_signal=require_novelty_boundary,
        )
        self.experiment_designer = ExperimentDesigner(self.llm_client)
        self.reviewer = ReviewerAgent(self.llm_client)
        self.meta_researcher = MetaResearcher(self.llm_client)

    def run(self, topic: ResearchTopic) -> ResearchPackage:
        decomposition = self.decomposer.run(TopicInput(topic=topic))
        if self.enable_mechanism_builder:
            mechanism = self.mechanism_builder.run(MechanismInput(topic=topic, decomposition=decomposition))
        else:
            mechanism = _placeholder_mechanism(topic)
        tensions = self.tension_finder.run(TensionInput(decomposition=decomposition, mechanism_model=mechanism)).tensions
        questions = self.question_generator.run(QuestionInput(tensions=tensions, mechanism_model=mechanism)).candidate_questions
        if self.enable_question_debate_refinement:
            questions = self.question_debate_refiner.run(
                QuestionDebateInput(
                    topic=topic,
                    decomposition=decomposition,
                    mechanism_model=mechanism,
                    tensions=tensions,
                    candidate_questions=questions,
                )
            ).candidate_questions

        certificates = []
        gate_decisions = []
        experiment_plans = []
        repair_records = []

        tensions_by_id = {tension.tension_id: tension for tension in tensions}
        for question in questions:
            tension = tensions_by_id.get(question.source_tension, tensions[0])
            certificate = self.certificate_builder.build(
                CertificateInput(
                    topic=topic,
                    decomposition=decomposition,
                    mechanism_model=mechanism,
                    tension=tension,
                    question=question,
                )
            )
            certificates.append(certificate)
            decision = self.gate.run(certificate)
            if self.enable_gate_repair and self.gate.should_repair(decision):
                original_suggestions = list(decision.repair_suggestions)
                certificate = self.certificate_repairer.repair(
                    CertificateRepairInput(topic=topic, certificate=certificate, gate_decision=decision)
                )
                decision = self.gate.run(certificate)
                certificate = certificate.model_copy()
                certificate.quality_scores = decision.scores
                certificates[-1] = certificate
                repair_records.append(
                    {
                        "question": certificate.research_question.question,
                        "original_suggestions": original_suggestions,
                        "remaining_suggestions": list(decision.repair_suggestions),
                    }
                )
            gate_decisions.append(decision)
            if decision.passed:
                experiment_plans.append(self.experiment_designer.run(ExperimentInput(certificate=certificate)))

        if certificates:
            order = sorted(
                range(len(certificates)),
                key=lambda index: _certificate_rank_key(certificates[index]),
                reverse=True,
            )
            certificates = [certificates[index] for index in order]
            gate_decisions = [gate_decisions[index] for index in order]

        package = ResearchPackage(
            topic=topic,
            topic_summary=f"First-principles research package for: {topic.topic}",
            first_principles_decomposition=decomposition,
            mechanism_model=mechanism,
            tensions=tensions,
            candidate_questions=questions,
            certificates=certificates,
            gate_decisions=gate_decisions,
            experiment_plans=experiment_plans,
            metadata={
                "llm_client": type(self.llm_client).__name__,
                "gate_repair_count": len(repair_records),
                "gate_repairs": repair_records,
                "ablation_settings": {
                    "enable_gate_repair": self.enable_gate_repair,
                    "require_novelty_boundary": self.gate.require_boundary_signal,
                    "enable_mechanism_builder": self.enable_mechanism_builder,
                    "enable_reviewer": self.enable_reviewer,
                    "enable_meta_researcher": self.enable_meta_researcher,
                    "enable_question_debate_refinement": self.enable_question_debate_refinement,
                },
            },
        )
        if self.enable_reviewer:
            package.review = self.reviewer.run(package)
        if self.enable_meta_researcher:
            package.self_improvement_update = self.meta_researcher.run(package)
        return package


def _certificate_rank_key(certificate):
    scores = certificate.quality_scores
    return (
        scores.average(),
        scores.novelty,
        scores.mechanism_clarity,
        scores.falsifiability,
        scores.experimentability,
        scores.first_principles_derivation,
    )


def _placeholder_mechanism(topic: ResearchTopic) -> MechanismModel:
    return MechanismModel(
        variables=[
            MechanismVariable(
                name="topic condition",
                role="input",
                description=f"The observed condition in {topic.topic}.",
            ),
            MechanismVariable(
                name="research outcome",
                role="outcome",
                description="The measured outcome or failure mode proposed by the research question.",
            ),
        ],
        causal_chain=[{"step": "The ablation omits explicit mechanism construction and passes only a generic topic-to-outcome relation downstream."}],
        mechanism_summary="Mechanism-builder ablation: no explicit mechanism model was constructed before tension finding.",
    )
