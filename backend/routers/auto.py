"""One-Click Smart Export router.

Endpoints:
- POST /api/auto/plan          → returns the auto-plan (no rendering, fast)
- POST /api/auto/preview/pdf   → returns a PDF blob (limited rows) for live preview
- POST /api/auto/export/pdf    → final PDF (full rows)
- POST /api/auto/export/word   → final DOCX
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, JSONResponse

from models.schemas import AutoExportRequest, output_mode_defaults
from services.auto_export import make_plan, render_auto
from services import pdfa as pdfa_service


def _apply_output_mode(req: AutoExportRequest) -> None:
    """If output_mode is set, it overrides watermark + pdf_a (consistent presets)."""
    if not req.output_mode:
        return
    defaults = output_mode_defaults(req.output_mode)
    if not defaults:
        return
    req.watermark.preset = defaults["watermark_preset"]
    req.pdf_a = bool(defaults["pdf_a"])


def _enforce_tier(req: AutoExportRequest) -> None:
    """Free tier: forces a 'Smart Excel Engine' watermark, blocks PDF/A."""
    if req.tier != "pro":
        req.watermark.preset = "custom"
        if not (req.watermark.text or "").strip():
            req.watermark.text = "Smart Excel Engine"
        req.watermark.opacity = max(0.10, min(0.18, req.watermark.opacity))
        req.pdf_a = False
        # Court-ready / official requested but blocked
        if req.output_mode in ("official", "court_ready"):
            req.output_mode = "draft"


def _maybe_pdfa(pdf_bytes: bytes, want_pdfa: bool, locale: str) -> tuple[bytes, dict]:
    """Apply Ghostscript PDF/A post-processing if requested and possible."""
    if not want_pdfa:
        return pdf_bytes, {"requested": False, "status": "off"}
    out, status, msg_he, msg_en = pdfa_service.to_pdfa(pdf_bytes)
    return out, {
        "requested": True,
        "status": status,
        "message": msg_he if locale.startswith("he") else msg_en,
    }


def _content_disposition(name: str, ext: str) -> str:
    full = f"{(name or 'export').strip() or 'export'}.{ext}"
    ascii_fallback = "".join(c if ord(c) < 128 else "_" for c in full) or f"export.{ext}"
    encoded = quote(full, safe="")
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def make_router(storage: Path) -> APIRouter:
    router = APIRouter(tags=["auto"])

    @router.post("/auto/plan")
    def auto_plan(req: AutoExportRequest):
        _apply_output_mode(req)
        try:
            plan, _ = make_plan(
                storage=storage, file_id=req.file_id,
                locale=req.locale, tier=req.tier,
                document_title=req.document_title,
                document_subtitle=req.document_subtitle,
            )
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

        return JSONResponse({
            "detection": {
                "type": plan.detection.detected_type,
                "confidence": plan.detection.confidence,
                "template_id": plan.detection.template_id,
                "reason": plan.detection.reason_he if req.locale.startswith("he") else plan.detection.reason_en,
                "primary_sheet_name": plan.detection.primary_sheet_name,
                "suggested_orientation": plan.detection.suggested_orientation,
            },
            "plan": {
                "page_size": plan.page_size,
                "orientation": plan.orientation,
                "rtl": plan.rtl,
                "sheet_name": plan.primary_sheet["sheet_name"],
                "column_indices": plan.column_indices,
                "priorities": {str(k): v for k, v in plan.priorities.items()},
                "anchor_column_index": plan.anchor_index,
                "title": plan.title,
                "subtitle": plan.subtitle,
                "explanations": plan.explanations,
                "tier_resolved": req.tier,
                "output_mode": req.output_mode,
            },
            "capabilities": {
                "pdfa_available": pdfa_service.is_available(),
                "tier": req.tier,
            },
        })

    @router.post("/auto/preview/pdf")
    def auto_preview_pdf(req: AutoExportRequest):
        _apply_output_mode(req)
        _enforce_tier(req)
        try:
            plan, path = make_plan(
                storage=storage, file_id=req.file_id,
                locale=req.locale, tier=req.tier,
                document_title=req.document_title,
                document_subtitle=req.document_subtitle,
            )
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

        pdf_bytes = render_auto(
            plan=plan, path=path, kind="pdf",
            locale=req.locale, margin_mm=12,
            logo_data_url=req.logo_data_url,
            watermark=req.watermark.model_dump(),
            pdf_a=req.pdf_a,
            row_limit=req.row_limit or 80,
        )
        # Skip Ghostscript on previews — it adds latency, and the verification
        # only matters on the final export. The header still tells the client
        # whether PDF/A *would* be applied on export.
        return Response(content=pdf_bytes, media_type="application/pdf", headers={
            "X-PDFA-Requested": "1" if req.pdf_a else "0",
            "X-PDFA-Available": "1" if pdfa_service.is_available() else "0",
        })

    @router.post("/auto/export/pdf")
    def auto_export_pdf(req: AutoExportRequest):
        _apply_output_mode(req)
        _enforce_tier(req)
        try:
            plan, path = make_plan(
                storage=storage, file_id=req.file_id,
                locale=req.locale, tier=req.tier,
                document_title=req.document_title,
                document_subtitle=req.document_subtitle,
            )
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

        pdf_bytes = render_auto(
            plan=plan, path=path, kind="pdf",
            locale=req.locale, margin_mm=12,
            logo_data_url=req.logo_data_url,
            watermark=req.watermark.model_dump(),
            pdf_a=req.pdf_a,
            row_limit=None,
        )

        pdf_bytes, pdfa_info = _maybe_pdfa(pdf_bytes, req.pdf_a, req.locale)

        headers = {
            "Content-Disposition": _content_disposition(plan.title, "pdf"),
            "X-PDFA-Requested": "1" if pdfa_info["requested"] else "0",
            "X-PDFA-Status": pdfa_info["status"],
        }
        if "message" in pdfa_info:
            from urllib.parse import quote
            headers["X-PDFA-Message"] = quote(pdfa_info["message"], safe="")
        return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

    @router.post("/auto/export/word")
    def auto_export_word(req: AutoExportRequest):
        _apply_output_mode(req)
        _enforce_tier(req)
        try:
            plan, path = make_plan(
                storage=storage, file_id=req.file_id,
                locale=req.locale, tier=req.tier,
                document_title=req.document_title,
                document_subtitle=req.document_subtitle,
            )
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))
        except ValueError as e:
            raise HTTPException(400, str(e))

        docx_bytes = render_auto(
            plan=plan, path=path, kind="word",
            locale=req.locale, margin_mm=12,
            logo_data_url=req.logo_data_url,
            watermark=req.watermark.model_dump(),
            pdf_a=False,
            row_limit=None,
        )
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": _content_disposition(plan.title, "docx")},
        )

    return router
