# FirstResearch Benchmark Report

## Average Scores

| System | N | Repeats | Derivation | Falsifiability | Mechanism | Novelty | Experimentability | Avg | Avg Std | Pass Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| certificate_only_ablation | 3 | 1 | 5.00 | 5.00 | 5.00 | 5.00 | 5.00 | 5.00 | 0.00 | 1.00 |
| firstresearch | 3 | 1 | 4.33 | 5.00 | 5.00 | 5.00 | 5.00 | 4.87 | 0.09 | 1.00 |
| firstresearch_debate_combo | 3 | 1 | 4.00 | 5.00 | 4.67 | 4.33 | 5.00 | 4.60 | 0.43 | 1.00 |

## Top Examples

- certificate_only_ablation on T001: avg=5.00, output=outputs\reports\deepseek_combo_study_packages\T001_certificate_only_ablation.json
- firstresearch_debate_combo on T001: avg=5.00, output=outputs\reports\deepseek_combo_study_packages\T001_firstresearch_debate_combo.json
- firstresearch on T002: avg=5.00, output=outputs\reports\deepseek_combo_study_packages\T002_firstresearch.json
- certificate_only_ablation on T002: avg=5.00, output=outputs\reports\deepseek_combo_study_packages\T002_certificate_only_ablation.json
- certificate_only_ablation on T003: avg=5.00, output=outputs\reports\deepseek_combo_study_packages\T003_certificate_only_ablation.json

## Failure Types

- No gate failures recorded.

## Comparison Table

| System | Average Score | Delta vs Full | Pass Rate |
|---|---:|---:|---:|
| certificate_only_ablation | 5.00 | +0.13 | 1.00 |
| firstresearch | 4.87 | +0.00 | 1.00 |
| firstresearch_debate_combo | 4.60 | -0.27 | 1.00 |
