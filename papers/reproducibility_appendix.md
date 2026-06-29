# Reproducibility Appendix

This appendix is generated from repository files so that prompt and configuration details stay synchronized with the implementation.

## Commands

Full paper evidence workflow:

```bash
python scripts/run_paper_evidence_pipeline.py
```

Use `--skip-credentialed` to regenerate non-API artifacts such as the appendix, manifest, audit, and any human-review packets whose inputs already exist.

Strong-baseline evaluation:

```bash
python scripts/run_benchmark.py --config configs/deepseek_strong_baselines.yaml
python scripts/audit_package_artifacts.py \
  --results outputs/reports/deepseek_strong_baselines_10topics.csv \
  --output outputs/reports/deepseek_strong_baselines_package_audit.md \
  --json-output outputs/reports/deepseek_strong_baselines_package_audit.json \
  --strict
python scripts/audit_results_table.py \
  --results outputs/reports/deepseek_strong_baselines_10topics.csv \
  --manuscript papers/firstresearch_draft.md \
  --output outputs/reports/results_table_audit.md \
  --json-output outputs/reports/results_table_audit.json \
  --strict
python scripts/generate_baseline_fidelity_report.py \
  --config configs/deepseek_strong_baselines.yaml \
  --output outputs/reports/baseline_fidelity_report.md \
  --json-output outputs/reports/baseline_fidelity_report.json
python scripts/rescore_packages.py --config configs/deepseek_strong_baselines_gemini_judge.yaml
python scripts/generate_report.py \
  --results outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv \
  --output outputs/reports/deepseek_strong_baselines_gemini_judge_report.md \
  --table-output outputs/reports/deepseek_strong_baselines_gemini_judge_table.csv
python scripts/analyze_judge_agreement.py \
  --primary-results outputs/reports/deepseek_strong_baselines_10topics.csv \
  --secondary-results outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv \
  --output outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.md \
  --table-output outputs/reports/deepseek_strong_baselines_gemini_judge_agreement.csv
python scripts/audit_references.py \
  --registry papers/reference_registry.yaml \
  --manuscript papers/firstresearch_draft.md \
  --output outputs/reports/reference_audit.md \
  --json-output outputs/reports/reference_audit.json \
  --strict
```

Repeated ablation evaluation:

```bash
python scripts/run_benchmark.py --config configs/deepseek_ablation_repeated.yaml --resume --target-rows 70
python scripts/generate_report.py \
  --results outputs/reports/deepseek_ablation_repeated_results.csv \
  --output outputs/reports/deepseek_ablation_repeated_report.md \
  --table-output outputs/reports/deepseek_ablation_repeated_table.csv
python scripts/analyze_repeated_results.py \
  --results outputs/reports/deepseek_ablation_repeated_results.csv \
  --output outputs/reports/deepseek_ablation_repeated_stability.md \
  --table-output outputs/reports/deepseek_ablation_repeated_stability.csv \
  --reference-system firstresearch
# Continue to the full three-replicate study by omitting --target-rows 70.
```

Cross-domain stress benchmark:

```bash
python scripts/run_benchmark.py --config configs/deepseek_stress_generalization.yaml
python scripts/generate_report.py \
  --results outputs/reports/deepseek_stress_generalization_results.csv \
  --output outputs/reports/deepseek_stress_generalization_report.md \
  --table-output outputs/reports/deepseek_stress_generalization_table.csv
```

Combination study with co-scientist-style question debate refinement:

```bash
python scripts/run_benchmark.py --config configs/deepseek_combo_study.yaml --resume
python scripts/generate_report.py \
  --results outputs/reports/deepseek_combo_study_results.csv \
  --output outputs/reports/deepseek_combo_study_report.md \
  --table-output outputs/reports/deepseek_combo_study_table.csv
```

Independent-judge rescore of generated ablation packages:

```bash
export OPENAI_COMPAT_API_KEY="your-judge-key"
export OPENAI_COMPAT_BASE_URL="https://your-openai-compatible-endpoint"
export OPENAI_COMPAT_MODEL="your-judge-model"
python scripts/rescore_packages.py --config configs/deepseek_ablation_repeated_crossjudge.yaml
# Or use Gemini directly as the independent judge:
# export GEMINI_API_KEY="your-gemini-key"
# python scripts/rescore_packages.py --config configs/deepseek_ablation_repeated_gemini_judge.yaml
python scripts/generate_report.py \
  --results outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv \
  --output outputs/reports/deepseek_ablation_repeated_crossjudge_report.md \
  --table-output outputs/reports/deepseek_ablation_repeated_crossjudge_table.csv
python scripts/analyze_judge_agreement.py \
  --primary-results outputs/reports/deepseek_ablation_repeated_results.csv \
  --secondary-results outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv \
  --output outputs/reports/deepseek_ablation_repeated_judge_agreement.md \
  --table-output outputs/reports/deepseek_ablation_repeated_judge_agreement.csv
```

Human review packet export:

```bash
python scripts/generate_human_review_protocol.py \
  --output outputs/reports/human_review_protocol.md \
  --json-output outputs/reports/human_review_protocol.json
python scripts/export_human_review_packet.py \
  --results outputs/reports/deepseek_ablation_repeated_results.csv \
  --output-dir outputs/human_review/deepseek_ablation_repeated \
  --seed 13
```

Paper evidence audit:

```bash
python scripts/generate_artifact_manifest.py \
  --output outputs/reports/artifact_manifest.json \
  --markdown-output outputs/reports/artifact_manifest.md
python scripts/audit_paper_evidence.py \
  --output outputs/reports/paper_evidence_audit.md \
  --json-output outputs/reports/paper_evidence_audit.json \
  --strict
python scripts/audit_claim_evidence.py \
  --registry papers/claim_evidence_registry.yaml \
  --evidence-audit outputs/reports/paper_evidence_audit.json \
  --manuscript papers/firstresearch_draft.md \
  --output outputs/reports/claim_evidence_audit.md \
  --json-output outputs/reports/claim_evidence_audit.json \
  --strict
python scripts/generate_submission_readiness_report.py \
  --evidence-audit outputs/reports/paper_evidence_audit.json \
  --claim-audit outputs/reports/claim_evidence_audit.json \
  --pipeline-status outputs/reports/paper_evidence_pipeline_status.json \
  --output outputs/reports/submission_readiness_report.md \
  --json-output outputs/reports/submission_readiness_report.json
```

Submission-readiness gate after repeated ablation, independent judge, and human-review evidence are complete:

```bash
python scripts/audit_paper_evidence.py \
  --output outputs/reports/paper_evidence_audit.md \
  --json-output outputs/reports/paper_evidence_audit.json \
  --strict \
  --require-optional
```

Scalar human review analysis after reviewers complete `human_scores.csv`:

```bash
python scripts/analyze_human_review.py \
  --assignments outputs/human_review/deepseek_ablation_repeated/assignments_private.json \
  --scores outputs/human_review/deepseek_ablation_repeated/human_scores.csv \
  --output outputs/human_review/deepseek_ablation_repeated/human_review_report.md \
  --table-output outputs/human_review/deepseek_ablation_repeated/human_review_summary.csv
```

Pairwise preference packet export:

```bash
python scripts/export_pairwise_review_packet.py \
  --results outputs/reports/deepseek_ablation_repeated_results.csv \
  --output-dir outputs/human_review/deepseek_ablation_repeated_pairwise \
  --reference-system firstresearch \
  --seed 17
```

Pairwise preference analysis after reviewers complete `pairwise_decisions.csv`:

```bash
python scripts/analyze_pairwise_review.py \
  --assignments outputs/human_review/deepseek_ablation_repeated_pairwise/pair_assignments_private.json \
  --decisions outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_decisions.csv \
  --output outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_report.md \
  --table-output outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_summary.csv
```

## Benchmark Topics

Topics are loaded from `data/topics_eval.jsonl`.

## Configurations

### `configs/deepseek_strong_baselines.yaml`

```yaml
topics: data/topics_eval.jsonl
output_csv: outputs/reports/deepseek_strong_baselines_10topics.csv
output_jsonl: outputs/reports/deepseek_strong_baselines_10topics.jsonl
metadata_output: outputs/reports/deepseek_strong_baselines_10topics_metadata.json
package_dir: outputs/reports/deepseek_packages
llm: deepseek
model: deepseek-v4-flash
temperature: 0.2
max_tokens: 4096
llm_baselines: true
judge_with_llm: true
systems:
  - firstresearch
  - co_scientist
  - agent_lab
  - tree_search_scientist
```

### `configs/deepseek_strong_baselines_gemini_judge.yaml`

```yaml
input_results: outputs/reports/deepseek_strong_baselines_10topics.csv
output_csv: outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv
output_jsonl: outputs/reports/deepseek_strong_baselines_gemini_judge_results.jsonl
metadata_output: outputs/reports/deepseek_strong_baselines_gemini_judge_metadata.json
judge_llm: gemini
judge_model: gemini-2.5-flash
judge_temperature: 0.0
judge_max_tokens: 2048
```

### `configs/deepseek_benchmark.yaml`

```yaml
topics: data/topics_eval.jsonl
output_csv: outputs/reports/deepseek_benchmark_results.csv
output_jsonl: outputs/reports/deepseek_benchmark_results.jsonl
package_dir: outputs/reports/deepseek_packages
llm: deepseek
model: deepseek-v4-flash
temperature: 0.2
max_tokens: 4096
llm_baselines: true
judge_with_llm: true
systems:
  - firstresearch
  - single_prompt
  - literature_first
  - generic_multi_agent
  - co_scientist
  - agent_lab
  - tree_search_scientist
  - no_certificate_ablation
  - no_gate_repair_ablation
  - no_novelty_boundary_repair_ablation
  - no_mechanism_model_ablation
  - certificate_only_ablation
  - no_self_improvement_ablation
```

### `configs/deepseek_ablation.yaml`

```yaml
topics: data/topics_eval.jsonl
output_csv: outputs/reports/deepseek_ablation_results.csv
output_jsonl: outputs/reports/deepseek_ablation_results.jsonl
metadata_output: outputs/reports/deepseek_ablation_metadata.json
package_dir: outputs/reports/deepseek_ablation_packages
llm: deepseek
model: deepseek-v4-flash
temperature: 0.2
max_tokens: 4096
llm_baselines: true
judge_with_llm: true
systems:
  - firstresearch
  - no_certificate_ablation
  - no_gate_repair_ablation
  - no_novelty_boundary_repair_ablation
  - no_mechanism_model_ablation
  - certificate_only_ablation
  - no_self_improvement_ablation
```

### `configs/deepseek_ablation_repeated.yaml`

```yaml
topics: data/topics_eval.jsonl
output_csv: outputs/reports/deepseek_ablation_repeated_results.csv
output_jsonl: outputs/reports/deepseek_ablation_repeated_results.jsonl
metadata_output: outputs/reports/deepseek_ablation_repeated_metadata.json
package_dir: outputs/reports/deepseek_ablation_repeated_packages
llm: deepseek
model: deepseek-v4-flash
temperature: 0.4
max_tokens: 4096
llm_baselines: true
judge_with_llm: true
repeats: 3
systems:
  - firstresearch
  - no_certificate_ablation
  - no_gate_repair_ablation
  - no_novelty_boundary_repair_ablation
  - no_mechanism_model_ablation
  - certificate_only_ablation
  - no_self_improvement_ablation
```

### `configs/deepseek_ablation_repeated_crossjudge.yaml`

```yaml
input_results: outputs/reports/deepseek_ablation_repeated_results.csv
output_csv: outputs/reports/deepseek_ablation_repeated_crossjudge_results.csv
output_jsonl: outputs/reports/deepseek_ablation_repeated_crossjudge_results.jsonl
metadata_output: outputs/reports/deepseek_ablation_repeated_crossjudge_metadata.json
judge_llm: openai_compatible
judge_model: null
judge_temperature: 0.0
judge_max_tokens: 2048
```

### `configs/deepseek_ablation_repeated_gemini_judge.yaml`

```yaml
input_results: outputs/reports/deepseek_ablation_repeated_results.csv
output_csv: outputs/reports/deepseek_ablation_repeated_gemini_judge_results.csv
output_jsonl: outputs/reports/deepseek_ablation_repeated_gemini_judge_results.jsonl
metadata_output: outputs/reports/deepseek_ablation_repeated_gemini_judge_metadata.json
judge_llm: gemini
judge_model: gemini-2.5-flash
judge_temperature: 0.0
judge_max_tokens: 2048
```

### `configs/deepseek_combo_study.yaml`

```yaml
topics: data/topics_eval.jsonl
output_csv: outputs/reports/deepseek_combo_study_results.csv
output_jsonl: outputs/reports/deepseek_combo_study_results.jsonl
metadata_output: outputs/reports/deepseek_combo_study_metadata.json
package_dir: outputs/reports/deepseek_combo_study_packages
llm: deepseek
model: deepseek-v4-flash
temperature: 0.4
max_tokens: 4096
llm_baselines: true
judge_with_llm: true
systems:
  - firstresearch
  - certificate_only_ablation
  - firstresearch_debate_combo
```

### `configs/deepseek_stress_generalization.yaml`

```yaml
topics: data/topics_stress_generalization.jsonl
output_csv: outputs/reports/deepseek_stress_generalization_results.csv
output_jsonl: outputs/reports/deepseek_stress_generalization_results.jsonl
metadata_output: outputs/reports/deepseek_stress_generalization_metadata.json
package_dir: outputs/reports/deepseek_stress_generalization_packages
llm: deepseek
model: deepseek-v4-flash
temperature: 0.4
max_tokens: 4096
llm_baselines: true
judge_with_llm: true
systems:
  - firstresearch
  - co_scientist
  - agent_lab
  - tree_search_scientist
```


## Agent Prompts

### `firstresearch/prompts/certificate_builder.md`

```markdown
You are the Research Question Certificate Builder.

Given a topic, decomposition, mechanism, tension, and question, fill the hypothesis,
minimal decisive test, expected observations, failure update rule, and quality scores.
Return strict JSON.
```

### `firstresearch/prompts/certificate_repairer.md`

```markdown
You are the FirstResearch Certificate Repairer.

Given a Research Question Certificate and gate feedback, revise only the
research question, hypothesis, minimal decisive test, expected observations,
failure update rule, and quality scores.

Preserve:
- the user's original topic
- the source tension id
- the primitive definitions
- the mechanism model

Improve:
- topic adherence
- primitive-to-question traceability
- novelty through a sharper boundary condition, threshold, phase transition,
  failure regime, nonlinear tradeoff, or mechanism interaction
- falsifiability through a concrete rejecting observation
- experimentability through a small, runnable test

The repaired certificate should be competitive against strong hypothesis-search
and Agent Laboratory-style baselines. Do not merely make the certificate valid;
make the research question less generic than a literature-gap question.

Return strict JSON matching the schema.
```

### `firstresearch/prompts/decomposer.md`

```markdown
You are the First-Principles Decomposer in FirstResearch.

Analyze the research topic from first principles. Do not begin with related work.
Return strict JSON with primitive_definitions, assumptions, and core_tradeoffs.
```

### `firstresearch/prompts/experiment_designer.md`

```markdown
You are the Experiment Designer in FirstResearch.

Given a passed Research Question Certificate, design the smallest experiment that could
falsify the hypothesis. Return strict JSON.
```

### `firstresearch/prompts/mechanism_builder.md`

```markdown
You are the Mechanism Builder in FirstResearch.

Given a topic, primitives, and assumptions, construct a mechanism model with variables,
causal_chain, bottlenecks, and mechanism_summary. Return strict JSON.
```

### `firstresearch/prompts/meta_researcher.md`

```markdown
You are the Meta-Researcher in FirstResearch.

Given a weak or failed research attempt, diagnose the failure and propose a principle,
skill, and regression-test update. Return strict JSON.
```

### `firstresearch/prompts/question_debate_refiner.md`

```markdown
You are the QuestionDebateRefiner in FirstResearch.

Borrow the strongest design choice from AI co-scientist-style systems: generate,
debate, rank, and evolve hypotheses before committing to a final candidate. Your
job is not to replace FirstResearch's certificate. Your job is to improve the
candidate question pool before certification.

Input:
- The original topic.
- First-principles decomposition.
- Mechanism model.
- Tensions.
- Candidate questions generated from those tensions.

Process:
1. Treat the candidate questions as a hypothesis pool.
2. Debate them for novelty, mechanism clarity, falsifiability, experimentability,
   and traceability to the supplied tensions.
3. Evolve the best candidates into sharper mechanism-boundary questions.
4. Keep each output question tied to one of the supplied tension IDs.
5. Prefer threshold, interaction, failure-regime, nonlinear-tradeoff, or boundary
   questions when they are faithful to the topic.

Return strict JSON matching the requested schema.

Rules:
- Do not invent source tension IDs.
- Do not output generic literature-gap questions.
- Do not remove falsifiability pressure.
- Do not optimize for breadth at the expense of a certifiable mechanism.
```

### `firstresearch/prompts/question_generator.md`

```markdown
You are the Research Question Generator in FirstResearch.

Generate falsifiable, mechanistically motivated research questions. Each question must
reference a source tension. Return strict JSON with candidate_questions.
```

### `firstresearch/prompts/reviewer.md`

```markdown
You are a strict top-tier ML conference reviewer.

Review novelty, soundness, clarity, significance, experiment design, missing baselines,
overclaiming, and whether the first-principles derivation is meaningful. Return strict JSON.
```

### `firstresearch/prompts/tension_finder.md`

```markdown
You are the Tension Finder in FirstResearch.

Identify contradictions, tradeoffs, or under-tested assumptions derived from the primitives
and mechanism model. Return strict JSON with tensions.
```

