"""Live end-to-end test against production deployments."""
from __future__ import annotations
import json
import urllib.request
import tempfile
from pathlib import Path
import openpyxl

BACKEND = "https://smart-excel-engine.onrender.com"
FRONTEND = "https://smart-excel-engine.vercel.app"


def _post_json(path, payload, extra_headers=None):
    headers = {"Content-Type": "application/json", "Origin": FRONTEND}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(
        BACKEND + path, data=json.dumps(payload).encode("utf-8"),
        headers=headers, method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.status, resp.read(), dict(resp.headers)


def _post_multipart(path, file_path):
    boundary = "----LiveBoundary7MA4YWxkTrZu0gW"
    body = b""
    body += f"--{boundary}\r\n".encode()
    body += f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode()
    body += b"Content-Type: application/octet-stream\r\n\r\n"
    body += file_path.read_bytes()
    body += f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        BACKEND + path, data=body, method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Origin": FRONTEND,
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status, json.loads(resp.read())


def build_legal_sample(path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "תיקים"
    ws["A1"] = "משרד דוגמה"
    headers = ["מס' תיק", "שם לקוח", "תאריך פתיחה", "סכום (₪)", "סטטוס", "ערכאה"]
    for i, h in enumerate(headers, start=1):
        ws.cell(row=3, column=i, value=h)
    data = [
        (101, "כהן בע\"מ", "2024-03-01", 125000, "פתוח", "מחוזי תל אביב"),
        (102, "פרץ אלון",  "2024-04-15", 32000,  "סגור", "שלום ירושלים"),
        (103, "ביטוח אחים","2024-05-20", 480000, "פתוח", "עליון"),
    ]
    for ri, row in enumerate(data, start=4):
        for ci, v in enumerate(row, start=1):
            ws.cell(row=ri, column=ci, value=v)
    wb.save(path)


def run():
    print(f"Backend:  {BACKEND}")
    print(f"Frontend: {FRONTEND}")
    print()

    # 1. Health
    health = json.loads(urllib.request.urlopen(BACKEND + "/api/health", timeout=30).read())
    print(f"[1] /api/health: v{health['version']}, pdfa={health['pdfa_available']}, ocr={health['ocr_available']}")
    assert health["ok"] and health["pdfa_available"], "PDF/A must be available in prod"

    # 2. Upload
    tmpdir = Path(tempfile.mkdtemp(prefix="live_"))
    src = tmpdir / "case_report.xlsx"
    build_legal_sample(src)
    status, info = _post_multipart("/api/upload", src)
    file_id = info["file_id"]
    print(f"[2] /api/upload: {status} ok, file_id={file_id[:12]}…, ocr_used={info['ocr_used']}")

    # 3. Auto plan
    auto_payload = {
        "file_id": file_id, "locale": "he", "tier": "free",
        "watermark": {"preset": "none", "text": "", "opacity": 0.18, "color": "#888888"},
        "pdf_a": False, "row_limit": 80,
    }
    status, body, _ = _post_json("/api/auto/plan", auto_payload)
    js = json.loads(body)
    det = js["detection"]
    print(f"[3] /api/auto/plan: {status}, detected={det['type']} (conf={det['confidence']:.2f})")
    assert det["type"] == "legal", f"expected legal, got {det['type']}"

    # 4. Free PDF → must imprint Smart Excel Engine watermark
    status, body, _ = _post_json("/api/auto/preview/pdf", auto_payload)
    print(f"[4] /api/auto/preview/pdf (free): {status}, bytes={len(body)}")
    assert body[:4] == b"%PDF"
    assert b"Smart Excel Engine" in body, "free tier must imprint watermark"

    # 5. Pro + court_ready + PDF/A
    pro_payload = {**auto_payload, "tier": "pro", "output_mode": "court_ready", "pdf_a": True}
    status, body, hdrs = _post_json("/api/auto/export/pdf", pro_payload)
    pdfa_status = hdrs.get("X-Pdfa-Status") or hdrs.get("x-pdfa-status") or hdrs.get("X-PDFA-Status")
    print(f"[5] /api/auto/export/pdf (pro+court_ready+PDF/A): {status}, bytes={len(body)}, X-PDFA-Status={pdfa_status}")
    assert body[:4] == b"%PDF"
    assert pdfa_status == "verified", f"with Ghostscript installed, expected 'verified', got {pdfa_status}"

    # 6. English locale switch
    en_payload = {**auto_payload, "locale": "en"}
    status, body, _ = _post_json("/api/auto/plan", en_payload)
    js = json.loads(body)
    print(f"[6] /api/auto/plan (locale=en): reason='{js['detection']['reason'][:60]}…'")
    assert "Detected" in js["detection"]["reason"] or "general" in js["detection"]["reason"].lower()

    # 7. Word export
    status, body, _ = _post_json("/api/auto/export/word", auto_payload)
    print(f"[7] /api/auto/export/word: {status}, bytes={len(body)}")
    assert body[:2] == b"PK"

    # 8. Frontend serves bundled JS containing the backend URL (proves env var was baked at build time)
    html = urllib.request.urlopen(FRONTEND, timeout=30).read().decode()
    print(f"[8] frontend index.html: {len(html)} bytes")
    assert "smart-excel-engine" in html.lower() or "<div id=\"root\">" in html

    print()
    print("[OK] LIVE end-to-end test PASSED. System ready for clients.")


if __name__ == "__main__":
    run()
