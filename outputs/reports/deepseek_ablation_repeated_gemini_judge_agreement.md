# Judge Agreement Analysis

Primary results: `outputs/reports/deepseek_ablation_repeated_results.csv`
Secondary results: `outputs/reports/deepseek_ablation_repeated_gemini_judge_results.csv`
Matched package rows: 126

## Metric Agreement

| Metric | N | Primary Mean | Secondary Mean | Delta | Delta Std | Pearson | Spearman |
|---|---:|---:|---:|---:|---:|---:|---:|
| average_score | 126 | 3.984 | 4.029 | +0.044 | 0.368 | 0.961 | 0.782 |
| novelty | 126 | 3.500 | 3.833 | +0.333 | 0.766 | 0.869 | 0.828 |
| mechanism_clarity | 126 | 3.770 | 3.754 | -0.016 | 0.864 | 0.845 | 0.740 |
| falsifiability | 126 | 4.381 | 4.349 | -0.032 | 0.332 | 0.979 | 0.994 |
| review_score | 126 | 6.810 | 6.563 | -0.246 | 0.914 | 0.915 | 0.835 |

## Within-Topic Rank Stability

| Metric | Groups | Mean Spearman | Top-System Match Rate |
|---|---:|---:|---:|
| average_score | 18 | 0.778 | 0.889 |
| novelty | 18 | 0.848 | 1.000 |
| mechanism_clarity | 18 | 0.766 | 1.000 |
| falsifiability | 18 | 1.000 | 1.000 |
| review_score | 18 | 0.877 | 0.944 |

## System-Level Means

| Metric | System | Primary Mean | Secondary Mean | Delta | Primary Rank | Secondary Rank | Rank Delta |
|---|---|---:|---:|---:|---:|---:|---:|
| average_score | certificate_only_ablation | 4.900 | 4.878 | -0.022 | 1.0 | 1.0 | +0.0 |
| average_score | firstresearch | 4.733 | 4.744 | +0.011 | 2.0 | 3.0 | +1.0 |
| average_score | no_certificate_ablation | 0.956 | 0.889 | -0.067 | 7.0 | 7.0 | +0.0 |
| average_score | no_gate_repair_ablation | 4.267 | 4.211 | -0.056 | 5.0 | 6.0 | +1.0 |
| average_score | no_mechanism_model_ablation | 3.944 | 4.311 | +0.367 | 6.0 | 5.0 | -1.0 |
| average_score | no_novelty_boundary_repair_ablation | 4.367 | 4.333 | -0.033 | 4.0 | 4.0 | +0.0 |
| average_score | no_self_improvement_ablation | 4.722 | 4.833 | +0.111 | 3.0 | 2.0 | -1.0 |
| novelty | certificate_only_ablation | 4.944 | 4.889 | -0.056 | 1.0 | 2.5 | +1.5 |
| novelty | firstresearch | 4.444 | 4.889 | +0.444 | 2.5 | 2.5 | +0.0 |
| novelty | no_certificate_ablation | 0.833 | 0.722 | -0.111 | 7.0 | 7.0 | +0.0 |
| novelty | no_gate_repair_ablation | 2.778 | 3.111 | +0.333 | 6.0 | 6.0 | +0.0 |
| novelty | no_mechanism_model_ablation | 3.944 | 4.722 | +0.778 | 4.0 | 4.0 | +0.0 |
| novelty | no_novelty_boundary_repair_ablation | 3.111 | 3.500 | +0.389 | 5.0 | 5.0 | +0.0 |
| novelty | no_self_improvement_ablation | 4.444 | 5.000 | +0.556 | 2.5 | 1.0 | -1.5 |
| mechanism_clarity | certificate_only_ablation | 4.944 | 4.889 | -0.056 | 1.0 | 1.0 | +0.0 |
| mechanism_clarity | firstresearch | 4.889 | 4.556 | -0.333 | 2.0 | 3.0 | +1.0 |
| mechanism_clarity | no_certificate_ablation | 0.889 | 0.778 | -0.111 | 7.0 | 7.0 | +0.0 |
| mechanism_clarity | no_gate_repair_ablation | 4.389 | 4.056 | -0.333 | 5.0 | 5.0 | +0.0 |
| mechanism_clarity | no_mechanism_model_ablation | 2.056 | 3.000 | +0.944 | 6.0 | 6.0 | +0.0 |
| mechanism_clarity | no_novelty_boundary_repair_ablation | 4.444 | 4.222 | -0.222 | 4.0 | 4.0 | +0.0 |
| mechanism_clarity | no_self_improvement_ablation | 4.778 | 4.778 | +0.000 | 3.0 | 2.0 | -1.0 |
| falsifiability | certificate_only_ablation | 5.000 | 5.000 | +0.000 | 3.5 | 3.5 | +0.0 |
| falsifiability | firstresearch | 5.000 | 5.000 | +0.000 | 3.5 | 3.5 | +0.0 |
| falsifiability | no_certificate_ablation | 0.667 | 0.444 | -0.222 | 7.0 | 7.0 | +0.0 |
| falsifiability | no_gate_repair_ablation | 5.000 | 5.000 | +0.000 | 3.5 | 3.5 | +0.0 |
| falsifiability | no_mechanism_model_ablation | 5.000 | 5.000 | +0.000 | 3.5 | 3.5 | +0.0 |
| falsifiability | no_novelty_boundary_repair_ablation | 5.000 | 5.000 | +0.000 | 3.5 | 3.5 | +0.0 |
| falsifiability | no_self_improvement_ablation | 5.000 | 5.000 | +0.000 | 3.5 | 3.5 | +0.0 |
| review_score | certificate_only_ablation | 9.278 | 9.389 | +0.111 | 1.0 | 1.0 | +0.0 |
| review_score | firstresearch | 7.889 | 7.722 | -0.167 | 3.0 | 2.0 | -1.0 |
| review_score | no_certificate_ablation | 2.389 | 2.000 | -0.389 | 7.0 | 7.0 | +0.0 |
| review_score | no_gate_repair_ablation | 6.444 | 6.056 | -0.389 | 6.0 | 6.0 | +0.0 |
| review_score | no_mechanism_model_ablation | 6.556 | 6.667 | +0.111 | 5.0 | 4.0 | -1.0 |
| review_score | no_novelty_boundary_repair_ablation | 7.000 | 6.556 | -0.444 | 4.0 | 5.0 | +1.0 |
| review_score | no_self_improvement_ablation | 8.111 | 7.556 | -0.556 | 2.0 | 3.0 | +1.0 |
