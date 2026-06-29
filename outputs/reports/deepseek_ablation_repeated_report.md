# FirstResearch Benchmark Report

## Average Scores

| System | N | Repeats | Derivation | Falsifiability | Mechanism | Novelty | Experimentability | Avg | Avg Std | Pass Rate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| certificate_only_ablation | 10 | 1 | 4.70 | 5.00 | 4.90 | 5.00 | 4.90 | 4.90 | 0.18 | 1.00 |
| firstresearch | 10 | 1 | 4.50 | 5.00 | 5.00 | 4.60 | 4.90 | 4.80 | 0.18 | 1.00 |
| no_certificate_ablation | 10 | 1 | 1.20 | 0.60 | 0.90 | 0.70 | 1.20 | 0.92 | 0.41 | 0.00 |
| no_gate_repair_ablation | 10 | 1 | 4.30 | 5.00 | 4.50 | 2.80 | 4.90 | 4.30 | 0.20 | 1.00 |
| no_mechanism_model_ablation | 10 | 1 | 3.60 | 5.00 | 1.70 | 3.70 | 4.90 | 3.78 | 0.37 | 1.00 |
| no_novelty_boundary_repair_ablation | 10 | 1 | 4.60 | 5.00 | 4.50 | 3.30 | 4.80 | 4.44 | 0.34 | 1.00 |
| no_self_improvement_ablation | 10 | 1 | 4.80 | 5.00 | 4.80 | 4.50 | 4.70 | 4.76 | 0.17 | 1.00 |

## Top Examples

- certificate_only_ablation on T001: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T001_certificate_only_ablation.json
- firstresearch on T002: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T002_firstresearch.json
- certificate_only_ablation on T002: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T002_certificate_only_ablation.json
- certificate_only_ablation on T003: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T003_certificate_only_ablation.json
- no_self_improvement_ablation on T003: avg=5.00, output=outputs\reports\deepseek_ablation_repeated_packages\r01_T003_no_self_improvement_ablation.json

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
| certificate_only_ablation | 4.90 | +0.10 | 1.00 |
| firstresearch | 4.80 | +0.00 | 1.00 |
| no_certificate_ablation | 0.92 | -3.88 | 0.00 |
| no_gate_repair_ablation | 4.30 | -0.50 | 1.00 |
| no_mechanism_model_ablation | 3.78 | -1.02 | 1.00 |
| no_novelty_boundary_repair_ablation | 4.44 | -0.36 | 1.00 |
| no_self_improvement_ablation | 4.76 | -0.04 | 1.00 |
