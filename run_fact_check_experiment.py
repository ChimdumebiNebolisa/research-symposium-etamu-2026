"""
Run fact-check prompts for each row in an experiment runs CSV via OpenAI API.
Reads OPENAI_API_KEY from the environment or .env. Writes results incrementally.

Defaults match the cleaned large-run artifacts documented in README.md.
"""

import csv
import os
import re
import sys
import argparse

from experiment_config import DEFAULT_TAG, MODEL_API_NAMES, VALID_LABELS

INPUT_PATH = f"experiment_runs_{DEFAULT_TAG}.csv"
OUTPUT_PATH = f"experiment_results_{DEFAULT_TAG}.csv"

PROMPT_CLAIM_ONLY = """Classify the claim as Supported or Refuted.
Output only one word: Supported or Refuted.

Claim: {claim}"""

PROMPT_CLAIM_PLUS = """Classify the claim as Supported or Refuted based only on the evidence provided.
Output only one word: Supported or Refuted.

Claim: {claim}
Evidence: {gold_evidence}"""

NOTE_MAX = 800


def row_key(row):
    return (
        str(row.get("claim_id") or row.get("example_id") or "").strip(),
        str(row.get("model", "")).strip(),
        str(row.get("condition", "")).strip(),
    )


def preflight_validate_rows(rows):
    missing = []
    for row in rows:
        condition = (row.get("condition") or "").strip()
        if condition != "claim_plus_evidence":
            continue
        if (row.get("gold_evidence") or "").strip():
            continue
        missing.append(row.get("claim_id") or row.get("example_id") or "")

    if missing:
        preview = ", ".join(str(x) for x in missing[:10])
        raise SystemExit(
            "Missing gold_evidence for claim_plus_evidence rows. "
            "Resolve FEVER evidence first (and ensure wiki shards are prepared). "
            f"Missing count={len(missing)} preview=[{preview}]"
        )


def build_prompt(row):
    condition = (row.get("condition") or "").strip()
    claim = row.get("claim_text") or row.get("claim") or ""
    evidence = row.get("gold_evidence") or ""
    if condition == "claim_only":
        return PROMPT_CLAIM_ONLY.format(claim=claim)
    if condition == "claim_plus_evidence":
        return PROMPT_CLAIM_PLUS.format(claim=claim, gold_evidence=evidence)
    raise ValueError(f"Unknown condition: {condition!r}")


def normalize_label(raw_text):
    """
    Return (canonical_label_or_None, raw_for_notes_if_invalid).
    """
    if raw_text is None:
        return None, ""
    s = raw_text.strip()
    if s in VALID_LABELS:
        return s, None
    low = s.lower()
    if low == "supported":
        return "Supported", None
    if low == "refuted":
        return "Refuted", None
    m = re.search(r"\b(supported|refuted)\b", s, re.IGNORECASE)
    if m:
        return "Supported" if m.group(1).lower() == "supported" else "Refuted", None
    s2 = s.strip('"\'.:;!?)(')
    if s2 in VALID_LABELS:
        return s2, None
    low2 = s2.lower()
    if low2 == "supported":
        return "Supported", None
    if low2 == "refuted":
        return "Refuted", None
    return None, raw_text


def write_output(path, fieldnames, rows):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    try:
        os.replace(tmp, path)
    except PermissionError:
        # Fallback for Windows file-lock/rename issues.
        # If atomic replace is blocked, rewrite the destination directly.
        with open(path, "w", encoding="utf-8", newline="") as out:
            w = csv.DictWriter(out, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        try:
            os.remove(tmp)
        except OSError:
            pass


def load_all_by_key(path):
    """Last row wins per (example_id, model, condition). Used to resume after partial runs."""
    out = {}
    if not os.path.isfile(path):
        return out
    with open(path, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[row_key(row)] = row
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Run fact-check prompts for each row in an experiment runs CSV."
    )
    parser.add_argument("--input", default=INPUT_PATH, help="Input experiment runs CSV")
    parser.add_argument("--output", default=OUTPUT_PATH, help="Output experiment results CSV")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    if not os.path.isfile(args.input):
        print(f"Input file not found: {args.input}", file=sys.stderr)
        print(
            "This repo's expanded runs file is usually "
            f"`{INPUT_PATH}`. "
            "Pass --input <path> if your file has another name.",
            file=sys.stderr,
        )
        sys.exit(1)

    def load_api_key():
        # 1) Prefer the environment (usual production/workstation pattern).
        env_key = os.getenv("OPENAI_API_KEY", "").strip()
        if env_key:
            print("OPENAI_API_KEY loaded from environment.")
            return env_key

        # 2) Fallback to local .env in the project root.
        # Keep parsing intentionally tiny and dependency-free.
        env_path = os.path.join(script_dir, ".env")
        if os.path.isfile(env_path):
            try:
                parsed = {}
                with open(env_path, encoding="utf-8") as f:
                    for raw_line in f:
                        line = raw_line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if line.startswith("export "):
                            line = line[len("export ") :].strip()
                        if "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
                            v = v[1:-1]
                        parsed[k] = v
                file_key = (parsed.get("OPENAI_API_KEY") or "").strip()
                if file_key:
                    print("OPENAI_API_KEY loaded from .env file.")
                    return file_key
            except Exception as e:
                print(f"Failed to read .env file: {type(e).__name__}: {e}", file=sys.stderr)

        return ""

    api_key = load_api_key()
    if not api_key:
        print("Missing OPENAI_API_KEY.", file=sys.stderr)
        print("Set it in your environment or in the project .env file, then re-run.", file=sys.stderr)
        print(f"  then: python {os.path.basename(__file__)}", file=sys.stderr)
        sys.exit(2)

    try:
        from openai import OpenAI
    except ImportError:
        print(
            "Install the OpenAI client: pip install -r requirements-openai.txt",
            file=sys.stderr,
        )
        sys.exit(3)

    client = OpenAI(api_key=api_key)

    with open(args.input, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise SystemExit("Input CSV has no header.")
        rows_in = list(reader)

    preflight_validate_rows(rows_in)

    by_key = load_all_by_key(args.output)
    results = []
    reused = 0
    api_calls = 0

    for i, base in enumerate(rows_in):
        k = row_key(base)
        row = dict(base)
        row.setdefault("error_type", "")
        row.setdefault("notes", "")

        prev = by_key.get(k)
        if prev:
            mo = (prev.get("model_output") or "").strip()
            if mo in VALID_LABELS:
                row["model_output"] = mo
                row["correct"] = prev.get("correct", "")
                row["error_type"] = prev.get("error_type", "") or ""
                row["notes"] = prev.get("notes", "") or ""
                results.append(row)
                reused += 1
                print(
                    f"[{i + 1}/{len(rows_in)}] skip (already valid): {k[0]} {k[1]} {k[2]}"
                )
                continue

        api_model = MODEL_API_NAMES.get((base.get("model") or "").strip())
        if not api_model:
            row["model_output"] = ""
            row["correct"] = "No"
            row["error_type"] = "invalid_model_name"
            row["notes"] = f"invalid_model_name:{base.get('model')!r}"[:NOTE_MAX]
            results.append(row)
            print(f"[{i + 1}/{len(rows_in)}] error: unknown model {base.get('model')!r}")
            write_output(args.output, fieldnames, results)
            continue

        try:
            prompt = build_prompt(base)
        except ValueError as e:
            row["model_output"] = ""
            row["correct"] = "No"
            row["error_type"] = "invalid_condition"
            row["notes"] = str(e)[:NOTE_MAX]
            results.append(row)
            print(f"[{i + 1}/{len(rows_in)}] error: {e}")
            write_output(args.output, fieldnames, results)
            continue

        print(f"[{i + 1}/{len(rows_in)}] API {api_model} {k[2]} example_id={k[0]}")
        raw_content = ""
        try:
            resp = client.chat.completions.create(
                model=api_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            raw_content = (resp.choices[0].message.content or "").strip()
            api_calls += 1
        except Exception as e:
            row["model_output"] = ""
            row["correct"] = "No"
            row["error_type"] = "api_error"
            row["notes"] = f"api_error:{type(e).__name__}:{e}"[:NOTE_MAX]
            results.append(row)
            print(f"  -> API failure: {e}")
            write_output(args.output, fieldnames, results)
            continue

        label, bad_raw = normalize_label(raw_content)
        gold = (row.get("true_label") or row.get("gold_label") or "").strip()

        if label is None:
            row["model_output"] = ""
            row["correct"] = "No"
            row["error_type"] = "invalid_model_output"
            snippet = (bad_raw or raw_content)[:NOTE_MAX]
            row["notes"] = f"invalid_model_output:{snippet}"
        else:
            row["model_output"] = label
            row["correct"] = "Yes" if label == gold else "No"
            row["notes"] = ""
            if row["correct"] == "Yes":
                row["error_type"] = ""
            elif gold == "Supported" and label == "Refuted":
                row["error_type"] = "supported_to_refuted"
            elif gold == "Refuted" and label == "Supported":
                row["error_type"] = "refuted_to_supported"
            else:
                row["error_type"] = "label_mismatch"
        results.append(row)
        by_key[k] = row
        safe_raw = raw_content.encode("ascii", "backslashreplace").decode("ascii")
        print(f"  -> raw={safe_raw!r} normalized={label!r} correct={row['correct']}")
        write_output(args.output, fieldnames, results)

    valid_count = sum(
        1 for r in results if (r.get("model_output") or "").strip() in VALID_LABELS
    )
    print()
    print(f"Done. Rows in output: {len(results)}")
    print(f"Reused from existing file (valid): {reused}")
    print(f"New API calls this run: {api_calls}")
    print(f"Rows with valid model_output (Supported/Refuted): {valid_count}")


if __name__ == "__main__":
    main()
