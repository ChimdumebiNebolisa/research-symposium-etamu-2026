import argparse
import csv
from pathlib import Path

VALID_LABELS = {"Supported", "Refuted"}


def row_key(row):
    return (
        str(row.get("claim_id") or row.get("example_id") or "").strip(),
        str(row.get("model", "")).strip(),
        str(row.get("condition", "")).strip(),
    )


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    return fields, rows


def main():
    parser = argparse.ArgumentParser(description="Merge base + shard result files into a final results CSV.")
    parser.add_argument("--base", required=True, help="Base partial results CSV")
    parser.add_argument("--runs", required=True, help="Full runs CSV (for final ordering)")
    parser.add_argument("--shards-dir", required=True, help="Directory containing shard result CSV files")
    parser.add_argument("--output", required=True, help="Merged output CSV")
    parser.add_argument("--shard-glob", default="experiment_results_balanced_10000_v1_remaining_shard_*.csv")
    args = parser.parse_args()

    base_path = Path(args.base)
    runs_path = Path(args.runs)
    shard_dir = Path(args.shards_dir)
    out_path = Path(args.output)

    if not runs_path.is_file():
        raise SystemExit(f"Missing runs file: {runs_path}")

    run_fields, run_rows = read_csv(runs_path)

    merged = {}

    if base_path.is_file():
        _, base_rows = read_csv(base_path)
        for r in base_rows:
            if (r.get("model_output") or "").strip() in VALID_LABELS:
                merged[row_key(r)] = r

    shard_files = sorted(shard_dir.glob(args.shard_glob))
    if not shard_files:
        raise SystemExit(f"No shard files found in {shard_dir} matching {args.shard_glob}")

    shard_rows = 0
    for sf in shard_files:
        _, rows = read_csv(sf)
        shard_rows += len(rows)
        for r in rows:
            if (r.get("model_output") or "").strip() in VALID_LABELS:
                merged[row_key(r)] = r

    final_rows = []
    missing = 0
    for r in run_rows:
        k = row_key(r)
        out = merged.get(k)
        if out is None:
            missing += 1
            out = dict(r)
            out.setdefault("model_output", "")
            out.setdefault("correct", "")
            out.setdefault("error_type", "")
            out.setdefault("notes", "")
        final_rows.append(out)

    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=run_fields)
        writer.writeheader()
        writer.writerows(final_rows)

    print(f"runs_rows={len(run_rows)}")
    print(f"merged_valid_predictions={len(merged)}")
    print(f"shard_files={len(shard_files)}")
    print(f"shard_rows={shard_rows}")
    print(f"missing_after_merge={missing}")
    print(f"wrote={out_path}")


if __name__ == "__main__":
    main()
