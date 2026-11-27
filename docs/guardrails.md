# LekhX Security & Guardrails

LekhX follows a fail-closed, local-only security model:

1. **Path Confinement**: Exported files and custom templates are resolved inside canonicalized `DATA_DIR/exports` and `DATA_DIR/templates` roots; symbolic links and `..` traversal components are rejected.
2. **XML & Markup Safety**: Every value interpolated into OOXML (`.docx`, `.xlsx`, `.pptx`) or HTML/Markdown previews is XML-escaped and normalized via `ftfy` / NFC Unicode normalization.
3. **NeMo Guardrails Integration**: `backend/app/guardrails.py` loads `backend/app/guardrails_config/config.yml` and `rails.co` to inspect prompts and generated specs alongside deterministic policy checks.
4. **Hugging Face Dataset Verification**: Remote downloads from `drishtijs/LekhX` check immutable commit revisions, file sizes, and SHA-256 digests (`scripts/hf_dataset_security.py`) with `trust_remote_code=False`.
5. **User Data Preservation**: Upgrades and dataset refreshes preserve `data/lekhx.db`, `data/exports`, `data/templates`, and existing `data/models`.
