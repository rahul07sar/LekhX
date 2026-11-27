"""Pydantic request, response, template, and document-plan schemas."""

from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field

OfficeFormat = Literal["doc", "pdf", "excel", "powerpoint", "notes"]


class TableData(BaseModel):
    """Structured tabular dataset rendered into tables or Excel worksheets."""

    title: str = Field(default="Summary Table", max_length=160)
    headers: list[str] = Field(default_factory=list, max_length=24)
    rows: list[list[str]] = Field(default_factory=list, max_length=500)


class DocumentSection(BaseModel):
    """Logical section rendered across reports, PDFs, notes, and slides."""

    heading: str = Field(..., min_length=1, max_length=160)
    paragraphs: list[str] = Field(default_factory=list, max_length=32)
    bullets: list[str] = Field(default_factory=list, max_length=40)


class SlidePlan(BaseModel):
    """Presentation slide specification including speaker notes."""

    title: str = Field(..., min_length=1, max_length=160)
    bullets: list[str] = Field(default_factory=list, max_length=12)
    speaker_notes: str = Field(default="", max_length=1200)


class DocumentPlan(BaseModel):
    """Validated structured document blueprint emitted by the planning layer."""

    title: str = Field(..., min_length=1, max_length=180)
    subtitle: str = Field(default="", max_length=240)
    format: OfficeFormat = "doc"
    language: str = Field(default="en", min_length=2, max_length=12)
    direction: Literal["ltr", "rtl"] = "ltr"
    template_id: str = Field(default="tpl-executive-report", max_length=80)
    accent_hex: str = Field(default="#1D4ED8", max_length=16)
    sections: list[DocumentSection] = Field(default_factory=list, max_length=30)
    tables: list[TableData] = Field(default_factory=list, max_length=10)
    slides: list[SlidePlan] = Field(default_factory=list, max_length=40)


class GenerateDocumentRequest(BaseModel):
    """User request to plan and export an office document."""

    prompt: str = Field(..., min_length=3, max_length=12000)
    title: str | None = Field(default=None, max_length=180)
    format: OfficeFormat = "doc"
    language: str = Field(default="en", min_length=2, max_length=12)
    template_id: str | None = Field(default=None, max_length=80)
    filename: str | None = Field(default=None, max_length=120)
    session_id: str | None = Field(default=None, max_length=80)
    plan_override: DocumentPlan | None = None


class GenerateDocumentResponse(BaseModel):
    """API response after creating and verifying a generated office file."""

    document_id: str
    title: str
    format: OfficeFormat
    language: str
    template_id: str
    filename: str
    download_url: str
    size_bytes: int
    sha256: str
    created_at: str
    plan: DocumentPlan
    planner_mode: str


class SettingsUpdateRequest(BaseModel):
    """Runtime preferences saved in local SQLite."""

    default_format: OfficeFormat | None = None
    default_language: str | None = Field(default=None, min_length=2, max_length=12)
    active_model: str | None = Field(default=None, max_length=120)
    llm_base_url: str | None = Field(default=None, max_length=240)
