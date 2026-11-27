# LekhX Office Formats Architecture

LekhX treats AI output and binary file serialization as two separate, verifiable layers:

1. **AI & Orchestration Layer**: Produces a validated `DocumentPlan` Pydantic object containing:
   - `title`, `subtitle`, `format` (`doc`, `pdf`, `excel`, `powerpoint`, `notes`), `language`, `template_id`
   - Ordered `sections` (heading, paragraphs, bullet points)
   - Optional structured `tables` (headers + tabular rows)
   - Optional `slides` (title, bullets, speaker notes)
2. **Deterministic Builder Layer** (`backend/app/document_generators.py`):
   - `doc` -> `.docx` OOXML ZIP archive (`[Content_Types].xml`, `_rels/.rels`, `word/document.xml`, `word/styles.xml`)
   - `pdf` -> `.pdf` multi-page document preserving Unicode text layers & clean readable page rendering
   - `excel` -> `.xlsx` OOXML spreadsheet workbook (`xl/workbook.xml`, `xl/worksheets/sheet*.xml`) with automatic typed numeric & inline UTF-8 cells
   - `powerpoint` -> `.pptx` OOXML presentation (`ppt/presentation.xml`, `ppt/slides/slide*.xml`, `ppt/notesSlides/` speaker notes)
   - `notes` -> `.md` (or `.txt`) structured outline notes with section anchors and action checklists

Every generated file is validated against `DATA_DIR/exports` path-confinement rules before saving and verified as readable bytes immediately after creation.
