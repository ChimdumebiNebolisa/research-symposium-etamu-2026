import argparse
import csv
import math
import os
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
        fieldnames = reader.fieldnames or []
        rows = list(reader)
    return fieldnames, rows


def write_csv(path, fieldnames, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(
        description="Split unfinished run rows into shard CSV files for parallel processing."
    )
    parser.add_argument("--runs", required=True, help="Full runs CSV path")
    parser.add_argument("--results", required=True, help="Existing partial/full results CSV path")
    parser.add_argument("--shards", type=int, default=4, help="Number of shard files")
    parser.add_argument(
        "--output-dir",
        default="parallel_shards_balanced_10000_v1",
        help="Directory where shard CSV files will be written",
    )
    parser.add_argument(
        "--prefix",
        default="experiment_runs_balanced_10000_v1_remaining_shard",
        help="Prefix for shard filenames",
    )
    args = parser.parse_args()

    if args.shards <= 0:
        raise SystemExit("--shards must be > 0")

    runs_path = Path(args.runs)
    results_path = Path(args.results)
    out_dir = Path(args.output_dir)

    if not runs_path.is_file():
        raise SystemExit(f"Missing runs file: {runs_path}")

    run_fields, run_rows = read_csv(runs_path)

    completed_keys = set()
    result_rows = []
    if results_path.is_file():
        _, result_rows = read_csv(results_path)
        for row in result_rows:
            if (row.get("model_output") or "").strip() in VALID_LABELS:
                completed_keys.add(row_key(row))

    remaining = [row for row in run_rows if row_key(row) not in completed_keys]

    out_dir.mkdir(parents=True, exist_ok=True)

    # Clear old shard files with same prefix in output dir.
    for existing in out_dir.glob(f"{args.prefix}_*.csv"):
        existing.unlink()

    total = len(remaining)
    per_shard = math.ceil(total / args.shards) if total else 0

    shard_files = []
    for i in range(args.shards):
        start = i * per_shard
        end = min(start + per_shard, total)
        chunk = remaining[start:end]
        if not chunk:
            continue
        shard_path = out_dir / f"{args.prefix}_{i + 1:02d}.csv"
        write_csv(shard_path, run_fields, chunk)
        shard_files.append((shard_path, len(chunk)))

    print(f"total_run_rows={len(run_rows)}")
    print(f"existing_result_rows={len(result_rows)}")
    print(f"completed_valid_keys={len(completed_keys)}")
    print(f"remaining_rows={len(remaining)}")
    print(f"shards_written={len(shard_files)}")
    for path, count in shard_files:
        print(f"{path} rows={count}")


if __name__ == "__main__":
    main()
