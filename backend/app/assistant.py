"""LangGraph-style document planning pipeline bridging LLM structuring and deterministic rendering."""

from __future__ import annotations

import json
import re
from uuid import uuid4

from .config import DEFAULT_MODEL_NAME
from .db import get_setting, save_generated_document
from .document_generators import generate_office_file
from .guardrails import normalize_multilingual_text, validate_generation_prompt
from .model_runtime import request_structured_completion
from .office_templates import get_language_pack, localized_section_label, resolve_template
from .reference_knowledge import search_knowledge
from .schemas import (
    DocumentPlan,
    DocumentSection,
    GenerateDocumentRequest,
    GenerateDocumentResponse,
    SlidePlan,
    TableData,
)

BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")


def _infer_title(prompt: str, fallback: str) -> str:
    first_line = normalize_multilingual_text(prompt).splitlines()[0]
    first_line = BULLET_PREFIX_RE.sub("", first_line).strip(" .:-")
    if 4 <= len(first_line) <= 90:
        return first_line
    if len(first_line) > 90:
        return first_line[:87].rstrip() + "..."
    return fallback


def _extract_bullets_and_rows(prompt: str) -> tuple[list[str], list[list[str]]]:
    lines = [normalize_multilingual_text(line) for line in prompt.splitlines() if line.strip()]
    bullets: list[str] = []
    rows: list[list[str]] = []

    for idx, line in enumerate(lines, start=1):
        cleaned = BULLET_PREFIX_RE.sub("", line).strip()
        if "|" in cleaned:
            parts = [part.strip() for part in cleaned.split("|") if part.strip()]
            if parts:
                while len(parts) < 4:
                    parts.append("-")
                rows.append(parts[:4])
                continue
        if ":" in cleaned and len(cleaned.split(":", 1)[0]) <= 36:
            left, right = [piece.strip() for piece in cleaned.split(":", 1)]
            rows.append([left, right, "User Input", "Draft"])
        bullets.append(cleaned)
        if not rows and idx <= 5:
            rows.append([f"{idx}", cleaned[:48], "Planned", "Active"])

    if not bullets:
        bullets = [normalize_multilingual_text(prompt)]
    if not rows:
        rows = [["1", bullets[0][:48], "General", "Ready"]]
    return bullets, rows


def _plan_offline_fallback(request: GenerateDocumentRequest) -> DocumentPlan:
    template = resolve_template(request.template_id, request.format)
    lang_pack = get_language_pack(request.language)
    bullets, rows = _extract_bullets_and_rows(request.prompt)
    title = normalize_multilingual_text(request.title or _infer_title(request.prompt, str(template.get("name") or "LekhX Document")))

    section_keys = list(template.get("default_sections") or ["overview", "key_findings", "recommendations"])
    sections: list[DocumentSection] = []
    chunk_size = max(1, (len(bullets) + len(section_keys) - 1) // len(section_keys))

    for idx, key in enumerate(section_keys):
        heading = localized_section_label(lang_pack, str(key))
        slice_items = bullets[idx * chunk_size : (idx + 1) * chunk_size]
        if not slice_items:
            slice_items = [bullets[min(idx, len(bullets) - 1)]]
        sections.append(
            DocumentSection(
                heading=heading,
                paragraphs=[slice_items[0]],
                bullets=slice_items[1:] if len(slice_items) > 1 else slice_items,
            )
        )

    tables: list[TableData] = []
    if request.format == "excel" or bool(template.get("include_table")):
        headers = [str(item) for item in (lang_pack.get("table_headers") or ["Item", "Details", "Category", "Value"])]
        tables.append(
            TableData(
                title=localized_section_label(lang_pack, "data_summary"),
                headers=headers,
                rows=rows,
            )
        )

    slides: list[SlidePlan] = []
    if request.format == "powerpoint":
        note_prefix = str(lang_pack.get("speaker_note_prefix") or "Speaker Notes")
        slides.append(
            SlidePlan(
                title=title,
                bullets=[str(template.get("description") or ""), f"{lang_pack.get('native_name', request.language)}"],
                speaker_notes=f"{note_prefix}: {title}",
            )
        )
        for sec in sections:
            slides.append(
                SlidePlan(
                    title=sec.heading,
                    bullets=[*sec.paragraphs, *sec.bullets][:6],
                    speaker_notes=f"{note_prefix}: {sec.heading}",
                )
            )

    return DocumentPlan(
        title=title,
        subtitle=normalize_multilingual_text(str(template.get("description") or "")),
        format=request.format,
        language=str(lang_pack.get("code") or request.language),
        direction="rtl" if str(lang_pack.get("direction", "ltr")) == "rtl" else "ltr",
        template_id=str(template.get("id") or "tpl-executive-report"),
        accent_hex=str(template.get("accent_hex") or "#1D4ED8"),
        sections=sections,
        tables=tables,
        slides=slides,
    )


def _try_llm_plan(request: GenerateDocumentRequest) -> tuple[DocumentPlan, str]:
    fallback = _plan_offline_fallback(request)
    knowledge = search_knowledge(request.prompt, limit=3)
    context_summary = "\n".join(f"- {item['title']}: {item['snippet']}" for item in knowledge)
    system_prompt = (
        "You are LekhX, an offline multilingual office document architect. "
        "Return valid JSON matching keys: title, subtitle, sections ([{heading, paragraphs, bullets}]), "
        "tables ([{title, headers, rows}]), slides ([{title, bullets, speaker_notes}]). "
        f"Write strictly in language code '{request.language}' and preserve all user facts."
    )
    user_prompt = (
        f"Target format: {request.format}\n"
        f"Template ID: {fallback.template_id}\n"
        f"Reference context:\n{context_summary}\n\n"
        f"User brief:\n{request.prompt}"
    )
    raw = request_structured_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model_name=get_setting("active_model", DEFAULT_MODEL_NAME),
    )
    if not raw:
        return fallback, "deterministic-offline"
    try:
        parsed = json.loads(raw)
        merged = fallback.model_dump()
        for key in ("title", "subtitle", "sections", "tables", "slides"):
            if key in parsed and parsed[key]:
                merged[key] = parsed[key]
        return DocumentPlan.model_validate(merged), "local-llm+template"
    except (json.JSONDecodeError, ValueError):
        return fallback, "deterministic-offline"


def generate_document(request: GenerateDocumentRequest) -> GenerateDocumentResponse:
    """Validate, plan, generate, verify, and persist a multilingual office artifact."""

    ok, error_message = validate_generation_prompt(request.prompt)
    if not ok:
        raise ValueError(error_message or "Invalid document generation prompt.")

    if request.plan_override is not None:
        plan = request.plan_override
        planner_mode = "user-edited-plan"
    else:
        plan, planner_mode = _try_llm_plan(request)

    artifact = generate_office_file(plan, filename=request.filename or plan.title)
    doc_id = f"doc_{uuid4().hex[:12]}"
    save_generated_document(
        doc_id=doc_id,
        session_id=request.session_id,
        title=plan.title,
        fmt=plan.format,
        language=plan.language,
        template_id=plan.template_id,
        filename=str(artifact["filename"]),
        relative_path=str(artifact["relative_path"]),
        size_bytes=int(artifact["size_bytes"]),
        sha256=str(artifact["sha256"]),
        plan=plan.model_dump(),
    )
    return GenerateDocumentResponse(
        document_id=doc_id,
        title=plan.title,
        format=plan.format,
        language=plan.language,
        template_id=plan.template_id,
        filename=str(artifact["filename"]),
        download_url=f"/api/documents/{doc_id}/download",
        size_bytes=int(artifact["size_bytes"]),
        sha256=str(artifact["sha256"]),
        created_at="",
        plan=plan,
        planner_mode=planner_mode,
    )
