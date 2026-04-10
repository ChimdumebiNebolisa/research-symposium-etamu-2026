# FEVER Evidence-Aware Fact-Checking: Presentation Dossier

## Abstract
This project asks a simple question: if we give an AI model the claim plus trusted evidence, does it fact-check better than when it sees the claim alone?

We tested this on a balanced FEVER sample of 10,000 claims (5,000 Supported, 5,000 Refuted) and evaluated two models (`gpt-5.4`, `gpt-5.4-mini`) in two settings (`claim_only`, `claim_plus_evidence`).

Main finding in plain English: evidence helps a lot. Across 40,000 model decisions, accuracy rises from 86.68% (claim only) to 95.79% (claim + evidence), an overall +9.11 percentage-point gain.

## Background
Public discussions around AI fact-checking often focus on one of two risks:
1. The model guesses from general world knowledge and gets details wrong.
2. The model is given evidence but still misreads it.

This experiment was designed for a non-technical decision question:
- If we are building a real fact-checking workflow for people, should we invest in evidence retrieval and evidence-aware prompting?

The benchmark answer from this study is yes.

## Methodology
### Dataset Used
- Source corpus: FEVER development set (`shared_task_dev.jsonl`)
- Included labels: `SUPPORTS`, `REFUTES`
- Excluded label: `NOT ENOUGH INFO`
- Final balanced sample: 10,000 claims total
  - 5,000 Supported
  - 5,000 Refuted
- Sampling seed: 42

Validation artifacts:
- `sample_validation_balanced_10000_v1.json`
- `dataset_validation_balanced_10000_v1.json`

### How the Dataset Was Used
1. Sampled 10,000 balanced claims from FEVER.
2. Resolved FEVER evidence pointers into readable text from local wiki shards.
3. Expanded each claim into 4 evaluation rows:
   - `gpt-5.4` + `claim_only`
   - `gpt-5.4` + `claim_plus_evidence`
   - `gpt-5.4-mini` + `claim_only`
   - `gpt-5.4-mini` + `claim_plus_evidence`
4. Total run size: 40,000 model decisions.
5. Scored each decision as correct/incorrect against FEVER ground truth.

### Pilot Testing Included
Before full execution, a pilot run was performed on 50 claims (200 model-condition rows):
- File set: `*_balanced_10000_v1_pilot.csv`
- Purpose: validate prompts, pipeline consistency, and signal direction before full spend.

Pilot summary (200 rows):
- Overall: 88.00%
- Claim only: 81.00%
- Claim + evidence: 95.00%

## Graphic
```mermaid
flowchart LR
    A[FEVER dev set] --> B[Balanced sample 10,000]
    B --> C[Resolve gold evidence]
    C --> D[Expand to 40,000 runs]
    D --> E[gpt-5.4 and gpt-5.4-mini]
    E --> F[claim_only vs claim_plus_evidence]
    F --> G[Scoring and error analysis]
```

## Results
### Full 10k Run (40,000 model-condition decisions)
From `experiment_summary_balanced_10000_v1.csv` and `experiment_metrics_balanced_10000_v1.csv`:

- Overall accuracy: 91.23% (36,494 / 40,000)
- Claim only: 86.68% (17,336 / 20,000)
- Claim + evidence: 95.79% (19,158 / 20,000)
- Net evidence gain (overall): +9.11 percentage points

### Model-by-Model Performance
- `gpt-5.4`
  - Claim only: 88.69%
  - Claim + evidence: 96.04%
  - Evidence gain: +7.35 pp
  - Evidence failure rate: 3.96%

- `gpt-5.4-mini`
  - Claim only: 84.67%
  - Claim + evidence: 95.54%
  - Evidence gain: +10.87 pp
  - Evidence failure rate: 4.46%

### Concrete 5.4 vs 5.4-mini Tradeoffs
This study does not show one model is universally better in every framing. It shows different strengths.

What `gpt-5.4` does better in this setup:
- Higher baseline accuracy when evidence is absent (88.69% vs 84.67%)
- Slightly lower evidence-condition failure rate (3.96% vs 4.46%)
- Slightly higher absolute evidence-condition accuracy (96.04% vs 95.54%)

What `gpt-5.4-mini` does better in this setup:
- Larger improvement once evidence is provided (+10.87 pp vs +7.35 pp)
- Strong evidence-conditioned performance close to `gpt-5.4` while gaining more from evidence relative to its baseline

Plain-language interpretation:
- If evidence may be missing or weak, `gpt-5.4` is safer.
- If evidence is consistently available and good, `gpt-5.4-mini` narrows the gap and benefits more from that evidence.

### Theme of Questions It Got Wrong
Error-theme analysis on full 10k errors (3,506 incorrect decisions):
- Number/date-heavy claims: 1,085 errors (~30.95%)
- Negation-heavy claims (`not`, `only`, `except`): 279 errors (~7.95%)
- Comparative wording (`more/less/first/last/before/after`): 213 errors (~6.08%)

Frequent mistake topics in claim text:
- Dates, birth/death timing, and release years (`born`, `released`, months)
- Media metadata (film, album, series, song)
- Identity/role statements and short factual qualifiers

Evidence-direction taxonomy in full 10k evidence condition:
- `gpt-5.4`: 396 evidence errors total
  - supported_to_refuted: 238
  - refuted_to_supported: 158
- `gpt-5.4-mini`: 446 evidence errors total
  - supported_to_refuted: 201
  - refuted_to_supported: 245

## Conclusion
For a broad audience, the takeaway is straightforward:
1. Evidence-aware prompting substantially improves fact-checking quality.
2. This improvement is consistent in pilot and full-scale runs.
3. `gpt-5.4` is stronger without evidence; `gpt-5.4-mini` gains more when evidence is supplied.
4. The hardest remaining failures are not random; they cluster around dates, numbers, negation, and comparison language.

In practical terms, if this is deployed for real users, the system should prioritize high-quality evidence retrieval and extra safeguards for number/date/negation claims.

## Appendix: Key Files
- Full results: `experiment_results_balanced_10000_v1.csv`
- Full summary: `experiment_summary_balanced_10000_v1.csv`
- Full metrics: `experiment_metrics_balanced_10000_v1.csv`
- Full taxonomy counts: `error_taxonomy_counts_balanced_10000_v1.csv`
- Pilot summary: `experiment_summary_balanced_10000_v1_pilot.csv`
- Pilot metrics: `experiment_metrics_balanced_10000_v1_pilot.csv`
