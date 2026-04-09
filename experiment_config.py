"""Shared configuration for FEVER fact-checking experiments."""

import glob
import os

DEFAULT_TAG = "balanced_10000_v1"

EXPECTED_PER_LABEL = 5000
EXPECTED_TOTAL = EXPECTED_PER_LABEL * 2

MODEL_API_NAMES = {
    "gpt-5.4": "gpt-5.4",
    "gpt-5.4-mini": "gpt-5.4-mini",
}

MODEL_NAMES = tuple(MODEL_API_NAMES.keys())
CONDITIONS = ("claim_only", "claim_plus_evidence")
RUNS = tuple((model, condition) for model in MODEL_NAMES for condition in CONDITIONS)

VALID_LABELS = ("Supported", "Refuted")

FEVER_WIKI_DOWNLOAD_URL = "https://s3-eu-west-1.amazonaws.com/fever.public/wiki-pages.zip"
FEVER_WIKI_DOWNLOAD_URLS = (
    FEVER_WIKI_DOWNLOAD_URL,
    "https://s3.amazonaws.com/fever.public/wiki-pages.zip",
    "https://fever.public.s3.amazonaws.com/wiki-pages.zip",
    "https://dl.fbaipublicfiles.com/fever/wiki-pages.zip",
)
WIKI_ROOT_DIR = "wiki-pages"
WIKI_SHARD_DIR = os.path.join(WIKI_ROOT_DIR, "wiki-pages")
WIKI_SHARD_PATTERN = os.path.join(WIKI_SHARD_DIR, "wiki-*.jsonl")


def list_wiki_shards(wiki_pattern=WIKI_SHARD_PATTERN):
    return sorted(glob.glob(wiki_pattern))


def require_wiki_shards(wiki_pattern=WIKI_SHARD_PATTERN):
    shards = list_wiki_shards(wiki_pattern)
    if shards:
        return shards

    raise FileNotFoundError(
        "Missing FEVER wiki shards. Expected files matching "
        f"{wiki_pattern}. Run prepare_fever_wiki_pages.py first."
    )
