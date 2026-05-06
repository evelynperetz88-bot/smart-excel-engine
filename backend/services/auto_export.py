"""One-Click Smart Export orchestrator.

Takes a file_id and a tier (free/pro), builds a complete export plan, and renders
PDF/Word — without any manual configuration from the user.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

from services.analyzer import analyze_workbook, extract_table
from services.detector import detect_report_type, DetectionResult
from services.templates import get_template
from services.layout_engine import build_columns, plan_layout
from services.pdf_renderer import render_pdf
from services.word_renderer import render_docx
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, A3, landscape, portrait


def _available_width_pt(page_size: str, orientation: str, margin_mm: float) -> float:
    base = A4 if page_size.upper() == "A4" else A3
    pagesize = landscape(base) if orientation.lower() == "landscape" else portrait(base)
    return pagesize[0] - 2 * margin_mm * mm


def _apply_template_priorities(headers: list[str], col_indices: list[int], template: dict) -> dict[int, str]:
    """Map template keyword hits to column indices."""
    if not template:
        return {}
    kws = template.get("priority_keywords", {})
    out: dict[int, str] = {}
    for pos, ci in enumerate(col_indices):
        h = (headers[pos] or "").lower()
        chosen = None
        for prio in ("high", "low", "medium"):
            for kw in kws.get(prio, []):
                if kw and kw.lower() in h:
                    chosen = prio
                    break
            if chosen:
                break
        if chosen:
            out[ci] = chosen
    return out


@dataclass
class AutoPlan:
    detection: DetectionResult
    template_id: str
    page_size: str
    orientation: str
    rtl: bool
    primary_sheet: dict
    column_indices: list[int]
    priorities: dict[int, str]   # col_index → priority
    anchor_index: int | None
    title: str
    subtitle: str
    explanations: list[str]      # human notes about decisions


def make_plan(
    *,
    storage: Path,
    file_id: str,
    locale: str = "he",
    tier: str = "free",
    document_title: str | None = None,
    document_subtitle: str | None = None,
) -> tuple[AutoPlan, str]:
    """Returns (plan, file_path_str). The file_path is the resolved storage path."""
    safe = "".join(ch for ch in file_id if ch.isalnum() or ch in "-_")
    if not safe or safe != file_id:
        raise ValueError("file_id לא תקין")
    candidates = list(storage.glob(f"{safe}.*"))
    if not candidates:
        raise FileNotFoundError("הקובץ לא נמצא")
    path = str(candidates[0])

    analysis = analyze_workbook(path)
    detection = detect_report_type(analysis)
    primary = next(s for s in analysis["sheets"] if s["sheet_name"] == detection.primary_sheet_name)

    # Choose columns: drop fully-empty
    column_indices = [c["index"] for c in primary["columns"] if not c["is_fully_empty"]]
    headers_for_kept = [c["header"] for c in primary["columns"] if not c["is_fully_empty"]]

    # Priorities: start from analyzer suggestion, then overlay template keywords (template wins)
    priorities: dict[int, str] = {}
    for c in primary["columns"]:
        if c["index"] in column_indices:
            priorities[c["index"]] = c.get("suggested_priority") or "medium"

    template = get_template(detection.template_id)
    if template:
        priorities.update(_apply_template_priorities(headers_for_kept, column_indices, template))

    # Anchor: leftmost High-priority column
    anchor_index = None
    for ci in column_indices:
        if priorities.get(ci) == "high":
            anchor_index = ci
            break

    page_size = (template or {}).get("page_size", "A4")
    rtl = (template or {}).get("rtl", locale == "he")
    orientation = detection.suggested_orientation

    explanations = [
        detection.reason_he if locale.startswith("he") else detection.reason_en,
    ]
    if template:
        tname = template.get("name_he" if locale.startswith("he") else "name_en", template["id"])
        explanations.append(
            f"הוחלה תבנית '{tname}'." if locale.startswith("he")
            else f"Applied template '{tname}'."
        )
    if anchor_index is not None:
        anchor_header = next((h for ci, h in zip(column_indices, headers_for_kept) if ci == anchor_index), "")
        explanations.append(
            f"עמודת '{anchor_header}' זוהתה כעמודת עוגן." if locale.startswith("he")
            else f"Column '{anchor_header}' selected as anchor."
        )
    explanations.append(
        f"כיוון נבחר: {orientation} (לפי {sum(1 for c in primary['columns'] if not c['is_fully_empty'])} עמודות נראות)."
        if locale.startswith("he")
        else f"Orientation: {orientation} ({sum(1 for c in primary['columns'] if not c['is_fully_empty'])} visible columns)."
    )

    plan = AutoPlan(
        detection=detection,
        template_id=detection.template_id,
        page_size=page_size,
        orientation=orientation,
        rtl=rtl,
        primary_sheet=primary,
        column_indices=column_indices,
        priorities=priorities,
        anchor_index=anchor_index,
        title=document_title or detection.primary_sheet_name,
        subtitle=document_subtitle or "",
        explanations=explanations,
    )
    return plan, path


def render_auto(
    *,
    plan: AutoPlan,
    path: str,
    kind: str,                 # "pdf" | "word"
    locale: str = "he",
    margin_mm: float = 12,
    logo_data_url: str | None = None,
    watermark: dict | None = None,
    pdf_a: bool = False,
    row_limit: int | None = None,
) -> bytes:
    table = extract_table(
        path,
        plan.primary_sheet["sheet_name"],
        plan.column_indices,
        skip_empty_rows=True,
        header_row=None,
        expand_merged=True,
    )
    rows = table["rows"]
    if row_limit is not None:
        rows = rows[: max(1, min(500, row_limit))]

    avail = _available_width_pt(plan.page_size, plan.orientation, margin_mm)

    est_widths: dict[int, int] = {}
    for pos, ci in enumerate(plan.column_indices):
        longest = len(table["headers"][pos] or "")
        for r in rows[:200]:
            if pos < len(r) and r[pos]:
                longest = max(longest, min(60, len(str(r[pos])) + 2))
        est_widths[ci] = max(8, min(60, max(longest, len(table["headers"][pos] or "") + 2)))

    cols = build_columns(table["headers"], plan.column_indices, est_widths, plan.priorities)
    layout = plan_layout(
        columns=cols,
        available_width_pt=avail,
        smart_layout=True,
        anchor_index=plan.anchor_index,
        locale=locale,
    )

    # Combine engine explanations with our top-level decisions
    layout.explanations = plan.explanations + layout.explanations

    section = {
        "title": plan.title,
        "layout": layout,
        "rows": rows,
        "positions_in_row": list(range(len(plan.column_indices))),
    }

    wm = watermark or {}
    if kind == "word":
        return render_docx(
            sections=[section],
            page_size=plan.page_size,
            orientation=plan.orientation,
            margin_mm=margin_mm,
            rtl=plan.rtl,
            locale=locale,
            header_title=plan.title,
            header_subtitle=plan.subtitle,
            logo_data_url=logo_data_url,
            show_page_numbers=True,
            show_generated_date=True,
        )
    return render_pdf(
        sections=[section],
        page_size=plan.page_size,
        orientation=plan.orientation,
        margin_mm=margin_mm,
        rtl=plan.rtl,
        locale=locale,
        header_title=plan.title,
        header_subtitle=plan.subtitle,
        logo_data_url=logo_data_url,
        show_page_numbers=True,
        show_generated_date=True,
        watermark_preset=wm.get("preset", "none"),
        watermark_text=wm.get("text", ""),
        watermark_opacity=float(wm.get("opacity", 0.18)),
        watermark_color=wm.get("color", "#888888"),
        pdf_a=pdf_a,
    )
