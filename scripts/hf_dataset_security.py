"""Verify immutable Hugging Face dataset inputs from drishtijs/LekhX before training."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
import re
from typing import Callable

COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def sha256(path: Path) -> str:
    """Compute SHA-256 digest for a local dataset artifact."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_dataset_lock(path: Path, expected_repository: str = "drishtijs/LekhX") -> dict:
    """Validate and return the pinned dataset lock JSON descriptor."""

    if not path.is_file() or path.is_symlink():
        raise ValueError("Dataset lock must be a regular version-controlled file")
    lock = json.loads(path.read_text(encoding="utf-8"))
    if lock.get("format") != 1 or lock.get("repository") != expected_repository:
        raise ValueError("Dataset lock repository or format is invalid")
    if not COMMIT_PATTERN.fullmatch(str(lock.get("revision", ""))):
        raise ValueError("Dataset lock must contain a full immutable commit revision")
    files = lock.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("Dataset lock must contain at least one file")
    for remote_path, metadata in files.items():
        path_parts = Path(remote_path).parts
        if not remote_path or remote_path.startswith("/") or ".." in path_parts:
            raise ValueError("Dataset lock contains an unsafe remote path")
        if not isinstance(metadata, dict) or not SHA256_PATTERN.fullmatch(str(metadata.get("sha256", ""))):
            raise ValueError(f"Dataset lock has an invalid SHA-256 for {remote_path}")
        if not isinstance(metadata.get("size_bytes"), int) or metadata["size_bytes"] <= 0:
            raise ValueError(f"Dataset lock has an invalid size for {remote_path}")
    return lock


def download_verified_dataset(
    *,
    api,
    downloader: Callable[..., str],
    lock: dict,
) -> dict[str, Path]:
    """Download files only from the pinned commit revision and verify size + SHA-256."""

    repository = lock["repository"]
    revision = lock["revision"]
    info = api.repo_info(repository, repo_type="dataset", revision=revision)
    if info.sha != revision:
        raise ValueError("Hugging Face did not resolve the exact locked dataset commit")

    verified: dict[str, Path] = {}
    for remote_path, metadata in lock["files"].items():
        local = Path(
            downloader(
                repository,
                remote_path,
                repo_type="dataset",
                revision=revision,
            )
        )
        if local.stat().st_size != metadata["size_bytes"]:
            raise ValueError(f"Dataset size mismatch: {remote_path}")
        actual = sha256(local)
        if not hmac.compare_digest(actual, metadata["sha256"]):
            raise ValueError(f"Dataset checksum mismatch: {remote_path}")
        verified[remote_path] = local
    return verified
