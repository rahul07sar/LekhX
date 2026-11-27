"""Generate offline SFT training examples from verified LekhX templates and language packs."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.office_templates import load_languages, load_templates, localized_section_label


def build_training_examples() -> list[dict[str, object]]:
    """Construct chat SFT examples combining templates, formats, and languages."""

    templates = load_templates()
    languages = load_languages()
    examples: list[dict[str, object]] = []

    for tpl in templates:
        formats = list(tpl.get("formats") or ["doc"])
        section_keys = list(tpl.get("default_sections") or ["overview"])
        for lang in languages:
            code = str(lang.get("code") or "en")
            native_name = str(lang.get("native_name") or code)
            for fmt in formats:
                plan_preview = {
                    "format": fmt,
                    "language": code,
                    "template_id": tpl.get("id"),
                    "sections": [
                        {
                            "heading": localized_section_label(lang, str(key)),
                            "paragraphs": [],
                            "bullets": [],
                        }
                        for key in section_keys
                    ],
                }
                examples.append(
                    {
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are LekhX, an offline multilingual office document architect. "
                                    "Emit strictly structured DocumentPlan JSON."
                                ),
                            },
                            {
                                "role": "user",
                                "content": f"Create a {fmt} file using template {tpl.get('id')} in {native_name} ({code}).",
                            },
                            {
                                "role": "assistant",
                                "content": json.dumps(plan_preview, ensure_ascii=False),
                            },
                        ]
                    }
                )
    return examples


def main() -> int:
    output_dir = ROOT_DIR / "data" / "training"
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / "sft_chat_dataset.jsonl"
    examples = build_training_examples()
    with out_file.open("w", encoding="utf-8") as handle:
        for row in examples:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"examples": len(examples), "output": str(out_file)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
