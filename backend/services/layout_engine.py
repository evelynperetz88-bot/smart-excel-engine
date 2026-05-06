"""Smart Layout Engine.

Splits selected columns into "page-groups": each group is a list of columns whose
combined visual width fits within the available page width.

Priority levels (high/medium/low) determine which columns get the "best real estate":
- High-priority columns are packed first into the earliest page-groups.
- Medium fill the rest of those groups.
- Low-priority columns are pushed to later page-groups.
- An optional anchor column is repeated as the first column of every group, so
  rows can be cross-referenced across the column-split (think: ID column).

The engine also produces human-readable explanations of *why* it placed each column
the way it did — useful for the UI's "Explainable Engine" panel.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable


PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


@dataclass
class ColSpec:
    index: int          # original column index in the source sheet
    pos: int            # position in the user-selected ordered list
    header: str
    estimated_width: int  # in characters
    priority: str       # high|medium|low
    is_anchor: bool = False


@dataclass
class PageGroup:
    """One horizontal slice of the table — fits in one page width."""
    columns: list[ColSpec]   # in display order
    char_budget: float
    used_chars: float


@dataclass
class LayoutResult:
    groups: list[PageGroup]
    explanations: list[str]
    anchor_index: int | None
    char_budget: float
    base_font_size: float


def _char_budget(available_width_pt: float, base_font_size: float) -> float:
    """Approximate number of characters that fit on one row at this font size."""
    char_w = base_font_size * 0.55
    return max(20.0, available_width_pt / char_w)


def _auto_font_size(num_columns: int, available_width_pt: float) -> float:
    if num_columns <= 0:
        return 10
    from reportlab.lib.units import mm
    per_col_mm = (available_width_pt / num_columns) / mm
    if per_col_mm >= 35:
        return 10
    if per_col_mm >= 25:
        return 9
    if per_col_mm >= 18:
        return 8
    if per_col_mm >= 13:
        return 7
    return 6


def _pack_one_group(
    pool: list[ColSpec],
    anchor: ColSpec | None,
    budget: float,
) -> tuple[PageGroup, list[ColSpec]]:
    used = 0.0
    chosen: list[ColSpec] = []
    if anchor is not None:
        used += anchor.estimated_width
        chosen.append(anchor)

    leftovers: list[ColSpec] = []
    # iterate in pool order (already prio-then-original-pos)
    for c in pool:
        w = c.estimated_width
        if used + w <= budget or not chosen:
            chosen.append(c)
            used += w
        else:
            leftovers.append(c)

    # restore visual order: by user position
    chosen.sort(key=lambda c: c.pos)
    return PageGroup(columns=chosen, char_budget=budget, used_chars=used), leftovers


def plan_layout(
    *,
    columns: list[ColSpec],
    available_width_pt: float,
    smart_layout: bool = True,
    anchor_index: int | None = None,
    locale: str = "he",
) -> LayoutResult:
    explanations: list[str] = []
    base_font_size = _auto_font_size(len(columns), available_width_pt)
    budget = _char_budget(available_width_pt, base_font_size)

    if not columns:
        return LayoutResult(groups=[], explanations=[], anchor_index=None,
                            char_budget=budget, base_font_size=base_font_size)

    total = sum(c.estimated_width for c in columns)

    # Resolve anchor
    anchor: ColSpec | None = None
    if anchor_index is not None:
        for c in columns:
            if c.index == anchor_index:
                anchor = c
                anchor.is_anchor = True
                break

    # Single group fits trivially
    if total <= budget or not smart_layout:
        if not smart_layout:
            explanations.append(_t(locale,
                "פיצול חכם בוטל ידנית — כל העמודות מוצגות יחד.",
                "Smart layout disabled — all columns rendered together."))
        elif total <= budget:
            explanations.append(_t(locale,
                f"כל {len(columns)} העמודות נכנסות לרוחב הדף — אין צורך בפיצול.",
                f"All {len(columns)} columns fit within page width — no split needed."))
        return LayoutResult(
            groups=[PageGroup(columns=list(columns), char_budget=budget, used_chars=total)],
            explanations=explanations,
            anchor_index=anchor.index if anchor else None,
            char_budget=budget,
            base_font_size=base_font_size,
        )

    explanations.append(_t(locale,
        f"רוחב כל העמודות גדול מהדף — מופעל פיצול חכם לעמודי-קבוצות.",
        "Total column width exceeds page — smart split enabled."))

    # Sort pool by priority then by user position
    pool = [c for c in columns if not c.is_anchor]
    pool.sort(key=lambda c: (PRIORITY_RANK.get(c.priority, 1), c.pos))

    groups: list[PageGroup] = []
    while pool:
        grp, pool = _pack_one_group(pool, anchor, budget)
        groups.append(grp)
        if not pool:
            break

    # Explanations per column placement
    if anchor is not None:
        explanations.append(_t(locale,
            f"עמודת '{anchor.header}' שוכפלה בכל קבוצה כעוגן לזיהוי-צולב.",
            f"Anchor column '{anchor.header}' duplicated across all groups for cross-reference."))

    placement: dict[int, int] = {}  # col index -> group number (1-based)
    for gi, g in enumerate(groups, start=1):
        for c in g.columns:
            if c.is_anchor and gi > 1:
                continue  # don't re-explain anchor
            placement.setdefault(c.index, gi)

    # Single human summary line per group
    for gi, g in enumerate(groups, start=1):
        names = ", ".join(c.header for c in g.columns)
        explanations.append(_t(locale,
            f"עמודי-קבוצה {gi}: {names}",
            f"Page-group {gi}: {names}"))

    # Highlight columns demoted by priority
    demoted = [c for c in columns if not c.is_anchor and placement.get(c.index, 1) > 1 and c.priority == "low"]
    if demoted:
        names = ", ".join(c.header for c in demoted)
        explanations.append(_t(locale,
            f"עמודות בעדיפות נמוכה הועברו לעמודי-קבוצות מאוחרים: {names}.",
            f"Low-priority columns moved to later page-groups: {names}."))

    return LayoutResult(
        groups=groups,
        explanations=explanations,
        anchor_index=anchor.index if anchor else None,
        char_budget=budget,
        base_font_size=base_font_size,
    )


def _t(locale: str, he: str, en: str) -> str:
    return he if locale.startswith("he") else en


def build_columns(
    headers: list[str],
    column_indices: list[int],
    estimated_widths: dict[int, int],
    priorities: dict[int, str],
) -> list[ColSpec]:
    """Build ColSpec list for layout planning. headers list is parallel to column_indices."""
    out: list[ColSpec] = []
    for pos, (ci, h) in enumerate(zip(column_indices, headers)):
        out.append(ColSpec(
            index=ci,
            pos=pos,
            header=h or f"#{ci + 1}",
            estimated_width=estimated_widths.get(ci, max(8, len(h or "") + 2)),
            priority=priorities.get(ci, "medium"),
        ))
    return out


def slice_rows(rows: list[list[str]], column_positions_in_row: list[int]) -> list[list[str]]:
    """Pick a subset of columns from each row by their position in the user-selected list."""
    out: list[list[str]] = []
    for r in rows:
        out.append([r[i] if i < len(r) else "" for i in column_positions_in_row])
    return out
