"""
Resolve gold_evidence in a FEVER source CSV by using the first FEVER evidence pointer
against local wiki-pages JSONL shards.
"""

import csv
import json
import os
import argparse

from experiment_config import DEFAULT_TAG, WIKI_SHARD_PATTERN, require_wiki_shards


INPUT_PATH = f"experiment_tracker_{DEFAULT_TAG}.csv"
OUTPUT_PATH = f"experiment_tracker_with_evidence_{DEFAULT_TAG}.csv"


def first_wiki_title_and_sentence_idx(evidence):
    first_set = evidence[0]
    first_item = first_set[0]
    return first_item[2], first_item[3]


def sentence_text_from_lines(lines_str, idx):
    target = str(idx)
    for raw_line in lines_str.split("\n"):
        parts = raw_line.split("\t")
        if len(parts) >= 2 and parts[0] == target:
            return parts[1]
    return None


def load_wiki_by_id(wiki_paths, needed_ids):
    pages = {}
    remaining = set(needed_ids)
    for path in sorted(wiki_paths):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                wid = doc.get("id")
                if wid in remaining:
                    pages[wid] = doc
                    remaining.discard(wid)
                    if not remaining:
                        return pages
    return pages


def main():
    parser = argparse.ArgumentParser(
        description="Resolve first FEVER evidence pointer to readable gold evidence."
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Input source/tracker CSV path")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output resolved CSV path")
    parser.add_argument(
        "--wiki-pattern",
        default=WIKI_SHARD_PATTERN,
        help="Glob pattern for local wiki shard JSONL files",
    )
    parser.add_argument(
        "--drop-unresolved",
        action="store_true",
        help="Drop rows where evidence cannot be resolved (otherwise keep and flag)",
    )
    parser.add_argument(
        "--summary-output",
        default="",
        help="Optional JSON summary output path",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    source_path = args.input
    if not os.path.isfile(source_path):
        raise SystemExit(
            f"Missing {source_path}; run extract_fever_balanced_sample.py first "
            "or pass --input <path>."
        )

    rows = []
    needed_titles = set()
    with open(source_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
            raw = row.get("raw_evidence") or ""
            evidence = json.loads(raw)
            title, _ = first_wiki_title_and_sentence_idx(evidence)
            needed_titles.add(title)

    try:
        wiki_paths = require_wiki_shards(args.wiki_pattern)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc))

    pages = load_wiki_by_id(wiki_paths, needed_titles)

    if not rows:
        raise SystemExit(f"No rows found in {source_path}")

    fieldnames = list(rows[0].keys())
    if "gold_evidence" not in fieldnames:
        fieldnames = fieldnames + ["gold_evidence"]
    if "resolver_note" not in fieldnames:
        fieldnames = fieldnames + ["resolver_note"]

    written_rows = []
    unresolved_rows = []

    for row in rows:
        out_row = dict(row)
        note = ""
        raw = row.get("raw_evidence") or ""
        try:
            evidence = json.loads(raw)
            title, sent_idx = first_wiki_title_and_sentence_idx(evidence)
            doc = pages.get(title)
            if doc is None:
                note = f"missing_wiki_page:{title}"
            else:
                text = sentence_text_from_lines(doc.get("lines") or "", sent_idx)
                if text is None:
                    note = f"missing_sentence:{title}:{sent_idx}"
                else:
                    out_row["gold_evidence"] = text
        except Exception as exc:
            note = f"bad_raw_evidence:{type(exc).__name__}"
        out_row["resolver_note"] = note

        if note:
            unresolved_rows.append(
                {
                    "claim_id": out_row.get("claim_id") or out_row.get("example_id") or "",
                    "note": note,
                }
            )
            if args.drop_unresolved:
                continue

        written_rows.append(out_row)

    with open(args.output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(written_rows)

    summary_output = args.summary_output or f"resolve_summary_{DEFAULT_TAG}.json"
    with open(summary_output, "w", encoding="utf-8") as out:
        json.dump(
            {
                "input_csv": args.input,
                "output_csv": args.output,
                "wiki_pattern": args.wiki_pattern,
                "drop_unresolved": args.drop_unresolved,
                "input_rows": len(rows),
                "written_rows": len(written_rows),
                "unresolved_count": len(unresolved_rows),
                "unresolved_preview": unresolved_rows[:25],
            },
            out,
            indent=2,
        )

    print(f"Input rows: {len(rows)}")
    print(f"Written rows: {len(written_rows)}")
    print(f"Unresolved rows: {len(unresolved_rows)}")
    print(f"Wrote {args.output}")
    print(f"Wrote {summary_output}")


if __name__ == "__main__":
    main()
