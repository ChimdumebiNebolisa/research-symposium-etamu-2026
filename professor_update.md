# Professor Update (1000-Claim Migration Status)

Date: 2026-04-05
Repo: research-symposium-etamu-2026 (branch: main)

## 1) Migration scope now implemented

The codebase has been migrated to the requested FEVER setup:

- Balanced FEVER dataset target: 1000 total (500 Supported, 500 Refuted)
- Exclude `NOT ENOUGH INFO`
- Conditions: `claim_only`, `claim_plus_evidence`
- Models: `gpt-5.4`, `gpt-5.4-mini`
- Centralized model/config constants in `experiment_config.py`
- Canonical row fields enforced across pipeline:
  - `claim_id`, `claim_text`, `true_label`, `gold_evidence`
- Strict validation before expansion with a saved JSON artifact
- Analysis extended with:
  - Accuracy by model-condition
  - Evidence gain per model
  - Evidence Failure Rate (EFR)

## 2) Artifacts generated in this update

Full-sample extraction artifacts:

- `fever_balanced_1000_v1_source.csv`
- `experiment_tracker_balanced_1000_v1.csv`
- `sample_provenance_balanced_1000_v1.csv`
- `sample_validation_balanced_1000_v1.json`

Pilot extraction artifacts (separated):

- `fever_balanced_50_pilot_v1_source.csv`
- `experiment_tracker_balanced_50_pilot_v1.csv`
- `sample_provenance_balanced_50_pilot_v1.csv`
- `sample_validation_balanced_50_pilot_v1.json`

Validation artifacts before expansion:

- `dataset_validation_balanced_50_pilot_v1.json`
- `dataset_validation_balanced_1000_v1.json`

## 3) Current blocker (execution not yet possible)

Evidence resolution is blocked because FEVER wiki shards are missing locally.

Expected files:

- `wiki-pages/wiki-pages/wiki-*.jsonl`

Observed resolver outcome:

- `resolve_gold_evidence.py` exits with: `No wiki shards at wiki-pages\\wiki-pages\\wiki-*.jsonl`

Because `gold_evidence` cannot be populated, strict validation correctly blocks expansion for both pilot and full sets:

- Pilot validation: 0 usable rows out of 50 (all missing `gold_evidence`)
- Full validation: 0 usable rows out of 1000 (all missing `gold_evidence`)

## 4) Immediate next step once blocker is removed

After FEVER wiki shards are added, run:

1. `resolve_gold_evidence.py` for pilot and full trackers
2. `expand_experiment_runs.py` to produce expanded runs after validation passes
3. `run_fact_check_experiment.py` for pilot first, then full
4. `analyze_experiment_results.py` to produce summary + metric artifacts

At that point, we can report final pilot/full accuracies, evidence gain, and EFR from the new 1000-claim design.
