"""Verify merged Hugging Face checkpoints or PEFT LoRA adapter exports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def verify_checkpoint_dir(model_dir: Path) -> dict[str, object]:
    """Check presence and basic validity of safetensors or adapter weights."""

    if not model_dir.is_dir():
        raise FileNotFoundError(f"Model directory does not exist: {model_dir}")

    merged_weights = model_dir / "model.safetensors"
    adapter_weights = model_dir / "adapter_model.safetensors"
    config_file = model_dir / "config.json"
    adapter_config = model_dir / "adapter_config.json"

    if merged_weights.is_file() and config_file.is_file():
        return {
            "status": "ok",
            "kind": "merged_model",
            "weights": str(merged_weights),
            "size_bytes": merged_weights.stat().st_size,
        }
    if adapter_weights.is_file() and adapter_config.is_file():
        return {
            "status": "ok",
            "kind": "peft_lora_adapter",
            "weights": str(adapter_weights),
            "size_bytes": adapter_weights.stat().st_size,
        }
    raise ValueError(
        f"No valid merged model (model.safetensors + config.json) or adapter export found in {model_dir}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a local LekhX checkpoint folder.")
    parser.add_argument("model_dir", type=Path, help="Path to local checkpoint directory.")
    args = parser.parse_args()
    try:
        report = verify_checkpoint_dir(args.model_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Verification failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
