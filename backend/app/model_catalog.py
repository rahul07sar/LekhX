"""Discovery and status reporting for bundled and local LekhX GGUF models."""

from __future__ import annotations

import json
from pathlib import Path

from .config import BUNDLED_MODELS_DIR, DEFAULT_MODEL_NAME, MODELS_DIR, REFERENCE_DATA_DIR
from .db import get_setting, set_setting

MODEL_RELEASES_PATH = REFERENCE_DATA_DIR / "model-releases.json"


def _load_release_catalog() -> list[dict[str, object]]:
    if not MODEL_RELEASES_PATH.is_file():
        return []
    payload = json.loads(MODEL_RELEASES_PATH.read_text(encoding="utf-8"))
    models = payload.get("models")
    return list(models) if isinstance(models, list) else []


def discover_local_gguf_files() -> dict[str, Path]:
    """Scan local and bundled model directories for `.gguf` weights."""

    found: dict[str, Path] = {}
    for directory in (MODELS_DIR, BUNDLED_MODELS_DIR):
        if not directory.is_dir():
            continue
        for item in sorted(directory.glob("*.gguf")):
            if item.is_file():
                found[item.stem] = item
                found[item.name] = item
    return found


def list_models() -> dict[str, object]:
    """Return all cataloged models enriched with local availability status."""

    local_files = discover_local_gguf_files()
    active_model = get_setting("active_model", DEFAULT_MODEL_NAME) or DEFAULT_MODEL_NAME
    catalog = []
    seen_ids: set[str] = set()

    for entry in _load_release_catalog():
        model_id = str(entry.get("id") or "")
        filename = str(entry.get("filename") or "")
        matched_path = local_files.get(filename) or local_files.get(model_id)
        item = dict(entry)
        item["installed"] = matched_path is not None
        item["local_path"] = str(matched_path) if matched_path else None
        item["active"] = model_id == active_model
        catalog.append(item)
        seen_ids.add(model_id)

    for stem, path in local_files.items():
        if stem.endswith(".gguf") or stem in seen_ids:
            continue
        catalog.append(
            {
                "id": stem,
                "display_name": stem,
                "family": "local-gguf",
                "quantization": "unknown",
                "filename": path.name,
                "installed": True,
                "local_path": str(path),
                "active": stem == active_model,
                "description": "Locally imported GGUF runtime checkpoint.",
            }
        )
        seen_ids.add(stem)

    return {
        "active_model": active_model,
        "models_dir": str(MODELS_DIR),
        "models": catalog,
    }


def set_active_model(model_id: str) -> str:
    """Persist the user's preferred local model identifier."""

    cleaned = model_id.strip()
    if not cleaned:
        raise ValueError("Model identifier cannot be empty.")
    set_setting("active_model", cleaned)
    return cleaned
