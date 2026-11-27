"""Tests for dynamic multilingual template and language pack resolution."""

from __future__ import annotations

import importlib
import json
import os
from pathlib import Path
import tempfile
import unittest


class OfficeTemplatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        os.environ["LEKHX_DATA_DIR"] = str(self.data_dir)
        for mod_name in ("backend.app.config", "backend.app.guardrails", "backend.app.office_templates"):
            if mod_name in importlib.sys.modules:
                importlib.reload(importlib.sys.modules[mod_name])

        from backend.app.office_templates import (
            get_language_pack,
            load_languages,
            load_templates,
            localized_section_label,
            resolve_template,
        )

        self.get_language_pack = get_language_pack
        self.load_languages = load_languages
        self.load_templates = load_templates
        self.localized_section_label = localized_section_label
        self.resolve_template = resolve_template

    def tearDown(self) -> None:
        os.environ.pop("LEKHX_DATA_DIR", None)
        self._tmp.cleanup()

    def test_languages_cover_multiple_scripts(self) -> None:
        codes = {str(item["code"]) for item in self.load_languages()}
        for required in ("en", "hi", "bn", "ta", "es", "fr", "de", "ar", "ja"):
            self.assertIn(required, codes)
        arabic = self.get_language_pack("ar")
        self.assertEqual(arabic["direction"], "rtl")
        hindi = self.get_language_pack("hi")
        self.assertEqual(self.localized_section_label(hindi, "executive_summary"), "कार्यकारी सारांश")

    def test_filter_templates_and_custom_user_template(self) -> None:
        excel_templates = self.load_templates(office_format="excel")
        self.assertTrue(any(t["id"] == "tpl-budget-ledger" for t in excel_templates))

        custom_dir = self.data_dir / "templates"
        custom_dir.mkdir(parents=True, exist_ok=True)
        (custom_dir / "custom-sop.json").write_text(
            json.dumps(
                {
                    "id": "tpl-custom-sop",
                    "name": "Custom SOP",
                    "category": "custom",
                    "formats": ["doc", "notes"],
                    "description": "User-authored SOP template.",
                    "default_sections": ["overview", "checklist"],
                }
            ),
            encoding="utf-8",
        )
        resolved = self.resolve_template("tpl-custom-sop", "doc")
        self.assertEqual(resolved["source"], "custom")
        self.assertEqual(resolved["name"], "Custom SOP")


if __name__ == "__main__":
    unittest.main()
