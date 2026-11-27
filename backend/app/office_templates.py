"""Dynamic multilingual catalog & template loader for office generation."""

from __future__ import annotations

import json
from pathlib import Path

from .config import REFERENCE_DATA_DIR, USER_TEMPLATES_DIR
from .guardrails import normalize_multilingual_text

TEMPLATES_PATH = REFERENCE_DATA_DIR / "lekhx-office-templates.jsonl"
MULTILINGUAL_PATH = REFERENCE_DATA_DIR / "lekhx-multilingual.jsonl"


def load_languages() -> list[dict[str, object]]:
    """Load supported language packs from bundled JSONL metadata."""

    if not MULTILINGUAL_PATH.is_file():
        return [
            {
                "code": "en",
                "name": "English",
                "native_name": "English",
                "direction": "ltr",
                "section_labels": {},
                "table_headers": ["Item", "Details", "Category", "Value"],
                "speaker_note_prefix": "Speaker Notes",
            }
        ]
    languages: list[dict[str, object]] = []
    for line in MULTILINGUAL_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            languages.append(json.loads(line))
    return languages


def get_language_pack(language_code: str) -> dict[str, object]:
    """Return the matching language pack, defaulting cleanly to English when unknown."""

    cleaned = (language_code or "en").strip().lower()
    packs = load_languages()
    for pack in packs:
        if str(pack.get("code", "")).lower() == cleaned:
            return pack
    return packs[0]


def load_templates(*, office_format: str | None = None) -> list[dict[str, object]]:
    """Load built-in templates and user templates from `USER_TEMPLATES_DIR`."""

    templates: list[dict[str, object]] = []
    if TEMPLATES_PATH.is_file():
        for line in TEMPLATES_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                item = json.loads(line)
                item["source"] = "built-in"
                templates.append(item)

    if USER_TEMPLATES_DIR.is_dir():
        for custom_file in sorted(USER_TEMPLATES_DIR.glob("*.json")):
            if custom_file.is_symlink() or not custom_file.is_file():
                continue
            try:
                item = json.loads(custom_file.read_text(encoding="utf-8"))
                if isinstance(item, dict) and item.get("id") and item.get("name"):
                    item["source"] = "custom"
                    templates.append(item)
            except (json.JSONDecodeError, OSError):
                continue

    if office_format:
        filtered = [
            tpl
            for tpl in templates
            if office_format in (tpl.get("formats") or [])
        ]
        if filtered:
            return filtered
    return templates


def resolve_template(template_id: str | None, office_format: str) -> dict[str, object]:
    """Find a requested template or pick the best matching template for the format."""

    all_templates = load_templates()
    if template_id:
        for tpl in all_templates:
            if str(tpl.get("id")) == template_id:
                return tpl
    matching = load_templates(office_format=office_format)
    if matching:
        return matching[0]
    return {
        "id": "tpl-executive-report",
        "name": "Executive Report",
        "category": "general",
        "formats": [office_format],
        "description": "Structured general office document.",
        "accent_hex": "#1D4ED8",
        "default_sections": ["overview", "key_findings", "recommendations"],
        "include_table": office_format == "excel",
    }


def localized_section_label(language_pack: dict[str, object], section_key: str) -> str:
    """Resolve a localized heading for a template section key."""

    labels = language_pack.get("section_labels") or {}
    if isinstance(labels, dict) and section_key in labels:
        return normalize_multilingual_text(str(labels[section_key]))
    return normalize_multilingual_text(section_key.replace("_", " ").title())
