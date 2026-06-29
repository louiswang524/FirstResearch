from __future__ import annotations

from pathlib import Path
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from firstresearch.utils.llm import LLMClient

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(Generic[InputT, OutputT]):
    name: str
    prompt_path: Path
    input_schema: type[InputT]
    output_schema: type[OutputT]

    def __init__(
        self,
        *,
        name: str,
        prompt_path: Path,
        input_schema: type[InputT],
        output_schema: type[OutputT],
        llm_client: LLMClient,
    ) -> None:
        self.name = name
        self.prompt_path = prompt_path
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.llm_client = llm_client

    @property
    def prompt_template(self) -> str:
        return self.prompt_path.read_text(encoding="utf-8")

    def run(self, input_obj: InputT) -> OutputT:
        payload = input_obj.model_dump(mode="json")
        payload["_agent"] = self.name
        payload["_output_schema"] = self.output_schema.model_json_schema()
        raw = self.llm_client.complete_json(system_prompt=self.prompt_template, user_payload=payload)
        return self.output_schema.model_validate(raw)


class DictInput(BaseModel):
    payload: dict[str, Any]
