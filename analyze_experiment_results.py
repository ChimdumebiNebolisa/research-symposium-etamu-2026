import csv
from collections import defaultdict
import argparse

INPUT_PATH = "experiment_results.csv"
OUTPUT_PATH = "experiment_summary.csv"


def pct(numerator, denominator):
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100.0


def summarize_rows(rows):
    total_rows = len(rows)
    valid_rows = [r for r in rows if (r.get("model_output") or "").strip() in ("Supported", "Refuted")]
    valid_predictions = len(valid_rows)
    correct_yes = sum(1 for r in valid_rows if (r.get("correct") or "").strip() == "Yes")
    incorrect_no = sum(1 for r in valid_rows if (r.get("correct") or "").strip() == "No")
    accuracy = pct(correct_yes, valid_predictions)
    return {
        "total_rows": total_rows,
        "valid_predictions": valid_predictions,
        "correct_yes": correct_yes,
        "incorrect_no": incorrect_no,
        "accuracy": accuracy,
    }


def grouped_summary(rows, key_fn):
    groups = defaultdict(list)
    for row in rows:
        groups[key_fn(row)].append(row)
    return groups


def print_block(title, summary):
    print(title)
    print(f"  total_rows: {summary['total_rows']}")
    print(f"  valid_predictions: {summary['valid_predictions']}")
    print(
        f"  correct_yes: {summary['correct_yes']} | incorrect_no: {summary['incorrect_no']}"
    )
    print(
        f"  accuracy: {summary['accuracy']:.2f}% "
        f"({summary['correct_yes']}/{summary['valid_predictions']})"
    )
    print()


def make_summary_record(group_type, group_value, summary):
    return {
        "group_type": group_type,
        "group_value": group_value,
        "total_rows": summary["total_rows"],
        "valid_predictions": summary["valid_predictions"],
        "correct_yes": summary["correct_yes"],
        "incorrect_no": summary["incorrect_no"],
        "accuracy": f"{summary['accuracy']:.2f}%",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze experiment results and write grouped summary CSV."
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Input experiment results CSV")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output summary CSV")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    summary_records = []

    overall = summarize_rows(rows)
    print("=== Experiment Summary ===")
    print_block("Overall", overall)
    summary_records.append(make_summary_record("overall", "all", overall))

    by_model = grouped_summary(rows, lambda r: (r.get("model") or "").strip())
    print("By model:")
    for model in sorted(by_model):
        s = summarize_rows(by_model[model])
        print_block(f"- {model}", s)
        summary_records.append(make_summary_record("model", model, s))

    by_condition = grouped_summary(rows, lambda r: (r.get("condition") or "").strip())
    print("By condition:")
    for condition in sorted(by_condition):
        s = summarize_rows(by_condition[condition])
        print_block(f"- {condition}", s)
        summary_records.append(make_summary_record("condition", condition, s))

    by_model_condition = grouped_summary(
        rows,
        lambda r: (
            (r.get("model") or "").strip(),
            (r.get("condition") or "").strip(),
        ),
    )
    print("By model + condition:")
    for model, condition in sorted(by_model_condition):
        s = summarize_rows(by_model_condition[(model, condition)])
        label = f"{model} | {condition}"
        print_block(f"- {label}", s)
        summary_records.append(make_summary_record("model_condition", label, s))

    print("Incorrect counts by model + condition:")
    for model, condition in sorted(by_model_condition):
        s = summarize_rows(by_model_condition[(model, condition)])
        print(f"  - {model} | {condition}: {s['incorrect_no']}")
    print()

    with open(args.output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(
            out,
            fieldnames=[
                "group_type",
                "group_value",
                "total_rows",
                "valid_predictions",
                "correct_yes",
                "incorrect_no",
                "accuracy",
            ],
        )
        w.writeheader()
        w.writerows(summary_records)

    print(f"Wrote {args.output}")
    print()

    incorrect_rows = [
        r
        for r in rows
        if (r.get("model_output") or "").strip() in ("Supported", "Refuted")
        and (r.get("correct") or "").strip() == "No"
    ]
    print("Incorrect rows:")
    if not incorrect_rows:
        print("  (none)")
        return

    for r in incorrect_rows:
        print(
            "  - "
            f"example_id={r.get('example_id')}, "
            f"claim={r.get('claim')}, "
            f"gold_label={r.get('gold_label')}, "
            f"model={r.get('model')}, "
            f"condition={r.get('condition')}, "
            f"model_output={r.get('model_output')}"
        )


if __name__ == "__main__":
    main()
