"""Download and prepare official FEVER pre-processed Wikipedia shard files."""

import argparse
import os
import shutil
import tempfile
import urllib.request
import urllib.error
import zipfile
from pathlib import Path

from experiment_config import (
    FEVER_WIKI_DOWNLOAD_URL,
    FEVER_WIKI_DOWNLOAD_URLS,
    WIKI_ROOT_DIR,
    WIKI_SHARD_DIR,
    WIKI_SHARD_PATTERN,
    list_wiki_shards,
    require_wiki_shards,
)


def download_zip(url, destination):
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; fever-data-setup/1.0)"},
    )
    with urllib.request.urlopen(request) as response, open(destination, "wb") as out:
        shutil.copyfileobj(response, out)


def attempt_download(urls, destination):
    failures = []
    for url in urls:
        try:
            print(f"Downloading FEVER wiki archive from: {url}")
            download_zip(url, destination)
            print(f"Downloaded archive: {destination}")
            return url
        except urllib.error.HTTPError as exc:
            failures.append(f"{url} -> HTTP {exc.code}")
        except urllib.error.URLError as exc:
            failures.append(f"{url} -> URL error: {exc.reason}")
        except Exception as exc:
            failures.append(f"{url} -> {type(exc).__name__}: {exc}")

    raise SystemExit(
        "Unable to download FEVER wiki archive from configured URLs.\n"
        + "\n".join(failures)
        + "\nUse --archive <local_wiki_pages.zip> if you already have the file."
    )


def discover_shards(root_dir):
    root = Path(root_dir)
    return sorted(root.rglob("wiki-*.jsonl"))


def copy_shards(shards, target_dir):
    os.makedirs(target_dir, exist_ok=True)
    copied = 0
    for source in shards:
        destination = os.path.join(target_dir, source.name)
        if os.path.isfile(destination):
            continue
        shutil.copy2(source, destination)
        copied += 1
    return copied


def main():
    parser = argparse.ArgumentParser(
        description="Download and arrange FEVER wiki shards for evidence resolution."
    )
    parser.add_argument(
        "--url",
        default=FEVER_WIKI_DOWNLOAD_URL,
        help="Primary URL for official FEVER pre-processed Wikipedia archive",
    )
    parser.add_argument(
        "--archive",
        default=os.path.join(WIKI_ROOT_DIR, "wiki-pages.zip"),
        help="Local zip path",
    )
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Redownload archive even if already present",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Delete existing shard directory before extraction",
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    existing = list_wiki_shards(WIKI_SHARD_PATTERN)
    if existing and not args.force_download and not args.force_refresh:
        print(f"Wiki shards already present: {len(existing)} files")
        print(f"Pattern: {WIKI_SHARD_PATTERN}")
        return

    if args.force_refresh and os.path.isdir(WIKI_SHARD_DIR):
        shutil.rmtree(WIKI_SHARD_DIR)

    archive_path = args.archive
    if args.force_download or not os.path.isfile(archive_path):
        urls = [args.url] + [u for u in FEVER_WIKI_DOWNLOAD_URLS if u != args.url]
        attempt_download(urls, archive_path)
    else:
        print(f"Using existing archive: {archive_path}")

    with tempfile.TemporaryDirectory(prefix="fever_wiki_extract_") as tmp_dir:
        print(f"Extracting archive into temporary directory: {tmp_dir}")
        with zipfile.ZipFile(archive_path) as zip_file:
            zip_file.extractall(tmp_dir)

        discovered = discover_shards(tmp_dir)
        if not discovered:
            raise SystemExit(
                "No wiki-*.jsonl files found in archive. "
                "Verify FEVER archive URL or archive contents."
            )

        copied = copy_shards(discovered, WIKI_SHARD_DIR)
        print(f"Discovered shard files: {len(discovered)}")
        print(f"Copied new shard files: {copied}")

    try:
        shards = require_wiki_shards(WIKI_SHARD_PATTERN)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc))

    print(f"Prepared FEVER wiki shards: {len(shards)} files")
    print(f"Shard directory: {WIKI_SHARD_DIR}")
    print(f"Shard glob: {WIKI_SHARD_PATTERN}")


if __name__ == "__main__":
    main()
