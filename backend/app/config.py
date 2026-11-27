"""Central configuration for the LekhX offline office backend."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.environ.get("LEKHX_DATA_DIR", str(ROOT_DIR / "data"))).expanduser().resolve()
DATABASE_PATH = DATA_DIR / "lekhx.db"
EXPORTS_DIR = DATA_DIR / "exports"
USER_TEMPLATES_DIR = DATA_DIR / "templates"
MODELS_DIR = DATA_DIR / "models"
RUNTIME_DIR = DATA_DIR / "runtime"
BUNDLED_MODELS_DIR = ROOT_DIR / "models"
REFERENCE_DATA_DIR = Path(__file__).resolve().parent / "reference_data"
MANIFEST_PATH = ROOT_DIR / "packages" / "common" / "manifest.json"
DIST_DIR = ROOT_DIR / "dist"
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "LEKHX_ALLOWED_ORIGINS",
        "http://127.0.0.1:3001,http://localhost:3001,http://127.0.0.1:8010,http://localhost:8010",
    ).split(",")
    if origin.strip()
]

SUPPORTED_FORMATS = ("doc", "pdf", "excel", "powerpoint", "notes")
FORMAT_EXTENSIONS = {
    "doc": ".docx",
    "pdf": ".pdf",
    "excel": ".xlsx",
    "powerpoint": ".pptx",
    "notes": ".md",
}


def load_app_manifest() -> dict[str, object]:
    """Read the packaged LekhX manifest JSON safely."""

    if not MANIFEST_PATH.is_file():
        return {
            "app_name": "LekhX",
            "version": "1.0.0",
            "dataset_version": "1.0",
            "huggingface_repo": os.environ.get("LEKHX_HF_DATASET_REPO", "drishtijs/LekhX"),
            "dataset_url": os.environ.get(
                "LEKHX_HF_DATASET_URL",
                "https://huggingface.co/datasets/drishtijs/LekhX",
            ),
            "default_model": os.environ.get("LEKHX_DEFAULT_MODEL", "lekhx-1.0.0"),
        }
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


MANIFEST = load_app_manifest()
APP_NAME = str(MANIFEST.get("app_name") or "LekhX")
APP_VERSION = str(MANIFEST.get("version") or "1.0.0")
DATASET_VERSION = str(MANIFEST.get("dataset_version") or "1.0")
HF_DATASET_REPO = os.environ.get(
    "LEKHX_HF_DATASET_REPO",
    str(MANIFEST.get("huggingface_repo") or "drishtijs/LekhX"),
)
HF_DATASET_URL = os.environ.get(
    "LEKHX_HF_DATASET_URL",
    str(MANIFEST.get("dataset_url") or f"https://huggingface.co/datasets/{HF_DATASET_REPO}"),
)
DEFAULT_LLM_BASE_URL = os.environ.get("LEKHX_LLM_BASE_URL", "http://127.0.0.1:8080/v1")
DEFAULT_MODEL_NAME = os.environ.get(
    "LEKHX_DEFAULT_MODEL",
    str(MANIFEST.get("default_model") or "lekhx-1.0.0"),
)
