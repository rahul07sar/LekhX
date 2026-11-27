# LekhX Project Map

## 1. Vision

**LekhX** is a fully offline-first, multi-language AI desktop platform for creating structured office documents directly from natural-language briefs, outlines, raw notes, and reusable templates:

- **Documents (`doc`)**: `.docx` formatted reports, proposals, formal letters, SOPs, and memos
- **PDFs (`pdf`)**: `.pdf` printable deliverables, briefs, summaries, and multi-language handouts
- **Spreadsheets (`excel`)**: `.xlsx` multi-sheet ledgers, trackers, budgets, schedules, and tabular reports
- **Presentations (`powerpoint`)**: `.pptx` slide decks with title slides, bullet sections, speaker notes, and themes
- **Notes (`notes`)**: `.md` / `.txt` structured meeting notes, study guides, action logs, and bilingual summaries

All inference, template selection, multilingual text structuring, retrieval, and file serialization run locally on Windows, Linux, and macOS with zero mandatory cloud dependency.

## 2. Core Product Principles

1. **Offline-First & Private**: Local GGUF models (`llama.cpp`), local SQLite (`FTS5`) storage, local FAISS/`fastembed` reference indexing, and zero external telemetry or document egress.
2. **Multi-Language by Design**: Native UTF-8 pipeline supporting English (`en`), Hindi (`hi`), Bengali (`bn`), Tamil (`ta`), Spanish (`es`), French (`fr`), German (`de`), Arabic (`ar`), and Japanese (`ja`), with locale-aware section headings, template metadata, and RTL/Unicode-safe rendering.
3. **Deterministic Binary Builders + AI Structuring**: The local LLM + LangGraph pipeline produces a validated structured `DocumentPlan` (title, language, template, sections, tables, slides, speaker notes), while tested deterministic builders (`backend/app/document_generators.py`) serialize compliant `.docx`, `.pdf`, `.xlsx`, `.pptx`, and `.md`/`.txt` files.
4. **Template-Driven Customization**: Templates live in inspectable JSONL/JSON catalogs (`backend/app/reference_data/`) and user template directories (`data/templates/`) rather than hardcoded prompts.
5. **Versioned Offline Updates via Hugging Face**: Packaged releases and incremental data/template/model updates publish cleanly to [`drishtijs/LekhX`](https://huggingface.co/datasets/drishtijs/LekhX) using `0-9` rollover versioning while keeping user documents and SQLite history untouched.

## 3. Technology Stack

Matched to the Drishti-Agent platform architecture:

- **Desktop & Frontend**:
  - [`drishtijs`](https://www.npmjs.com/package/drishtijs) (`2.4.0`) pure JavaScript ESM UI (`app/`, `drishti.app.js`, `drishti.config.json`) without TypeScript
  - DOM-safe component rendering (`document.createElement` + `textContent`) with strict CSP in `index.html`
- **Backend API & Orchestration**:
  - `Python 3.12` + `FastAPI` + `Uvicorn` + `Pydantic v2`
  - `LangGraph` workflow orchestration (`plan -> template bind -> guardrails -> generate -> verify`)
  - `SQLite` (`WAL` mode + `FTS5`) for chat sessions, generated file history, settings, and indexed templates/reference datasets
- **Local AI, Retrieval & Guardrails**:
  - `llama.cpp` server runtime executing local `.gguf` checkpoints
  - `fastembed` + `faiss-cpu` for multilingual semantic retrieval over templates and user reference docs
  - `NeMo Guardrails` (`backend/app/guardrails_config/`) + deterministic XML/path/input validation
  - `PEFT` (`LoRA` / `QLoRA`) + `transformers` + `gguf` for offline model fine-tuning and export

## 4. Repository Layout

```text
lekhX/
├── # Project guidelines.md        # Engineering, security, multilingual & sync rules
├── project-map.md                 # This architecture & roadmap document
├── README.md                      # Quick start, stack & usage overview
├── package.json                   # DrishtiJS UI + backend & model helper scripts
├── drishti.app.js                 # DrishtiJS JavaScript app manifest
├── drishti.config.json            # DrishtiJS workspace configuration
├── index.html                     # CSP-hardened DrishtiJS HTML entrypoint
├── requirements-backend.txt       # FastAPI, Pydantic, Uvicorn, Office & PDF stack
├── requirements-ai.txt            # LangGraph, FAISS, fastembed, sentence-transformers
├── requirements-model-dev.txt     # Transformers, PEFT/LoRA, bitsandbytes, gguf
├── public/                        # Packaged SVG/PNG logo assets
├── app/                           # Pure JavaScript DrishtiJS workspace UI (no TypeScript)
│   ├── main.js
│   ├── styles.css                 # Clean responsive offline studio styles
│   ├── layout/AppShell.js         # Header, HF dataset & runtime status shell
│   ├── pages/home.js              # Studio form, format/language/template controls & history
│   ├── lib/api.js                 # Typed-free fetch helper targeting FastAPI /api/*
│   └── components/
│       ├── TemplateGallery.js     # Filterable format & template selector
│       └── DocumentPreview.js     # Live structured section/table/slide preview + export bar
├── backend/app/
│   ├── __init__.py
│   ├── config.py                  # Paths, DATA_DIR/exports/templates/models, runtime env
│   ├── hardware_profile.py        # CPU/RAM/tier profiling for llama.cpp defaults
│   ├── db.py                      # SQLite schema (settings, chats, documents, FTS5 knowledge)
│   ├── schemas.py                 # Pydantic request/response & DocumentPlan contracts
│   ├── guardrails.py              # Path confinement, prompt validation & NeMo integration
│   ├── guardrails_config/         # NeMo Guardrails YAML + Colang policy files
│   ├── model_runtime.py           # llama.cpp local HTTP client & deterministic fallback planner
│   ├── model_catalog.py           # Bundled/local/recommended GGUF & LoRA model registry
│   ├── reference_knowledge.py     # FTS5 + dense retrieval for templates & office guides
│   ├── office_templates.py        # Multilingual template catalog & localization loader
│   ├── document_generators.py     # Validated .docx, .pdf, .xlsx, .pptx, .md/.txt builders
│   ├── assistant.py               # Document structuring & multi-step generation workflow
│   ├── updates.py                 # Offline/HF release & model/template update check + apply
│   ├── main.py                    # FastAPI app, REST endpoints & dist static serving
│   └── reference_data/            # Bundled templates, multilingual packs & model release index
├── packages/common/
│   ├── manifest.json              # Canonical LekhX release + HF dataset coordinate manifest
│   ├── release_numbering.py       # 0-9 rollover version helper
│   ├── frontend_build.mjs         # Source-to-dist SHA-256 build provenance verifier
│   ├── build_app_payload.py       # Cross-platform app payload packager
│   ├── publish_data_payload.py    # Versioned template/knowledge/model update payload builder
│   └── publish_to_huggingface.py  # Publisher targeting drishtijs/LekhX on Hugging Face
├── scripts/
│   ├── hf_dataset_security.py     # Immutable commit & SHA-256 verifier for drishtijs/LekhX
│   ├── hf-cloud-dataset-lock.json # Pinned dataset lock descriptor
│   ├── prepare_training_data.py   # Build SFT datasets from office templates & multilingual examples
│   ├── train_model.py             # Offline LoRA/QLoRA training + adapter merge entrypoint
│   ├── verify_model_checkpoint.py # Checkpoint integrity validator
│   ├── check_model_tools.py       # Model toolchain & GGUF converter preflight check
│   └── ingest_reference_datasets.py # Index bundled templates & docs into SQLite FTS5
├── docs/                          # Format specs, multilingual templates, guardrails & model tooling
└── tests/                         # Automated tests covering all 5 formats, templates, API & security
```

## 5. Planned Milestones

1. **Core Platform (v1.0.x)**: FastAPI studio backend, React UI, 5 deterministic office builders (`docx`, `pdf`, `xlsx`, `pptx`, `notes`), multilingual template catalog, SQLite history, and Hugging Face sync pipeline (`drishtijs/LekhX`).
2. **Domain Fine-Tuning (v1.1.x)**: Populate `drishtijs/LekhX` with verified multilingual office instruction pairs (`sft_chat_dataset.jsonl`) and train lightweight `LekhX-1.0` LoRA + GGUF checkpoints tailored to structured JSON/outline generation.
3. **Rich Charts & Visual Layouts (v1.2.x)**: Add chart embedding inside `.xlsx`/`.pptx`, custom institutional letterhead themes for `.docx`/`.pdf`, and side-by-side bilingual document generation.
4. **Cross-Platform Installer (v1.3.x)**: Package Tauri desktop bundles for macOS, Linux, and Windows with bundled default GGUF runtime and seamless in-app dataset/model upgrades.
