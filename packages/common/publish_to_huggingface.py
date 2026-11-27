"""Publish built LekhX release payloads and documentation to drishtijs/LekhX on Hugging Face."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[2]
REPO = os.environ.get("LEKHX_HF_DATASET_REPO", "drishtijs/LekhX")


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload LekhX release assets to Hugging Face.")
    parser.add_argument("--repo", default=REPO, help="Target Hugging Face dataset repository.")
    parser.add_argument(
        "--releases-dir",
        type=Path,
        default=ROOT_DIR / "dist" / "releases",
        help="Directory containing built archives and update manifests.",
    )
    parser.add_argument("--dry-run", action="store_true", help="List files without uploading.")
    args = parser.parse_args()

    files = []
    if args.releases_dir.is_dir():
        files.extend(sorted(p for p in args.releases_dir.iterdir() if p.is_file()))
    manifest_file = ROOT_DIR / "packages" / "common" / "manifest.json"
    if manifest_file.is_file():
        files.append(manifest_file)

    if args.dry_run:
        print(f"Dry run for dataset repository: {args.repo}")
        for item in files:
            print(f" - {item.relative_to(ROOT_DIR)}")
        return 0

    try:
        from huggingface_hub import HfApi
    except ImportError as exc:
        print(f"huggingface_hub is required to upload releases: {exc}", file=sys.stderr)
        return 1

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    api = HfApi(token=token)
    for item in files:
        path_in_repo = (
            item.name
            if item.parent == args.releases_dir
            else str(item.relative_to(ROOT_DIR)).replace("\\", "/")
        )
        print(f"Uploading {path_in_repo} -> {args.repo} ...")
        api.upload_file(
            path_or_fileobj=str(item),
            path_in_repo=path_in_repo,
            repo_id=args.repo,
            repo_type="dataset",
            commit_message=f"Publish LekhX release asset {path_in_repo}",
        )
    print(f"Done uploading to https://huggingface.co/datasets/{args.repo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
