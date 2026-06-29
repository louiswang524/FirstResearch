import pytest

from firstresearch.orchestrator import ResearchOrchestrator
from firstresearch.schemas import ResearchQuestionCertificate, ResearchTopic


def test_orchestrator_produces_valid_certificate():
    package = ResearchOrchestrator().run(ResearchTopic(topic="Agent skill discovery"))
    assert package.certificates
    certificate = package.certificates[0]
    assert len(certificate.primitive_definitions) >= 3
    assert certificate.minimal_decisive_test.falsifying_observation
    assert package.gate_decisions[0].passed


def test_certificate_requires_question_to_reference_tension():
    package = ResearchOrchestrator().run(ResearchTopic(topic="Agent skill discovery"))
    data = package.certificates[0].model_dump(mode="json")
    data["research_question"]["source_tension"] = "WRONG"
    with pytest.raises(ValueError, match="source tension"):
        ResearchQuestionCertificate.model_validate(data)

