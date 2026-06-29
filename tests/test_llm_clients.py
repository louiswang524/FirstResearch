from __future__ import annotations

from typing import Any

from firstresearch.utils.llm import GeminiClient, build_llm_client, simplify_json_schema


class RecordingGeminiClient(GeminiClient):
    def __init__(self) -> None:
        super().__init__(api_key="test-key", model="gemini-test", temperature=0.0, max_tokens=123)
        self.body: dict[str, Any] | None = None

    def _post_json(self, body: dict[str, Any]) -> dict[str, Any]:
        self.body = body
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"score": 5, "rationale": "valid json"}',
                            }
                        ]
                    }
                }
            ]
        }


def test_gemini_client_requests_json_mode():
    client = RecordingGeminiClient()
    result = client.complete_json(
        system_prompt="Judge strictly.",
        user_payload={
            "_agent": "Judge",
            "_output_schema": {
                "$defs": {
                    "Score": {
                        "type": "object",
                        "title": "Score",
                        "properties": {"value": {"type": "integer", "minimum": 0, "maximum": 5}},
                        "required": ["value"],
                    }
                },
                "type": "object",
                "properties": {"score": {"$ref": "#/$defs/Score"}, "rationale": {"type": "string"}},
                "required": ["score", "rationale"],
            },
        },
    )

    assert result == {"score": 5, "rationale": "valid json"}
    assert client.body is not None
    assert client.body["generationConfig"]["responseMimeType"] == "application/json"
    assert client.body["generationConfig"]["temperature"] == 0.0
    assert client.body["generationConfig"]["maxOutputTokens"] == 123
    assert client.body["generationConfig"]["responseSchema"]["properties"]["score"]["type"] == "object"
    assert client.body["systemInstruction"]["parts"][0]["text"] == "Judge strictly."


def test_build_llm_client_accepts_gemini_env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")

    client = build_llm_client("gemini")

    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-test"


def test_simplify_json_schema_inlines_local_refs():
    schema = {
        "$defs": {
            "Nested": {
                "title": "Nested",
                "type": "object",
                "properties": {"value": {"title": "Value", "type": "integer"}},
                "required": ["value"],
            }
        },
        "title": "Root",
        "type": "object",
        "properties": {"nested": {"$ref": "#/$defs/Nested"}},
        "required": ["nested"],
    }

    simplified = simplify_json_schema(schema)

    assert "$defs" not in simplified
    assert "title" not in simplified
    assert simplified["properties"]["nested"]["type"] == "object"
    assert simplified["properties"]["nested"]["properties"]["value"] == {"type": "integer"}
