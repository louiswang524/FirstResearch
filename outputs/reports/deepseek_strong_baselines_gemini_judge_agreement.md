# Judge Agreement Analysis

Primary results: `outputs/reports/deepseek_strong_baselines_10topics.csv`
Secondary results: `outputs/reports/deepseek_strong_baselines_gemini_judge_results.csv`
Matched package rows: 40

## Metric Agreement

| Metric | N | Primary Mean | Secondary Mean | Delta | Delta Std | Pearson | Spearman |
|---|---:|---:|---:|---:|---:|---:|---:|
| average_score | 40 | 4.345 | 4.420 | +0.075 | 0.193 | 0.865 | 0.894 |
| novelty | 40 | 3.900 | 4.125 | +0.225 | 0.570 | 0.722 | 0.749 |
| mechanism_clarity | 40 | 4.125 | 4.275 | +0.150 | 0.477 | 0.745 | 0.765 |
| falsifiability | 40 | 4.900 | 4.925 | +0.025 | 0.156 | 0.854 | 0.854 |
| review_score | 40 | 7.800 | 8.300 | +0.500 | 0.806 | 0.469 | 0.469 |

## Within-Topic Rank Stability

| Metric | Groups | Mean Spearman | Top-System Match Rate |
|---|---:|---:|---:|
| average_score | 10 | 0.888 | 0.800 |
| novelty | 10 | 0.693 | 0.900 |
| mechanism_clarity | 10 | 0.697 | 1.000 |
| falsifiability | 10 | 0.258 | 1.000 |
| review_score | 10 | 0.477 | 0.900 |

## System-Level Means

| Metric | System | Primary Mean | Secondary Mean | Delta | Primary Rank | Secondary Rank | Rank Delta |
|---|---|---:|---:|---:|---:|---:|---:|
| average_score | agent_lab | 4.120 | 4.160 | +0.040 | 4.0 | 4.0 | +0.0 |
| average_score | co_scientist | 4.180 | 4.280 | +0.100 | 3.0 | 3.0 | +0.0 |
| average_score | firstresearch | 4.760 | 4.860 | +0.100 | 1.0 | 1.0 | +0.0 |
| average_score | tree_search_scientist | 4.320 | 4.380 | +0.060 | 2.0 | 2.0 | +0.0 |
| novelty | agent_lab | 3.500 | 3.800 | +0.300 | 4.0 | 3.0 | -1.0 |
| novelty | co_scientist | 3.900 | 4.000 | +0.100 | 2.0 | 2.0 | +0.0 |
| novelty | firstresearch | 4.500 | 5.000 | +0.500 | 1.0 | 1.0 | +0.0 |
| novelty | tree_search_scientist | 3.700 | 3.700 | +0.000 | 3.0 | 4.0 | +1.0 |
| mechanism_clarity | agent_lab | 3.800 | 3.900 | +0.100 | 3.0 | 4.0 | +1.0 |
| mechanism_clarity | co_scientist | 3.700 | 4.200 | +0.500 | 4.0 | 2.5 | -1.5 |
| mechanism_clarity | firstresearch | 5.000 | 4.800 | -0.200 | 1.0 | 1.0 | +0.0 |
| mechanism_clarity | tree_search_scientist | 4.000 | 4.200 | +0.200 | 2.0 | 2.5 | +0.5 |
| falsifiability | agent_lab | 4.800 | 4.800 | +0.000 | 4.0 | 4.0 | +0.0 |
| falsifiability | co_scientist | 4.900 | 4.900 | +0.000 | 2.5 | 3.0 | +0.5 |
| falsifiability | firstresearch | 4.900 | 5.000 | +0.100 | 2.5 | 1.5 | -1.0 |
| falsifiability | tree_search_scientist | 5.000 | 5.000 | +0.000 | 1.0 | 1.5 | +0.5 |
| review_score | agent_lab | 7.500 | 8.200 | +0.700 | 4.0 | 3.0 | -1.0 |
| review_score | co_scientist | 7.800 | 8.500 | +0.700 | 2.5 | 2.0 | -0.5 |
| review_score | firstresearch | 8.100 | 7.800 | -0.300 | 1.0 | 4.0 | +3.0 |
| review_score | tree_search_scientist | 7.800 | 8.700 | +0.900 | 2.5 | 1.0 | -1.5 |
