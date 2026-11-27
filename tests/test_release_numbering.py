"""Tests for 0-9 release version rollover rules."""

from __future__ import annotations

import unittest

from packages.common.release_numbering import bump_dataset_version, bump_semver


class ReleaseNumberingTests(unittest.TestCase):
    def test_semver_zero_to_nine_rollover(self) -> None:
        self.assertEqual(bump_semver("1.0.0"), "1.0.1")
        self.assertEqual(bump_semver("1.0.9"), "1.1.0")
        self.assertEqual(bump_semver("1.9.9"), "2.0.0")
        self.assertEqual(bump_semver("1.9.3", part="minor"), "2.0.0")

    def test_dataset_version_rollover(self) -> None:
        self.assertEqual(bump_dataset_version("1.0"), "1.1")
        self.assertEqual(bump_dataset_version("1.9"), "2.0")


if __name__ == "__main__":
    unittest.main()
