from __future__ import annotations
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from services.analyzer import analyze_workbook
from services.ocr import ocr_pdf_to_xlsx, is_available as ocr_available

ALLOWED_EXTS = {".xlsx", ".xls", ".xlsm"}
PDF_EXTS = {".pdf"}
MAX_BYTES = 50 * 1024 * 1024


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
        if suffix in PDF_EXTS:
            xlsx_bytes, err = ocr_pdf_to_xlsx(content)
            if err or not xlsx_bytes:
                raise HTTPException(400, f"OCR לא זמין או נכשל: {err}")
            content = xlsx_bytes
            suffix = ".xlsx"
            ocr_used = True
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
