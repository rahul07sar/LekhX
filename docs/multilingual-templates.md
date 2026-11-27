# Multilingual Templates Design

LekhX never hardcodes language-specific copy inside generation handlers. Instead, templates and language metadata are loaded dynamically from:

1. Built-in JSONL template catalog: `backend/app/reference_data/lekhx-office-templates.jsonl`
2. Built-in localized phrase/section glossary: `backend/app/reference_data/lekhx-multilingual.jsonl`
3. User-provided custom JSON templates inside `DATA_DIR/templates/`

## Supported Language Packs

- `en` — English (`ltr`)
- `hi` — हिन्दी / Hindi (`ltr`)
- `bn` — বাংলা / Bengali (`ltr`)
- `ta` — தமிழ் / Tamil (`ltr`)
- `es` — Español (`ltr`)
- `fr` — Français (`ltr`)
- `de` — Deutsch (`ltr`)
- `ar` — العربية / Arabic (`rtl`)
- `ja` — 日本語 / Japanese (`ltr`)

Templates specify compatible formats (`doc`, `pdf`, `excel`, `powerpoint`, `notes`), localized section structures, default table column templates, and styling tokens (accent palette, slide layout, typography direction).
