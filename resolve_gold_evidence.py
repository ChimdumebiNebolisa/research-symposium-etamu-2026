"""
Fill gold_evidence in the pilot CSV by resolving the first FEVER evidence pointer
against local wiki-pages JSONL shards (same convention as inspect_fever_evidence.py).
"""

import csv
import glob
import json
import os
import argparse


PILOT_PATH = "fever_pilot.csv"
WIKI_PATTERN = os.path.join("wiki-pages", "wiki-pages", "wiki-*.jsonl")
OUTPUT_PATH = "resolved_gold_evidence.csv"


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
    parser.add_argument("--input", default=PILOT_PATH, help="Input source/tracker CSV path")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output resolved CSV path")
    parser.add_argument(
        "--wiki-pattern",
        default=WIKI_PATTERN,
        help="Glob pattern for local wiki shard JSONL files",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    pilot_path = args.input
    if not os.path.isfile(pilot_path):
        raise SystemExit(f"Missing {pilot_path}; run extract_fever_pilot.py first.")

    rows = []
    needed_titles = set()
    with open(pilot_path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
            raw = row.get("raw_evidence") or ""
            evidence = json.loads(raw)
            title, _ = first_wiki_title_and_sentence_idx(evidence)
            needed_titles.add(title)

    wiki_paths = glob.glob(args.wiki_pattern)
    if not wiki_paths:
        raise SystemExit(f"No wiki shards at {args.wiki_pattern}")

    pages = load_wiki_by_id(wiki_paths, needed_titles)

    fieldnames = list(rows[0].keys()) if rows else []
    if "gold_evidence" not in fieldnames:
        fieldnames = fieldnames + ["gold_evidence"]
    if "resolver_note" not in fieldnames:
        fieldnames = fieldnames + ["resolver_note"]

    with open(args.output, "w", encoding="utf-8", newline="") as out:
        w = csv.DictWriter(out, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            out_row = dict(row)
            note = ""
            raw = row.get("raw_evidence") or ""
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
            out_row["resolver_note"] = note
            w.writerow(out_row)


if __name__ == "__main__":
    main()
