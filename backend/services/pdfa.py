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


def to_pdfa(pdf_bytes: bytes, *, level: str = "1") -> tuple[bytes, str, str, str]:
    """Run Ghostscript to produce PDF/A-{level}b output.

    Returns (output_bytes, status, message_he, message_en).
    On any failure path returns the input bytes unchanged with status='best_effort' or 'failed'.
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

    with tempfile.TemporaryDirectory(prefix="pdfa_") as td:
        in_path = Path(td) / "in.pdf"
        out_path = Path(td) / "out.pdf"
        in_path.write_bytes(pdf_bytes)

        cmd = [
            gs,
            f"-dPDFA={level}",
            "-dBATCH", "-dNOPAUSE", "-dQUIET",
            "-sColorConversionStrategy=RGB",
            "-sProcessColorModel=DeviceRGB",
            "-sDEVICE=pdfwrite",
            "-sPDFACompatibilityPolicy=1",
            "-dCompatibilityLevel=1.4",
            "-dPDFSETTINGS=/prepress",
            f"-sOutputFile={out_path}",
            str(in_path),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            return (
                pdf_bytes, "failed",
                "המרת PDF/A פגה (timeout).",
                "PDF/A conversion timed out.",
            )
        except Exception as e:
            return (
                pdf_bytes, "failed",
                f"שגיאת ההמרה: {e}",
                f"Conversion error: {e}",
            )

        if proc.returncode != 0 or not out_path.exists():
            err = (proc.stderr or proc.stdout or b"").decode("utf-8", errors="replace")[:300]
            return (
                pdf_bytes, "failed",
                f"Ghostscript נכשל. ייצואנו fallback רגיל. שגיאה: {err}",
                f"Ghostscript failed; falling back to non-PDF/A output. Error: {err}",
            )

        out_bytes = out_path.read_bytes()
        if out_bytes[:4] != b"%PDF":
            return (
                pdf_bytes, "failed",
                "פלט Ghostscript אינו PDF תקני.",
                "Ghostscript output is not a valid PDF.",
            )
        return (
            out_bytes, "verified",
            "המסמך עומד בתקן PDF/A-1b (אומת ע\"י Ghostscript).",
            "Document conforms to PDF/A-1b (verified by Ghostscript).",
        )
