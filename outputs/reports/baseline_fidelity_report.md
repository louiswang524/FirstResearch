# Baseline Fidelity Report

These are controlled prompt-level workflow approximations. They test whether FirstResearch outperforms strong ideation patterns under a shared model, schema, and judge protocol; they do not claim to reproduce the full published systems.

## Configuration

- Config: `configs/deepseek_strong_baselines.yaml`
- Topics: `data/topics_eval.jsonl`
- LLM backend: `deepseek`
- Model: `deepseek-v4-flash`
- LLM baselines: `true`
- LLM judge: `true`
- Systems: firstresearch, co_scientist, agent_lab, tree_search_scientist

## Fidelity Cards

### `co_scientist`

Source pattern: AI co-scientist-style hypothesis generation

Implemented elements:
- diverse hypothesis generation
- reflection/debate/ranking over generated hypotheses
- evolution/refinement of the selected hypothesis
- shared ResearchPackage output schema for scoring

Omitted elements:
- no reproduction of the original system code or proprietary orchestration
- no large-scale asynchronous agent pool
- no external biomedical or literature-tool integration
- no full published-system search budget

Fairness controls:
- same topic inputs as FirstResearch
- same generation model family in configured DeepSeek runs
- same output schema before scoring
- same LLM-judge rubric and benchmark CSV format

### `agent_lab`

Source pattern: Agent Laboratory-style staged research assistant

Implemented elements:
- literature-plan stage
- experiment-plan stage
- professor/reviewer critique stage
- final synthesis stage
- shared ResearchPackage output schema for scoring

Omitted elements:
- no execution of the public Agent Laboratory codebase
- no full paper-writing pipeline
- no human-in-the-loop protocol
- no experiment execution environment

Fairness controls:
- same topics and model configuration as FirstResearch
- same final package schema
- same judge prompt and metrics
- same artifact storage convention

### `tree_search_scientist`

Source pattern: AI Scientist-v2-style branch search

Implemented elements:
- frontier generation of multiple research branches
- branch ranking by novelty, mechanism clarity, falsifiability, and feasibility
- selected-branch expansion into one package
- shared ResearchPackage output schema for scoring

Omitted elements:
- no reproduction of AI Scientist-v2 code
- no workshop-paper generation pipeline
- no code execution or experiment-running loop
- no full tree-search compute budget

Fairness controls:
- same topic set
- same configured model backend
- same final scoring rubric
- same CSV/report machinery

## Interpretation Boundary

The resulting table should be described as a controlled comparison against strong prompt-level baseline patterns, not as a claim of superiority over the complete published systems.
