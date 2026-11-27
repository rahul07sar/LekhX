"""Tests verifying deterministic multi-language generation across docx, pdf, xlsx, pptx, and notes."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from pypdf import PdfReader


class DocumentGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self._tmp.name)
        os.environ["LEKHX_DATA_DIR"] = str(self.data_dir)
        for mod_name in (
            "backend.app.config",
            "backend.app.guardrails",
            "backend.app.document_generators",
            "backend.app.schemas",
        ):
            if mod_name in importlib.sys.modules:
                importlib.reload(importlib.sys.modules[mod_name])

        from backend.app.document_generators import generate_office_file
        from backend.app.guardrails import resolve_safe_export_path
        from backend.app.schemas import DocumentPlan, DocumentSection, SlidePlan, TableData

        self.generate_office_file = generate_office_file
        self.resolve_safe_export_path = resolve_safe_export_path
        self.DocumentPlan = DocumentPlan
        self.DocumentSection = DocumentSection
        self.SlidePlan = SlidePlan
        self.TableData = TableData

    def tearDown(self) -> None:
        os.environ.pop("LEKHX_DATA_DIR", None)
        self._tmp.cleanup()

    def test_generate_docx_multilingual_xml_valid(self) -> None:
        plan = self.DocumentPlan(
            title="वार्षिक रिपोर्ट 2026 & Overview",
            subtitle="Offline Hindi & English Report",
            format="doc",
            language="hi",
            template_id="tpl-executive-report",
            sections=[
                self.DocumentSection(
                    heading="कार्यकारी सारांश",
                    paragraphs=["सभी डेटा स्थानीय मशीन पर सुरक्षित रहता है।"],
                    bullets=["पॉइंट 1 <verified>", "पॉइंट 2"],
                )
            ],
            tables=[
                self.TableData(
                    title="सारांश तालिका",
                    headers=["विषय", "मान"],
                    rows=[["बजट", "1500"]],
                )
            ],
        )
        result = self.generate_office_file(plan, filename="hindi-report")
        out_path = Path(str(result["path"]))
        self.assertTrue(out_path.is_file())
        self.assertEqual(out_path.suffix, ".docx")
        with zipfile.ZipFile(out_path, "r") as archive:
            doc_xml = archive.read("word/document.xml").decode("utf-8")
            ET.fromstring(doc_xml)
            self.assertIn("कार्यकारी सारांश", doc_xml)
            self.assertIn("1500", doc_xml)

    def test_generate_xlsx_preserves_numbers_and_utf8(self) -> None:
        plan = self.DocumentPlan(
            title="Presupuesto Q1",
            format="excel",
            language="es",
            template_id="tpl-budget-ledger",
            sections=[self.DocumentSection(heading="Resumen", paragraphs=["Control local."])],
            tables=[
                self.TableData(
                    title="Partidas",
                    headers=["Elemento", "Cantidad"],
                    rows=[["Servidores", "42"], ["Licencias", "125.50"]],
                )
            ],
        )
        result = self.generate_office_file(plan)
        out_path = Path(str(result["path"]))
        self.assertEqual(out_path.suffix, ".xlsx")
        with zipfile.ZipFile(out_path, "r") as archive:
            sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
            ET.fromstring(sheet_xml)
            self.assertIn("<v>42</v>", sheet_xml)
            self.assertIn("<v>125.50</v>", sheet_xml)
            self.assertIn("Servidores", sheet_xml)

    def test_generate_pptx_with_speaker_notes(self) -> None:
        plan = self.DocumentPlan(
            title="Atelier Français",
            format="powerpoint",
            language="fr",
            template_id="tpl-pitch-deck",
            slides=[
                self.SlidePlan(
                    title="Architecture Hors Ligne",
                    bullets=["IA locale via llama.cpp", "Modèles multilingues"],
                    speaker_notes="Présenter les points clés en français.",
                )
            ],
        )
        result = self.generate_office_file(plan)
        out_path = Path(str(result["path"]))
        self.assertEqual(out_path.suffix, ".pptx")
        with zipfile.ZipFile(out_path, "r") as archive:
            names = set(archive.namelist())
            self.assertIn("ppt/slides/slide1.xml", names)
            self.assertIn("ppt/notesSlides/notesSlide1.xml", names)
            notes_xml = archive.read("ppt/notesSlides/notesSlide1.xml").decode("utf-8")
            ET.fromstring(notes_xml)
            self.assertIn("Présenter les points clés", notes_xml)

    def test_generate_pdf_and_notes(self) -> None:
        pdf_plan = self.DocumentPlan(
            title="Quarterly Brief",
            subtitle="Readable PDF Test",
            format="pdf",
            language="en",
            sections=[
                self.DocumentSection(
                    heading="Highlights",
                    paragraphs=["All inference happens on-device."],
                    bullets=["Fast generation", "Zero cloud upload"],
                )
            ],
        )
        pdf_res = self.generate_office_file(pdf_plan)
        pdf_path = Path(str(pdf_res["path"]))
        self.assertEqual(pdf_path.suffix, ".pdf")
        reader = PdfReader(str(pdf_path))
        self.assertGreaterEqual(len(reader.pages), 1)
        self.assertEqual(reader.metadata.get("/Title"), "Quarterly Brief")

        notes_plan = pdf_plan.model_copy(update={"format": "notes", "language": "ar", "direction": "rtl"})
        notes_res = self.generate_office_file(notes_plan, filename="arabic-notes")
        notes_text = Path(str(notes_res["path"])).read_text(encoding="utf-8")
        self.assertIn("# Quarterly Brief", notes_text)
        self.assertIn("- Zero cloud upload", notes_text)

    def test_export_path_confinement_sanitizes_traversal(self) -> None:
        resolved = self.resolve_safe_export_path("../../etc/passwd", ".docx")
        self.assertEqual(resolved.parent, (self.data_dir / "exports").resolve())
        self.assertTrue(resolved.name.endswith(".docx"))


if __name__ == "__main__":
    unittest.main()
