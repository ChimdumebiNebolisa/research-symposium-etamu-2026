import csv
import json

INPUT_PATH = "fever_pilot_sample.csv"
OUTPUT_PATH = "fever_evidence_inspection.csv"


def first_page_and_sentence_idx(evidence):
    first_set = evidence[0]
    first_item = first_set[0]
    return first_item[2], first_item[3]


def main():
    rows_out = []
    with open(INPUT_PATH, encoding="utf-8", newline="") as f:
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
    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)


if __name__ == "__main__":
    main()
