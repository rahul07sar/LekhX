"""Offline LoRA / QLoRA fine-tuning harness for LekhX multilingual office models."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Fine-tune a LekhX LoRA/QLoRA adapter locally.")
    parser.add_argument("--base-model", default="Qwen/Qwen2.5-0.5B-Instruct")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=ROOT_DIR / "data" / "training" / "sft_chat_dataset.jsonl",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT_DIR / "data" / "models" / "lekhx-1.0.0-lora",
    )
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--merge", action="store_true", help="Merge LoRA adapter into model.safetensors.")
    args = parser.parse_args()

    if not args.dataset.is_file():
        print(
            f"Training dataset not found at {args.dataset}. Run scripts/prepare_training_data.py first.",
            file=sys.stderr,
        )
        return 1

    try:
        from peft import LoraConfig  # noqa: F401
        from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: F401
    except ImportError as exc:
        print(f"Install requirements-model-dev.txt to train models locally: {exc}", file=sys.stderr)
        return 1

    print(
        "Validated training prerequisites:",
        {
            "base_model": args.base_model,
            "dataset": str(args.dataset),
            "output_dir": str(args.output_dir),
            "epochs": args.epochs,
            "trust_remote_code": False,
            "merge_on_finish": args.merge,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
