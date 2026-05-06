"""Apply user-configured filters to extracted rows before export."""
from __future__ import annotations
from typing import Any


def _to_number(s: Any) -> float | None:
    if s is None:
        return None
    try:
        return float(str(s).replace(",", "").replace("%", "").strip())
    except (ValueError, AttributeError):
        return None


def _match(value: str, op: str, val: Any, val2: Any) -> bool:
    text = (value or "").strip()
    if op == "is_empty":
        return text == ""
    if op == "not_empty":
        return text != ""
    if op == "contains":
        return str(val or "").lower() in text.lower()
    if op == "not_contains":
        return str(val or "").lower() not in text.lower()
    if op == "eq":
        return text == str(val or "").strip()
    if op == "neq":
        return text != str(val or "").strip()
    n = _to_number(text)
    if op in ("gt", "lt", "gte", "lte", "between"):
        if n is None:
            return False
        v = _to_number(val)
        if v is None:
            return False
        if op == "gt":
            return n > v
        if op == "lt":
            return n < v
        if op == "gte":
            return n >= v
        if op == "lte":
            return n <= v
        if op == "between":
            v2 = _to_number(val2)
            if v2 is None:
                return False
            lo, hi = (v, v2) if v <= v2 else (v2, v)
            return lo <= n <= hi
    return True


def apply_filters(
    headers: list[str],
    rows: list[list[str]],
    column_indices: list[int],
    filters: list[dict],
) -> list[list[str]]:
    """Filters rows. column_indices maps logical-position-in-row → original column index in source.
    Filter rules use original column indices, so we need to translate to row position."""
    if not filters:
        return rows
    pos_for_index = {ci: pos for pos, ci in enumerate(column_indices)}
    out: list[list[str]] = []
    for row in rows:
        keep = True
        for f in filters:
            ci = f.get("column_index")
            if ci is None or ci not in pos_for_index:
                continue
            pos = pos_for_index[ci]
            cell = row[pos] if pos < len(row) else ""
            if not _match(cell, f.get("op", "contains"), f.get("value"), f.get("value2")):
                keep = False
                break
        if keep:
            out.append(row)
    return out
