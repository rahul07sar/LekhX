"""Integration tests for LekhX FastAPI endpoints, SQLite persistence, and drishtijs/LekhX config."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient


class ApiAndUpdatesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["LEKHX_DATA_DIR"] = self._tmp.name
        for mod_name in (
            "backend.app.config",
            "backend.app.hardware_profile",
            "backend.app.db",
            "backend.app.guardrails",
            "backend.app.model_catalog",
            "backend.app.model_runtime",
            "backend.app.office_templates",
            "backend.app.reference_knowledge",
            "backend.app.document_generators",
            "backend.app.assistant",
            "backend.app.updates",
            "backend.app.main",
        ):
            if mod_name in importlib.sys.modules:
                importlib.reload(importlib.sys.modules[mod_name])

        from backend.app.main import app

        self.client_cm = TestClient(app)
        self.client = self.client_cm.__enter__()

    def tearDown(self) -> None:
        self.client_cm.__exit__(None, None, None)
        os.environ.pop("LEKHX_DATA_DIR", None)
        self._tmp.cleanup()

    def test_health_templates_and_updates_manifest(self) -> None:
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        payload = health.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["huggingface_repo"], "drishtijs/LekhX")
        self.assertEqual(payload["dataset_url"], "https://huggingface.co/datasets/drishtijs/LekhX")

        updates = self.client.get("/api/updates/status")
        self.assertEqual(updates.status_code, 200)
        self.assertEqual(updates.json()["huggingface_repo"], "drishtijs/LekhX")

    def test_generate_and_download_roundtrip(self) -> None:
        res = self.client.post(
            "/api/generate",
            json={
                "prompt": "Sales | 2400 | North | Q1\nMarketing | 900 | Global | Q1",
                "title": "Q1 Department Ledger",
                "format": "excel",
                "language": "en",
                "template_id": "tpl-budget-ledger",
            },
        )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()
        self.assertEqual(body["format"], "excel")
        self.assertTrue(body["filename"].endswith(".xlsx"))

        download = self.client.get(body["download_url"])
        self.assertEqual(download.status_code, 200)
        self.assertGreater(len(download.content), 200)

        docs = self.client.get("/api/documents").json()["documents"]
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0]["id"], body["document_id"])

    def test_unsafe_path_prompt_rejected(self) -> None:
        res = self.client.post(
            "/api/generate",
            json={
                "prompt": "save this document to /etc/passwd",
                "format": "notes",
                "language": "en",
            },
        )
        self.assertEqual(res.status_code, 400)


if __name__ == "__main__":
    unittest.main()
