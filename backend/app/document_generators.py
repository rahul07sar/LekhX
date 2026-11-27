"""Deterministic multi-language binary builders for Word, PDF, Excel, PowerPoint, and Notes."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from html import escape
import io
from pathlib import Path
import re
import textwrap
from xml.sax.saxutils import escape as xml_escape
import zipfile

from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter

from .config import EXPORTS_DIR, FORMAT_EXTENSIONS
from .guardrails import normalize_multilingual_text, resolve_safe_export_path
from .schemas import DocumentPlan, DocumentSection, SlidePlan, TableData

FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Kohinoor.ttc",
    "/System/Library/Fonts/Supplemental/NotoSansDevanagari-Regular.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)
NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        if Path(candidate).is_file():
            try:
                return ImageFont.truetype(candidate, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    cleaned = (hex_color or "#1D4ED8").strip().lstrip("#")
    if len(cleaned) != 6:
        return (29, 78, 216)
    try:
        return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))
    except ValueError:
        return (29, 78, 216)


def _xml(text: str) -> str:
    return xml_escape(normalize_multilingual_text(text), {'"': "&quot;", "'": "&apos;"})


def _column_letter(index_zero_based: int) -> str:
    result = ""
    index = index_zero_based + 1
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        result = chr(65 + remainder) + result
    return result


def _docx_paragraph(text: str, *, style: str | None = None, bullet: bool = False) -> str:
    p_pr = ""
    if style:
        p_pr = f'<w:pPr><w:pStyle w:val="{_xml(style)}"/></w:pPr>'
    prefix = "• " if bullet else ""
    return (
        f"<w:p>{p_pr}"
        f'<w:r><w:t xml:space="preserve">{_xml(prefix + text)}</w:t></w:r>'
        "</w:p>"
    )


def _docx_table(table: TableData) -> str:
    rows_xml: list[str] = []
    all_rows = ([table.headers] if table.headers else []) + list(table.rows)
    for row in all_rows:
        cells = "".join(
            "<w:tc><w:p><w:r>"
            f'<w:t xml:space="preserve">{_xml(str(cell))}</w:t>'
            "</w:r></w:p></w:tc>"
            for cell in row
        )
        rows_xml.append(f"<w:tr>{cells}</w:tr>")
    return (
        '<w:tbl><w:tblPr><w:tblBorders>'
        '<w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:left w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        "</w:tblBorders></w:tblPr>"
        + "".join(rows_xml)
        + "</w:tbl>"
    )


def _build_docx(plan: DocumentPlan, destination: Path) -> None:
    body_parts: list[str] = [_docx_paragraph(plan.title, style="Heading1")]
    if plan.subtitle:
        body_parts.append(_docx_paragraph(plan.subtitle, style="Subtitle"))
    body_parts.append(_docx_paragraph(f"Language: {plan.language} | Template: {plan.template_id}"))

    for section in plan.sections:
        body_parts.append(_docx_paragraph(section.heading, style="Heading2"))
        for paragraph in section.paragraphs:
            body_parts.append(_docx_paragraph(paragraph))
        for bullet in section.bullets:
            body_parts.append(_docx_paragraph(bullet, bullet=True))

    for table in plan.tables:
        if table.title:
            body_parts.append(_docx_paragraph(table.title, style="Heading2"))
        body_parts.append(_docx_table(table))

    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(body_parts)
        + "<w:sectPr/></w:body></w:document>"
    )
    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
        '<w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Heading2"><w:name w:val="heading 2"/>'
        '<w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>'
        '<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/>'
        '<w:rPr><w:i/><w:sz w:val="24"/></w:rPr></w:style>'
        "</w:styles>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>'
        "</Relationships>"
    )
    doc_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        archive.writestr("_rels/.rels", root_rels.encode("utf-8"))
        archive.writestr("word/_rels/document.xml.rels", doc_rels.encode("utf-8"))
        archive.writestr("word/styles.xml", styles_xml.encode("utf-8"))
        archive.writestr("word/document.xml", document_xml.encode("utf-8"))


def _excel_sheet_xml(rows: list[list[str]]) -> str:
    row_xml: list[str] = []
    for r_idx, row in enumerate(rows, start=1):
        cells_xml: list[str] = []
        for c_idx, raw_value in enumerate(row):
            cell_ref = f"{_column_letter(c_idx)}{r_idx}"
            val = normalize_multilingual_text(str(raw_value))
            if r_idx > 1 and NUMERIC_RE.fullmatch(val):
                cells_xml.append(f'<c r="{cell_ref}"><v>{val}</v></c>')
            else:
                cells_xml.append(
                    f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{_xml(val)}</t></is></c>'
                )
        row_xml.append(f'<row r="{r_idx}">{"".join(cells_xml)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def _build_xlsx(plan: DocumentPlan, destination: Path) -> None:
    sheets: list[tuple[str, list[list[str]]]] = []

    if plan.tables:
        for idx, table in enumerate(plan.tables, start=1):
            sheet_name = (table.title or f"Sheet{idx}")[:28]
            rows = ([table.headers] if table.headers else []) + list(table.rows)
            sheets.append((sheet_name, rows))

    summary_rows: list[list[str]] = [
        ["Title", plan.title],
        ["Subtitle", plan.subtitle],
        ["Language", plan.language],
        ["Template", plan.template_id],
        [],
        ["Section", "Content"],
    ]
    for section in plan.sections:
        combined = " ".join([*section.paragraphs, *[f"- {b}" for b in section.bullets]]).strip()
        summary_rows.append([section.heading, combined])
    sheets.append(("Overview", summary_rows))

    sheet_entries = []
    rel_entries = []
    type_overrides = []
    sheet_payloads: dict[str, bytes] = {}

    for idx, (name, rows) in enumerate(sheets, start=1):
        safe_sheet_name = re.sub(r"[:\\/?*\[\]]", "-", name).strip() or f"Sheet{idx}"
        sheet_entries.append(f'<sheet name="{_xml(safe_sheet_name[:31])}" sheetId="{idx}" r:id="rId{idx}"/>')
        rel_entries.append(
            f'<Relationship Id="rId{idx}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{idx}.xml"/>'
        )
        type_overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{idx}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        )
        sheet_payloads[f"xl/worksheets/sheet{idx}.xml"] = _excel_sheet_xml(rows).encode("utf-8")

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(type_overrides)
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{''.join(sheet_entries)}</sheets></workbook>"
    )
    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(rel_entries)
        + "</Relationships>"
    )

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        archive.writestr("_rels/.rels", root_rels.encode("utf-8"))
        archive.writestr("xl/workbook.xml", workbook_xml.encode("utf-8"))
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels.encode("utf-8"))
        for part_name, payload in sheet_payloads.items():
            archive.writestr(part_name, payload)


def _pptx_text_paragraphs(lines: list[str], *, font_size_hundredths: int = 2000) -> str:
    paragraphs = []
    for line in lines:
        paragraphs.append(
            "<a:p><a:r>"
            f'<a:rPr lang="en-US" sz="{font_size_hundredths}" dirty="0"/>'
            f"<a:t>{_xml(line)}</a:t>"
            "</a:r></a:p>"
        )
    if not paragraphs:
        paragraphs.append("<a:p><a:endParaRPr/></a:p>")
    return "".join(paragraphs)


def _build_pptx(plan: DocumentPlan, destination: Path) -> None:
    slides: list[SlidePlan] = list(plan.slides)
    if not slides:
        slides.append(
            SlidePlan(
                title=plan.title,
                bullets=[plan.subtitle] if plan.subtitle else [f"Language: {plan.language}"],
                speaker_notes="",
            )
        )
        for section in plan.sections:
            slides.append(
                SlidePlan(
                    title=section.heading,
                    bullets=[*section.paragraphs, *section.bullets][:8],
                    speaker_notes="",
                )
            )

    slide_ids = []
    pres_rels = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>'
    ]
    overrides = [
        '<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>',
        '<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>',
        '<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>',
    ]

    slide_parts: dict[str, bytes] = {}
    for idx, slide in enumerate(slides, start=1):
        rel_id = f"rId{idx + 1}"
        slide_ids.append(f'<p:sldId id="{255 + idx}" r:id="{rel_id}"/>')
        pres_rels.append(
            f'<Relationship Id="{rel_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide{idx}.xml"/>'
        )
        overrides.append(
            f'<Override PartName="/ppt/slides/slide{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
        )
        slide_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
            "<p:cSld><p:spTree>"
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            "<p:grpSpPr><a:xfrm/></p:grpSpPr>"
            '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="457200" y="365760"/><a:ext cx="8229600" cy="914400"/></a:xfrm></p:spPr>'
            "<p:txBody><a:bodyPr/><a:lstStyle/>"
            + _pptx_text_paragraphs([slide.title], font_size_hundredths=3000)
            + "</p:txBody></p:sp>"
            '<p:sp><p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            '<p:spPr><a:xfrm><a:off x="457200" y="1463040"/><a:ext cx="8229600" cy="4572000"/></a:xfrm></p:spPr>'
            "<p:txBody><a:bodyPr/><a:lstStyle/>"
            + _pptx_text_paragraphs([f"• {b}" for b in slide.bullets], font_size_hundredths=1800)
            + "</p:txBody></p:sp>"
            "</p:spTree></p:cSld></p:sld>"
        )
        slide_parts[f"ppt/slides/slide{idx}.xml"] = slide_xml.encode("utf-8")

        slide_rel_items = [
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
        ]
        if slide.speaker_notes.strip():
            overrides.append(
                f'<Override PartName="/ppt/notesSlides/notesSlide{idx}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/>'
            )
            slide_rel_items.append(
                f'<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesSlide" Target="../notesSlides/notesSlide{idx}.xml"/>'
            )
            notes_xml = (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<p:notes xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                "<p:cSld><p:spTree>"
                '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
                "<p:grpSpPr><a:xfrm/></p:grpSpPr>"
                '<p:sp><p:nvSpPr><p:cNvPr id="2" name="Notes"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
                "<p:spPr/><p:txBody><a:bodyPr/><a:lstStyle/>"
                + _pptx_text_paragraphs([slide.speaker_notes], font_size_hundredths=1400)
                + "</p:txBody></p:sp>"
                "</p:spTree></p:cSld></p:notes>"
            )
            slide_parts[f"ppt/notesSlides/notesSlide{idx}.xml"] = notes_xml.encode("utf-8")

        slide_rels_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(slide_rel_items)
            + "</Relationships>"
        )
        slide_parts[f"ppt/slides/_rels/slide{idx}.xml.rels"] = slide_rels_xml.encode("utf-8")

    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        + "".join(overrides)
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>'
        "</Relationships>"
    )
    presentation_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        "<p:sldMasterIdLst><p:sldMasterId id=\"2147483648\" r:id=\"rId1\"/></p:sldMasterIdLst>"
        f"<p:sldIdLst>{''.join(slide_ids)}</p:sldIdLst>"
        '<p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>'
        '<p:notesSz cx="6858000" cy="9144000"/>'
        "</p:presentation>"
    )
    presentation_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(pres_rels)
        + "</Relationships>"
    )
    slide_master_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>'
        '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
        "</p:sldMaster>"
    )
    slide_master_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>'
        "</Relationships>"
    )
    slide_layout_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="titleAndBody">'
        '<p:cSld><p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/></p:spTree></p:cSld>'
        "</p:sldLayout>"
    )
    slide_layout_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>'
        "</Relationships>"
    )

    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        archive.writestr("_rels/.rels", root_rels.encode("utf-8"))
        archive.writestr("ppt/presentation.xml", presentation_xml.encode("utf-8"))
        archive.writestr("ppt/_rels/presentation.xml.rels", presentation_rels.encode("utf-8"))
        archive.writestr("ppt/slideMasters/slideMaster1.xml", slide_master_xml.encode("utf-8"))
        archive.writestr("ppt/slideMasters/_rels/slideMaster1.xml.rels", slide_master_rels.encode("utf-8"))
        archive.writestr("ppt/slideLayouts/slideLayout1.xml", slide_layout_xml.encode("utf-8"))
        archive.writestr("ppt/slideLayouts/_rels/slideLayout1.xml.rels", slide_layout_rels.encode("utf-8"))
        for part_name, payload in slide_parts.items():
            archive.writestr(part_name, payload)


def _build_pdf(plan: DocumentPlan, destination: Path) -> None:
    page_w, page_h = 1240, 1754  # 150 DPI A4
    margin_x = 96
    max_y = page_h - 110
    accent = _hex_to_rgb(plan.accent_hex)
    title_font = _load_font(38)
    heading_font = _load_font(26)
    body_font = _load_font(20)
    small_font = _load_font(16)

    pages: list[Image.Image] = []
    current = Image.new("RGB", (page_w, page_h), (255, 255, 255))
    draw = ImageDraw.Draw(current)
    draw.rectangle([0, 0, page_w, 16], fill=accent)
    y = 72

    def new_page() -> None:
        nonlocal current, draw, y
        pages.append(current)
        current = Image.new("RGB", (page_w, page_h), (255, 255, 255))
        draw = ImageDraw.Draw(current)
        draw.rectangle([0, 0, page_w, 10], fill=accent)
        y = 72

    def draw_wrapped(text: str, font: ImageFont.ImageFont, color: tuple[int, int, int], step: int, indent: int = 0) -> None:
        nonlocal y
        for line in textwrap.wrap(normalize_multilingual_text(text), width=74) or [""]:
            if y + step > max_y:
                new_page()
            draw.text((margin_x + indent, y), line, fill=color, font=font)
            y += step

    draw_wrapped(plan.title, title_font, (15, 23, 42), 48)
    if plan.subtitle:
        draw_wrapped(plan.subtitle, heading_font, (71, 85, 105), 34)
    draw_wrapped(f"Language: {plan.language}  |  Template: {plan.template_id}", small_font, (100, 116, 139), 30)
    y += 12

    for section in plan.sections:
        if y + 60 > max_y:
            new_page()
        draw_wrapped(section.heading, heading_font, accent, 38)
        for paragraph in section.paragraphs:
            draw_wrapped(paragraph, body_font, (30, 41, 59), 28)
        for bullet in section.bullets:
            draw_wrapped(f"• {bullet}", body_font, (30, 41, 59), 28, indent=20)
        y += 10

    for table in plan.tables:
        if table.title:
            draw_wrapped(table.title, heading_font, accent, 36)
        if table.headers:
            draw_wrapped(" | ".join(table.headers), body_font, (15, 23, 42), 28)
        for row in table.rows:
            draw_wrapped(" | ".join(str(cell) for cell in row), body_font, (51, 65, 85), 26)
        y += 12

    pages.append(current)

    raw_pdf_buffer = io.BytesIO()
    pages[0].save(
        raw_pdf_buffer,
        format="PDF",
        resolution=150.0,
        save_all=True,
        append_images=pages[1:],
    )
    raw_pdf_buffer.seek(0)

    reader = PdfReader(raw_pdf_buffer)
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.add_metadata(
        {
            "/Title": normalize_multilingual_text(plan.title),
            "/Subject": normalize_multilingual_text(plan.subtitle or plan.template_id),
            "/Producer": "LekhX Offline Office Engine",
            "/Keywords": f"{plan.language},{plan.format},{plan.template_id}",
        }
    )
    with destination.open("wb") as handle:
        writer.write(handle)


def _build_notes(plan: DocumentPlan, destination: Path) -> None:
    lines = [f"# {normalize_multilingual_text(plan.title)}"]
    if plan.subtitle:
        lines.extend(["", f"_{normalize_multilingual_text(plan.subtitle)}_"])
    lines.extend(["", f"- Language: `{plan.language}`", f"- Template: `{plan.template_id}`", ""])

    for section in plan.sections:
        lines.append(f"## {normalize_multilingual_text(section.heading)}")
        lines.append("")
        for paragraph in section.paragraphs:
            lines.append(normalize_multilingual_text(paragraph))
            lines.append("")
        for bullet in section.bullets:
            lines.append(f"- {normalize_multilingual_text(bullet)}")
        if section.bullets:
            lines.append("")

    for table in plan.tables:
        if table.title:
            lines.append(f"## {normalize_multilingual_text(table.title)}")
            lines.append("")
        if table.headers:
            headers = [normalize_multilingual_text(h) for h in table.headers]
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join("---" for _ in headers) + " |")
        for row in table.rows:
            cells = [normalize_multilingual_text(str(cell)).replace("|", "\\|") for cell in row]
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    destination.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _verify_generated_file(fmt: str, path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Generated {fmt} output is missing or empty: {path}")
    if fmt in {"doc", "excel", "powerpoint"}:
        with zipfile.ZipFile(path, "r") as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names:
                raise RuntimeError(f"Invalid OOXML container generated for {fmt}")
    elif fmt == "pdf":
        reader = PdfReader(str(path))
        if len(reader.pages) < 1:
            raise RuntimeError("Generated PDF contains zero pages.")
    elif fmt == "notes":
        if not path.read_text(encoding="utf-8").strip():
            raise RuntimeError("Generated notes file is blank.")


def generate_office_file(plan: DocumentPlan, filename: str | None = None) -> dict[str, object]:
    """Serialize `DocumentPlan` into a verified office artifact inside `EXPORTS_DIR`."""

    ext = FORMAT_EXTENSIONS[plan.format]
    target_name = filename or plan.title
    destination = resolve_safe_export_path(target_name, ext)

    if destination.exists():
        timestamp = datetime.now(timezone.utc).strftime("%H%M%S")
        destination = resolve_safe_export_path(f"{destination.stem}-{timestamp}", ext)

    builders = {
        "doc": _build_docx,
        "excel": _build_xlsx,
        "powerpoint": _build_pptx,
        "pdf": _build_pdf,
        "notes": _build_notes,
    }
    builders[plan.format](plan, destination)
    _verify_generated_file(plan.format, destination)

    sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
    relative_path = str(destination.relative_to(EXPORTS_DIR.resolve())).replace("\\", "/")
    return {
        "path": str(destination),
        "filename": destination.name,
        "relative_path": relative_path,
        "size_bytes": destination.stat().st_size,
        "sha256": sha256,
    }
