# FEVER Evidence-Aware Fact-Checking Pipeline

## Summary
This repository is a research pipeline for evaluating whether adding gold evidence improves LLM fact-checking on FEVER claims. It is built for a symposium or judging context (results reporting) and for contributors who want to reproduce or extend the experiment scripts.

## Status
- Current state: active research code, script-driven, no web app.
- Completed artifacts in repo: pilot and full runs for the balanced_1000_v1 tag.
- Not present: automated tests, deployment config, packaged CLI, pinned environment lock file.

## Demo
- Live app: MISSING (this repo is not an application service).
- Demo video: MISSING.
- Screenshots: MISSING.

## Problem
Fact-checking models can perform differently when given evidence versus claim text alone. This project measures that gap on a balanced FEVER subset and records both accuracy and evidence-related failure patterns.

## Solution
The repository implements a strict CSV pipeline:
1. Sample a balanced FEVER subset.
2. Resolve gold evidence from local FEVER wiki shards.
3. Expand each claim into model x condition runs.
4. Call OpenAI chat completions for each run.
5. Analyze accuracy, evidence gain, and evidence failure taxonomy.

## Core Features
- Balanced sampling for Supported and Refuted claims only.
- Strict validation before expansion (fails fast if evidence is missing or labels are unbalanced).
- Two model conditions per claim:
  - claim_only
  - claim_plus_evidence
- Resume-safe execution in result generation (reuses valid prior rows).
- Output artifacts for:
  - grouped summaries
  - evidence gain and evidence failure rate
  - evidence-condition error rows
  - error taxonomy counts
  - failure examples

## User Flow
1. Prepare local FEVER wiki shards.
2. Extract balanced source and tracker CSV files.
3. Resolve evidence text into gold_evidence.
4. Validate and expand into run matrix.
5. Run pilot subset first.
6. Run full set.
7. Analyze result CSV into summary and metrics CSV files.

## Tech Stack
- Language: Python (standard library scripts)
- External package: openai (see requirements-openai.txt)
- Data format: CSV, JSON, JSONL
- External data dependency:
  - FEVER dev set (shared_task_dev.jsonl)
  - FEVER wiki shards at wiki-pages/wiki-pages/wiki-*.jsonl

## Architecture Overview
~~~mermaid
flowchart TD
    A[shared_task_dev.jsonl] --> B[extract_fever_balanced_sample.py]
    B --> C[experiment_tracker_balanced_1000_v1.csv]
    C --> D[resolve_gold_evidence.py]
    D --> E[experiment_tracker_with_evidence_balanced_1000_v1.csv]
    E --> F[expand_experiment_runs.py]
    F --> G[experiment_runs_balanced_1000_v1.csv]
    G --> H[create_pilot_runs_subset.py]
    H --> I[experiment_runs_balanced_1000_v1_pilot.csv]
    I --> J[run_fact_check_experiment.py]
    G --> J
    J --> K[experiment_results_*.csv]
    K --> L[analyze_experiment_results.py]
    L --> M[summary metrics taxonomy failures]
~~~

### Data Model Notes
- Canonical columns used across scripts:
  - claim_id
  - claim_text
  - true_label
  - gold_evidence
- Backward-compatible aliases are still written:
  - example_id
  - claim
  - gold_label

## Folder Structure (Current, Grounded)
~~~text
.
|- analyze_experiment_results.py
|- create_pilot_runs_subset.py
|- expand_experiment_runs.py
|- experiment_config.py
|- extract_fever_balanced_sample.py
|- prepare_fever_wiki_pages.py
|- resolve_gold_evidence.py
|- run_fact_check_experiment.py
|- requirements-openai.txt
|- shared_task_dev.jsonl
|- wiki-pages/                      # local FEVER shards, ignored by git
|- archive_old_pipeline/            # historical pipeline artifacts
|  |- legacy_large_v1_clean/
|- experiment_*_balanced_1000_v1*.csv
|- sample_*_balanced_*.json
|- dataset_validation_*.json
|- resolve_summary_balanced_1000_v1.json
|- professor_update.md
|- README.md
~~~

## Local Setup

### Prerequisites
- Python 3 installed and available as python.
- FEVER dev JSONL file in repo root: shared_task_dev.jsonl.
- OpenAI API key.
- Sufficient disk space for FEVER wiki shard files.

### Install
~~~powershell
python -m pip install -r requirements-openai.txt
~~~

### Environment Variables
- Required for API execution:
  - OPENAI_API_KEY
- The runner first checks process environment, then falls back to .env in project root.

Example .env entry:
~~~text
OPENAI_API_KEY=your_key_here
~~~

### Database Setup
No database is used in this repository.

### Run Commands (Full Flow)
1) Prepare FEVER wiki data
~~~powershell
python prepare_fever_wiki_pages.py
~~~

If remote download fails, pass a local archive:
~~~powershell
python prepare_fever_wiki_pages.py --archive path\to\wiki-pages.zip
~~~

2) Build balanced source and tracker
~~~powershell
python extract_fever_balanced_sample.py
~~~

3) Resolve gold evidence
~~~powershell
python resolve_gold_evidence.py
~~~

4) Validate and expand to run matrix
~~~powershell
python expand_experiment_runs.py
~~~

5) Build pilot subset from expanded runs
~~~powershell
python create_pilot_runs_subset.py --input experiment_runs_balanced_1000_v1.csv --output experiment_runs_balanced_1000_v1_pilot.csv --pilot-claims 50
~~~

6) Run pilot
~~~powershell
python run_fact_check_experiment.py --input experiment_runs_balanced_1000_v1_pilot.csv --output experiment_results_balanced_1000_v1_pilot.csv
~~~

7) Analyze pilot
~~~powershell
python analyze_experiment_results.py --input experiment_results_balanced_1000_v1_pilot.csv --output experiment_summary_balanced_1000_v1_pilot.csv --metrics-output experiment_metrics_balanced_1000_v1_pilot.csv
~~~

8) Run full
~~~powershell
python run_fact_check_experiment.py
~~~

9) Analyze full
~~~powershell
python analyze_experiment_results.py
~~~

## Scripts
- experiment_config.py
  - Shared constants: models, conditions, expected counts, wiki shard paths.
- prepare_fever_wiki_pages.py
  - Downloads or reuses FEVER wiki zip and prepares shard files.
- extract_fever_balanced_sample.py
  - Samples balanced FEVER claims and writes source/tracker/provenance/validation artifacts.
- resolve_gold_evidence.py
  - Resolves first evidence pointer to gold_evidence text.
- expand_experiment_runs.py
  - Validates source rows and expands each claim into model-condition rows.
- create_pilot_runs_subset.py
  - Selects first N unique claim IDs from expanded full runs for pilot.
- run_fact_check_experiment.py
  - Calls OpenAI API, writes incremental CSV, supports resume behavior.
- analyze_experiment_results.py
  - Produces grouped summary plus metrics and error analysis CSV files.

## Testing and Verification
Automated unit or integration tests are not present.

Current verification model is artifact-based:
- sample_validation_balanced_1000_v1.json confirms 500/500 balance.
- dataset_validation_balanced_1000_v1.json confirms ready_for_expansion=true.
- experiment_results_balanced_1000_v1.csv contains 4000 rows.
- experiment_results_balanced_1000_v1_pilot.csv contains 200 rows.

Quick manual checks:
~~~powershell
python analyze_experiment_results.py --input experiment_results_balanced_1000_v1.csv --output experiment_summary_balanced_1000_v1.csv --metrics-output experiment_metrics_balanced_1000_v1.csv
~~~

## Results Snapshot (Committed Artifacts)

### Dataset Pipeline Counts
| Artifact | Rows |
|---|---:|
| fever_balanced_1000_v1_source.csv | 1000 |
| experiment_tracker_balanced_1000_v1.csv | 1000 |
| experiment_tracker_with_evidence_balanced_1000_v1.csv | 1000 |
| experiment_runs_balanced_1000_v1.csv | 4000 |
| experiment_results_balanced_1000_v1.csv | 4000 |
| experiment_runs_balanced_1000_v1_pilot.csv | 200 |
| experiment_results_balanced_1000_v1_pilot.csv | 200 |

### Full Run Accuracy (balanced_1000_v1)
| Model + Condition | Accuracy | Correct / Valid |
|---|---:|---:|
| gpt-5.4 + claim_only | 86.30% | 863 / 1000 |
| gpt-5.4 + claim_plus_evidence | 94.20% | 942 / 1000 |
| gpt-5.4-mini + claim_only | 83.20% | 832 / 1000 |
| gpt-5.4-mini + claim_plus_evidence | 93.40% | 934 / 1000 |

~~~mermaid
pie showData
    title Full Run Correct Predictions (out of 1000 each)
    "gpt-5.4 claim_only" : 863
    "gpt-5.4 claim_plus_evidence" : 942
    "gpt-5.4-mini claim_only" : 832
    "gpt-5.4-mini claim_plus_evidence" : 934
~~~

### Pilot Run Accuracy (balanced_1000_v1_pilot)
| Model + Condition | Accuracy | Correct / Valid |
|---|---:|---:|
| gpt-5.4 + claim_only | 92.00% | 46 / 50 |
| gpt-5.4 + claim_plus_evidence | 94.00% | 47 / 50 |
| gpt-5.4-mini + claim_only | 78.00% | 39 / 50 |
| gpt-5.4-mini + claim_plus_evidence | 96.00% | 48 / 50 |

### Evidence Gain and Evidence Failure Rate
| Split | Model | Evidence Gain (pp) | Evidence Failure Rate (%) |
|---|---|---:|---:|
| Full | gpt-5.4 | 7.90 | 5.80 |
| Full | gpt-5.4-mini | 10.20 | 6.60 |
| Pilot | gpt-5.4 | 2.00 | 6.00 |
| Pilot | gpt-5.4-mini | 18.00 | 4.00 |

### Evidence-Condition Error Taxonomy (Full)
| Model | Taxonomy | Count |
|---|---|---:|
| gpt-5.4 | supported_to_refuted | 38 |
| gpt-5.4 | refuted_to_supported | 20 |
| gpt-5.4-mini | supported_to_refuted | 37 |
| gpt-5.4-mini | refuted_to_supported | 29 |

## Deployment
No deployment configuration is present (no Dockerfile, compose file, CI pipeline, or hosting config).

## Known Limitations
- No automated tests.
- No packaged command interface; scripts are run directly.
- .env is local and ignored; environment setup is manual.
- FEVER wiki download may fail in some environments; local archive fallback is required.
- Resolver summary and dataset validation are aligned for the final balanced_1000_v1 artifacts.
- Some older pilot artifacts (balanced_50_pilot_v1) show a failed path due to missing evidence, while the successful pilot results come from balanced_1000_v1_pilot.

## Future Improvements (Implied by Current Repo)
- Add automated tests for each pipeline stage.
- Add resolver normalization/fallback logic for Unicode page-title mismatches.
- Add reproducible environment pinning beyond openai>=1.0.0.
- Add a lightweight script to generate plots directly from summary/metrics CSV artifacts.

## License
License is not yet specified in this repository.

## Repository Housekeeping
Legacy large_v1_clean artifacts were moved to:
- archive_old_pipeline/legacy_large_v1_clean/
