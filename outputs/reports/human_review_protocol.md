# Blinded Human Review Protocol for FirstResearch Research-Package Evaluation

## Purpose

Assess whether human reviewers agree that FirstResearch packages are stronger than matched prompt-level baseline and ablation packages on derivation, falsifiability, mechanism clarity, novelty, and experimentability.

## Reviewer Plan

- Minimum reviewers: 2
- Target reviewers: 3

Reviewer profile:
- ML, NLP, AI-agent, or research-methodology background
- able to judge whether a research question is mechanistic, falsifiable, and experimentable
- not involved in generating the packages being reviewed

## Inputs

- `scalar_results_csv`: `outputs/reports/deepseek_ablation_repeated_results.csv`
- `scalar_packet_dir`: `outputs/human_review/deepseek_ablation_repeated`
- `pairwise_packet_dir`: `outputs/human_review/deepseek_ablation_repeated_pairwise`

## Blinding

- Review files use generated IDs such as HR0001 and PW0001.
- System names and source package paths are kept only in private assignment JSON files.
- Pairwise package order is randomized independently for each pair.
- Reviewers are instructed not to infer or identify the generating system.

## Scalar Score CSV

Required columns:
- `blind_id`
- `reviewer_id`
- `first_principles_derivation`
- `falsifiability`
- `mechanism_clarity`
- `novelty`
- `experimentability`
- `review_score`
- `recommendation`

## Pairwise Decision CSV

Required columns:
- `pair_id`
- `decision`

Allowed decisions:
- `prefer_a`
- `prefer_b`
- `tie`
- `cannot_judge`

## Analysis Plan

- Compute per-system scalar means and standard deviations for the five rubric dimensions and average score.
- Report reviewer-style score and top recommendation by system.
- Compute pairwise wins, losses, ties, win rate, and tie-aware preference score.
- Treat pairwise preference as the primary human-validity signal because scalar ratings may compress strong packages.
- Do not upgrade paper claims from preliminary to supported by humans until completed scalar and pairwise reports exist.

## Ethics and Data Handling

- No human-subject behavioral experiment is conducted; reviewers evaluate generated research-package text.
- No private or sensitive participant data are collected by the repository scripts.
- Reviewer identities should be stored outside public artifacts unless reviewers consent to attribution.

## Commands

```bash
python scripts/export_human_review_packet.py --results outputs/reports/deepseek_ablation_repeated_results.csv --output-dir outputs/human_review/deepseek_ablation_repeated --seed 13
python scripts/analyze_human_review.py --assignments outputs/human_review/deepseek_ablation_repeated/assignments_private.json --scores outputs/human_review/deepseek_ablation_repeated/human_scores.csv --output outputs/human_review/deepseek_ablation_repeated/human_review_report.md --table-output outputs/human_review/deepseek_ablation_repeated/human_review_summary.csv
python scripts/export_pairwise_review_packet.py --results outputs/reports/deepseek_ablation_repeated_results.csv --output-dir outputs/human_review/deepseek_ablation_repeated_pairwise --reference-system firstresearch --seed 17
python scripts/analyze_pairwise_review.py --assignments outputs/human_review/deepseek_ablation_repeated_pairwise/pair_assignments_private.json --decisions outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_decisions.csv --output outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_report.md --table-output outputs/human_review/deepseek_ablation_repeated_pairwise/pairwise_summary.csv
```
