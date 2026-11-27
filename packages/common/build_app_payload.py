"""Build reproducible LekhX app payload bundles containing backend, UI, and configs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile

ROOT_DIR = Path(__file__).resolve().parents[2]
INCLUDE_PATHS = [
    "app",
    "public",
    "drishti.app.js",
    "drishti.config.json",
    "index.html",
    "package.json",
    "backend/app",
    "docs",
    "packages/common/manifest.json",
    "packages/common/release_numbering.py",
    "scripts/ingest_reference_datasets.py",
    "requirements-backend.txt",
    "README.md",
    "# Project guidelines.md",
    "project-map.md",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build_app_payload(output_dir: Path | None = None) -> dict[str, object]:
    """Package LekhX runtime assets into a verifiable `.tar.gz` archive."""

    manifest = json.loads((ROOT_DIR / "packages/common/manifest.json").read_text(encoding="utf-8"))
    version = str(manifest["version"])
    target_dir = (output_dir or ROOT_DIR / "dist" / "releases").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / f"lekhx-app-{version}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        for rel in INCLUDE_PATHS:
            candidate = ROOT_DIR / rel
            if candidate.exists():
                tar.add(candidate, arcname=rel)
        dist_dir = ROOT_DIR / "dist"
        if (dist_dir / "index.html").is_file():
            for child in sorted(dist_dir.iterdir()):
                if child.name == "releases":
                    continue
                tar.add(child, arcname=f"dist/{child.name}")

    checksum = _sha256(archive_path)
    return {
        "version": version,
        "archive_path": str(archive_path),
        "sha256": checksum,
        "size_bytes": archive_path.stat().st_size,
    }


if __name__ == "__main__":
    print(json.dumps(build_app_payload(), indent=2))
