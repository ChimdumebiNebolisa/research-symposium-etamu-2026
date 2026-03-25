import csv
import os
import argparse

INPUT_PATH = "experiment_tracker_with_evidence.csv"
OUTPUT_PATH = "experiment_runs.csv"

RUNS = [
    ("GPT-4.1", "claim_only"),
    ("GPT-4.1", "claim_plus_evidence"),
    ("GPT-4.1 mini", "claim_only"),
    ("GPT-4.1 mini", "claim_plus_evidence"),
]

KEEP = ("example_id", "claim", "gold_label", "gold_evidence", "raw_evidence")
OUT_FIELDS = [
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


def main():
    parser = argparse.ArgumentParser(
        description="Expand source tracker rows into model x condition experiment runs."
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Input tracker-with-evidence CSV path")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output experiment runs CSV path")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    sources = []
    with open(args.input, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            sources.append(row)

    expanded = []
    for row in sources:
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

    print(f"Source rows: {len(sources)}")
    print(f"Experiment rows written: {len(expanded)}")
    print(f"Wrote {args.output}")
    print()
    print("Preview (first 8 rows: example_id, model, condition):")
    for r in expanded[:8]:
        print(
            f"  id={r['example_id']!r} model={r['model']!r} condition={r['condition']!r}"
        )


if __name__ == "__main__":
    main()
