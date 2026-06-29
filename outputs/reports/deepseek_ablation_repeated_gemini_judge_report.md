# FirstResearch Benchmark Report

## Average Scores

| System | N | Repeats | Derivation | Falsifiability | Mechanism | Novelty | Experimentability | Avg | Avg Std | Pass Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| certificate_only_ablation | 18 | 2 | 4.61 | 5.00 | 4.89 | 4.89 | 5.00 | 4.88 | 0.15 | 1.00 |
| firstresearch | 18 | 2 | 4.39 | 5.00 | 4.56 | 4.89 | 4.89 | 4.74 | 0.13 | 1.00 |
| no_certificate_ablation | 18 | 2 | 0.89 | 0.44 | 0.78 | 0.72 | 1.61 | 0.89 | 0.38 | 0.00 |
| no_gate_repair_ablation | 18 | 2 | 4.11 | 5.00 | 4.06 | 3.11 | 4.78 | 4.21 | 0.19 | 1.00 |
| no_mechanism_model_ablation | 18 | 2 | 4.00 | 5.00 | 3.00 | 4.72 | 4.83 | 4.31 | 0.47 | 1.00 |
| no_novelty_boundary_repair_ablation | 18 | 2 | 4.17 | 5.00 | 4.22 | 3.50 | 4.78 | 4.33 | 0.21 | 1.00 |
| no_self_improvement_ablation | 18 | 2 | 4.44 | 5.00 | 4.78 | 5.00 | 4.94 | 4.83 | 0.15 | 1.00 |

## Top Examples

- certificate_only_ablation on T001: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T001_certificate_only_ablation.json
- certificate_only_ablation on T002: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T002_certificate_only_ablation.json
- certificate_only_ablation on T003: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T003_certificate_only_ablation.json
- certificate_only_ablation on T006: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T006_certificate_only_ablation.json
- no_self_improvement_ablation on T006: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T006_no_self_improvement_ablation.json

## Failure Types

- no_certificate_ablation on T001: did not pass certificate gate
- no_certificate_ablation on T002: did not pass certificate gate
- no_certificate_ablation on T003: did not pass certificate gate
- no_certificate_ablation on T004: did not pass certificate gate
- no_certificate_ablation on T005: did not pass certificate gate
- no_certificate_ablation on T006: did not pass certificate gate
- no_certificate_ablation on T007: did not pass certificate gate
- no_certificate_ablation on T008: did not pass certificate gate
- no_certificate_ablation on T009: did not pass certificate gate
- no_certificate_ablation on T010: did not pass certificate gate

## Comparison Table

| System | Average Score | Delta vs Full | Pass Rate |
|---|---:|---:|---:|
| certificate_only_ablation | 4.88 | +0.13 | 1.00 |
| firstresearch | 4.74 | +0.00 | 1.00 |
| no_certificate_ablation | 0.89 | -3.86 | 0.00 |
| no_gate_repair_ablation | 4.21 | -0.53 | 1.00 |
| no_mechanism_model_ablation | 4.31 | -0.43 | 1.00 |
| no_novelty_boundary_repair_ablation | 4.33 | -0.41 | 1.00 |
| no_self_improvement_ablation | 4.83 | +0.09 | 1.00 |
