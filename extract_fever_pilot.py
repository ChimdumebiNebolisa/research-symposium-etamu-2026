import csv
import json

INPUT_PATH = "shared_task_dev.jsonl"
OUTPUT_PATH = "fever_pilot_sample.csv"

LABEL_MAP = {"SUPPORTS": "Supported", "REFUTES": "Refuted"}


def main():
    supports = []
    refutes = []

    with open(INPUT_PATH, encoding="utf-8") as f:
        for line in f:
            if len(supports) >= 5 and len(refutes) >= 5:
                break
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            label = row.get("label")
            if label == "NOT ENOUGH INFO":
                continue
            if label == "SUPPORTS" and len(supports) < 5:
                supports.append(row)
            elif label == "REFUTES" and len(refutes) < 5:
                refutes.append(row)

    ordered = supports + refutes

    fieldnames = [
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

    with open(OUTPUT_PATH, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
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


if __name__ == "__main__":
    main()
