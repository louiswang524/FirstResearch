from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Any


class LLMClient(ABC):
    @abstractmethod
    def complete_json(self, *, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON-compatible object for an agent call."""


class LLMClientError(RuntimeError):
    """Raised when an LLM provider cannot return valid JSON."""


class OpenAICompatibleClient(LLMClient):
    """Minimal OpenAI Chat Completions compatible JSON client.

    This avoids a hard SDK dependency and works with DeepSeek's OpenAI-format API.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout_seconds: int = 120,
        retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    def complete_json(self, *, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Return only valid JSON. Do not wrap it in Markdown. "
            "The JSON must match the requested schema.\n\n"
            f"Input:\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}"
        )
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                data = self._post_json("/chat/completions", body)
                content = data["choices"][0]["message"]["content"]
                return parse_json_object(content)
            except Exception as exc:  # provider errors are retried once or twice
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1.5 * (attempt + 1))
        raise LLMClientError(f"LLM request failed after retries: {last_error}") from last_error

    def _post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"HTTP {exc.code} from LLM provider: {details}") from exc


class DeepSeekClient(OpenAICompatibleClient):
    def __init__(
        self,
        *,
        api_key: str,
        model: str = "deepseek-v4-flash",
        base_url: str = "https://api.deepseek.com",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout_seconds: int = 120,
        retries: int = 2,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout_seconds=timeout_seconds,
            retries=retries,
        )


class GeminiClient(LLMClient):
    """Minimal Gemini generateContent JSON client.

    Uses the Gemini Developer API directly so the benchmark runner does not need
    an SDK dependency.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.5-flash",
        base_url: str = "https://generativelanguage.googleapis.com/v1beta",
        temperature: float = 0.2,
        max_tokens: int = 4096,
        timeout_seconds: int = 120,
        retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    def complete_json(self, *, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        prompt = (
            "Return only valid JSON. Do not wrap it in Markdown. "
            "The JSON must match the requested schema.\n\n"
            f"Input:\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}"
        )
        body = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
                "responseMimeType": "application/json",
            },
        }
        output_schema = user_payload.get("_output_schema")
        if isinstance(output_schema, dict):
            body["generationConfig"]["responseSchema"] = simplify_json_schema(output_schema)
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                data = self._post_json(body)
                parts = data["candidates"][0]["content"]["parts"]
                content = "".join(part.get("text", "") for part in parts)
                return parse_json_object(content)
            except Exception as exc:  # provider errors are retried once or twice
                last_error = exc
                if attempt < self.retries:
                    time.sleep(1.5 * (attempt + 1))
        raise LLMClientError(f"Gemini request failed after retries: {last_error}") from last_error

    def _post_json(self, body: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        request = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"HTTP {exc.code} from Gemini: {details}") from exc


class MockLLMClient(LLMClient):
    """Deterministic local client for tests and demos."""

    def __init__(self, responses: dict[str, dict[str, Any]] | None = None):
        self.responses = responses or {}
        self.calls: list[dict[str, Any]] = []

    def complete_json(self, *, system_prompt: str, user_payload: dict[str, Any]) -> dict[str, Any]:
        agent_name = str(user_payload.get("_agent", ""))
        self.calls.append({"agent": agent_name, "payload": user_payload})
        if agent_name in self.responses:
            return self.responses[agent_name]
        return default_response(agent_name, user_payload)


def build_llm_client(
    provider: str = "mock",
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> LLMClient:
    provider = provider.lower()
    if provider == "mock":
        return MockLLMClient()
    if provider == "deepseek":
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise LLMClientError("Set DEEPSEEK_API_KEY before using --llm deepseek.")
        return DeepSeekClient(
            api_key=api_key,
            model=model or os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
            base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise LLMClientError("Set GEMINI_API_KEY before using --llm gemini.")
        return GeminiClient(
            api_key=api_key,
            model=model or os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
            base_url=os.environ.get("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta"),
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "openai_compatible":
        api_key = os.environ.get("OPENAI_COMPAT_API_KEY")
        base_url = os.environ.get("OPENAI_COMPAT_BASE_URL")
        if not api_key or not base_url:
            raise LLMClientError("Set OPENAI_COMPAT_API_KEY and OPENAI_COMPAT_BASE_URL before using --llm openai_compatible.")
        return OpenAICompatibleClient(
            api_key=api_key,
            base_url=base_url,
            model=model or os.environ.get("OPENAI_COMPAT_MODEL", "default"),
            temperature=temperature,
            max_tokens=max_tokens,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")


def parse_json_object(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            raise
        value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("LLM output must be a JSON object")
    return value


def simplify_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline local refs and keep the subset Gemini needs for structured output."""

    defs = schema.get("$defs", {})

    def visit(node: Any) -> Any:
        if isinstance(node, list):
            return [visit(item) for item in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            ref = node["$ref"]
            prefix = "#/$defs/"
            if isinstance(ref, str) and ref.startswith(prefix):
                return visit(defs[ref.removeprefix(prefix)])
        kept: dict[str, Any] = {}
        for key, value in node.items():
            if key in {"$defs", "$ref", "title", "description"}:
                continue
            kept[key] = visit(value)
        return kept

    return visit(schema)


def default_response(agent_name: str, payload: dict[str, Any]) -> dict[str, Any]:
    topic = _topic_text(payload)
    if agent_name == "CoScientistGenerate":
        return {
            "hypotheses": [
                {
                    "hypothesis_id": "H1",
                    "question": f"When should an agent compose existing skills rather than discover a new skill for {topic}?",
                    "hypothesis": "Composition is preferable when task novelty can be decomposed into known subrequirements.",
                    "mechanism": "Existing skills cover subrequirements, so discovery adds retrieval overhead without increasing capability.",
                    "experiment": "Compare compose-first and discover-first policies across compositional and truly novel tasks.",
                    "novelty_rationale": "Focuses on the boundary condition for skill creation rather than generic skill discovery.",
                    "risks": ["Requires reliable labels for compositional versus truly novel requirements."],
                },
                {
                    "hypothesis_id": "H2",
                    "question": f"Does skill-library size change the optimal discovery threshold for {topic}?",
                    "hypothesis": "The discovery threshold should rise as library redundancy increases.",
                    "mechanism": "Larger redundant libraries increase retrieval confusion and duplicate skill cost.",
                    "experiment": "Vary library size and redundancy while measuring discovery decisions and success.",
                    "novelty_rationale": "Tests a dynamic threshold rather than a fixed policy.",
                    "risks": ["Library redundancy may be hard to measure automatically."],
                },
                {
                    "hypothesis_id": "H3",
                    "question": f"Can agents predict future utility before creating a skill for {topic}?",
                    "hypothesis": "Future utility prediction reduces low-value skill creation.",
                    "mechanism": "Skills only help if future tasks reuse their requirements.",
                    "experiment": "Compare skill creation with and without future recurrence estimates.",
                    "novelty_rationale": "Treats skill discovery as an investment decision.",
                    "risks": ["Future task distributions may be unknown."],
                },
            ]
        }
    if agent_name == "CoScientistDebate":
        return {
            "critiques": [
                "H1 is the most directly aligned to the compose-versus-discover topic and has a decisive controlled experiment.",
                "H2 is mechanistic but depends on a good redundancy metric.",
                "H3 is interesting but shifts toward forecasting future task distributions.",
            ],
            "ranking": ["H1", "H2", "H3"],
            "winning_hypothesis_id": "H1",
            "synthesis": "Evolve H1 by explicitly measuring task success, duplicate skill growth, and routing errors across requirement regimes.",
        }
    if agent_name == "CoScientistEvolve":
        return {
            "primitive_definitions": [
                {"name": "skill", "definition": "A reusable behavior or procedure available to an agent.", "why_primitive": "The decision concerns reusing or creating skills."},
                {"name": "composition", "definition": "Solving a task by combining existing skills.", "why_primitive": "It is the alternative to new skill discovery."},
                {"name": "task novelty", "definition": "The degree to which a task requires behavior not inferable from existing skills.", "why_primitive": "It determines whether discovery is needed."},
            ],
            "assumptions": [
                {"assumption": "Some tasks are compositional rather than truly novel.", "rationale": "Otherwise composition would not be a meaningful option.", "possible_failure": "Tasks may require genuinely new behavior."},
                {"assumption": "New skills add retrieval and maintenance overhead.", "rationale": "Skill creation can harm future routing through redundancy.", "possible_failure": "A perfect retrieval system could avoid this cost."},
            ],
            "mechanism_summary": "Task requirements map to existing skill coverage; if requirements are compositional, composition preserves success while avoiding duplicate skill growth, but if requirements are non-inferable, discovery is necessary.",
            "tension": "A new skill may solve the current task but make future skill routing worse when the task could have been solved by composing existing skills.",
            "question": "When does composing existing skills outperform discovering a new skill in lifelong coding agents?",
            "question_type": "diagnostic",
            "hypothesis": "Composing existing skills outperforms new-skill discovery when task requirements are compositional and the skill library already covers the required subskills.",
            "predicted_effect": "Composition matches success while reducing duplicate skill growth and routing errors.",
            "experiment": "Create coding tasks in three regimes: single-skill sufficient, multi-skill composition sufficient, and genuinely novel. Compare always-discover, always-compose, and novelty-gated policies.",
            "independent_variables": ["task requirement regime", "skill-selection policy"],
            "dependent_variables": ["task success", "duplicate skill rate", "routing error rate", "cost per solved task"],
            "controls": ["same model", "same initial skill library", "same task templates", "same budget"],
            "falsifying_observation": "Composition fails to match discovery success on compositional tasks or does not reduce duplicate skills/routing errors.",
            "expected_support": ["Composition matches discovery success in compositional regimes while reducing duplicate skills."],
            "expected_reject": ["Discovery dominates composition on compositional tasks without increasing duplicate skills or routing errors."],
            "failure_update": "Revise the definition of compositionality or add a stronger composition operator.",
            "novelty_note": "The question isolates a boundary condition for skill discovery instead of assuming new skill creation is always beneficial.",
            "quality_scores": {
                "first_principles_derivation": 4,
                "falsifiability": 5,
                "mechanism_clarity": 5,
                "novelty": 4,
                "experimentability": 5,
            },
        }
    if agent_name == "AgentLabLiterature":
        return {
            "related_work_claims": [
                "Skill-discovery agents can improve future task performance by caching reusable procedures.",
                "Composition and retrieval can solve many tasks without expanding the skill library.",
            ],
            "inferred_gap": "Existing agent-skill evaluations rarely isolate when new skill creation is better than composition under controlled requirement regimes.",
            "closest_baselines": ["always discover", "always retrieve", "retrieve then compose"],
        }
    if agent_name == "AgentLabExperiment":
        return {
            "proposed_question": "Can a literature-gap-derived novelty classifier decide when to discover new skills rather than compose existing skills?",
            "proposed_hypothesis": "A classifier trained on task requirement features improves the discover-versus-compose decision compared with fixed policies.",
            "experiment_design": "Build controlled coding tasks with labeled requirement regimes and compare fixed policies to a learned novelty classifier.",
            "implementation_risks": ["Classifier labels may leak task templates.", "The benchmark may overfit to synthetic requirement regimes."],
        }
    if agent_name == "AgentLabCritique":
        return {
            "strengths": ["Clear baselines", "Runnable controlled experiment"],
            "weaknesses": ["May become a classifier benchmark rather than a mechanism test", "Needs falsifying observations tied to skill-library costs"],
            "required_revisions": ["Add duplicate skill rate and routing error metrics", "State when the classifier would be falsified"],
        }
    if agent_name == "AgentLabSynthesize":
        return {
            "primitive_definitions": [
                {"name": "skill", "definition": "A reusable behavior that can be retrieved or invoked by an agent.", "why_primitive": "Skill creation and reuse are the core choices."},
                {"name": "composition", "definition": "Solving a task by combining existing skills.", "why_primitive": "Composition is the main alternative to discovery."},
                {"name": "novelty classifier", "definition": "A decision rule that estimates whether existing skills cover a task requirement.", "why_primitive": "The baseline frames the choice as classification."},
            ],
            "assumptions": [
                {"assumption": "Task requirement features predict whether composition is sufficient.", "rationale": "A classifier needs observable features linked to the decision.", "possible_failure": "The decisive requirement may be non-observable before solving."},
                {"assumption": "Skill creation has measurable downstream costs.", "rationale": "Otherwise over-creating skills would not be penalized.", "possible_failure": "Retrieval may remain robust despite library growth."},
            ],
            "mechanism_summary": "Task features predict whether existing skills cover requirements; classifier errors route tasks to unnecessary discovery or insufficient composition, affecting success and library bloat.",
            "tension": "A classifier may improve routing accuracy but hide the mechanism by learning dataset artifacts rather than true requirement novelty.",
            "question": "Can a novelty classifier decide when coding agents should discover new skills rather than compose existing skills?",
            "question_type": "algorithmic",
            "hypothesis": "A novelty classifier using requirement-coverage features improves routing accuracy and reduces duplicate skills relative to fixed discover or compose policies.",
            "predicted_effect": "Higher routing accuracy with lower duplicate skill rate at matched task success.",
            "experiment": "Create coding tasks labeled as single-skill, compositional, or novel. Train a classifier on requirement-coverage features and compare it to always-discover, always-compose, and oracle labels.",
            "independent_variables": ["routing policy", "task requirement regime"],
            "dependent_variables": ["routing accuracy", "task success", "duplicate skill rate", "cost per solved task"],
            "controls": ["same model", "same initial skill library", "same train/test split"],
            "falsifying_observation": "The classifier fails to improve routing accuracy or duplicate skill rate over fixed policies at matched task success.",
            "expected_support": ["Classifier improves routing and reduces duplicate skill growth without lowering success."],
            "expected_reject": ["Fixed policies match or beat the classifier on routing and library quality."],
            "failure_update": "Revise the observable requirement features or abandon classifier framing for a mechanism-specific gate.",
            "novelty_note": "The baseline tests a literature-gap-driven learned policy, but is less derivation-auditable than FirstResearch.",
            "quality_scores": {
                "first_principles_derivation": 3,
                "falsifiability": 5,
                "mechanism_clarity": 4,
                "novelty": 3,
                "experimentability": 5,
            },
        }
    if agent_name == "TreeSearchBranch":
        return {
            "branches": [
                {
                    "branch_id": "B1",
                    "research_direction": "Threshold boundary between composition and discovery.",
                    "mechanism_bet": "Task novelty and library interference jointly determine when composition fails.",
                    "minimal_experiment": "Cross novelty regimes with library interference and compare fixed versus threshold-gated policies.",
                    "expected_failure_mode": "The boundary may collapse if composition quality is too weak.",
                },
                {
                    "branch_id": "B2",
                    "research_direction": "Representation separability as a trigger for new skill creation.",
                    "mechanism_bet": "Composition fails when required behavior is not separable in existing skill embeddings.",
                    "minimal_experiment": "Vary embedding separability and compare composed versus new-skill policies.",
                    "expected_failure_mode": "Embedding separability may not predict execution behavior.",
                },
                {
                    "branch_id": "B3",
                    "research_direction": "Long-horizon reuse value for discovered skills.",
                    "mechanism_bet": "Discovery is useful only when future recurrence amortizes creation cost.",
                    "minimal_experiment": "Vary future recurrence and discovery cost across task streams.",
                    "expected_failure_mode": "Future recurrence may be unobservable at decision time.",
                },
            ]
        }
    if agent_name == "TreeSearchSelect":
        return {
            "selected_branch_id": "B1",
            "ranking": ["B1", "B2", "B3"],
            "selection_rationale": "B1 best matches the topic and gives a falsifiable boundary condition.",
            "expansion_instructions": [
                "Make the novelty-by-interference interaction explicit.",
                "Include fixed-policy and threshold-gate baselines.",
                "Define a rejecting observation where no switch boundary exists.",
            ],
        }
    if agent_name == "TreeSearchExpand":
        return {
            "primitive_definitions": [
                {"name": "task novelty", "definition": "How far task requirements are from behaviors covered by existing skills.", "why_primitive": "It determines whether existing skills can solve the task."},
                {"name": "library interference", "definition": "Retrieval ambiguity or duplicate-skill conflict caused by the skill library.", "why_primitive": "It mediates the cost of reuse and composition."},
                {"name": "discovery threshold", "definition": "The boundary where creating a new skill becomes better than composing old ones.", "why_primitive": "It is the decision rule being tested."},
            ],
            "assumptions": [
                {"assumption": "Task novelty and library interference are measurable before or during routing.", "rationale": "The threshold gate needs observable inputs.", "possible_failure": "The relevant novelty may only appear after execution."},
                {"assumption": "Composition and discovery have different error profiles.", "rationale": "Without different failure modes, no boundary can exist.", "possible_failure": "Both policies may fail on the same tasks."},
            ],
            "mechanism_summary": "As task novelty and library interference rise, composition accumulates mismatch and retrieval errors; beyond a threshold, new skill discovery has higher expected utility despite creation cost.",
            "tension": "Agents may over-compose to avoid discovery cost, but composition can silently fail when novelty and library interference interact.",
            "question": "Is there a novelty-by-library-interference threshold where discovering a new skill becomes better than composing existing skills?",
            "question_type": "causal",
            "hypothesis": "Discovery outperforms composition only above a joint threshold of task novelty and library interference; below that threshold, composition has equal success and lower cost.",
            "predicted_effect": "A crossover interaction in success and cost between composition and discovery policies.",
            "experiment": "Generate coding tasks across three novelty levels and three library-interference levels. Compare always-compose, always-discover, and threshold-gated policies.",
            "independent_variables": ["task novelty level", "library interference level", "skill policy"],
            "dependent_variables": ["task success", "cost per solved task", "routing error rate", "duplicate skill rate"],
            "controls": ["same model", "same task templates", "same initial library", "same execution budget"],
            "falsifying_observation": "No crossover appears: one policy dominates across all novelty and interference levels, or the threshold gate fails to beat fixed policies.",
            "expected_support": ["Composition wins below the threshold, discovery wins above it, and threshold gating improves aggregate cost-success tradeoff."],
            "expected_reject": ["No measurable threshold or interaction is observed."],
            "failure_update": "Replace the threshold model with a different mechanism such as representation separability or future recurrence.",
            "novelty_note": "This branch-search baseline turns the compose-versus-discover question into a threshold law over two measurable mechanisms.",
            "quality_scores": {
                "first_principles_derivation": 4,
                "falsifiability": 5,
                "mechanism_clarity": 5,
                "novelty": 5,
                "experimentability": 5,
            },
        }
    if agent_name.startswith("Baseline_"):
        offset = 0
        if "literature_first" in agent_name or "generic_multi_agent" in agent_name:
            offset = 1
        return {
            "primitive_definitions": [
                {"name": "system", "definition": "The agent or research method under study.", "why_primitive": "It is the object being evaluated."},
                {"name": "task", "definition": "A problem instance the system attempts.", "why_primitive": "Research claims are tested on tasks."},
                {"name": "metric", "definition": "A numerical or qualitative measure of outcome quality.", "why_primitive": "Experiments need observations."},
            ],
            "assumptions": [
                {"assumption": "Improving the method improves the observed metric.", "rationale": "The baseline frames research as performance improvement.", "possible_failure": "The metric may not capture the mechanism."},
                {"assumption": "The topic has a remaining research gap.", "rationale": "A new question requires unknown behavior.", "possible_failure": "The gap may already be answered."},
            ],
            "mechanism_summary": f"A generic auto-research baseline proposes an improvement for {topic} and evaluates it by metric change.",
            "tension": "The baseline may identify a plausible gap without isolating the mechanism that would falsify it.",
            "question": f"What research gap remains for {topic}?",
            "question_type": "algorithmic",
            "hypothesis": "A targeted method improves the chosen metric over a basic baseline.",
            "predicted_effect": "Higher measured quality under matched evaluation.",
            "experiment": "Compare the proposed method against a basic baseline on a small topic set.",
            "independent_variables": ["method"],
            "dependent_variables": ["quality score"],
            "controls": ["same topics", "same model", "same evaluator"],
            "falsifying_observation": "The proposed method does not improve quality under matched settings.",
            "expected_support": ["The proposed method scores higher than the baseline."],
            "expected_reject": ["Scores are equal or worse than the baseline."],
            "failure_update": "Revise the assumed gap or metric.",
            "novelty_note": "The idea is plausible but less derivation-grounded than FirstResearch.",
            "quality_scores": {
                "first_principles_derivation": 2 + offset,
                "falsifiability": 2 + offset,
                "mechanism_clarity": 2 + offset,
                "novelty": 2 + offset,
                "experimentability": 3 + offset,
            },
        }
    if agent_name == "BenchmarkJudge":
        return {
            "scores": {
                "first_principles_derivation": 4,
                "falsifiability": 4,
                "mechanism_clarity": 4,
                "novelty": 3,
                "experimentability": 4,
            },
            "review_score": 7,
            "recommendation": "weak_accept",
            "rationale": "Mock judge assigns a stable dry-run score.",
        }
    if agent_name == "FirstPrinciplesDecomposer":
        return {
            "primitive_definitions": [
                {
                    "name": "task requirement",
                    "definition": "A condition that must be satisfied for a task outcome to be valid.",
                    "why_primitive": "Skill and routing decisions only matter relative to requirements.",
                },
                {
                    "name": "skill",
                    "definition": "A reusable procedure that reduces future problem-solving cost.",
                    "why_primitive": "The system studies whether reuse or creation is warranted.",
                },
                {
                    "name": "composition",
                    "definition": "Combining existing reusable procedures without adding a new one.",
                    "why_primitive": "Composition is the main alternative to skill discovery.",
                },
            ],
            "assumptions": [
                {
                    "assumption": "Future tasks share latent requirement structure.",
                    "rationale": "Without recurrence, skill reuse has little value.",
                    "possible_failure": "Tasks may be mostly one-off or underspecified.",
                },
                {
                    "assumption": "Skill libraries impose retrieval and maintenance costs.",
                    "rationale": "Adding skills can harm future selection even if one task improves.",
                    "possible_failure": "A perfect retriever could make library size irrelevant.",
                },
            ],
            "core_tradeoffs": [
                {
                    "tradeoff": "new-skill benefit versus future retrieval interference",
                    "variables": ["task novelty", "library size", "routing accuracy", "future cost"],
                }
            ],
        }
    if agent_name == "MechanismBuilder":
        return {
            "variables": [
                {"name": "task novelty", "role": "input", "description": "How much the task requires behavior not covered by existing skills."},
                {"name": "retrieval fit", "role": "mediator", "description": "How well existing skills match the task requirements."},
                {"name": "library complexity", "role": "confounder", "description": "The size and redundancy of the skill library."},
                {"name": "task success and cost", "role": "outcome", "description": "Whether the task is solved and how much effort it takes."},
            ],
            "causal_chain": [
                {"step": "Task requirements determine whether existing skills are sufficient."},
                {"step": "The agent chooses retrieval, composition, or discovery based on perceived novelty."},
                {"step": "The choice affects immediate success, cost, and future library complexity."},
            ],
            "bottlenecks": [
                {"bottleneck": "novelty estimation", "why_it_matters": "Misclassifying compositional tasks as novel creates duplicate skills."}
            ],
            "mechanism_summary": f"{topic} depends on estimating when requirements exceed existing skill coverage while accounting for future library costs.",
        }
    if agent_name == "TensionFinder":
        return {
            "tensions": [
                {
                    "tension_id": "TENSION-001",
                    "statement": "Creating a new skill can improve the current task while degrading future routing through duplicate or overly specific skills.",
                    "derived_from": ["skill", "composition", "new-skill benefit versus future retrieval interference"],
                    "why_it_matters": "The local reward for adding a skill may conflict with long-run agent performance.",
                    "what_existing_methods_may_miss": "They may count successful skill creation without measuring library bloat or routing errors.",
                    "testability": 5,
                }
            ]
        }
    if agent_name == "QuestionGenerator":
        return {
            "candidate_questions": [
                {
                    "question": "When does composing existing skills outperform discovering a new skill in lifelong coding agents?",
                    "question_type": "diagnostic",
                    "source_tension": "TENSION-001",
                    "expected_contribution": "A diagnostic benchmark and gate for skill discovery decisions.",
                }
            ]
        }
    if agent_name == "QuestionDebateRefiner":
        return {
            "candidate_questions": [
                {
                    "question": "At what task-novelty and library-interference threshold does composing existing skills stop outperforming discovering a new skill in lifelong coding agents?",
                    "question_type": "diagnostic",
                    "source_tension": "TENSION-001",
                    "expected_contribution": "A co-scientist-style debate/evolution refinement of the compose-versus-discover boundary before certification.",
                }
            ]
        }
    if agent_name == "CertificateBuilder":
        return {
            "hypothesis": {
                "statement": "A composition-first novelty gate matches task success while reducing duplicate skill growth on compositional tasks.",
                "predicted_effect": "Lower duplicate skill rate with no meaningful loss in task success.",
            },
            "minimal_decisive_test": {
                "experiment": "Run controlled coding tasks where requirements are single-skill, compositional, or truly novel.",
                "independent_variables": ["requirement condition", "skill policy"],
                "dependent_variables": ["task success", "duplicate skill rate", "routing accuracy", "cost per solved task"],
                "controls": ["same base model", "same task budget", "same starting skill library"],
                "falsifying_observation": "The novelty gate reduces duplicate skills only by substantially lowering task success, or fails to reduce duplicates.",
            },
            "expected_observations": {
                "supports_hypothesis": ["Composition-first policy keeps success within tolerance while reducing duplicate skills."],
                "rejects_hypothesis": ["Always-discover dominates both success and library quality under matched budgets."],
            },
            "failure_update_rule": {
                "if_failed": "Inspect whether novelty was defined too coarsely or composition was underpowered.",
                "assumption_to_revise": "Skill libraries impose retrieval and maintenance costs.",
                "next_question": "Which kinds of library complexity actually cause routing failures?",
            },
            "quality_scores": {
                "first_principles_derivation": 5,
                "falsifiability": 5,
                "mechanism_clarity": 4,
                "novelty": 4,
                "experimentability": 5,
            },
        }
    if agent_name == "CertificateRepairer":
        return {
            "research_question": {
                "question": "At what task-novelty and library-interference threshold does composing existing skills stop outperforming discovering a new skill in lifelong coding agents?",
                "question_type": "diagnostic",
                "source_tension": "TENSION-001",
                "expected_contribution": "A threshold law for the compose-versus-discover boundary in skill-library agents.",
            },
            "hypothesis": {
                "statement": "Composition outperforms discovery below a joint threshold where task novelty is decomposable and library interference is low, but discovery outperforms composition once novelty and interference jointly exceed that boundary.",
                "predicted_effect": "A measurable interaction: composition wins in low-novelty/low-interference regimes, while discovery wins in high-novelty/high-interference regimes.",
            },
            "minimal_decisive_test": {
                "experiment": "Construct coding tasks crossing task novelty (covered, compositional, non-inferable) with library interference (low, medium, high duplicate/retrieval ambiguity). Compare always-discover, always-compose, and threshold-gated policies under the same initial library.",
                "independent_variables": ["task novelty regime", "library interference level", "skill-selection policy"],
                "dependent_variables": ["task success", "duplicate skill rate", "routing error rate", "cost per solved task"],
                "controls": ["same base model", "same initial skill library", "same task templates", "same budget"],
                "falsifying_observation": "There is no novelty-by-interference interaction: composition and discovery do not switch dominance across the predicted boundary, or the threshold gate fails to beat both fixed policies.",
            },
            "expected_observations": {
                "supports_hypothesis": ["Composition dominates below the novelty/interference boundary, discovery dominates above it, and the threshold gate avoids duplicate growth."],
                "rejects_hypothesis": ["One fixed policy dominates across all novelty and interference regimes."],
            },
            "failure_update_rule": {
                "if_failed": "Revise the assumed interaction between novelty and library interference or replace the threshold model with a different mechanism.",
                "assumption_to_revise": "Skill libraries impose retrieval and maintenance costs.",
                "next_question": "Which measurable forms of library interference actually cause the compose-versus-discover boundary?",
            },
            "quality_scores": {
                "first_principles_derivation": 5,
                "falsifiability": 5,
                "mechanism_clarity": 5,
                "novelty": 5,
                "experimentability": 5,
            },
        }
    if agent_name == "ExperimentDesigner":
        return {
            "hypothesis": "A composition-first novelty gate matches task success while reducing duplicate skill growth on compositional tasks.",
            "independent_variables": ["task requirement condition", "skill-selection policy"],
            "dependent_variables": ["task success", "duplicate skill rate", "routing accuracy", "cost per solved task"],
            "controlled_variables": ["base model", "initial library", "time budget", "task templates"],
            "baselines": [
                {"name": "always_discover", "description": "Create a new skill after each solved task."},
                {"name": "always_retrieve", "description": "Use only the nearest existing skill."},
                {"name": "retrieve_compose", "description": "Retrieve and compose available skills without novelty gating."},
            ],
            "metrics": [
                {"name": "success_rate", "definition": "Solved tasks divided by attempted tasks."},
                {"name": "duplicate_skill_rate", "definition": "New skills semantically overlapping existing skills divided by created skills."},
                {"name": "routing_accuracy", "definition": "Fraction of tasks assigned to the intended skill policy for the condition."},
            ],
            "expected_result": "The novelty gate reduces duplicate skills on compositional tasks while preserving success.",
            "falsifying_result": "The gate either fails to reduce duplicates or reduces duplicates with a large success penalty.",
            "minimum_viable_experiment": "Generate 30 template coding tasks across three requirement conditions and run each policy with a mock or real coding-agent harness.",
            "risks_and_confounds": ["Template tasks may make novelty easier than realistic coding tasks."],
        }
    if agent_name == "ReviewerAgent":
        return {
            "summary": "The package has a clear mechanism and a small diagnostic experiment, but needs real coding-agent task evidence.",
            "strengths": ["Falsifiable certificate", "Mechanism-level variables", "Concrete baselines"],
            "weaknesses": ["Literature grounding is not implemented in this prototype", "Human validation of duplicate skills is needed"],
            "questions": ["How robust is the novelty gate across task distributions?"],
            "missing_baselines": ["random routing", "oracle novelty labels"],
            "score": 7,
            "confidence": 3,
            "recommendation": "weak_accept",
        }
    if agent_name == "MetaResearcher":
        return {
            "failure_type": "prototype_limitation",
            "root_cause": "The current pipeline uses deterministic mock outputs rather than empirical agent runs.",
            "violated_principle": "Research claims require evidence matched to the falsifying test.",
            "new_or_updated_principle": "Do not claim benchmark superiority until benchmark results are produced.",
            "new_or_updated_skill": "evidence_strength_check",
            "regression_test": "Reject reports that infer strong claims from mock-only runs.",
        }
    raise ValueError(f"No mock response for agent {agent_name!r}: {json.dumps(payload)[:200]}")


def _topic_text(payload: dict[str, Any]) -> str:
    topic = payload.get("topic", {})
    if isinstance(topic, dict):
        return str(topic.get("topic", "the topic"))
    return str(topic or "the topic")
