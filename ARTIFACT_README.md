# FirstResearch Reproducibility Artifact

This repository contains the anonymized code, prompts, configs, benchmark topics, saved model outputs, and audit scripts used for the paper:

**FirstResearch: Auditable Question Formation for LLM Scientific Discovery Agents**

The artifact supports three levels of reproducibility:

1. **No-API verification:** run unit tests, regenerate reports from saved CSV/package artifacts, audit paper tables, and verify headline numbers.
2. **Independent-judge rescore:** rescore saved packages with Gemini or any OpenAI-compatible judge endpoint.
3. **Full regeneration:** rerun the DeepSeek-backed generation and judging workflows with fresh API calls.

No API keys are included. Set keys only through environment variables.

## Quick Start

```bash
python -m pip install -e .
python -m pytest
python scripts/check_expected_results.py
python scripts/reproduce_paper.py --no-api
```

The no-API path should finish locally and checks the saved artifacts used by the paper.

## Reproduce Saved-Artifact Results

```bash
python scripts/reproduce_paper.py --no-api
```

This regenerates:

- strong-baseline reports and table audits
- baseline-fidelity report
- reference and claim-evidence audits
- artifact manifest
- reproducibility appendix
- submission-readiness summary

It does not call external LLM APIs.

## Verify Headline Numbers

```bash
python scripts/check_expected_results.py
```

The checker validates the headline numbers reported in the paper, including:

- DeepSeek strong-baseline system means
- Gemini strong-baseline rescore means
- DeepSeek/Gemini strong-baseline judge agreement
- one-repeat DeepSeek ablation checkpoint means
- Gemini ablation rescore checkpoint means

## Reproduce With External APIs

Set the required credentials, then run:

```bash
export DEEPSEEK_API_KEY="your-key"
export GEMINI_API_KEY="your-key"
python scripts/reproduce_paper.py --with-api
```

For PowerShell:

```powershell
$env:DEEPSEEK_API_KEY="your-key"
$env:GEMINI_API_KEY="your-key"
python scripts/reproduce_paper.py --with-api
```

The full API path may be expensive and stochastic because it regenerates LLM outputs.

## Independent Judge Only

To rescore saved packages without regenerating packages:

```bash
export GEMINI_API_KEY="your-key"
python scripts/rescore_packages.py --config configs/deepseek_strong_baselines_gemini_judge.yaml
python scripts/rescore_packages.py --config configs/deepseek_ablation_repeated_gemini_judge.yaml
python scripts/analyze_judge_agreement.py \
  --primary-results outputs/reports/deepseek_strong_baselines_10topics.csv \
  --secondary-results outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv \
  --output outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.md \
  --table-output outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.csv
```

## Repository Layout

- `firstresearch/`: pipeline, schemas, agents, baselines, scoring, and LLM clients.
- `firstresearch/prompts/`: prompts for decomposition, mechanisms, certificates, repair, review, and baselines.
- `configs/`: exact configs for the reported runs and rescoring.
- `data/`: benchmark topics.
- `scripts/`: benchmark, report, audit, rescore, and artifact scripts.
- `outputs/reports/`: saved CSVs, reports, package JSONs, and audit artifacts used by the paper.
- `papers/`: manuscript draft, registry files, and reproducibility appendix.
- `tests/`: unit and pipeline tests.

## Double-Blind / Anonymous GitHub Notes

This artifact is intended for an anonymous repository. Avoid adding:

- author names
- institutional paths
- API keys or `.env` files
- private review notes that identify authors

Before uploading, run:

```bash
python scripts/prepare_anonymous_github_artifact.py
```

The generated zip under `outputs/firstresearch_anonymous_github_artifact.zip` contains the curated anonymous artifact.

