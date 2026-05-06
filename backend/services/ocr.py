"""OCR service: convert scanned PDFs to a workable Excel-like grid via the local
'dik' (DocImageKit) CLI if available, otherwise return a clear error.

The integration shells out to `dik` because that's how the user's existing
DocImageKit toolchain is exposed.
"""
from __future__ import annotations
import shutil
import subprocess
import tempfile
from pathlib import Path


def is_available() -> bool:
    return shutil.which("dik") is not None


def ocr_pdf_to_xlsx(pdf_bytes: bytes) -> tuple[bytes, str | None]:
    """Run OCR on a PDF and return (xlsx_bytes, error_message_or_none).
    On success: returns the xlsx bytes ready to be persisted into storage and analyzed.
    On failure or unavailable tool: returns (b"", error_message).
    """
    if not is_available():
        return b"", "DocImageKit CLI ('dik') not found in PATH. OCR requires it to be installed."

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        in_pdf = td_path / "input.pdf"
        in_pdf.write_bytes(pdf_bytes)
        out_xlsx = td_path / "output.xlsx"

        # We try a few likely sub-command shapes since DocImageKit's exact CLI surface
        # may vary. The first one that returns 0 wins.
        candidates = [
            ["dik", "ocr", "--input", str(in_pdf), "--output", str(out_xlsx), "--format", "xlsx"],
            ["dik", "convert", str(in_pdf), str(out_xlsx)],
            ["dik", "pdf-to-xlsx", str(in_pdf), str(out_xlsx)],
        ]
        last_err = ""
        for cmd in candidates:
            try:
                proc = subprocess.run(cmd, capture_output=True, timeout=120)
                if proc.returncode == 0 and out_xlsx.exists():
                    return out_xlsx.read_bytes(), None
                last_err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace")
            except FileNotFoundError:
                return b"", "DocImageKit CLI ('dik') not callable."
            except subprocess.TimeoutExpired:
                return b"", "OCR timed out (>120s)."
            except Exception as e:
                last_err = str(e)

        return b"", f"OCR failed via 'dik'. Last error: {last_err[:300]}"
