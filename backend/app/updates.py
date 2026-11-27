"""Local & Hugging Face (drishtijs/LekhX) release status and safe update checks."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import APP_VERSION, DATASET_VERSION, HF_DATASET_REPO, HF_DATASET_URL, load_app_manifest


def get_local_update_status() -> dict[str, object]:
    """Return local release metadata and drishtijs/LekhX repository coordinates."""

    manifest = load_app_manifest()
    return {
        "app_name": manifest.get("app_name", "LekhX"),
        "current_version": APP_VERSION,
        "dataset_version": DATASET_VERSION,
        "huggingface_repo": HF_DATASET_REPO,
        "dataset_url": HF_DATASET_URL,
        "remote_manifest_url": f"https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/lekhx-update-manifest.json",
        "preserved_paths": manifest.get("user_data_paths_preserved_on_update", []),
        "model_updates": manifest.get("model_updates", []),
    }


def check_remote_updates(timeout_seconds: float = 4.0) -> dict[str, object]:
    """Query `drishtijs/LekhX` for a newer `lekhx-update-manifest.json` when online."""

    status = get_local_update_status()
    url = str(status["remote_manifest_url"])
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            remote = json.loads(response.read().decode("utf-8"))
        remote_version = str(remote.get("version") or APP_VERSION)
        remote_dataset_version = str(remote.get("dataset_version") or DATASET_VERSION)
        return {
            **status,
            "reachable": True,
            "update_available": (remote_version != APP_VERSION) or (remote_dataset_version != DATASET_VERSION),
            "remote_version": remote_version,
            "remote_dataset_version": remote_dataset_version,
            "remote_model_updates": remote.get("model_updates", []),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            **status,
            "reachable": False,
            "update_available": False,
            "detail": f"Offline or no published manifest yet on {HF_DATASET_REPO}: {exc}",
        }
