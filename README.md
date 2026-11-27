# LekhX

**LekhX** is an offline-first, multi-language AI office document platform that turns plain-language briefs, structured notes, and reusable templates into ready-to-use **Word (`.docx`)**, **PDF (`.pdf`)**, **Excel (`.xlsx`)**, **PowerPoint (`.pptx`)**, and **Markdown/Text Notes (`.md` / `.txt`)** files completely on your machine.

- **Hugging Face Dataset Repository**: [`https://huggingface.co/datasets/drishtijs/LekhX`](https://huggingface.co/datasets/drishtijs/LekhX)
- **Architecture & Guidelines**: See [`project-map.md`](project-map.md) and [`# Project guidelines.md`](%23%20Project%20guidelines.md)

## Supported Formats

| Format Key | Extension | Use Cases |
| --- | --- | --- |
| `doc` | `.docx` | Executive reports, proposals, formal letters, SOPs, project briefs |
| `pdf` | `.pdf` | Printable handouts, multilingual summaries, distribution-ready documents |
| `excel` | `.xlsx` | Budgets, KPI trackers, timelines, multi-language schedules, tables |
| `powerpoint` | `.pptx` | Pitch decks, training slides, quarterly reviews with speaker notes |
| `notes` | `.md` / `.txt` | Meeting minutes, study guides, structured action items, checklists |

## Technology Stack

- **Frontend / UI**: [`drishtijs`](https://www.npmjs.com/package/drishtijs) (`v2.4.0`, pure JavaScript ESM DOM components under `app/` — no TypeScript)
- **Backend**: Python 3.12, FastAPI, Pydantic, Uvicorn (`backend/app/`)
- **AI & Retrieval**: Local `llama.cpp` (`.gguf`), LangGraph workflow, SQLite + FTS5 knowledge base, `fastembed` + `faiss-cpu`, NeMo Guardrails
- **Model Dev & Packaging**: `transformers`, `peft` (LoRA/QLoRA), `gguf`, SHA-256 dataset lock verification (`scripts/hf_dataset_security.py`), and release sync to `drishtijs/LekhX`

## Multi-Language Support

LekhX preserves full UTF-8 content across templates, headings, tables, slides, and generated office files, with localized starter template packs for:

- English (`en`), Hindi (`hi`), Bengali (`bn`), Tamil (`ta`), Spanish (`es`), French (`fr`), German (`de`), Arabic (`ar`), Japanese (`ja`)

## Quick Start

### 1. Backend Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements-backend.txt
# Optional full AI/RAG & model-dev dependencies:
# pip install -r requirements-ai.txt

python scripts/ingest_reference_datasets.py
uvicorn backend.app.main:app --reload --port 8010
```

### 2. DrishtiJS UI Setup

```bash
npm install
npm run check
npm run dev
```

For production builds via DrishtiJS:

```bash
npm run build
```

### 3. Run Automated Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT License — see [`LICENSE`](LICENSE).
