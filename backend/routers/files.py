from __future__ import annotations
import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.analyzer import analyze_workbook
from services.ocr import ocr_pdf_to_xlsx, is_available as ocr_available

ALLOWED_EXTS = {".xlsx", ".xls", ".xlsm"}
PDF_EXTS = {".pdf"}
MAX_BYTES = 50 * 1024 * 1024


def _convert_xls_to_xlsx(xls_bytes: bytes) -> bytes:
    """Convert legacy Excel 97-2003 (.xls) to modern .xlsx using xlrd + openpyxl.
    Loses native formatting; preserves cell values, sheet names, and structure —
    which is exactly what our analyzer/exporter needs.
    """
    import xlrd
    from openpyxl import Workbook

    book = xlrd.open_workbook(file_contents=xls_bytes)
    wb = Workbook()
    # Remove the default sheet that openpyxl creates
    if wb.active and wb.active.title in wb.sheetnames:
        wb.remove(wb.active)

    for sheet_name in book.sheet_names():
        src = book.sheet_by_name(sheet_name)
        # openpyxl limits sheet titles to 31 chars
        title = (sheet_name or "Sheet")[:31] or "Sheet"
        ws = wb.create_sheet(title)
        for r in range(src.nrows):
            for c in range(src.ncols):
                v = src.cell_value(r, c)
                # xlrd returns 0.0 for empty numeric cells; keep them as-is
                ws.cell(row=r + 1, column=c + 1, value=v)
        # Carry over merged ranges
        for mr in getattr(src, "merged_cells", []):
            rlo, rhi, clo, chi = mr
            try:
                ws.merge_cells(
                    start_row=rlo + 1, end_row=rhi,
                    start_column=clo + 1, end_column=chi,
                )
            except Exception:
                pass

    if not wb.sheetnames:
        wb.create_sheet("Sheet1")

    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def make_router(storage: Path) -> APIRouter:
    router = APIRouter(tags=["files"])

    @router.post("/upload")
    async def upload(file: UploadFile = File(...)):
        original_name = file.filename or ""
        suffix = Path(original_name).suffix.lower()
        content = await file.read()
        if not content:
            raise HTTPException(400, "הקובץ ריק")
        if len(content) > MAX_BYTES:
            raise HTTPException(413, "הקובץ חורג מ-50MB")

        ocr_used = False
        converted_from_xls = False
        if suffix in PDF_EXTS:
            xlsx_bytes, err = ocr_pdf_to_xlsx(content)
            if err or not xlsx_bytes:
                raise HTTPException(400, f"OCR לא זמין או נכשל: {err}")
            content = xlsx_bytes
            suffix = ".xlsx"
            ocr_used = True
        elif suffix == ".xls":
            # Legacy Excel 97-2003 — convert to .xlsx in memory so the rest of the
            # pipeline (openpyxl-based) can handle it normally.
            try:
                content = _convert_xls_to_xlsx(content)
            except Exception as e:
                raise HTTPException(400, f"לא ניתן להמיר קובץ .xls לפורמט המודרני: {e}")
            suffix = ".xlsx"
            converted_from_xls = True
        elif suffix not in ALLOWED_EXTS:
            raise HTTPException(400, f"סיומת לא נתמכת: {suffix}. נתמך: {sorted(ALLOWED_EXTS | PDF_EXTS)}")

        file_id = uuid.uuid4().hex
        target = storage / f"{file_id}{suffix}"
        target.write_bytes(content)

        try:
            analysis = analyze_workbook(str(target))
        except Exception as e:
            target.unlink(missing_ok=True)
            raise HTTPException(400, f"קובץ Excel לא תקין: {e}")

        return {
            "file_id": file_id,
            "filename": original_name,
            "size_bytes": len(content),
            "ocr_used": ocr_used,
            "converted_from_xls": converted_from_xls,
            "analysis": analysis,
        }

    @router.delete("/file/{file_id}")
    def delete_file(file_id: str):
        safe = "".join(ch for ch in file_id if ch.isalnum() or ch in "-_")
        if safe != file_id:
            raise HTTPException(400, "file_id לא תקין")
        for p in storage.glob(f"{safe}.*"):
            try:
                p.unlink()
            except OSError:
                pass
        return {"deleted": True}

    @router.get("/ocr/status")
    def ocr_status():
        return {"available": ocr_available()}

    return router
