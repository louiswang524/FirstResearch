from pathlib import Path

from pydantic import BaseModel

from firstresearch.agents.base import BaseAgent
from firstresearch.utils.llm import MockLLMClient


class InputModel(BaseModel):
    value: str


class OutputModel(BaseModel):
    result: str


def test_base_agent_uses_mock_response(tmp_path: Path):
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Return JSON.", encoding="utf-8")
    client = MockLLMClient({"EchoAgent": {"result": "ok"}})
    agent = BaseAgent(
        name="EchoAgent",
        prompt_path=prompt,
        input_schema=InputModel,
        output_schema=OutputModel,
        llm_client=client,
    )
    assert agent.run(InputModel(value="hello")).result == "ok"
    assert client.calls[0]["agent"] == "EchoAgent"

