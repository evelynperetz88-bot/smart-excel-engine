from __future__ import annotations
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from models.schemas import ExportRequest, PreviewRequest
from services.analyzer import extract_table
from services.filters import apply_filters
from services.layout_engine import build_columns, plan_layout
from services.pdf_renderer import render_pdf
from services.word_renderer import render_docx
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A4, A3, landscape, portrait


def _path_for(storage: Path, file_id: str) -> Path:
    safe = "".join(ch for ch in file_id if ch.isalnum() or ch in "-_")
    if not safe or safe != file_id:
        raise HTTPException(400, "file_id לא תקין")
    candidates = list(storage.glob(f"{safe}.*"))
    if not candidates:
        raise HTTPException(404, "הקובץ לא נמצא")
    return candidates[0]


def _available_width_pt(page_size: str, orientation: str, margin_mm: float) -> float:
    base = A4 if page_size.upper() == "A4" else A3
    pagesize = landscape(base) if orientation.lower() == "landscape" else portrait(base)
    return pagesize[0] - 2 * margin_mm * mm


def _build_sections(storage: Path, req) -> list[dict]:
    sections: list[dict] = []
    avail = _available_width_pt(req.page_size, req.orientation, req.margin_mm)

    for spec in req.sheets:
        path = _path_for(storage, req.file_id)
        try:
            table = extract_table(
                str(path),
                spec.sheet_name,
                spec.column_indices,
                skip_empty_rows=spec.skip_empty_rows,
                header_row=spec.header_row,
                expand_merged=True,
            )
        except ValueError as e:
            raise HTTPException(400, str(e))

        # Filters
        filter_dicts = [f.model_dump() for f in spec.filters]
        rows = apply_filters(table["headers"], table["rows"], spec.column_indices, filter_dicts)

        # Build estimated widths from headers + sampled cells (since analyzer's widths are sheet-wide)
        est_widths: dict[int, int] = {}
        for pos, ci in enumerate(spec.column_indices):
            longest = len(table["headers"][pos] or "")
            for r in rows[:200]:
                if pos < len(r) and r[pos]:
                    longest = max(longest, max((len(line) for line in str(r[pos]).splitlines() or [str(r[pos])]), default=0))
            est_widths[ci] = min(60, max(8, longest + 2))

        priorities = {ci: spec.priorities.get(ci, "medium") for ci in spec.column_indices}
        cols = build_columns(table["headers"], spec.column_indices, est_widths, priorities)

        layout = plan_layout(
            columns=cols,
            available_width_pt=avail,
            smart_layout=req.smart_layout,
            anchor_index=req.anchor_column_index,
            locale=req.locale,
        )

        if not req.explain:
            layout.explanations = []

        sections.append({
            "title": spec.section_title or spec.sheet_name,
            "layout": layout,
            "rows": rows,
            "positions_in_row": list(range(len(spec.column_indices))),
            # for preview metadata:
            "_headers": table["headers"],
            "_row_count": len(rows),
        })
    return sections


def _safe_name(s: str) -> str:
    return "".join(c for c in (s or "") if c.isalnum() or c in "-_ ").strip() or "export"


def _content_disposition(name: str, ext: str) -> str:
    """RFC 5987-compliant Content-Disposition supporting non-ASCII filenames."""
    from urllib.parse import quote
    full_unicode = f"{name}.{ext}"
    ascii_fallback = "".join(c if ord(c) < 128 else "_" for c in full_unicode) or f"export.{ext}"
    encoded = quote(full_unicode, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def make_router(storage: Path) -> APIRouter:
    router = APIRouter(tags=["export"])

    def _enforce_tier(req):
        """Free tier: forces a Smart Excel Engine watermark and disables PDF/A."""
        if getattr(req, "tier", "free") != "pro":
            req.watermark.preset = "custom"
            if not (req.watermark.text or "").strip():
                req.watermark.text = "Smart Excel Engine"
            req.watermark.opacity = max(0.10, min(0.18, req.watermark.opacity))
            req.pdf_a = False

    @router.post("/export/pdf")
    def export_pdf(req: ExportRequest):
        _enforce_tier(req)
        sections = _build_sections(storage, req)
        pdf_bytes = render_pdf(
            sections=sections,
            page_size=req.page_size, orientation=req.orientation,
            margin_mm=req.margin_mm, rtl=req.rtl, locale=req.locale,
            header_title=req.header.title,
            header_subtitle=req.header.subtitle,
            logo_data_url=req.header.logo_data_url,
            show_page_numbers=req.header.show_page_numbers,
            show_generated_date=req.header.show_generated_date,
            watermark_preset=req.watermark.preset,
            watermark_text=req.watermark.text,
            watermark_opacity=req.watermark.opacity,
            watermark_color=req.watermark.color,
            pdf_a=req.pdf_a,
        )
        name = req.header.title or req.sheets[0].sheet_name or "export"
        return Response(content=pdf_bytes, media_type="application/pdf",
                        headers={"Content-Disposition": _content_disposition(name, "pdf")})

    @router.post("/export/word")
    def export_word(req: ExportRequest):
        _enforce_tier(req)
        sections = _build_sections(storage, req)
        docx_bytes = render_docx(
            sections=sections,
            page_size=req.page_size, orientation=req.orientation,
            margin_mm=req.margin_mm, rtl=req.rtl, locale=req.locale,
            header_title=req.header.title,
            header_subtitle=req.header.subtitle,
            logo_data_url=req.header.logo_data_url,
            show_page_numbers=req.header.show_page_numbers,
            show_generated_date=req.header.show_generated_date,
        )
        name = req.header.title or req.sheets[0].sheet_name or "export"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": _content_disposition(name, "docx")},
        )

    @router.post("/preview/pdf")
    def preview_pdf(req: PreviewRequest):
        _enforce_tier(req)
        sections = _build_sections(storage, req)
        for s in sections:
            s["rows"] = s["rows"][: max(1, min(500, req.row_limit))]
        pdf_bytes = render_pdf(
            sections=sections,
            page_size=req.page_size, orientation=req.orientation,
            margin_mm=req.margin_mm, rtl=req.rtl, locale=req.locale,
            header_title=req.header.title,
            header_subtitle=req.header.subtitle,
            logo_data_url=req.header.logo_data_url,
            show_page_numbers=req.header.show_page_numbers,
            show_generated_date=req.header.show_generated_date,
            watermark_preset=req.watermark.preset,
            watermark_text=req.watermark.text,
            watermark_opacity=req.watermark.opacity,
            watermark_color=req.watermark.color,
            pdf_a=req.pdf_a,
        )
        return Response(content=pdf_bytes, media_type="application/pdf")

    @router.post("/preview/data")
    def preview_data(req: PreviewRequest):
        sections = _build_sections(storage, req)
        out = []
        for s in sections:
            out.append({
                "title": s["title"],
                "headers": s["_headers"],
                "rows": s["rows"][: max(1, min(500, req.row_limit))],
                "row_count": s["_row_count"],
                "groups": [
                    {
                        "columns": [
                            {"index": c.index, "header": c.header, "priority": c.priority, "is_anchor": c.is_anchor}
                            for c in g.columns
                        ],
                        "used_chars": g.used_chars,
                        "char_budget": g.char_budget,
                    }
                    for g in s["layout"].groups
                ],
                "explanations": s["layout"].explanations,
                "base_font_size": s["layout"].base_font_size,
            })
        return {"sections": out}

    return router
