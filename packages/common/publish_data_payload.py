"""Build versioned LekhX data, template, and model update payloads for drishtijs/LekhX."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile

ROOT_DIR = Path(__file__).resolve().parents[2]
COMMON_DIR = Path(__file__).resolve().parent


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def build_data_payload(output_dir: Path | None = None) -> dict[str, object]:
    """Create the versioned dataset + template archive + update manifest JSON."""

    manifest = json.loads((COMMON_DIR / "manifest.json").read_text(encoding="utf-8"))
    version = str(manifest["version"])
    dataset_version = str(manifest["dataset_version"])
    repo_id = str(manifest.get("huggingface_repo") or "drishtijs/LekhX")

    target_dir = (output_dir or ROOT_DIR / "dist" / "releases").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / f"lekhx-data-{dataset_version}.tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        ref_dir = ROOT_DIR / "backend" / "app" / "reference_data"
        if ref_dir.is_dir():
            tar.add(ref_dir, arcname="reference_data")
        docs_dir = ROOT_DIR / "docs"
        if docs_dir.is_dir():
            tar.add(docs_dir, arcname="docs")

    payload_manifest = {
        "app_name": "LekhX",
        "version": version,
        "dataset_version": dataset_version,
        "huggingface_repo": repo_id,
        "dataset_url": f"https://huggingface.co/datasets/{repo_id}",
        "archive_filename": archive_path.name,
        "archive_sha256": _sha256(archive_path),
        "archive_size_bytes": archive_path.stat().st_size,
        "model_updates": manifest.get("model_updates", []),
    }
    manifest_out = target_dir / "lekhx-update-manifest.json"
    manifest_out.write_text(json.dumps(payload_manifest, indent=2) + "\n", encoding="utf-8")
    return {
        "archive_path": str(archive_path),
        "manifest_path": str(manifest_out),
        "payload": payload_manifest,
    }


if __name__ == "__main__":
    print(json.dumps(build_data_payload(), indent=2))
