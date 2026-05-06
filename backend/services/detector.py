"""Smart Report Detection.

Looks at the headers + a sample of cell values to classify the report type.
Returns the type with the highest confidence score.

This is the brain behind the One-Click "Generate Perfect Report" button.
"""
from __future__ import annotations
from dataclasses import dataclass


@dataclass
class DetectionResult:
    detected_type: str               # financial | legal | inventory | general
    confidence: float                # 0..1
    template_id: str                 # which template to apply
    reason_he: str                   # human-readable, Hebrew
    reason_en: str                   # human-readable, English
    primary_sheet_name: str
    suggested_orientation: str       # portrait | landscape


# (lowercased) keyword → score weight. Strong words contribute more.
SIGNATURES: dict[str, dict[str, float]] = {
    "financial": {
        # strong
        "חשבונית": 3.0, "invoice": 3.0,
        "מע\"מ": 3.0, "מעמ": 3.0, "vat": 3.0, "tax": 2.5,
        "סכום": 2.5, "amount": 2.5, "total": 2.5, "סה\"כ": 2.5, "סהכ": 2.5,
        "ספק": 2.0, "vendor": 2.0, "supplier": 2.0,
        # weak
        "מחיר": 1.0, "price": 1.0, "cost": 1.0,
        "תשלום": 1.5, "payment": 1.5,
        "balance": 1.5, "יתרה": 1.5,
        "currency": 1.0, "מטבע": 1.0,
    },
    "legal": {
        "תיק": 3.0, "מס' תיק": 3.5, "מספר תיק": 3.5, "case": 2.5,
        "תביעה": 3.0, "תביעות": 2.5,
        "ערעור": 3.0, "ערכאה": 2.5,
        "בית משפט": 3.0, "court": 2.5,
        "עו\"ד": 2.0, "עוד": 1.5, "advocate": 2.0, "attorney": 2.0,
        "plaintiff": 2.0, "defendant": 2.0,
        "תובע": 2.0, "נתבע": 2.0,
        "סטטוס": 0.5, "תאריך פתיחה": 1.5,
        "פסק דין": 2.0, "verdict": 2.0, "ruling": 1.5,
        "client": 1.0, "לקוח": 1.0,
    },
    "inventory": {
        "sku": 3.5, "barcode": 3.0, "ברקוד": 3.0,
        "מלאי": 2.5, "stock": 2.5,
        "quantity": 2.5, "qty": 2.5, "כמות": 2.5,
        "פריט": 2.0, "item": 2.0, "product": 2.0, "מוצר": 2.0,
        "מחסן": 2.0, "warehouse": 2.0,
        "מיקום": 1.5, "location": 1.5, "shelf": 1.5,
        "קטגוריה": 1.0, "category": 1.0,
        "supplier": 1.0, "ספק": 1.0,
    },
}


TEMPLATE_MAP = {
    "financial": "financial",
    "legal": "legal",
    "inventory": "inventory",
    "general": "general",
}


def _pick_primary_sheet(sheets: list[dict]) -> dict:
    """Prefer the sheet with the most non-empty cells (data-rich)."""
    best = sheets[0]
    best_score = -1
    for s in sheets:
        rows = max(0, s.get("total_rows", 0) - s.get("detected_header_row", 1))
        non_empty_cols = sum(1 for c in s.get("columns", []) if not c.get("is_fully_empty"))
        score = rows * non_empty_cols * (s.get("data_density") or 0.0)
        if score > best_score:
            best_score = score
            best = s
    return best


def _score_type(headers: list[str], samples: list[str]) -> dict[str, float]:
    """Return a {type: score} dict by counting keyword hits in headers + sample values."""
    blob_parts: list[str] = []
    for h in headers:
        if h:
            blob_parts.append(h.lower())
    for v in samples:
        if v:
            blob_parts.append(v.lower())
    blob = " ".join(blob_parts)

    scores: dict[str, float] = {}
    for tname, kw_map in SIGNATURES.items():
        s = 0.0
        for kw, weight in kw_map.items():
            if kw.lower() in blob:
                s += weight
        scores[tname] = s
    return scores


def detect_report_type(analysis: dict) -> DetectionResult:
    sheets = analysis.get("sheets") or []
    if not sheets:
        return DetectionResult(
            detected_type="general",
            confidence=0.0,
            template_id="general",
            reason_he="אין נתונים לזיהוי — שימוש בתבנית כללית.",
            reason_en="No data to classify — falling back to general template.",
            primary_sheet_name="",
            suggested_orientation="portrait",
        )

    primary = _pick_primary_sheet(sheets)
    headers = [c.get("header") or "" for c in primary.get("columns", [])]
    samples: list[str] = []
    for c in primary.get("columns", []):
        for v in (c.get("sample_values") or [])[:3]:
            if v:
                samples.append(str(v))

    scores = _score_type(headers, samples)
    if not scores:
        scores = {"general": 0.0}

    best_type, best_score = max(scores.items(), key=lambda kv: kv[1])
    # Confidence: best_score normalized to a 0..1 scale via squashing
    # (≥ 6 → essentially certain, 3 → meaningful, < 1.5 → fallback to general)
    if best_score < 1.5:
        best_type = "general"
        confidence = 0.4
    else:
        confidence = min(1.0, best_score / 6.0)

    n_visible_cols = sum(1 for c in primary.get("columns", []) if not c.get("is_fully_empty"))
    suggested_orientation = "landscape" if n_visible_cols >= 8 else "portrait"

    matched_kws = []
    if best_type in SIGNATURES:
        blob = " ".join((h or "").lower() for h in headers)
        for kw in SIGNATURES[best_type]:
            if kw.lower() in blob:
                matched_kws.append(kw)
        matched_kws = matched_kws[:4]

    if best_type == "general":
        reason_he = "לא זוהו דפוסים חזקים — המערכת בחרה תבנית כללית."
        reason_en = "No strong signal detected — using the general template."
    else:
        type_he = {"financial": "כספי", "legal": "משפטי", "inventory": "מלאי"}[best_type]
        type_en = {"financial": "financial", "legal": "legal", "inventory": "inventory"}[best_type]
        kws_str = ", ".join(matched_kws) or "—"
        reason_he = f"זוהה דוח {type_he} (ביטחון {confidence:.0%}). מילים שזוהו: {kws_str}."
        reason_en = f"Detected {type_en} report (confidence {confidence:.0%}). Matched keywords: {kws_str}."

    return DetectionResult(
        detected_type=best_type,
        confidence=round(confidence, 3),
        template_id=TEMPLATE_MAP[best_type],
        reason_he=reason_he,
        reason_en=reason_en,
        primary_sheet_name=primary.get("sheet_name") or "",
        suggested_orientation=suggested_orientation,
    )
