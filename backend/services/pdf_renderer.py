"""PDF renderer that consumes the Smart Layout Engine output.

For each sheet × page-group it renders a Table; sheets are separated by hard page
breaks; page-groups are separated by hard page breaks too (so the visual order is:
[sheet1.group1] PB [sheet1.group2] PB [sheet2.group1] ...).
"""
from __future__ import annotations
import os
import re
import base64
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, A3, landscape, portrait
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame,
    Table, TableStyle, Paragraph, Spacer, PageBreak, Image,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT

try:
    from bidi.algorithm import get_display
except ImportError:  # pragma: no cover
    def get_display(text):
        return text

from .layout_engine import LayoutResult, PageGroup, ColSpec, slice_rows


HEBREW_FONT = "AppFont"
HEBREW_FONT_BOLD = "AppFont-Bold"
_FONT_REGISTERED = False


def _register_fonts() -> None:
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return
    # Allow override via env var (path to a TTF that supports Hebrew).
    override = os.environ.get("HEBREW_FONT_PATH")
    if override and os.path.exists(override):
        bold = os.environ.get("HEBREW_FONT_BOLD_PATH") or override
        pdfmetrics.registerFont(TTFont(HEBREW_FONT, override))
        pdfmetrics.registerFont(TTFont(HEBREW_FONT_BOLD, bold))
        _FONT_REGISTERED = True
        return

    candidates = [
        # Windows
        (r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\arialbd.ttf"),
        (r"C:\Windows\Fonts\tahoma.ttf", r"C:\Windows\Fonts\tahomabd.ttf"),
        (r"C:\Windows\Fonts\david.ttf", r"C:\Windows\Fonts\davidbd.ttf"),
        # Linux (Debian/Ubuntu — installed by the Dockerfile via fonts-dejavu / fonts-noto-core)
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
         "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
         "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        # macOS
        ("/System/Library/Fonts/Supplemental/Arial.ttf",
         "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
        ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ]
    for regular, bold in candidates:
        if os.path.exists(regular):
            pdfmetrics.registerFont(TTFont(HEBREW_FONT, regular))
            pdfmetrics.registerFont(TTFont(HEBREW_FONT_BOLD, bold if os.path.exists(bold) else regular))
            _FONT_REGISTERED = True
            return
    raise RuntimeError(
        "No Hebrew-capable TTF found. Install fonts-dejavu (Linux), Arial/Tahoma (Windows), "
        "or set HEBREW_FONT_PATH env var to a TTF path."
    )


_HEBREW_RE = re.compile(r"[֐-׿יִ-ﭏ]")


def _has_hebrew(s: str) -> bool:
    return bool(_HEBREW_RE.search(s or ""))


def _shape(text: str) -> str:
    if not text:
        return ""
    return get_display(text) if _has_hebrew(text) else text


def _pagesize(size: str, orientation: str):
    base = A4 if size.upper() == "A4" else A3
    return landscape(base) if orientation.lower() == "landscape" else portrait(base)


def _decode_logo(data_url: str | None) -> bytes | None:
    if not data_url or not data_url.startswith("data:"):
        return None
    try:
        _, b64 = data_url.split(",", 1)
        return base64.b64decode(b64)
    except Exception:
        return None


def _hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    h = (hex_color or "#888888").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return r, g, b
    except Exception:
        return 0.53, 0.53, 0.53


def _resolve_watermark(preset: str, text: str, locale: str) -> str:
    if preset == "draft":
        return "טיוטה" if locale.startswith("he") else "DRAFT"
    if preset == "official":
        return "רשמי" if locale.startswith("he") else "OFFICIAL"
    if preset == "custom":
        return (text or "").strip()
    return ""


class PDFBuilder:
    def __init__(
        self,
        *,
        page_size: str = "A4",
        orientation: str = "portrait",
        margin_mm: float = 12,
        rtl: bool = True,
        locale: str = "he",
        header_title: str = "",
        header_subtitle: str = "",
        logo_bytes: bytes | None = None,
        show_page_numbers: bool = True,
        show_generated_date: bool = True,
        watermark_preset: str = "none",
        watermark_text: str = "",
        watermark_opacity: float = 0.18,
        watermark_color: str = "#888888",
        pdf_a: bool = False,
        author: str = "Smart Excel Engine",
    ):
        _register_fonts()
        self.pagesize = _pagesize(page_size, orientation)
        self.margin = margin_mm * mm
        self.rtl = rtl
        self.locale = locale
        self.header_title = header_title
        self.header_subtitle = header_subtitle
        self.logo_bytes = logo_bytes
        self.show_page_numbers = show_page_numbers
        self.show_generated_date = show_generated_date
        self.pdf_a = pdf_a
        self.author = author
        self.watermark_text = _resolve_watermark(watermark_preset, watermark_text, locale)
        self.watermark_opacity = max(0.05, min(0.6, float(watermark_opacity)))
        self.watermark_color = watermark_color

        self._story: list = []
        self._buf = BytesIO()

        self.available_width = self.pagesize[0] - 2 * self.margin
        self.available_height = self.pagesize[1] - 2 * self.margin
        # leave room for header band
        self._header_height = (self._compute_header_height())
        self._content_height = self.available_height - self._header_height

    def _compute_header_height(self) -> float:
        h = 0
        if self.header_title:
            h += 16
        if self.header_subtitle:
            h += 12
        if self.logo_bytes:
            h = max(h, 24 * mm)
        if h > 0:
            h += 4 * mm
        return h

    def _para_styles(self, base_font_size: float):
        align = TA_RIGHT if self.rtl else TA_LEFT
        wrap = "RTL" if self.rtl else "CJK"
        return {
            "cell": ParagraphStyle(
                "cell", fontName=HEBREW_FONT, fontSize=base_font_size,
                leading=base_font_size * 1.25, alignment=align, wordWrap=wrap,
            ),
            "header_cell": ParagraphStyle(
                "header_cell", fontName=HEBREW_FONT_BOLD, fontSize=base_font_size + 1,
                leading=(base_font_size + 1) * 1.25, alignment=TA_CENTER,
                textColor=colors.whitesmoke, wordWrap=wrap,
            ),
            "section": ParagraphStyle(
                "section", fontName=HEBREW_FONT_BOLD, fontSize=12,
                alignment=TA_CENTER, spaceAfter=4, textColor=colors.HexColor("#1f4e79"),
            ),
            "explain": ParagraphStyle(
                "explain", fontName=HEBREW_FONT, fontSize=8,
                alignment=align, textColor=colors.HexColor("#666666"),
                wordWrap=wrap, leading=11,
            ),
        }

    def _shape_cell(self, value: str, style: ParagraphStyle) -> Paragraph:
        safe = (value or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Paragraph(_shape(safe).replace("\n", "<br/>"), style)

    def _column_widths(self, group_columns: list[ColSpec], rows: list[list[str]], font_size: float) -> list[float]:
        n = len(group_columns)
        if n == 0:
            return []
        char_w = font_size * 0.55
        sample_rows = rows[:200]
        raw: list[float] = []
        for i, col in enumerate(group_columns):
            max_chars = len(col.header or "")
            for r in sample_rows:
                if i < len(r):
                    cell = r[i] or ""
                    for line in (cell.splitlines() or [cell]):
                        if len(line) > max_chars:
                            max_chars = len(line)
            max_chars = min(max_chars, 60)
            raw.append(max(8, max_chars + 2) * char_w)

        total = sum(raw)
        if total <= 0:
            return [self.available_width / n] * n
        scale = self.available_width / total
        widths = [w * scale for w in raw]

        min_w = 16 * mm
        deficit = 0.0
        for i, w in enumerate(widths):
            if w < min_w:
                deficit += min_w - w
                widths[i] = min_w
        if deficit > 0:
            donors = [(i, widths[i]) for i in range(n) if widths[i] > min_w * 1.2]
            donor_total = sum(w for _, w in donors)
            if donor_total > 0:
                for i, w in donors:
                    widths[i] -= deficit * (w / donor_total)
        return widths

    def _build_one_table(self, group: PageGroup, row_subset: list[list[str]], font_size: float) -> Table:
        styles = self._para_styles(font_size)
        cols = list(group.columns)
        rows = [list(r) for r in row_subset]

        # RTL: reverse visual column order so the source's first column appears on the right
        if self.rtl:
            cols = list(reversed(cols))
            rows = [list(reversed(r)) for r in rows]

        col_widths = self._column_widths(cols, rows, font_size)

        table_data: list[list[Paragraph]] = []
        table_data.append([self._shape_cell(c.header, styles["header_cell"]) for c in cols])
        for r in rows:
            padded = list(r) + [""] * (len(cols) - len(r))
            table_data.append([self._shape_cell(c, styles["cell"]) for c in padded[: len(cols)]])

        t = Table(table_data, colWidths=col_widths, repeatRows=1, splitByRow=True)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTNAME", (0, 0), (-1, 0), HEBREW_FONT_BOLD),
            ("FONTNAME", (0, 1), (-1, -1), HEBREW_FONT),
            ("FONTSIZE", (0, 0), (-1, 0), font_size + 1),
            ("FONTSIZE", (0, 1), (-1, -1), font_size),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("ALIGN", (0, 1), (-1, -1), "RIGHT" if self.rtl else "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bfbfbf")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f6fb")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        return t

    def add_section(
        self,
        *,
        section_title: str | None,
        layout: LayoutResult,
        all_rows: list[list[str]],
        column_indices_in_row: list[int],  # for each layout column, position in `all_rows`
    ) -> None:
        styles = self._para_styles(layout.base_font_size)

        if section_title:
            self._story.append(Paragraph(_shape(section_title), styles["section"]))
            self._story.append(Spacer(1, 2 * mm))

        for gi, group in enumerate(layout.groups):
            if gi > 0:
                self._story.append(PageBreak())
            # slice rows to group columns
            positions_in_row = [column_indices_in_row[c.pos] for c in group.columns]
            sliced = slice_rows(all_rows, positions_in_row)

            if len(layout.groups) > 1:
                count_text = (
                    f"קבוצת עמודים {gi + 1} מתוך {len(layout.groups)}"
                    if self.locale.startswith("he")
                    else f"Page-group {gi + 1} of {len(layout.groups)}"
                )
                self._story.append(Paragraph(_shape(count_text), styles["explain"]))
                self._story.append(Spacer(1, 2 * mm))

            self._story.append(self._build_one_table(group, sliced, layout.base_font_size))

        if layout.explanations:
            self._story.append(Spacer(1, 4 * mm))
            label = "הסבר פריסה:" if self.locale.startswith("he") else "Layout notes:"
            self._story.append(Paragraph(_shape(label), styles["section"]))
            for line in layout.explanations:
                self._story.append(Paragraph(_shape("• " + line), styles["explain"]))

    def add_page_break(self) -> None:
        self._story.append(PageBreak())

    def _draw_watermark(self, canvas):
        if not self.watermark_text:
            return
        canvas.saveState()
        try:
            canvas.setFillAlpha(self.watermark_opacity)
        except Exception:
            pass
        r, g, b = _hex_to_rgb01(self.watermark_color)
        canvas.setFillColorRGB(r, g, b)
        # size: roughly proportional to page diagonal
        diag = (self.pagesize[0] ** 2 + self.pagesize[1] ** 2) ** 0.5
        # width per character at sz: 0.55 * sz. We want text width ≈ diag * 0.7
        approx_chars = max(4, len(self.watermark_text))
        size = min(160, max(40, (diag * 0.7) / (approx_chars * 0.55)))
        canvas.setFont(HEBREW_FONT_BOLD, size)
        canvas.translate(self.pagesize[0] / 2, self.pagesize[1] / 2)
        canvas.rotate(35)
        text = _shape(self.watermark_text)
        tw = canvas.stringWidth(text, HEBREW_FONT_BOLD, size)
        canvas.drawString(-tw / 2, -size / 2, text)
        canvas.restoreState()

    def _on_page(self, canvas, doc):
        # Watermark goes UNDER the table content — draw before saveState/header
        self._draw_watermark(canvas)
        canvas.saveState()
        # Header band
        x_left = self.margin
        x_right = self.pagesize[0] - self.margin
        y_top = self.pagesize[1] - self.margin
        cur_y = y_top

        if self.logo_bytes:
            try:
                from reportlab.lib.utils import ImageReader
                img = ImageReader(BytesIO(self.logo_bytes))
                logo_w = 22 * mm
                logo_h = 22 * mm
                if self.rtl:
                    canvas.drawImage(img, x_right - logo_w, cur_y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
                else:
                    canvas.drawImage(img, x_left, cur_y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
            except Exception:
                pass

        if self.header_title:
            canvas.setFont(HEBREW_FONT_BOLD, 14)
            text = _shape(self.header_title)
            tw = canvas.stringWidth(text, HEBREW_FONT_BOLD, 14)
            canvas.drawString((self.pagesize[0] - tw) / 2, cur_y - 10, text)
        if self.header_subtitle:
            canvas.setFont(HEBREW_FONT, 10)
            text = _shape(self.header_subtitle)
            tw = canvas.stringWidth(text, HEBREW_FONT, 10)
            canvas.drawString((self.pagesize[0] - tw) / 2, cur_y - 24, text)

        # Footer
        canvas.setFont(HEBREW_FONT, 8)
        canvas.setFillColor(colors.HexColor("#666666"))
        if self.show_generated_date:
            stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            label = f"נוצר: {stamp}" if self.locale.startswith("he") else f"Generated: {stamp}"
            canvas.drawString(x_left, self.margin / 2, _shape(label))
        if self.show_page_numbers:
            page = canvas.getPageNumber()
            total = getattr(doc, "_total_pages", "?")
            label = f"עמוד {page} מתוך {total}" if self.locale.startswith("he") else f"Page {page} of {total}"
            text = _shape(label)
            tw = canvas.stringWidth(text, HEBREW_FONT, 8)
            canvas.drawString(x_right - tw, self.margin / 2, text)
        canvas.restoreState()

    def build(self) -> bytes:
        # Two-pass to get total page count
        def make_doc(buf):
            doc = BaseDocTemplate(
                buf, pagesize=self.pagesize,
                leftMargin=self.margin, rightMargin=self.margin,
                topMargin=self.margin + self._header_height,
                bottomMargin=self.margin + 6 * mm,
                title=self.header_title or "Excel Export",
                author=self.author,
                subject=self.header_subtitle or "Generated by Smart Excel Engine",
                keywords="excel,export,smart-layout,bidi,rtl",
                producer=("Smart Excel Engine — PDF/A best-effort" if self.pdf_a
                          else "Smart Excel Engine"),
                creator="Smart Excel Engine",
            )
            frame = Frame(
                self.margin, self.margin + 6 * mm,
                self.available_width,
                self.available_height - self._header_height - 6 * mm,
                id="content", showBoundary=0,
            )
            doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=self._on_page)])
            return doc

        # Pass 1 — count pages
        first = BytesIO()
        doc1 = make_doc(first)
        from copy import deepcopy
        doc1.build(deepcopy(self._story))
        total_pages = doc1.page

        # Pass 2 — render with known total
        doc2 = make_doc(self._buf)
        doc2._total_pages = total_pages
        doc2.build(self._story)
        return self._buf.getvalue()


def render_pdf(
    *,
    sections: list[dict],
    page_size: str,
    orientation: str,
    margin_mm: float,
    rtl: bool,
    locale: str,
    header_title: str = "",
    header_subtitle: str = "",
    logo_data_url: str | None = None,
    show_page_numbers: bool = True,
    show_generated_date: bool = True,
    watermark_preset: str = "none",
    watermark_text: str = "",
    watermark_opacity: float = 0.18,
    watermark_color: str = "#888888",
    pdf_a: bool = False,
) -> bytes:
    builder = PDFBuilder(
        page_size=page_size, orientation=orientation, margin_mm=margin_mm,
        rtl=rtl, locale=locale,
        header_title=header_title, header_subtitle=header_subtitle,
        logo_bytes=_decode_logo(logo_data_url),
        show_page_numbers=show_page_numbers,
        show_generated_date=show_generated_date,
        watermark_preset=watermark_preset, watermark_text=watermark_text,
        watermark_opacity=watermark_opacity, watermark_color=watermark_color,
        pdf_a=pdf_a,
    )
    for i, s in enumerate(sections):
        if i > 0:
            builder.add_page_break()
        builder.add_section(
            section_title=s.get("title"),
            layout=s["layout"],
            all_rows=s["rows"],
            column_indices_in_row=s["positions_in_row"],
        )
    return builder.build()
