"""Shared release and dataset version numbering with 0-9 rollover rules."""

from __future__ import annotations

import re

SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.([0-9])\.([0-9])$")
DATASET_VERSION_PATTERN = re.compile(r"^(0|[1-9]\d*)\.([0-9])$")


def parse_semver(version: str) -> tuple[int, int, int]:
    """Parse a release string using 0-9 rollover for minor and patch digits."""

    match = SEMVER_PATTERN.fullmatch(version.strip())
    if not match:
        raise ValueError(
            f"Unsupported version format {version!r}; expected M.m.p with 0-9 minor/patch digits."
        )
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_semver(version: str, part: str = "patch") -> str:
    """Increment a semver string with 0-9 rollover across patch and minor digits."""

    major, minor, patch = parse_semver(version)
    if part == "major":
        return f"{major + 1}.0.0"
    if part == "minor":
        if minor >= 9:
            return f"{major + 1}.0.0"
        return f"{major}.{minor + 1}.0"
    if part == "patch":
        if patch < 9:
            return f"{major}.{minor}.{patch + 1}"
        if minor < 9:
            return f"{major}.{minor + 1}.0"
        return f"{major + 1}.0.0"
    raise ValueError(f"Unknown bump part {part!r}; expected 'major', 'minor', or 'patch'.")


def parse_dataset_version(version: str) -> tuple[int, int]:
    """Parse a dataset version string with a 0-9 minor rollover digit."""

    match = DATASET_VERSION_PATTERN.fullmatch(version.strip())
    if not match:
        raise ValueError(
            f"Unsupported dataset version {version!r}; expected M.m with a 0-9 minor digit."
        )
    return int(match.group(1)), int(match.group(2))


def bump_dataset_version(version: str) -> str:
    """Increment a dataset version with 0-9 minor rollover into the major version."""

    major, minor = parse_dataset_version(version)
    if minor >= 9:
        return f"{major + 1}.0"
    return f"{major}.{minor + 1}"
