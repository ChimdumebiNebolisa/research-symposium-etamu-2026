import csv
import json
import os
import argparse
from collections import Counter

from experiment_config import (
    DEFAULT_TAG,
    EXPECTED_PER_LABEL,
    EXPECTED_TOTAL,
    RUNS,
    VALID_LABELS,
)

INPUT_PATH = f"experiment_tracker_with_evidence_{DEFAULT_TAG}.csv"
OUTPUT_PATH = f"experiment_runs_{DEFAULT_TAG}.csv"
VALIDATION_PATH = f"dataset_validation_{DEFAULT_TAG}.json"

KEEP = (
    "claim_id",
    "claim_text",
    "true_label",
    "example_id",
    "claim",
    "gold_label",
    "gold_evidence",
    "raw_evidence",
)
OUT_FIELDS = [
    "claim_id",
    "claim_text",
    "true_label",
    "example_id",
    "claim",
    "gold_label",
    "gold_evidence",
    "raw_evidence",
    "model",
    "condition",
    "model_output",
    "correct",
    "error_type",
    "notes",
]


def normalize_source_row(row):
    claim_id = (row.get("claim_id") or row.get("example_id") or "").strip()
    claim_text = (row.get("claim_text") or row.get("claim") or "").strip()
    true_label = (row.get("true_label") or row.get("gold_label") or "").strip()
    gold_evidence = (row.get("gold_evidence") or "").strip()
    raw_evidence = row.get("raw_evidence") or ""

    out = {k: row.get(k, "") for k in KEEP}
    out["claim_id"] = claim_id
    out["claim_text"] = claim_text
    out["true_label"] = true_label
    out["example_id"] = claim_id
    out["claim"] = claim_text
    out["gold_label"] = true_label
    out["gold_evidence"] = gold_evidence
    out["raw_evidence"] = raw_evidence
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Expand source tracker rows into model x condition experiment runs."
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Input tracker-with-evidence CSV path")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output experiment runs CSV path")
    parser.add_argument(
        "--validation-output",
        default=VALIDATION_PATH,
        help="Output JSON file for dataset validation details",
    )
    parser.add_argument(
        "--expected-total",
        type=int,
        default=EXPECTED_TOTAL,
        help="Expected number of usable source rows before expansion",
    )
    parser.add_argument(
        "--expected-per-label",
        type=int,
        default=EXPECTED_PER_LABEL,
        help="Expected count per label (Supported and Refuted)",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if not os.path.isfile(args.input):
        raise SystemExit(
            f"Input file not found: {args.input}. "
            "Run resolve_gold_evidence.py first so gold_evidence is populated."
        )

    sources = []
    with open(args.input, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            sources.append(normalize_source_row(row))

    seen_ids = set()
    usable_sources = []
    unusable = []
    label_counts = Counter()

    for row in sources:
        claim_id = row["claim_id"]
        claim_text = row["claim_text"]
        true_label = row["true_label"]
        gold_evidence = row["gold_evidence"]

        if not claim_id:
            unusable.append({"claim_id": "", "reason": "missing_claim_id"})
            continue
        if claim_id in seen_ids:
            unusable.append({"claim_id": claim_id, "reason": "duplicate_claim_id"})
            continue
        if not claim_text:
            unusable.append({"claim_id": claim_id, "reason": "missing_claim_text"})
            continue
        if true_label not in VALID_LABELS:
            unusable.append({"claim_id": claim_id, "reason": f"invalid_true_label:{true_label}"})
            continue
        if not gold_evidence:
            unusable.append({"claim_id": claim_id, "reason": "missing_gold_evidence"})
            continue

        seen_ids.add(claim_id)
        label_counts[true_label] += 1
        usable_sources.append(row)

    is_expected_total = len(usable_sources) == args.expected_total
    is_balanced = (
        label_counts.get("Supported", 0) == args.expected_per_label
        and label_counts.get("Refuted", 0) == args.expected_per_label
    )
    validation_payload = {
        "input_csv": args.input,
        "source_rows": len(sources),
        "usable_rows": len(usable_sources),
        "unusable_rows": len(unusable),
        "expected_total": args.expected_total,
        "expected_per_label": args.expected_per_label,
        "label_counts": dict(label_counts),
        "is_expected_total": is_expected_total,
        "is_balanced": is_balanced,
        "ready_for_expansion": is_expected_total and is_balanced and not unusable,
        "unusable_preview": unusable[:50],
    }
    with open(args.validation_output, "w", encoding="utf-8") as out:
        json.dump(validation_payload, out, indent=2)

    if not validation_payload["ready_for_expansion"]:
        print("Dataset validation failed. Expansion aborted.")
        print(f"Wrote {args.validation_output}")
        print(
            f"usable_rows={len(usable_sources)} expected_total={args.expected_total} "
            f"label_counts={dict(label_counts)} unusable_rows={len(unusable)}"
        )
        raise SystemExit(1)

    expanded = []
    for row in usable_sources:
        base = {k: row.get(k, "") for k in KEEP}
        for model, condition in RUNS:
            out = dict(base)
            out["model"] = model
            out["condition"] = condition
            out["model_output"] = ""
            out["correct"] = ""
            out["error_type"] = ""
            out["notes"] = ""
            expanded.append(out)

    with open(args.output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=OUT_FIELDS)
        w.writeheader()
        w.writerows(expanded)

    print(f"Source rows: {len(usable_sources)}")
    print(f"Experiment rows written: {len(expanded)}")
    print(f"Wrote {args.output}")
    print(f"Wrote {args.validation_output}")
    print()
    print("Preview (first 8 rows: claim_id, model, condition):")
    for r in expanded[:8]:
        print(f"  id={r['claim_id']!r} model={r['model']!r} condition={r['condition']!r}")


if __name__ == "__main__":
    main()
