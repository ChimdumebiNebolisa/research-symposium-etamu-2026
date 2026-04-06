"""Aggregate completed manual taxonomy annotations by model and overall."""

import argparse
import csv
import os
import sys
from collections import defaultdict

from experiment_config import DEFAULT_TAG

INPUT_PATH = f"manual_annotations_evidence_failures_{DEFAULT_TAG}.csv"
OUTPUT_PATH = f"manual_annotation_taxonomy_summary_{DEFAULT_TAG}.csv"

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


def init_group_stats():
    return {
        "total_rows": 0,
        "labeled_rows": 0,
        "unlabeled_rows": 0,
        "counts": defaultdict(int),
    }


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate completed manual taxonomy labels into counts and percentages "
            "by model and overall."
        )
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Input annotation CSV")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output aggregate CSV")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    with open(args.input, encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    required_columns = {"model", "taxonomy_label"}
    if not rows:
        print("Input file has no rows.", file=sys.stderr)
        sys.exit(1)

    missing_columns = required_columns - set(rows[0].keys())
    if missing_columns:
        print(
            "Input file is missing required columns: "
            + ", ".join(sorted(missing_columns)),
            file=sys.stderr,
        )
        sys.exit(1)

    allowed = set(TAXONOMY_LABELS)
    invalid_labels = []

    overall = init_group_stats()
    by_model = defaultdict(init_group_stats)

    for idx, row in enumerate(rows, start=2):
        model = (row.get("model") or "").strip() or "unknown"
        label = (row.get("taxonomy_label") or "").strip()

        for stats in (overall, by_model[model]):
            stats["total_rows"] += 1

        if not label:
            overall["unlabeled_rows"] += 1
            by_model[model]["unlabeled_rows"] += 1
            continue

        if label not in allowed:
            invalid_labels.append((idx, label, model))
            continue

        overall["labeled_rows"] += 1
        by_model[model]["labeled_rows"] += 1
        overall["counts"][label] += 1
        by_model[model]["counts"][label] += 1

    if invalid_labels:
        preview = "; ".join(
            [f"line={line} model={model} label={label}" for line, label, model in invalid_labels[:10]]
        )
        print(
            "Found invalid taxonomy_label values. "
            "Use only the allowed labels. "
            f"Invalid count={len(invalid_labels)} preview=[{preview}]",
            file=sys.stderr,
        )
        sys.exit(1)

    records = []

    def append_group(group_type, group_value, stats):
        for label in TAXONOMY_LABELS:
            count = stats["counts"].get(label, 0)
            percentage = pct(count, stats["labeled_rows"])
            records.append(
                {
                    "group_type": group_type,
                    "group_value": group_value,
                    "taxonomy_label": label,
                    "count": count,
                    "percentage": f"{percentage:.2f}",
                    "labeled_total": stats["labeled_rows"],
                    "unlabeled_total": stats["unlabeled_rows"],
                    "total_rows": stats["total_rows"],
                }
            )

    append_group("overall", "all", overall)
    for model in sorted(by_model):
        append_group("model", model, by_model[model])

    with open(args.output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(
            out,
            fieldnames=[
                "group_type",
                "group_value",
                "taxonomy_label",
                "count",
                "percentage",
                "labeled_total",
                "unlabeled_total",
                "total_rows",
            ],
        )
        w.writeheader()
        w.writerows(records)

    print(f"Wrote {args.output}")
    print(
        "Overall labeled rows: "
        f"{overall['labeled_rows']} / {overall['total_rows']} "
        f"({pct(overall['labeled_rows'], overall['total_rows']):.2f}%)"
    )
    for model in sorted(by_model):
        stats = by_model[model]
        print(
            f"- {model}: labeled={stats['labeled_rows']} "
            f"unlabeled={stats['unlabeled_rows']} total={stats['total_rows']}"
        )


if __name__ == "__main__":
    main()
