"""
Resolve gold_evidence in a FEVER source CSV by selecting one complete FEVER
evidence set against local wiki-pages JSONL shards.
"""

import csv
import json
import os
import argparse
import hashlib
import unicodedata

from experiment_config import DEFAULT_TAG, WIKI_SHARD_PATTERN, require_wiki_shards


INPUT_PATH = f"experiment_tracker_{DEFAULT_TAG}.csv"
OUTPUT_PATH = f"experiment_tracker_with_evidence_{DEFAULT_TAG}.csv"


def canonicalize_wiki_title(title):
    return unicodedata.normalize("NFC", str(title).strip())


def parse_pointer(item):
    if not isinstance(item, list) or len(item) < 4:
        raise ValueError("invalid_evidence_pointer")

    title = item[2]
    sent_idx = item[3]

    if title is None or str(title).strip() == "":
        raise ValueError("invalid_evidence_pointer_title")

    try:
        sent_idx = int(sent_idx)
    except (TypeError, ValueError):
        raise ValueError("invalid_evidence_pointer_sentence_index")

    return canonicalize_wiki_title(title), sent_idx


def parse_evidence_sets(raw_evidence):
    evidence = json.loads(raw_evidence)
    if not isinstance(evidence, list):
        raise ValueError("invalid_raw_evidence_format")

    parsed_sets = []
    for set_idx, evidence_set in enumerate(evidence):
        if not isinstance(evidence_set, list) or not evidence_set:
            continue

        pointers = []
        for item in evidence_set:
            title, sent_idx = parse_pointer(item)
            pointers.append((title, sent_idx))

        if pointers:
            parsed_sets.append(
                {
                    "set_index": set_idx,
                    "pointers": pointers,
                }
            )

    if not parsed_sets:
        raise ValueError("no_evidence_sets")

    return parsed_sets


def iter_needed_titles(evidence_sets):
    for evidence_set in evidence_sets:
        for title, _ in evidence_set["pointers"]:
            yield title


def sentence_text_from_lines(lines_str, idx):
    target = str(idx)
    for raw_line in lines_str.split("\n"):
        parts = raw_line.split("\t")
        if len(parts) >= 2 and parts[0] == target:
            return parts[1]
    return None


def resolve_evidence_set(evidence_set, pages):
    sentences = []
    page_titles = []

    for title, sent_idx in evidence_set["pointers"]:
        doc = pages.get(title)
        if doc is None:
            return None, f"missing_wiki_page:{title}"

        sentence = sentence_text_from_lines(doc.get("lines") or "", sent_idx)
        if sentence is None:
            return None, f"missing_sentence:{title}:{sent_idx}"

        page_titles.append(title)
        sentences.append(sentence)

    payload = json.dumps(
        {
            "set_index": evidence_set["set_index"],
            "pointers": [
                {"page": page, "sent_idx": sent_idx}
                for page, sent_idx in evidence_set["pointers"]
            ],
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    set_id = "fever_set_" + hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]

    resolved = {
        "set_index": evidence_set["set_index"],
        "sentences": sentences,
        "pages": page_titles,
        "set_size": len(sentences),
        "set_id": set_id,
    }
    return resolved, ""


def choose_shortest_complete_set(evidence_sets, pages):
    best = None
    first_failure = ""

    for evidence_set in evidence_sets:
        resolved, failure = resolve_evidence_set(evidence_set, pages)
        if resolved is None:
            if not first_failure:
                first_failure = failure
            continue

        if best is None:
            best = resolved
            continue

        if resolved["set_size"] < best["set_size"]:
            best = resolved
            continue

        if (
            resolved["set_size"] == best["set_size"]
            and resolved["set_index"] < best["set_index"]
        ):
            best = resolved

    if best is not None:
        return best, ""

    return None, first_failure or "no_complete_evidence_set"


def load_wiki_by_id(wiki_paths, needed_ids):
    pages = {}
    remaining = {canonicalize_wiki_title(x) for x in needed_ids}
    for path in sorted(wiki_paths):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                doc = json.loads(line)
                wid = canonicalize_wiki_title(doc.get("id") or "")
                if wid in remaining:
                    pages[wid] = doc
                    remaining.discard(wid)
                    if not remaining:
                        return pages
    return pages


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Resolve one complete FEVER evidence set to readable gold evidence "
            "(shortest complete set)."
        )
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
            try:
                evidence_sets = parse_evidence_sets(raw)
                needed_titles.update(iter_needed_titles(evidence_sets))
            except Exception:
                continue

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
    if "evidence_sentences_json" not in fieldnames:
        fieldnames = fieldnames + ["evidence_sentences_json"]
    if "evidence_pages_json" not in fieldnames:
        fieldnames = fieldnames + ["evidence_pages_json"]
    if "evidence_set_size" not in fieldnames:
        fieldnames = fieldnames + ["evidence_set_size"]
    if "evidence_set_id" not in fieldnames:
        fieldnames = fieldnames + ["evidence_set_id"]
    if "resolver_note" not in fieldnames:
        fieldnames = fieldnames + ["resolver_note"]

    written_rows = []
    unresolved_rows = []

    for row in rows:
        out_row = dict(row)
        note = ""
        raw = row.get("raw_evidence") or ""
        try:
            evidence_sets = parse_evidence_sets(raw)
            chosen_set, note = choose_shortest_complete_set(evidence_sets, pages)
            if chosen_set is not None:
                out_row["evidence_sentences_json"] = json.dumps(
                    chosen_set["sentences"],
                    ensure_ascii=False,
                )
                out_row["evidence_pages_json"] = json.dumps(
                    chosen_set["pages"],
                    ensure_ascii=False,
                )
                out_row["evidence_set_size"] = str(chosen_set["set_size"])
                out_row["evidence_set_id"] = chosen_set["set_id"]
                # Keep backward compatibility by preserving gold_evidence as a prompt-ready string.
                out_row["gold_evidence"] = " ".join(chosen_set["sentences"]).strip()
        except Exception as exc:
            note = f"bad_raw_evidence:{type(exc).__name__}"

        if note:
            out_row.setdefault("evidence_sentences_json", "")
            out_row.setdefault("evidence_pages_json", "")
            out_row.setdefault("evidence_set_size", "")
            out_row.setdefault("evidence_set_id", "")
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
