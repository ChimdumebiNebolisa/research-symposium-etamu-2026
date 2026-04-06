import argparse
import csv
import json
import os
import random
from collections import Counter

from experiment_config import DEFAULT_TAG, EXPECTED_PER_LABEL

INPUT_PATH = "shared_task_dev.jsonl"
LABEL_MAP = {"SUPPORTS": "Supported", "REFUTES": "Refuted"}

TRACKER_FIELDS = [
    "claim_id",
    "claim_text",
    "true_label",
    "raw_evidence",
    "gold_evidence",
    "example_id",
    "claim",
    "gold_label",
    "model",
    "condition",
    "model_output",
    "correct",
    "error_type",
    "notes",
]

SOURCE_FIELDS = [
    "claim_id",
    "claim_text",
    "true_label",
    "raw_evidence",
    "example_id",
    "claim",
    "gold_label",
]

PROVENANCE_FIELDS = ["claim_id", "true_label", "seed", "input_file"]


def to_output_row(src_row):
    claim_id = str(src_row["id"])
    claim_text = src_row["claim"]
    true_label = LABEL_MAP[src_row["label"]]
    raw_evidence = json.dumps(src_row["evidence"], separators=(",", ":"))
    return {
        "claim_id": claim_id,
        "claim_text": claim_text,
        "true_label": true_label,
        "raw_evidence": raw_evidence,
        "gold_evidence": "",
        # Backward-compatible aliases used by older scripts/artifacts.
        "example_id": claim_id,
        "claim": claim_text,
        "gold_label": true_label,
        "model": "",
        "condition": "",
        "model_output": "",
        "correct": "",
        "error_type": "",
        "notes": "",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Extract a balanced FEVER sample (Supported + Refuted only)."
    )
    parser.add_argument(
        "--input", default=INPUT_PATH, help="Path to FEVER dev JSONL (shared_task_dev.jsonl)"
    )
    parser.add_argument(
        "--per-label",
        type=int,
        default=EXPECTED_PER_LABEL,
        help="Number of examples per label (Supported and Refuted)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used for reproducible balanced sampling",
    )
    parser.add_argument(
        "--tag",
        default=DEFAULT_TAG,
        help="File tag for output names",
    )
    args = parser.parse_args()

    if args.per_label <= 0:
        raise SystemExit("--per-label must be > 0")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    supports = []
    refutes = []

    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            label = row.get("label")
            if label == "SUPPORTS":
                supports.append(row)
            elif label == "REFUTES":
                refutes.append(row)

    if len(supports) < args.per_label or len(refutes) < args.per_label:
        raise SystemExit(
            "Could not reach requested balanced count. "
            f"supports={len(supports)} refutes={len(refutes)} per_label={args.per_label}"
        )

    rng = random.Random(args.seed)
    sampled_supports = rng.sample(supports, args.per_label)
    sampled_refutes = rng.sample(refutes, args.per_label)
    ordered = sampled_supports + sampled_refutes
    rng.shuffle(ordered)

    structured_rows = [to_output_row(r) for r in ordered]
    source_path = f"fever_{args.tag}_source.csv"
    tracker_path = f"experiment_tracker_{args.tag}.csv"
    provenance_path = f"sample_provenance_{args.tag}.csv"
    validation_path = f"sample_validation_{args.tag}.json"

    with open(source_path, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=SOURCE_FIELDS)
        w.writeheader()
        for row in structured_rows:
            w.writerow({k: row.get(k, "") for k in SOURCE_FIELDS})

    with open(tracker_path, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=TRACKER_FIELDS)
        w.writeheader()
        for row in structured_rows:
            w.writerow({k: row.get(k, "") for k in TRACKER_FIELDS})

    with open(provenance_path, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=PROVENANCE_FIELDS)
        w.writeheader()
        for row in structured_rows:
            w.writerow(
                {
                    "claim_id": row["claim_id"],
                    "true_label": row["true_label"],
                    "seed": args.seed,
                    "input_file": args.input,
                }
            )

    counts = Counter(row["true_label"] for row in structured_rows)
    with open(validation_path, "w", encoding="utf-8") as out:
        json.dump(
            {
                "input_file": args.input,
                "seed": args.seed,
                "per_label_requested": args.per_label,
                "total_rows": len(structured_rows),
                "label_counts": dict(counts),
                "output_source_csv": source_path,
                "output_tracker_csv": tracker_path,
                "output_provenance_csv": provenance_path,
            },
            out,
            indent=2,
        )

    print(f"Per label: {args.per_label}")
    print(f"Total source examples: {len(structured_rows)}")
    print(f"Label counts: {dict(counts)}")
    print(f"Seed: {args.seed}")
    print(f"Wrote {source_path}")
    print(f"Wrote {tracker_path}")
    print(f"Wrote {provenance_path}")
    print(f"Wrote {validation_path}")


if __name__ == "__main__":
    main()
