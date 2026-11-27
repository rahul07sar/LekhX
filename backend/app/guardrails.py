"""Deterministic input validation, path confinement, and NeMo Guardrails adapter."""

from __future__ import annotations

from pathlib import Path
import re
import unicodedata

try:
    from ftfy import fix_text
except ImportError:  # pragma: no cover - optional fallback when ftfy not installed
    def fix_text(text: str) -> str:
        return text

from .config import EXPORTS_DIR, USER_TEMPLATES_DIR

FORBIDDEN_PATH_TOKENS = re.compile(
    r"(?:\.\.[/\\]|(?:^|[\s\"'])/(?:etc|System|Windows)/|C:\\Windows)",
    re.IGNORECASE,
)
SAFE_FILENAME_STRIP = re.compile(r"[^\w.\- ]+", re.UNICODE)


def normalize_multilingual_text(text: str) -> str:
    """Repair mojibake and apply NFC Unicode normalization for office exports."""

    cleaned = fix_text(text or "")
    return unicodedata.normalize("NFC", cleaned).strip()


def validate_generation_prompt(prompt: str) -> tuple[bool, str | None]:
    """Reject empty or unsafe system-file overwrite instructions before planning."""

    normalized = normalize_multilingual_text(prompt)
    if len(normalized) < 3:
        return False, "Please provide at least a short topic or content brief."
    if FORBIDDEN_PATH_TOKENS.search(normalized):
        return False, "LekhX only exports office files inside the managed export directory."
    return True, None


def sanitize_filename(raw_name: str, expected_extension: str) -> str:
    """Produce a safe, portable filename ending in the expected extension."""

    stem = Path(raw_name or "document").stem.strip()
    stem = SAFE_FILENAME_STRIP.sub("-", stem).strip(" .-")
    if not stem:
        stem = "lekhx-document"
    stem = stem[:80]
    ext = expected_extension if expected_extension.startswith(".") else f".{expected_extension}"
    return f"{stem}{ext}"


def resolve_safe_export_path(filename: str, expected_extension: str) -> Path:
    """Resolve an export file path guaranteed to stay inside `EXPORTS_DIR` without symlinks."""

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    root = EXPORTS_DIR.resolve()
    safe_name = sanitize_filename(filename, expected_extension)
    candidate = (root / safe_name).resolve()
    if candidate.parent != root:
        raise ValueError("Unsafe export path outside managed export directory.")
    if candidate.exists() and candidate.is_symlink():
        raise ValueError("Refusing to overwrite symbolic link in export directory.")
    return candidate


def resolve_safe_template_path(template_filename: str) -> Path:
    """Resolve a user template JSON path safely inside `USER_TEMPLATES_DIR`."""

    USER_TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    root = USER_TEMPLATES_DIR.resolve()
    safe_name = sanitize_filename(template_filename, ".json")
    candidate = (root / safe_name).resolve()
    if candidate.parent != root or candidate.is_symlink():
        raise ValueError("Unsafe custom template path.")
    return candidate
