# FEVER Fact-Checking Experiment (Symposium Project)

## What this project is testing

This project asks a simple question:

Do language models get better at fact-checking when they are given correct evidence, and do they still make mistakes anyway?

To test that, each claim is run in two settings:
- one where the model sees only the claim
- one where the model sees the claim plus trusted gold evidence

## How the experiment works

1. Take examples from FEVER development data.
2. Keep only claims labeled `Supported` or `Refuted`.
3. Build a source tracker with claim text, label, and evidence pointers.
4. Resolve the first evidence pointer into readable sentence text (`gold_evidence`).
5. Expand each source claim into 4 runs:
   - GPT-4.1 + claim_only
   - GPT-4.1 + claim_plus_evidence
   - GPT-4.1 mini + claim_only
   - GPT-4.1 mini + claim_plus_evidence
6. Run prompts and store model outputs.
7. Score each run as correct or incorrect and summarize results.

## Label meanings

- `Supported`: the claim is true based on the gold evidence.
- `Refuted`: the claim is false based on the gold evidence.

## Condition meanings

- `claim_only`: model sees only the claim text.
- `claim_plus_evidence`: model sees the claim text and the gold evidence sentence.

## Model variants

- `GPT-4.1`: larger model variant.
- `GPT-4.1 mini`: smaller/faster variant.

## Current Pipeline Status

The core pipeline is working end-to-end for the pilot:
- FEVER sampling done
- source examples selected
- evidence resolved into readable text
- experiment runs expanded
- model outputs collected
- summary generated

## Current Progress

Current completed run (10 source examples -> 40 total runs):
- Total runs: 40
- Valid predictions: 40
- Correct: 39
- Overall accuracy: 97.5%
- Incorrect cases: 1
  - `example_id`: 89891
  - claim: "Damon Albarn's debut album was released in 2011."
  - gold label: `Refuted`
  - model: `GPT-4.1 mini`
  - condition: `claim_only`
  - model output: `Supported`

## What this result suggests

In this small pilot, giving evidence appears to help consistency: the only mistake happened in `claim_only`, while all `claim_plus_evidence` runs were correct.

## Important limitation

This is still a small sample, so the result is promising but not enough to make a strong conclusion yet.

## Next Step

Scale to a much larger balanced sample (Supported/Refuted), keep the same experiment design, and continue reporting results as the dataset grows.
