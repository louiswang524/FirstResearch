# Paper Evidence Audit

| Check | Required | Status | Detail | Path |
|---|---:|---|---|---|
| strong_baseline_csv | true | PASS | 40 rows; expected at least 40 | `outputs\reports\deepseek_strong_baselines_10topics.csv` |
| strong_baseline_report | true | PASS | exists (1301 bytes) | `outputs\reports\deepseek_strong_baselines_10topics.md` |
| strong_baseline_metadata | true | PASS | run_id=legacy-deepseek-strong-baselines-10topics | `outputs\reports\deepseek_strong_baselines_10topics_metadata.json` |
| strong_baseline_gemini_csv | true | PASS | 40 rows; expected at least 40 | `outputs\reports\deepseek_strong_baselines_gemini_judge_results.csv` |
| strong_baseline_gemini_agreement_report | true | PASS | contains required strings | `outputs\reports\deepseek_strong_baselines_gemini_judge_agreement.md` |
| strong_baseline_package_audit | true | PASS | contains required strings | `outputs\reports\deepseek_strong_baselines_package_audit.md` |
| results_table_audit | true | PASS | contains required strings | `outputs\reports\results_table_audit.md` |
| strong_baseline_config | true | PASS | exists (496 bytes) | `configs\deepseek_strong_baselines.yaml` |
| baseline_fidelity_report | true | PASS | contains required strings | `outputs\reports\baseline_fidelity_report.md` |
| reference_audit | true | PASS | contains required strings | `outputs\reports\reference_audit.md` |
| human_review_protocol | true | PASS | contains required strings | `outputs\reports\human_review_protocol.md` |
| repro_appendix | true | PASS | contains required strings | `papers\reproducibility_appendix.md` |
| artifact_manifest | true | PASS | 289 entries; expected at least 10 | `outputs\reports\artifact_manifest.json` |
| claim_evidence_registry | true | PASS | exists (2850 bytes) | `papers\claim_evidence_registry.yaml` |
| repeated_ablation_csv | false | MISSING | 126 rows; expected at least 210 | `outputs\reports\deepseek_ablation_repeated_results.csv` |
| ablation_checkpoint_csv | true | PASS | 126 rows; expected at least 70 | `outputs\reports\deepseek_ablation_repeated_results.csv` |
| ablation_checkpoint_report | true | PASS | contains required strings | `outputs\reports\deepseek_ablation_repeated_report.md` |
| crossjudge_csv | true | PASS | 126 rows; expected at least 70 | `outputs\reports\deepseek_ablation_repeated_gemini_judge_results.csv` |
| crossjudge_agreement_report | true | PASS | contains required strings | `outputs\reports\deepseek_ablation_repeated_gemini_judge_agreement.md` |
| repeated_stability_report | false | PASS | contains required strings | `outputs\reports\deepseek_ablation_repeated_stability.md` |
| stress_generalization_csv | false | MISSING | missing | `outputs\reports\deepseek_stress_generalization_results.csv` |
| stress_generalization_report | false | MISSING | missing | `outputs\reports\deepseek_stress_generalization_report.md` |
| human_scalar_report | false | MISSING | missing | `outputs\human_review\deepseek_ablation_repeated\human_review_report.md` |
| human_pairwise_report | false | MISSING | missing | `outputs\human_review\deepseek_ablation_repeated_pairwise\pairwise_report.md` |

Required checks cover evidence already claimed in the draft.
Optional checks cover planned evidence needed to strengthen the paper before submission.
