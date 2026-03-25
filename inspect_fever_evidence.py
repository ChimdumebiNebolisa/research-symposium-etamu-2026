import csv
import json
import argparse

INPUT_PATH = "fever_pilot.csv"
OUTPUT_PATH = "pilot_evidence_index.csv"


def first_page_and_sentence_idx(evidence):
    first_set = evidence[0]
    first_item = first_set[0]
    return first_item[2], first_item[3]


def main():
    parser = argparse.ArgumentParser(
        description="Build first-evidence page/sentence index from a source CSV."
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Input source CSV path")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output index CSV path")
    args = parser.parse_args()

    rows_out = []
    with open(args.input, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            raw = row["raw_evidence"]
            evidence = json.loads(raw)
            page, sent_idx = first_page_and_sentence_idx(evidence)
            rows_out.append(
                {
                    "example_id": row["example_id"],
                    "claim": row["claim"],
                    "gold_label": row["gold_label"],
                    "first_evidence_page": page,
                    "first_evidence_sentence_idx": sent_idx,
                }
            )

    fieldnames = [
        "example_id",
        "claim",
        "gold_label",
        "first_evidence_page",
        "first_evidence_sentence_idx",
    ]
    with open(args.output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)


if __name__ == "__main__":
    main()
