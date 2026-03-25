import argparse
import csv
import json
import os

INPUT_PATH = "shared_task_dev.jsonl"
LABEL_MAP = {"SUPPORTS": "Supported", "REFUTES": "Refuted"}

TRACKER_FIELDS = [
    "example_id",
    "claim",
    "gold_label",
    "raw_evidence",
    "gold_evidence",
    "model",
    "condition",
    "model_output",
    "correct",
    "error_type",
    "notes",
]

SOURCE_FIELDS = ["example_id", "claim", "gold_label", "raw_evidence"]


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
        default=50,
        help="Number of examples per label (Supported and Refuted)",
    )
    parser.add_argument(
        "--tag",
        default="large_v1",
        help="File tag for output names, e.g. large_v1",
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
            if len(supports) >= args.per_label and len(refutes) >= args.per_label:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            label = row.get("label")
            if label == "SUPPORTS" and len(supports) < args.per_label:
                supports.append(row)
            elif label == "REFUTES" and len(refutes) < args.per_label:
                refutes.append(row)

    if len(supports) < args.per_label or len(refutes) < args.per_label:
        raise SystemExit(
            "Could not reach requested balanced count. "
            f"supports={len(supports)} refutes={len(refutes)} per_label={args.per_label}"
        )

    ordered = supports + refutes
    source_path = f"fever_{args.tag}_source.csv"
    tracker_path = f"experiment_tracker_{args.tag}.csv"

    with open(source_path, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=SOURCE_FIELDS)
        w.writeheader()
        for r in ordered:
            w.writerow(
                {
                    "example_id": r["id"],
                    "claim": r["claim"],
                    "gold_label": LABEL_MAP[r["label"]],
                    "raw_evidence": json.dumps(r["evidence"], separators=(",", ":")),
                }
            )

    with open(tracker_path, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=TRACKER_FIELDS)
        w.writeheader()
        for r in ordered:
            w.writerow(
                {
                    "example_id": r["id"],
                    "claim": r["claim"],
                    "gold_label": LABEL_MAP[r["label"]],
                    "raw_evidence": json.dumps(r["evidence"], separators=(",", ":")),
                    "gold_evidence": "",
                    "model": "",
                    "condition": "",
                    "model_output": "",
                    "correct": "",
                    "error_type": "",
                    "notes": "",
                }
            )

    print(f"Per label: {args.per_label}")
    print(f"Total source examples: {len(ordered)}")
    print(f"Wrote {source_path}")
    print(f"Wrote {tracker_path}")


if __name__ == "__main__":
    main()
