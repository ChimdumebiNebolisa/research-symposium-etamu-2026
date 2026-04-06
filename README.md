# FEVER Fact-Checking With and Without Evidence (2026 Setup)

This repository now targets a FEVER-only experiment with a strict, balanced design:

- Source data: `shared_task_dev.jsonl` (FEVER dev)
- Labels included: `Supported` and `Refuted` only
- Labels excluded: `NOT ENOUGH INFO`
- Full dataset size: 1000 claims total (500 Supported, 500 Refuted)
- Conditions: `claim_only`, `claim_plus_evidence`
- Models: `gpt-5.4`, `gpt-5.4-mini`

Each source claim expands to 4 runs (2 models x 2 conditions).

## Core scripts

- `experiment_config.py`: shared constants (models, conditions, target counts, default tag)
- `prepare_fever_wiki_pages.py`: downloads and prepares FEVER wiki shards
- `extract_fever_balanced_sample.py`: reproducible balanced FEVER sampling + provenance artifacts
- `resolve_gold_evidence.py`: resolves first FEVER evidence pointer to `gold_evidence`
- `expand_experiment_runs.py`: strict dataset validation + run expansion
- `create_pilot_runs_subset.py`: creates a small pilot run CSV from full expanded runs
- `run_fact_check_experiment.py`: OpenAI execution with resumable incremental writes
- `analyze_experiment_results.py`: grouped accuracy plus required metrics

## Canonical row fields

The pipeline now carries canonical columns:

- `claim_id`
- `claim_text`
- `true_label`
- `gold_evidence`

Legacy alias columns (`example_id`, `claim`, `gold_label`) are still written for backward compatibility.

## Required metrics

The analysis script writes:

- Accuracy by model-condition pair
- Evidence gain per model: `accuracy(claim_plus_evidence) - accuracy(claim_only)`
- Evidence Failure Rate (EFR) per model in `claim_plus_evidence`:
  - incorrect predictions / valid predictions under evidence condition

Artifacts:

- `experiment_summary_<tag>.csv`
- `experiment_metrics_<tag>.csv`

## Standard full workflow (1000 claims)

0. Prepare FEVER wiki shards first:

```powershell
python prepare_fever_wiki_pages.py
```

If remote download is blocked, provide a local archive path:

```powershell
python prepare_fever_wiki_pages.py --archive path\to\wiki-pages.zip
```

1. Extract a balanced source set:

```powershell
python extract_fever_balanced_sample.py
```

Default outputs:

- `fever_balanced_1000_v1_source.csv`
- `experiment_tracker_balanced_1000_v1.csv`
- `sample_provenance_balanced_1000_v1.csv`
- `sample_validation_balanced_1000_v1.json`

2. Resolve FEVER evidence text (requires local FEVER wiki shards):

```powershell
python resolve_gold_evidence.py
```

Default outputs:

- `experiment_tracker_with_evidence_balanced_1000_v1.csv`
- `resolve_summary_balanced_1000_v1.json`

3. Validate dataset readiness and expand runs:

```powershell
python expand_experiment_runs.py
```

Default outputs:

- `dataset_validation_balanced_1000_v1.json`
- `experiment_runs_balanced_1000_v1.csv`

Expansion aborts if rows are unusable, unbalanced, or not exactly 1000.

4. Build a small pilot from the full expanded runs:

```powershell
python create_pilot_runs_subset.py --input experiment_runs_balanced_1000_v1.csv --output experiment_runs_balanced_1000_v1_pilot.csv --pilot-claims 50
```

5. Execute pilot model runs first:

```powershell
python run_fact_check_experiment.py --input experiment_runs_balanced_1000_v1_pilot.csv --output experiment_results_balanced_1000_v1_pilot.csv
```

6. Analyze pilot results:

```powershell
python analyze_experiment_results.py --input experiment_results_balanced_1000_v1_pilot.csv --output experiment_summary_balanced_1000_v1_pilot.csv --metrics-output experiment_metrics_balanced_1000_v1_pilot.csv
```

7. Execute full model runs after pilot succeeds:

```powershell
python run_fact_check_experiment.py
```

Default output:

- `experiment_results_balanced_1000_v1.csv`

8. Analyze full results and metrics:

```powershell
python analyze_experiment_results.py
```

Default outputs:

- `experiment_summary_balanced_1000_v1.csv`
- `experiment_metrics_balanced_1000_v1.csv`
- `evidence_condition_errors_balanced_1000_v1.csv`
- `error_taxonomy_counts_balanced_1000_v1.csv`
- `example_failure_cases_balanced_1000_v1.csv`

## Pilot workflow (separate outputs)

Pilot is intentionally separated from full outputs:

```powershell
python extract_fever_balanced_sample.py --per-label 25 --seed 42 --tag balanced_50_pilot_v1
python resolve_gold_evidence.py --input experiment_tracker_balanced_50_pilot_v1.csv --output experiment_tracker_with_evidence_balanced_50_pilot_v1.csv --summary-output resolve_summary_balanced_50_pilot_v1.json
python expand_experiment_runs.py --input experiment_tracker_with_evidence_balanced_50_pilot_v1.csv --output experiment_runs_balanced_50_pilot_v1.csv --validation-output dataset_validation_balanced_50_pilot_v1.json --expected-total 50 --expected-per-label 25
python run_fact_check_experiment.py --input experiment_runs_balanced_50_pilot_v1.csv --output experiment_results_balanced_50_pilot_v1.csv
python analyze_experiment_results.py --input experiment_results_balanced_50_pilot_v1.csv --output experiment_summary_balanced_50_pilot_v1.csv --metrics-output experiment_metrics_balanced_50_pilot_v1.csv
```

## Completed run results (2026-04-05)

The following runs were completed in this workspace under the `balanced_1000_v1` tag.

### Pilot run (50 claims -> 200 rows)

Accuracy by model-condition:

- `gpt-5.4 | claim_only`: 92.00% (46/50)
- `gpt-5.4 | claim_plus_evidence`: 94.00% (47/50)
- `gpt-5.4-mini | claim_only`: 78.00% (39/50)
- `gpt-5.4-mini | claim_plus_evidence`: 96.00% (48/50)

Evidence gain / EFR:

- `gpt-5.4`: evidence gain +2.00 pp, EFR 6.00%
- `gpt-5.4-mini`: evidence gain +18.00 pp, EFR 4.00%

Artifacts:

- `experiment_results_balanced_1000_v1_pilot.csv`
- `experiment_summary_balanced_1000_v1_pilot.csv`
- `experiment_metrics_balanced_1000_v1_pilot.csv`
- `evidence_condition_errors_balanced_1000_v1_pilot.csv`
- `error_taxonomy_counts_balanced_1000_v1_pilot.csv`
- `example_failure_cases_balanced_1000_v1_pilot.csv`

### Full run (1000 claims -> 4000 rows)

Accuracy by model-condition:

- `gpt-5.4 | claim_only`: 86.30% (863/1000)
- `gpt-5.4 | claim_plus_evidence`: 94.20% (942/1000)
- `gpt-5.4-mini | claim_only`: 83.20% (832/1000)
- `gpt-5.4-mini | claim_plus_evidence`: 93.40% (934/1000)

Evidence gain / EFR:

- `gpt-5.4`: evidence gain +7.90 pp, EFR 5.80%
- `gpt-5.4-mini`: evidence gain +10.20 pp, EFR 6.60%

Taxonomy counts (evidence-condition incorrect rows):

- `gpt-5.4`: `supported_to_refuted=38`, `refuted_to_supported=20`
- `gpt-5.4-mini`: `supported_to_refuted=37`, `refuted_to_supported=29`

Artifacts:

- `experiment_results_balanced_1000_v1.csv`
- `experiment_summary_balanced_1000_v1.csv`
- `experiment_metrics_balanced_1000_v1.csv`
- `evidence_condition_errors_balanced_1000_v1.csv`
- `error_taxonomy_counts_balanced_1000_v1.csv`
- `example_failure_cases_balanced_1000_v1.csv`

## Important dependency note

Evidence resolution requires FEVER wiki shard files matching:

- `wiki-pages/wiki-pages/wiki-*.jsonl`

If these files are missing, evidence cannot be resolved, validation will fail for missing `gold_evidence`, and model execution should not proceed.
