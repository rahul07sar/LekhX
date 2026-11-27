# Local Models & Offline Tooling

LekhX shares the same offline AI stack as Drishti-Agent:

- **Runtime**: `llama.cpp` server exposing an OpenAI-compatible local `/v1/chat/completions` endpoint, tuned dynamically by `backend/app/hardware_profile.py` (`small`, `balanced`, `advanced` hardware tiers).
- **Default & Fallback Models**:
  - `lekhx-1.0.0` (domain fine-tuned multilingual office planning GGUF, planned for `drishtijs/LekhX`)
  - `qwen2.5-0.5b` (lightweight general multilingual Q4_K_M baseline)
- **Fine-Tuning Pipeline**:
  - `scripts/prepare_training_data.py` builds instruction SFT JSONL data from verified templates and multilingual office scenarios.
  - `scripts/train_model.py` runs local PEFT LoRA / QLoRA fine-tuning from Hugging Face open-weights models (`trust_remote_code=False`) and merges adapters cleanly into `model.safetensors`.
  - `scripts/verify_model_checkpoint.py` verifies `model.safetensors` / adapter exports before GGUF conversion and publication to [`https://huggingface.co/datasets/drishtijs/LekhX`](https://huggingface.co/datasets/drishtijs/LekhX).
