import csv
import os
import argparse

TRACKER_PATH = "AI Fact checker - Experiment Tracker.csv"
RESOLVED_PATH = "resolved_gold_evidence.csv"
OUTPUT_PATH = "experiment_tracker_with_evidence.csv"


def main():
    parser = argparse.ArgumentParser(
        description="Merge resolved gold evidence into a tracker CSV by example_id."
    )
    parser.add_argument("--tracker", default=TRACKER_PATH, help="Input tracker CSV path")
    parser.add_argument("--resolved", default=RESOLVED_PATH, help="Resolved evidence CSV path")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output merged tracker CSV path")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    gold_by_id = {}
    with open(args.resolved, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            eid = str(row.get("example_id", "")).strip()
            if eid:
                gold_by_id[eid] = row.get("gold_evidence") or ""

    rows_out = []
    fieldnames = None
    matched = 0
    filled = 0

    with open(args.tracker, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise SystemExit("Tracker has no header row.")
        for row in reader:
            eid = str(row.get("example_id", "")).strip()
            if eid in gold_by_id:
                matched += 1
                g = gold_by_id[eid]
                if g:
                    filled += 1
                row["gold_evidence"] = g
            rows_out.append(row)

    with open(args.output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_out)

    print(f"Matched example_ids: {matched}")
    print(f"Rows with non-empty gold_evidence filled: {filled}")
    print(f"Wrote {args.output}")
    print()
    print("Preview (first 3 rows: example_id, gold_evidence char count):")
    for r in rows_out[:3]:
        ge = r.get("gold_evidence") or ""
        print(f"  id={r.get('example_id')} gold_evidence_len={len(ge)}")


if __name__ == "__main__":
    main()
