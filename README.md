# FEVER Fact-Checking With and Without Evidence

## Plain-English overview

This project tests whether language models get better at fact-checking when you give them the *correct evidence*, and whether they still make mistakes anyway.

The dataset source is **FEVER development data**.

## Research question

When a model is asked to judge a claim:

- Does accuracy improve when we provide the gold evidence text?
- Even with correct evidence, what kinds of mistakes still happen?

## Why this matters

If evidence helps a lot, that supports the idea that fact-checking tools should focus on retrieving and showing reliable evidence.  
If errors still happen with correct evidence, that means we also need to understand model failure modes (not just better retrieval).

## How the experiment works

- **Claim**: a short statement that is either true or false.
- **Evidence**: a trusted sentence from FEVER’s linked Wikipedia evidence (“gold evidence”).
- **Labels (ground truth)**:
  - **Supported**: the claim is true based on the gold evidence.
  - **Refuted**: the claim is false based on the gold evidence.
- **Conditions (what the model sees)**:
  - **claim_only**: the model sees only the claim.
  - **claim_plus_evidence**: the model sees the claim + the gold evidence sentence.
- **Models tested (same runs, same prompts, different models)**:
  - **GPT-4.1**
  - **GPT-4.1 mini**

Each source example is expanded into **4 runs** (2 models × 2 conditions).

## Current pipeline

- **Source extraction**: sample FEVER dev examples (Supported/Refuted only) into a source CSV.
- **Evidence resolution**: turn the first FEVER evidence pointer into readable `gold_evidence` text using local wiki shards.
- **Experiment expansion**: expand each source row into the 4 runs (models × conditions).
- **Model evaluation**: run a simple prompt that outputs only `Supported` or `Refuted`, save outputs and correctness.
- **Summary analysis**: compute accuracy overall and by model/condition.

## Current progress

- **Earlier pilot (completed)**: a small 10-example / 40-run pilot was run earlier to confirm the pipeline works.
- **Main current result (focus)**: the cleaned larger run below is the current source of truth.

Data cleaning note:
- One source example had unresolved evidence due to a wiki page title mismatch/missing page:
  - **Dropped example_id `197381`** (Simón Bolívar page title issue) so the cleaned dataset stayed consistent.

## Latest results (cleaned larger run)

Cleaned large run size:
- **99 source examples**
- **396 total runs**
- **371 correct**
- **93.69% overall accuracy**

Accuracy by condition:
- **claim_only**: **89.90%** (178/198)
- **claim_plus_evidence**: **97.47%** (193/198)

Accuracy by model:
- **GPT-4.1**: **93.94%** (186/198)
- **GPT-4.1 mini**: **93.43%** (185/198)

Accuracy by model + condition:
- **GPT-4.1 | claim_only**: **91.92%**
- **GPT-4.1 | claim_plus_evidence**: **95.96%**
- **GPT-4.1 mini | claim_only**: **87.88%**
- **GPT-4.1 mini | claim_plus_evidence**: **98.99%**

## Key takeaways (careful interpretation)

- **Fact:** Adding correct evidence improves accuracy a lot in this run (89.90% → 97.47%).
- **Fact:** Errors still happen even with correct evidence (there are still incorrect rows under `claim_plus_evidence`).
- **Interpretation (tentative):** The smaller model (**GPT-4.1 mini**) appears to benefit more from evidence, because its `claim_only` accuracy is lower and its `claim_plus_evidence` accuracy is very high.

## Limitations

- This is still a limited sample from FEVER dev, so don’t treat these numbers as a final conclusion.
- Evidence resolution currently uses the **first** FEVER evidence pointer (not all evidence sentences).
- Some “errors” may be driven by ambiguous wording in claims, evidence phrasing, or edge cases in FEVER.

## Next step

Do error analysis on the failed rows from the cleaned large run:
- Start with `experiment_results_large_v1_clean.csv`
- Filter to rows where `correct == "No"`
- Group mistakes by pattern (examples: date errors, negation, entity mix-ups, ignoring evidence, etc.)

## Project file overview (practical)

Main cleaned large-run artifacts:
- `fever_large_v1_source_clean.csv`: the 99 source claims (Supported/Refuted only)
- `resolved_gold_evidence_large_v1_clean.csv`: source rows + resolved `gold_evidence` (cleaned)
- `experiment_runs_large_v1_clean.csv`: expanded 396 runs (models × conditions)
- `experiment_results_large_v1_clean.csv`: model outputs + correctness for the 396 runs
- `experiment_summary_large_v1_clean.csv`: accuracy breakdowns used in the numbers above

Key scripts:
- `extract_fever_balanced_sample.py`: build a balanced FEVER sample
- `resolve_gold_evidence.py`: resolve gold evidence sentences from local wiki shards
- `expand_experiment_runs.py`: expand sources into runs
- `run_fact_check_experiment.py`: run the evaluation prompt and save results
- `analyze_experiment_results.py`: summarize results into a small CSV
