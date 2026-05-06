"""Built-in report templates loader."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "builtin_templates"


def list_templates() -> list[dict]:
    out = []
    if not ROOT.exists():
        return out
    for p in sorted(ROOT.glob("*.json")):
        try:
            with p.open("r", encoding="utf-8") as fh:
                out.append(json.load(fh))
        except Exception:
            continue
    return out


def get_template(template_id: str) -> dict | None:
    for t in list_templates():
        if t.get("id") == template_id:
            return t
    return None


def apply_template_priorities(headers: list[str], template_id: str | None) -> dict[int, str]:
    """Return {col_index → priority} based on header keyword matches in the template.
    col_index here is the index *within the headers list*; callers can map back if needed.
    """
    if not template_id:
        return {}
    tpl = get_template(template_id)
    if not tpl:
        return {}
    keywords = tpl.get("priority_keywords", {})
    out: dict[int, str] = {}
    for i, h in enumerate(headers):
        h_low = (h or "").lower()
        matched = False
        for prio in ("high", "low", "medium"):
            for kw in keywords.get(prio, []):
                if kw and kw.lower() in h_low:
                    out[i] = prio
                    matched = True
                    break
            if matched:
                break
    return out
