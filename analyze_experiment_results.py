import argparse
import csv
import os
import sys
from collections import defaultdict

from experiment_config import CONDITIONS, DEFAULT_TAG, VALID_LABELS

INPUT_PATH = f"experiment_results_{DEFAULT_TAG}.csv"
OUTPUT_PATH = f"experiment_summary_{DEFAULT_TAG}.csv"
METRICS_PATH = f"experiment_metrics_{DEFAULT_TAG}.csv"
EVIDENCE_ERRORS_PATH = f"evidence_condition_errors_{DEFAULT_TAG}.csv"
TAXONOMY_COUNTS_PATH = f"error_taxonomy_counts_{DEFAULT_TAG}.csv"
EXAMPLE_FAILURES_PATH = f"example_failure_cases_{DEFAULT_TAG}.csv"
MANUAL_ANNOTATION_PATH = f"manual_annotations_evidence_failures_{DEFAULT_TAG}.csv"

TAXONOMY_LABELS = (
    "evidence_neglect",
    "evidence_misinterpretation",
    "multi_sentence_integration_failure",
    "negation_or_contradiction_failure",
    "numerical_or_comparative_failure",
    "entity_or_attribute_confusion",
    "distractor_susceptibility",
    "other_or_ambiguous",
)


def pct(numerator, denominator):
    if denominator == 0:
        return 0.0
    return (numerator / denominator) * 100.0


def summarize_rows(rows):
    total_rows = len(rows)
    valid_rows = [
        r for r in rows if (r.get("model_output") or "").strip() in VALID_LABELS
    ]
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


def evidence_error_taxonomy(row):
    error_type = (row.get("error_type") or "").strip()
    if error_type:
        return error_type

    model_output = (row.get("model_output") or "").strip()
    if model_output not in VALID_LABELS:
        return "invalid_or_missing_output"

    gold = (row.get("true_label") or row.get("gold_label") or "").strip()
    if gold == "Supported" and model_output == "Refuted":
        return "supported_to_refuted"
    if gold == "Refuted" and model_output == "Supported":
        return "refuted_to_supported"
    return "other_error"


def get_raw_model_output(row):
    candidate_fields = (
        "raw_model_output",
        "raw_output",
        "raw_response",
        "response_text",
        "model_response",
        "response",
    )
    for field in candidate_fields:
        value = (row.get(field) or "").strip()
        if value:
            return value

    notes = (row.get("notes") or "").strip()
    prefix = "invalid_model_output:"
    if notes.startswith(prefix):
        return notes[len(prefix) :].strip()
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="Analyze experiment results and write grouped summary CSV."
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Input experiment results CSV")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output summary CSV")
    parser.add_argument(
        "--metrics-output",
        default=METRICS_PATH,
        help="Output metrics CSV path (accuracy, evidence gain, evidence failure rate)",
    )
    parser.add_argument(
        "--evidence-errors-output",
        default=EVIDENCE_ERRORS_PATH,
        help="Output CSV for evidence-condition incorrect rows",
    )
    parser.add_argument(
        "--taxonomy-output",
        default=TAXONOMY_COUNTS_PATH,
        help="Output CSV for error taxonomy counts",
    )
    parser.add_argument(
        "--example-failures-output",
        default=EXAMPLE_FAILURES_PATH,
        help="Output CSV for 2-4 example failure cases",
    )
    parser.add_argument(
        "--manual-annotation-output",
        default=MANUAL_ANNOTATION_PATH,
        help="Output CSV for manual coding of claim_plus_evidence failures",
    )
    parser.add_argument(
        "--example-failures-max",
        type=int,
        default=4,
        help="Maximum number of failure examples to write (2-4 recommended)",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Input file not found: {args.input}", file=sys.stderr)
        print(
            "Run `python run_fact_check_experiment.py` first (it writes the results CSV), "
            "or pass an existing file with --input.",
            file=sys.stderr,
        )
        sys.exit(1)

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

    # Required metrics for this experiment.
    models = sorted(
        {
            (r.get("model") or "").strip()
            for r in rows
            if (r.get("model") or "").strip()
        }
    )
    metrics_rows = []
    for model in models:
        by_condition_for_model = {
            condition: summarize_rows(
                [
                    r
                    for r in rows
                    if (r.get("model") or "").strip() == model
                    and (r.get("condition") or "").strip() == condition
                ]
            )
            for condition in CONDITIONS
        }

        claim_only_summary = by_condition_for_model["claim_only"]
        claim_plus_summary = by_condition_for_model["claim_plus_evidence"]

        evidence_gain = claim_plus_summary["accuracy"] - claim_only_summary["accuracy"]
        evidence_failure_rate = pct(
            claim_plus_summary["incorrect_no"], claim_plus_summary["valid_predictions"]
        )

        metrics_rows.append(
            {
                "metric_name": "accuracy",
                "model": model,
                "condition": "claim_only",
                "value": f"{claim_only_summary['accuracy']:.2f}",
                "numerator": claim_only_summary["correct_yes"],
                "denominator": claim_only_summary["valid_predictions"],
            }
        )
        metrics_rows.append(
            {
                "metric_name": "accuracy",
                "model": model,
                "condition": "claim_plus_evidence",
                "value": f"{claim_plus_summary['accuracy']:.2f}",
                "numerator": claim_plus_summary["correct_yes"],
                "denominator": claim_plus_summary["valid_predictions"],
            }
        )
        metrics_rows.append(
            {
                "metric_name": "evidence_gain_pp",
                "model": model,
                "condition": "claim_plus_evidence_minus_claim_only",
                "value": f"{evidence_gain:.2f}",
                "numerator": "",
                "denominator": "",
            }
        )
        metrics_rows.append(
            {
                "metric_name": "evidence_failure_rate_percent",
                "model": model,
                "condition": "claim_plus_evidence",
                "value": f"{evidence_failure_rate:.2f}",
                "numerator": claim_plus_summary["incorrect_no"],
                "denominator": claim_plus_summary["valid_predictions"],
            }
        )

    with open(args.metrics_output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(
            out,
            fieldnames=[
                "metric_name",
                "model",
                "condition",
                "value",
                "numerator",
                "denominator",
            ],
        )
        w.writeheader()
        w.writerows(metrics_rows)

    print("Key metrics:")
    for row in metrics_rows:
        if row["metric_name"] in ("evidence_gain_pp", "evidence_failure_rate_percent"):
            print(
                f"  - {row['metric_name']} | {row['model']} | "
                f"{row['condition']}: {row['value']}"
            )
    print(f"Wrote {args.metrics_output}")
    print()

    incorrect_rows = [
        r
        for r in rows
        if (r.get("model_output") or "").strip() in VALID_LABELS
        and (r.get("correct") or "").strip() == "No"
    ]
    print("Incorrect rows:")
    if not incorrect_rows:
        print("  (none)")
    else:
        for r in incorrect_rows:
            print(
                "  - "
                f"claim_id={r.get('claim_id') or r.get('example_id')}, "
                f"claim={r.get('claim_text') or r.get('claim')}, "
                f"true_label={r.get('true_label') or r.get('gold_label')}, "
                f"model={r.get('model')}, "
                f"condition={r.get('condition')}, "
                f"model_output={r.get('model_output')}"
            )

    evidence_condition_errors = [
        r
        for r in rows
        if (r.get("condition") or "").strip() == "claim_plus_evidence"
        and (r.get("correct") or "").strip() == "No"
    ]

    evidence_error_fields = [
        "claim_id",
        "claim_text",
        "true_label",
        "model",
        "condition",
        "model_output",
        "gold_evidence",
        "error_type",
        "notes",
    ]
    with open(args.evidence_errors_output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=evidence_error_fields)
        w.writeheader()
        for r in evidence_condition_errors:
            w.writerow(
                {
                    "claim_id": r.get("claim_id") or r.get("example_id") or "",
                    "claim_text": r.get("claim_text") or r.get("claim") or "",
                    "true_label": r.get("true_label") or r.get("gold_label") or "",
                    "model": r.get("model") or "",
                    "condition": r.get("condition") or "",
                    "model_output": r.get("model_output") or "",
                    "gold_evidence": r.get("gold_evidence") or "",
                    "error_type": r.get("error_type") or "",
                    "notes": r.get("notes") or "",
                }
            )

    manual_annotation_fields = [
        "claim_id",
        "claim",
        "true_label",
        "predicted_label",
        "model",
        "gold_evidence",
        "raw_model_output",
        "taxonomy_label",
        "taxonomy_notes",
    ]
    with open(args.manual_annotation_output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=manual_annotation_fields)
        w.writeheader()
        for r in evidence_condition_errors:
            taxonomy_label = (r.get("taxonomy_label") or "").strip()
            if taxonomy_label not in TAXONOMY_LABELS:
                taxonomy_label = ""

            w.writerow(
                {
                    "claim_id": r.get("claim_id") or r.get("example_id") or "",
                    "claim": r.get("claim_text") or r.get("claim") or "",
                    "true_label": r.get("true_label") or r.get("gold_label") or "",
                    "predicted_label": r.get("model_output") or "",
                    "model": r.get("model") or "",
                    "gold_evidence": r.get("gold_evidence") or "",
                    "raw_model_output": get_raw_model_output(r),
                    "taxonomy_label": taxonomy_label,
                    "taxonomy_notes": r.get("taxonomy_notes") or r.get("notes") or "",
                }
            )

    taxonomy_counts = defaultdict(int)
    for r in evidence_condition_errors:
        model = (r.get("model") or "").strip()
        taxonomy = evidence_error_taxonomy(r)
        taxonomy_counts[(model, taxonomy)] += 1

    with open(args.taxonomy_output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(
            out,
            fieldnames=["model", "taxonomy", "count"],
        )
        w.writeheader()
        for (model, taxonomy), count in sorted(taxonomy_counts.items()):
            w.writerow({"model": model, "taxonomy": taxonomy, "count": count})

    example_max = max(2, min(4, args.example_failures_max))
    examples = evidence_condition_errors[:example_max]
    with open(args.example_failures_output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(
            out,
            fieldnames=[
                "claim_id",
                "claim_text",
                "true_label",
                "model",
                "model_output",
                "gold_evidence",
                "error_type",
                "notes",
            ],
        )
        w.writeheader()
        for r in examples:
            w.writerow(
                {
                    "claim_id": r.get("claim_id") or r.get("example_id") or "",
                    "claim_text": r.get("claim_text") or r.get("claim") or "",
                    "true_label": r.get("true_label") or r.get("gold_label") or "",
                    "model": r.get("model") or "",
                    "model_output": r.get("model_output") or "",
                    "gold_evidence": r.get("gold_evidence") or "",
                    "error_type": evidence_error_taxonomy(r),
                    "notes": r.get("notes") or "",
                }
            )

    print(f"Wrote {args.evidence_errors_output}")
    print(f"Wrote {args.taxonomy_output}")
    print(f"Wrote {args.example_failures_output}")
    print(f"Wrote {args.manual_annotation_output}")

if __name__ == "__main__":
    main()
