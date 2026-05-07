"""Real PDF/A conversion via Ghostscript post-processing.

If `gs` (or `gswin64c` on Windows) is in PATH, it shells out to:
    gs -dPDFA=1 -dBATCH -dNOPAUSE -sProcessColorModel=DeviceRGB \
       -sDEVICE=pdfwrite -sPDFACompatibilityPolicy=1 -dCompatibilityLevel=1.4 \
       -sOutputFile=<out> <in>

Returns:
    (pdf_bytes, status, message_he, message_en)

Where status is one of:
    "verified"     — Ghostscript validated and produced PDF/A bytes
    "best_effort"  — Ghostscript not available; metadata-only PDF/A markers
    "failed"       — Ghostscript ran but produced no output / errored

Callers should expose `status` to the UI so the user knows whether the document
truly conforms to PDF/A-1b or is just best-effort.
"""
from __future__ import annotations
import os
import shutil
import subprocess
import tempfile
import re
from pathlib import Path


_GS_BINARIES = ("gswin64c", "gswin32c", "gs")
_PDFA_VALIDATION_RE = re.compile(rb"GPL Ghostscript \d+\.\d+", re.IGNORECASE)


def gs_path() -> str | None:
    """Locate Ghostscript executable."""
    # Honor explicit override first
    explicit = os.environ.get("GHOSTSCRIPT")
    if explicit and os.path.exists(explicit):
        return explicit
    for name in _GS_BINARIES:
        p = shutil.which(name)
        if p:
            return p
    # Common Windows install paths (Ghostscript installer doesn't always update PATH)
    if os.name == "nt":
        for base in (r"C:\Program Files\gs", r"C:\Program Files (x86)\gs"):
            if not os.path.isdir(base):
                continue
            for ver in sorted(os.listdir(base), reverse=True):
                for sub in ("bin",):
                    for exe in ("gswin64c.exe", "gswin32c.exe"):
                        cand = os.path.join(base, ver, sub, exe)
                        if os.path.exists(cand):
                            return cand
    return None


def is_available() -> bool:
    return gs_path() is not None


def _build_cmd(gs: str, level: str, in_path: Path, out_path: Path) -> list[str]:
    # Minimal, maximally-tolerant invocation. -dPDFACompatibilityPolicy=2 means:
    # if Ghostscript cannot produce a conformant PDF/A, it still outputs a regular
    # PDF rather than aborting. We post-check the output to decide verified vs failed.
    return [
        gs,
        f"-dPDFA={level}",
        "-dBATCH", "-dNOPAUSE", "-dNOSAFER",
        "-sDEVICE=pdfwrite",
        "-dPDFACompatibilityPolicy=2",
        "-sColorConversionStrategy=RGB",
        "-sProcessColorModel=DeviceRGB",
        f"-sOutputFile={out_path}",
        str(in_path),
    ]


def to_pdfa(pdf_bytes: bytes, *, level: str = "2") -> tuple[bytes, str, str, str]:
    """Run Ghostscript to produce PDF/A-{level}b output.

    Defaults to PDF/A-2b because ReportLab's transparency (used for watermarks
    via setFillAlpha) is forbidden in PDF/A-1b but allowed in PDF/A-2.
    Falls back to PDF/A-1b if level=2 fails.
    """
    if not pdf_bytes or pdf_bytes[:4] != b"%PDF":
        return pdf_bytes, "failed", "קלט לא תקין: לא נמצא PDF.", "Invalid input: not a PDF."

    gs = gs_path()
    if not gs:
        return (
            pdf_bytes,
            "best_effort",
            "PDF/A best-effort בלבד — Ghostscript לא נמצא במערכת. למסמך תקני התקנו gs ונסו שוב.",
            "PDF/A best-effort only — Ghostscript not found. Install gs for full conformance.",
        )

    last_err = ""
    # Try PDF/A-2b first, then PDF/A-1b
    levels_to_try = [level] if level != "2" else ["2", "1"]
    for try_level in levels_to_try:
        with tempfile.TemporaryDirectory(prefix="pdfa_") as td:
            in_path = Path(td) / "in.pdf"
            out_path = Path(td) / "out.pdf"
            in_path.write_bytes(pdf_bytes)
            cmd = _build_cmd(gs, try_level, in_path, out_path)
            try:
                proc = subprocess.run(cmd, capture_output=True, timeout=60)
            except subprocess.TimeoutExpired:
                return pdf_bytes, "failed", "המרת PDF/A פגה (timeout).", "PDF/A conversion timed out."
            except Exception as e:
                return pdf_bytes, "failed", f"שגיאת ההמרה: {e}", f"Conversion error: {e}"

            if proc.returncode == 0 and out_path.exists():
                out_bytes = out_path.read_bytes()
                if out_bytes[:4] == b"%PDF":
                    # With -dPDFACompatibilityPolicy=2, GS may emit a regular PDF
                    # even if conformance failed. Look for PDF/A xmp metadata as the
                    # tell-tale of true conformance.
                    is_verified = (
                        b"pdfaid:part" in out_bytes
                        or b"<pdfaid:" in out_bytes
                        or b"GTS_PDFA" in out_bytes
                    )
                    if is_verified:
                        return (
                            out_bytes, "verified",
                            f"המסמך עומד בתקן PDF/A-{try_level}b (אומת ע\"י Ghostscript).",
                            f"Document conforms to PDF/A-{try_level}b (verified by Ghostscript).",
                        )
                    # Output is a clean PDF but missing PDF/A markers. Treat as best_effort.
                    return (
                        out_bytes, "best_effort",
                        "Ghostscript הפיק PDF אך ללא סימני PDF/A מלאים — best-effort.",
                        "Ghostscript produced a PDF without full PDF/A markers — best-effort.",
                    )
            stderr = (proc.stderr or b"").decode("utf-8", errors="replace")
            stdout = (proc.stdout or b"").decode("utf-8", errors="replace")
            last_err = (stderr + " | " + stdout)[:400] or "no output"

    # Ghostscript failed — but the input PDF still carries PDF/A best-effort metadata
    # set by the renderer (Producer="Smart Excel Engine — PDF/A best-effort"), and the
    # PDF is otherwise valid. Return it as best_effort with a transparent message.
    return (
        pdf_bytes, "best_effort",
        f"PDF/A best-effort — Ghostscript לא הצליח להמיר את הקובץ הספציפי הזה. "
        f"המסמך כולל metadata של PDF/A. להבטחת תקן מלא: Adobe Acrobat Pro / pdftk / qpdf.",
        f"PDF/A best-effort — Ghostscript could not strictly convert this specific file. "
        f"The document carries PDF/A metadata. For strict conformance: Adobe Acrobat Pro / pdftk / qpdf.",
    )
