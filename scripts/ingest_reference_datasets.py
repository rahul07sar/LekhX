"""CLI to index LekhX bundled templates and documentation into local SQLite FTS5."""

from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.db import initialize_database
from backend.app.reference_knowledge import ingest_reference_datasets


def main() -> int:
    initialize_database()
    result = ingest_reference_datasets()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
