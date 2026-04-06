"""Create a small pilot subset from expanded full experiment runs."""

import argparse
import csv
import os

from experiment_config import DEFAULT_TAG

INPUT_PATH = f"experiment_runs_{DEFAULT_TAG}.csv"
OUTPUT_PATH = f"experiment_runs_{DEFAULT_TAG}_pilot.csv"


def sort_key_claim_id(value):
    text = str(value)
    if text.isdigit():
        return (0, int(text))
    return (1, text)


def main():
    parser = argparse.ArgumentParser(
        description="Create a pilot run CSV from the full expanded runs file."
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Full experiment runs CSV")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Pilot experiment runs CSV")
    parser.add_argument(
        "--pilot-claims",
        type=int,
        default=50,
        help="Number of unique claims to include in the pilot subset",
    )
    args = parser.parse_args()

    if args.pilot_claims <= 0:
        raise SystemExit("--pilot-claims must be > 0")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if not os.path.isfile(args.input):
        raise SystemExit(f"Input file not found: {args.input}")

    with open(args.input, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise SystemExit("Input CSV has no header")
        rows = list(reader)

    unique_claim_ids = sorted(
        {
            str(r.get("claim_id") or r.get("example_id") or "").strip()
            for r in rows
            if str(r.get("claim_id") or r.get("example_id") or "").strip()
        },
        key=sort_key_claim_id,
    )

    if len(unique_claim_ids) < args.pilot_claims:
        raise SystemExit(
            f"Only found {len(unique_claim_ids)} unique claim IDs; requested {args.pilot_claims}"
        )

    selected_ids = set(unique_claim_ids[: args.pilot_claims])
    pilot_rows = [
        row
        for row in rows
        if str(row.get("claim_id") or row.get("example_id") or "").strip() in selected_ids
    ]

    with open(args.output, "w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(pilot_rows)

    print(f"Selected pilot claims: {len(selected_ids)}")
    print(f"Pilot run rows: {len(pilot_rows)}")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
