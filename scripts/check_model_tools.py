"""Preflight check for local Python AI, PEFT, and GGUF packaging dependencies."""

from __future__ import annotations

import importlib.util
import json
import shutil

REQUIRED_MODULES = (
    "fastapi",
    "pydantic",
    "uvicorn",
    "pypdf",
    "PIL",
    "ftfy",
    "transformers",
    "peft",
    "safetensors",
    "huggingface_hub",
    "gguf",
)


def check_toolchain() -> dict[str, object]:
    """Inspect Python package availability and optional llama.cpp CLI binaries."""

    modules = {name: importlib.util.find_spec(name) is not None for name in REQUIRED_MODULES}
    binaries = {
        "llama-server": shutil.which("llama-server"),
        "llama-cli": shutil.which("llama-cli"),
        "node": shutil.which("node"),
        "npm": shutil.which("npm"),
    }
    return {"modules": modules, "binaries": binaries}


if __name__ == "__main__":
    print(json.dumps(check_toolchain(), indent=2))
