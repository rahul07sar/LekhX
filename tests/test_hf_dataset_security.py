"""Tests for immutable Hugging Face dataset lock validation."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from scripts.hf_dataset_security import download_verified_dataset, load_dataset_lock, sha256


class FakeRepoInfo:
    def __init__(self, sha: str) -> None:
        self.sha = sha


class FakeApi:
    def __init__(self, sha: str) -> None:
        self._sha = sha

    def repo_info(self, *_args, **_kwargs) -> FakeRepoInfo:
        return FakeRepoInfo(self._sha)


class HfDatasetSecurityTests(unittest.TestCase):
    def test_lock_and_checksum_verification(self) -> None:
        commit = "a" * 40
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sample = root / "sft.jsonl"
            sample.write_text('{"id": 1}\n', encoding="utf-8")
            digest = sha256(sample)

            lock_path = root / "lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "format": 1,
                        "repository": "drishtijs/LekhX",
                        "revision": commit,
                        "files": {
                            "training/sft.jsonl": {
                                "sha256": digest,
                                "size_bytes": sample.stat().st_size,
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )
            lock = load_dataset_lock(lock_path, expected_repository="drishtijs/LekhX")
            verified = download_verified_dataset(
                api=FakeApi(commit),
                downloader=lambda *_args, **_kwargs: str(sample),
                lock=lock,
            )
            self.assertEqual(verified["training/sft.jsonl"], sample)

    def test_rejects_wrong_repo_or_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            lock_path = Path(tmp) / "bad-lock.json"
            lock_path.write_text(
                json.dumps(
                    {
                        "format": 1,
                        "repository": "other/Repo",
                        "revision": "b" * 40,
                        "files": {"../secret": {"sha256": "0" * 64, "size_bytes": 10}},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_dataset_lock(lock_path, expected_repository="drishtijs/LekhX")


if __name__ == "__main__":
    unittest.main()
