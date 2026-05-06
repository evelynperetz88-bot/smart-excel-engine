from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any

Priority = Literal["high", "medium", "low"]
FilterOp = Literal["eq", "neq", "contains", "not_contains", "gt", "lt", "gte", "lte", "between", "is_empty", "not_empty"]


class FilterRule(BaseModel):
    column_index: int
    op: FilterOp
    value: Any | None = None
    value2: Any | None = None  # for between


class SheetExportSpec(BaseModel):
    sheet_name: str
    column_indices: list[int]
    priorities: dict[int, Priority] = Field(default_factory=dict)  # col_index -> priority
    filters: list[FilterRule] = Field(default_factory=list)
    skip_empty_rows: bool = True
    header_row: Optional[int] = None
    section_title: Optional[str] = None


class HeaderConfig(BaseModel):
    title: str = ""
    subtitle: str = ""
    logo_data_url: Optional[str] = None  # data:image/png;base64,...
    show_page_numbers: bool = True
    show_generated_date: bool = True


WatermarkPreset = Literal["none", "draft", "official", "custom"]
OutputMode = Literal["draft", "official", "court_ready"]


class WatermarkConfig(BaseModel):
    preset: WatermarkPreset = "none"
    text: str = ""           # used when preset == "custom" (or as override)
    opacity: float = 0.18    # 0..1
    color: str = "#888888"


def output_mode_defaults(mode: OutputMode | None) -> dict:
    """Map an output mode to (watermark_preset, pdf_a, header_style).
    'court_ready' is a Pro-only stricter variant of 'official'.
    """
    if mode == "draft":
        return {"watermark_preset": "draft", "pdf_a": False, "header_style": "standard"}
    if mode == "official":
        return {"watermark_preset": "none", "pdf_a": True, "header_style": "standard"}
    if mode == "court_ready":
        return {"watermark_preset": "none", "pdf_a": True, "header_style": "formal"}
    return {}


class ExportRequest(BaseModel):
    file_id: str
    sheets: list[SheetExportSpec]
    page_size: str = Field("A4", pattern="^(A4|A3|a4|a3)$")
    orientation: str = Field("portrait", pattern="^(portrait|landscape)$")
    margin_mm: float = 12
    rtl: bool = True
    locale: str = "he"
    header: HeaderConfig = Field(default_factory=HeaderConfig)
    smart_layout: bool = True
    anchor_column_index: Optional[int] = None  # repeated across page-groups for cross-ref
    explain: bool = True
    template_id: Optional[str] = None
    watermark: WatermarkConfig = Field(default_factory=WatermarkConfig)
    pdf_a: bool = False
    tier: Literal["free", "pro"] = "free"


class PreviewRequest(BaseModel):
    file_id: str
    sheets: list[SheetExportSpec]
    page_size: str = "A4"
    orientation: str = "portrait"
    margin_mm: float = 12
    rtl: bool = True
    locale: str = "he"
    header: HeaderConfig = Field(default_factory=HeaderConfig)
    smart_layout: bool = True
    anchor_column_index: Optional[int] = None
    row_limit: int = 80
    explain: bool = True
    template_id: Optional[str] = None
    watermark: WatermarkConfig = Field(default_factory=WatermarkConfig)
    pdf_a: bool = False
    tier: Literal["free", "pro"] = "free"


class AutoExportRequest(BaseModel):
    """One-Click smart export — only the file_id and the user's tier/locale are needed."""
    file_id: str
    locale: str = "he"
    tier: Literal["free", "pro"] = "free"
    document_title: Optional[str] = None
    document_subtitle: Optional[str] = None
    logo_data_url: Optional[str] = None
    watermark: WatermarkConfig = Field(default_factory=WatermarkConfig)
    pdf_a: bool = False
    output_mode: Optional[OutputMode] = None  # if set, overrides watermark + pdf_a
    row_limit: Optional[int] = None


class TemplateInfo(BaseModel):
    id: str
    name_he: str
    name_en: str
    description_he: str
    description_en: str
    page_size: str
    orientation: str
    rtl: bool
    smart_layout: bool
    priority_keywords: dict[str, list[str]]  # priority -> list of keyword stems
