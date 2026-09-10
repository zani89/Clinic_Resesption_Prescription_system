"""
print_slip.py — Prescription header generator and printer for Alees Medical Center.

Prints only the required header:
1. Doctor Name (Teal)
2. Qualifications & Specialization
3. Patient Info Row: Name | Gender | Age | [Token #: N] | Date
With support for configurable font styles, font sizes, horizontal allocations, and reserved pre-printed letterhead areas.
"""

import os
import sys
from datetime import datetime
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewDialog
from PySide6.QtGui import QPainter, QFont, QPageSize, QPageLayout, QColor, QPen, QBrush, QImage, QPixmap
from PySide6.QtCore import Qt, QRectF
from models.slip_config import load_slip_config

# ─────────────────────────────────────────────────────────────────────────────
# STYLING CONSTANTS (Matching Reference Design)
# ─────────────────────────────────────────────────────────────────────────────
TEAL_COLOR       = "#00677F"   # Primary Brand Teal
DARK_SLATE_COLOR = "#1E293B"   # Dark Text for Labels / Degrees
GRAY_TEXT_COLOR  = "#475569"   # Secondary Text for Specialization
WHITE_COLOR      = "#FFFFFF"

# Default Doctor Info fallback
DEFAULT_DEGREES = "MBBS DCH DCN JAPAN"
DEFAULT_SPECIALIZATION = "CONSULTANT CHILD SPECIALIST PEDIATRIC NEUROPHYSICIAN"

# Output directory for saved PDFs
if getattr(sys, 'frozen', False):
    OUTPUT_DIR = os.path.join(os.path.dirname(sys.executable), "printed_slips")
else:
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "printed_slips")
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# DATA EXTRACTION & FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _get_val(obj, key, default=""):
    """Safely extracts a field from a dataclass object, dict, or row."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _format_date(date_str: str) -> str:
    """Formats date to MM-DD-YYYY to match the reference format (e.g. 08-16-2026)."""
    if not date_str:
        return datetime.now().strftime("%m-%d-%Y")
    try:
        if "-" in str(date_str):
            parts = str(date_str).split("-")
            if len(parts) == 3 and len(parts[0]) == 4:  # YYYY-MM-DD -> MM-DD-YYYY
                return f"{parts[1]}-{parts[2]}-{parts[0]}"
    except Exception:
        pass
    return str(date_str)


def _extract_slip_data(patient=None, doctor=None, visit=None) -> dict:
    """Consolidates and formats all fields needed for the prescription header."""
    p_name = str(_get_val(patient, "name", "SIAL")).strip().upper() if patient else "SIAL"
    
    raw_gender = _get_val(patient, "gender", "Male") if patient else "Male"
    gender = str(raw_gender).capitalize() if raw_gender else "Male"
    
    raw_age = _get_val(patient, "age", "15") if patient else "15"
    age = f"{raw_age} y" if raw_age else "15 y"
    
    # Visit & Token
    raw_date = _get_val(visit, "visit_date", "") if visit else ""
    date_str = _format_date(raw_date)
    
    token_num = _get_val(visit, "token_number") or _get_val(visit, "token_no") or 7 if visit else 7
    
    # Doctor Info — always pulled from the DB doctor object
    if doctor:
        raw_doc_name = str(_get_val(doctor, "name", "")).strip().upper()
        doc_spec      = str(_get_val(doctor, "specialization", "")).strip().upper()
        # Try degrees field if it exists on the object (future-proof)
        doc_degrees   = str(_get_val(doctor, "degrees", "")).strip().upper()
    else:
        raw_doc_name  = ""
        doc_spec      = ""
        doc_degrees   = ""

    # Ensure "DR." prefix
    if raw_doc_name and not raw_doc_name.startswith("DR.") and not raw_doc_name.startswith("DR "):
        doc_display_name = f"DR. {raw_doc_name}"
    else:
        doc_display_name = raw_doc_name or "DR. DOCTOR"

    # Split long names onto two lines
    words = doc_display_name.split()
    if len(words) >= 4:
        mid = len(words) // 2
        doc_lines = [" ".join(words[:mid]), " ".join(words[mid:])]
    else:
        doc_lines = [doc_display_name]

    # Degrees: use DB value if available, else config default
    degrees = doc_degrees if doc_degrees else DEFAULT_DEGREES

    # Specialization: use DB value if available, else fallback default
    if doc_spec:
        specialization = f"CONSULTANT {doc_spec}" if not doc_spec.startswith("CONSULTANT") else doc_spec
    else:
        specialization = DEFAULT_SPECIALIZATION

    return {
        "doc_lines": doc_lines,
        "degrees": degrees,
        "specialization": specialization,
        "patient_name": p_name,
        "gender": gender,
        "age": age,
        "token_number": token_num,
        "token_str": f"Token #: {token_num}",
        "date_str": date_str
    }


def _make_qfont(family: str, size: float, style_str: str = "Regular") -> QFont:
    """Helper to construct QFont with size and font style (Regular, Bold, Italic, Bold Italic)."""
    style_lower = (style_str or "Regular").lower()
    is_bold = "bold" in style_lower
    is_italic = "italic" in style_lower
    
    weight = QFont.Weight.Bold if is_bold else QFont.Weight.Normal
    font = QFont(family, int(size), weight)
    font.setItalic(is_italic)
    return font


_PAGE_DIMENSIONS_MM = {
    "A5":     (148.0, 210.0),
    "A4":     (210.0, 297.0),
    "Letter": (215.9, 279.4),
    "Legal":  (215.9, 355.6),
}


def _get_page_dimensions_mm(config: dict) -> tuple[float, float]:
    """Returns (width_mm, height_mm) based on 'page_size' and 'page_orientation' in config."""
    if not config:
        return (148.0, 210.0)
    size_str = str(config.get("page_size", "A5")).strip()
    orientation_str = str(config.get("page_orientation", "Portrait")).strip()
    
    if size_str == "Custom":
        w = float(config.get("custom_page_width_mm", 148.0))
        h = float(config.get("custom_page_height_mm", 210.0))
    else:
        w, h = _PAGE_DIMENSIONS_MM.get(size_str, (148.0, 210.0))
        
    if orientation_str == "Landscape":
        return (max(w, h), min(w, h))
    return (min(w, h), max(w, h))


# ─────────────────────────────────────────────────────────────────────────────
# PYSIDE6 / QT RENDERING ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def render_slip_on_painter(painter: QPainter, dpi: int, patient=None, doctor=None, visit=None, config: dict = None, is_preview: bool = False):
    """
    Renders the prescription header dynamically using configured font styles, font sizes,
    reserved pre-printed area, allocations, and margins.
    """
    if config is None:
        config = load_slip_config()

    def mm2px(mm_val: float) -> int:
        return int(float(mm_val) * dpi / 25.4)

    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)

    data = _extract_slip_data(patient, doctor, visit)

    font_fam = config.get("font_family", "Arial")
    page_w_mm, _ = _get_page_dimensions_mm(config)
    page_w_px = mm2px(page_w_mm)
    margin_left = mm2px(config.get("margin_left_mm", 12.0))
    margin_right = mm2px(config.get("margin_right_mm", config.get("margin_left_mm", 12.0)))
    x_left = margin_left
    x_right = page_w_px - margin_right

    top_margin_px = mm2px(config.get("top_margin_mm", 14.0))
    reserved_top_mm = float(config.get("reserved_top_area_mm", 0.0))
    reserved_top_px = mm2px(reserved_top_mm)

    # ── Reserved Letterhead Guide (Rendered only on preview if enabled) ─────
    if is_preview and reserved_top_mm > 0 and config.get("show_reserved_area_guide", True):
        res_rect = QRectF(0, 0, page_w_px, reserved_top_px)
        painter.fillRect(res_rect, QColor(241, 245, 249, 180)) # Light soft slate tint
        painter.setPen(QPen(QColor("#94A3B8"), 1, Qt.DashLine))
        painter.drawRect(res_rect)
        
        guide_font = QFont(font_fam, 8, QFont.Weight.Normal)
        guide_font.setItalic(True)
        painter.setFont(guide_font)
        painter.setPen(QColor("#64748B"))
        painter.drawText(
            res_rect, Qt.AlignCenter,
            f"🏛 Reserved Pre-printed Letterhead Area ({reserved_top_mm:g} mm)"
        )

    cur_y = top_margin_px + reserved_top_px

    # 1. Doctor Name
    doc_font_size = float(config.get("doc_name_font_size", 15.0))
    doc_style = config.get("doc_name_font_style", "Bold")
    painter.setFont(_make_qfont(font_fam, doc_font_size, doc_style))
    painter.setPen(QColor(TEAL_COLOR))

    line_spacing = config.get("doc_name_line_spacing_mm", 6.5)
    for line in data["doc_lines"]:
        painter.drawText(margin_left, cur_y + mm2px(5.0), line)
        cur_y += mm2px(line_spacing)

    cur_y += mm2px(1.0)

    # 2. Degrees / Qualifications
    deg_font_size = float(config.get("degrees_font_size", 8.5))
    deg_style = config.get("degrees_font_style", "Bold")
    painter.setFont(_make_qfont(font_fam, deg_font_size, deg_style))
    painter.setPen(QColor(DARK_SLATE_COLOR))
    painter.drawText(margin_left, cur_y + mm2px(3.5), data["degrees"])
    cur_y += mm2px(config.get("degrees_spacing_mm", 5.0))

    # 3. Specialization
    spec_font_size = float(config.get("specialization_font_size", 7.5))
    spec_style = config.get("specialization_font_style", "Regular")
    painter.setFont(_make_qfont(font_fam, spec_font_size, spec_style))
    painter.setPen(QColor(GRAY_TEXT_COLOR))
    painter.drawText(margin_left, cur_y + mm2px(3.0), data["specialization"])
    
    doc_bottom_gap = config.get("doctor_bottom_spacing_mm", 8.5)
    cur_y += mm2px(doc_bottom_gap)

    # 4. Patient Information Row: Name | Gender | Age | [Token #: N] | Date
    pat_font_size = float(config.get("patient_font_size", 9.0))
    pat_lbl_style = config.get("patient_label_style", "Bold")
    pat_val_style = config.get("patient_value_style", "Regular")
    
    font_lbl = _make_qfont(font_fam, pat_font_size, pat_lbl_style)
    font_val = _make_qfont(font_fam, pat_font_size, pat_val_style)
    
    y_offset = float(config.get("patient_y_offset_mm", 0.0))
    line_pad_top = float(config.get("patient_line_padding_top_mm", 5.5))
    line_pad_bottom = float(config.get("patient_line_padding_bottom_mm", 3.5))

    top_line_y = cur_y + mm2px(y_offset)
    row_baseline = top_line_y + mm2px(line_pad_top)
    bottom_line_y = row_baseline + mm2px(line_pad_bottom)

    # 4a. Measure width of each item for layout
    painter.setFont(font_lbl)
    w_lbl_name = painter.fontMetrics().horizontalAdvance("Name: ")
    w_lbl_gender = painter.fontMetrics().horizontalAdvance("Gender: ")
    w_lbl_age = painter.fontMetrics().horizontalAdvance("Age: ")
    w_lbl_date = painter.fontMetrics().horizontalAdvance("Date: ")

    painter.setFont(font_val)
    w_val_name = painter.fontMetrics().horizontalAdvance(data["patient_name"])
    w_val_gender = painter.fontMetrics().horizontalAdvance(data["gender"])
    w_val_age = painter.fontMetrics().horizontalAdvance(data["age"])
    w_val_date = painter.fontMetrics().horizontalAdvance(data["date_str"])

    w1 = w_lbl_name + w_val_name
    w2 = w_lbl_gender + w_val_gender
    w3 = w_lbl_age + w_val_age

    tok_font_size = float(config.get("token_font_size", 9.0))
    tok_style = config.get("token_font_style", "Bold")
    font_tok = _make_qfont(font_fam, tok_font_size, tok_style)
    painter.setFont(font_tok)
    tok_text = data["token_str"]
    pad_px = mm2px(float(config.get("token_badge_padding_mm", 3.5)))
    w_tok_text = painter.fontMetrics().horizontalAdvance(tok_text)
    w4 = w_tok_text + pad_px if config.get("show_token_badge", True) else w_tok_text

    w5 = w_lbl_date + w_val_date

    # 4b. Position items: auto-fit to span across page or use manual X offsets
    if config.get("auto_fit_patient_row", True):
        avail_w = x_right - x_left
        total_items_w = w1 + w2 + w3 + w4 + w5
        gap = (avail_w - total_items_w) / 4.0
        min_gap = mm2px(3.0)
        if gap < min_gap:
            gap = min_gap
        x_name = x_left
        x_gender = int(x_name + w1 + gap)
        x_age = int(x_gender + w2 + gap)
        x_token = int(x_age + w3 + gap)
        if avail_w >= total_items_w + 4 * min_gap:
            x_date = int(x_right - w5)
        else:
            x_date = int(x_token + w4 + gap)
    else:
        x_name = mm2px(config.get("name_x_mm", 12.0))
        x_gender = mm2px(config.get("gender_x_mm", 44.0))
        x_age = mm2px(config.get("age_x_mm", 68.0))
        x_token = mm2px(config.get("token_x_mm", 88.0))
        x_date = mm2px(config.get("date_x_mm", 112.0))

    # 4c. Draw top and bottom divider lines enclosing patient details
    if config.get("show_patient_lines", True):
        line_color_str = config.get("patient_line_color", TEAL_COLOR)
        line_thickness = float(config.get("patient_line_thickness", 1.0))
        lines_style = config.get("patient_lines_style", "Single")
        lines_align = str(config.get("patient_line_alignment", "Full Width"))

        if "Match Content" in lines_align:
            line_x_start = x_name
            line_x_end = x_date + w5
        elif "Compact Inset" in lines_align:
            line_x_start = x_left + mm2px(10.0)
            line_x_end = x_right - mm2px(10.0)
        else:  # "Full Width"
            line_x_start = x_left
            line_x_end = x_right

        pen = QPen(QColor(line_color_str))
        pen_width = max(1.0, float(mm2px(0.35 * line_thickness)))
        pen.setWidthF(pen_width)
        painter.setPen(pen)

        painter.drawLine(line_x_start, int(top_line_y), line_x_end, int(top_line_y))
        painter.drawLine(line_x_start, int(bottom_line_y), line_x_end, int(bottom_line_y))

        if lines_style == "Double":
            offset_px = max(2, mm2px(1.2))
            painter.drawLine(line_x_start, int(top_line_y - offset_px), line_x_end, int(top_line_y - offset_px))
            painter.drawLine(line_x_start, int(bottom_line_y + offset_px), line_x_end, int(bottom_line_y + offset_px))

    # 4d. Draw patient details
    # Name: <NAME>
    painter.setFont(font_lbl)
    painter.setPen(QColor(DARK_SLATE_COLOR))
    painter.drawText(x_name, row_baseline, "Name: ")
    painter.setFont(font_val)
    painter.drawText(x_name + w_lbl_name, row_baseline, data["patient_name"])

    # Gender: <GENDER>
    painter.setFont(font_lbl)
    painter.drawText(x_gender, row_baseline, "Gender: ")
    painter.setFont(font_val)
    painter.drawText(x_gender + w_lbl_gender, row_baseline, data["gender"])

    # Age: <AGE>
    painter.setFont(font_lbl)
    painter.drawText(x_age, row_baseline, "Age: ")
    painter.setFont(font_val)
    painter.drawText(x_age + w_lbl_age, row_baseline, data["age"])

    # Token Badge: [Token #: N]
    painter.setFont(font_tok)
    h_mm = float(config.get("token_badge_height_mm", 5.2))
    bh = mm2px(h_mm)
    badge_rect = QRectF(x_token, row_baseline - bh + mm2px(1.0), w4, bh)

    if config.get("show_token_badge", True):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(TEAL_COLOR)))
        painter.drawRect(badge_rect)
        painter.setPen(QColor(WHITE_COLOR))
        painter.drawText(badge_rect, Qt.AlignCenter, tok_text)
    else:
        painter.setPen(QColor(TEAL_COLOR))
        painter.drawText(x_token, row_baseline, tok_text)

    # Date: <DATE>
    painter.setFont(font_lbl)
    painter.setPen(QColor(DARK_SLATE_COLOR))
    painter.drawText(x_date, row_baseline, "Date: ")
    painter.setFont(font_val)
    painter.drawText(x_date + w_lbl_date, row_baseline, data["date_str"])

    # 5. Vertical Divider Line on the Left 1/3rd of the Page
    if config.get("show_vertical_line", True):
        vert_align = str(config.get("vertical_line_alignment", "Left 1/3rd (33.3%)"))
        if "1/4" in vert_align or "25%" in vert_align:
            vert_ratio = 0.25
        elif "30%" in vert_align:
            vert_ratio = 0.30
        elif "1/3" in vert_align or "33" in vert_align:
            vert_ratio = 0.333
        elif "2/5" in vert_align or "40%" in vert_align:
            vert_ratio = 0.40
        elif "Center" in vert_align or "50%" in vert_align:
            vert_ratio = 0.50
        else:
            vert_ratio = float(config.get("vertical_line_ratio", 0.333))

        x_vert = int(x_left + (x_right - x_left) * vert_ratio)

        y_vert_start = int(bottom_line_y)
        if config.get("show_patient_lines", True) and config.get("patient_lines_style", "Single") == "Double":
            y_vert_start += max(2, mm2px(1.2))

        bottom_margin_mm = float(config.get("bottom_margin_mm", 15.0))
        bottom_margin_px = mm2px(bottom_margin_mm)
        _, page_h_mm = _get_page_dimensions_mm(config)
        page_h_px = mm2px(page_h_mm)

        dev_h = painter.device().height() if painter.device() else page_h_px
        y_vert_end = min(page_h_px - bottom_margin_px, dev_h - mm2px(4.0))

        if y_vert_end > y_vert_start:
            vert_color = config.get("vertical_line_color", config.get("patient_line_color", TEAL_COLOR))
            vert_thick = float(config.get("vertical_line_thickness", config.get("patient_line_thickness", 1.0)))

            pen_v = QPen(QColor(vert_color))
            pen_v.setWidthF(max(1.0, float(mm2px(0.35 * vert_thick))))
            painter.setPen(pen_v)
            painter.drawLine(x_vert, y_vert_start, x_vert, int(y_vert_end))

            # Optional Rx symbol to the right of the vertical divider line
            if config.get("show_rx_symbol", True):
                rx_font = QFont("Times New Roman" if "times" in font_fam.lower() else font_fam, 14, QFont.Weight.Bold)
                rx_font.setItalic(True)
                painter.setFont(rx_font)
                painter.setPen(QColor(vert_color))
                painter.drawText(x_vert + mm2px(4.0), y_vert_start + mm2px(7.5), "℞")


# ─────────────────────────────────────────────────────────────────────────────
# PAGE SIZE HELPER
# ─────────────────────────────────────────────────────────────────────────────
_PAGE_SIZE_MAP = {
    "A5":     QPageSize.PageSizeId.A5,
    "A4":     QPageSize.PageSizeId.A4,
    "Letter": QPageSize.PageSizeId.Letter,
    "Legal":  QPageSize.PageSizeId.Legal,
}


def _get_page_size(config: dict) -> QPageSize:
    """Returns a QPageSize from the config 'page_size' key."""
    size_str = str(config.get("page_size", "A5")).strip()
    if size_str == "Custom":
        from PySide6.QtCore import QSizeF
        w = float(config.get("custom_page_width_mm", 148.0))
        h = float(config.get("custom_page_height_mm", 210.0))
        return QPageSize(QSizeF(w, h), QPageSize.Unit.Millimeter)
    page_id = _PAGE_SIZE_MAP.get(size_str, QPageSize.PageSizeId.A5)
    return QPageSize(page_id)


def apply_page_settings(printer: QPrinter, config: dict):
    """Applies page size and orientation from config to a QPrinter instance."""
    printer.setPageSize(_get_page_size(config))
    orientation_str = str(config.get("page_orientation", "Portrait")).strip()
    if orientation_str == "Landscape":
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
    else:
        printer.setPageOrientation(QPageLayout.Orientation.Portrait)


def _render_slip_qt(printer: QPrinter, patient=None, doctor=None, visit=None, config: dict = None):
    """
    Renders the exact prescription header onto QPrinter using PySide6 QPainter.
    """
    if config:
        apply_page_settings(printer, config)
    painter = QPainter(printer)
    dpi = printer.resolution()
    render_slip_on_painter(painter, dpi, patient, doctor, visit, config, is_preview=False)
    painter.end()


def render_preview_pixmap(config: dict = None, patient=None, doctor=None, visit=None, target_width: int = 700) -> QPixmap:
    """
    Renders a crisp raster preview of the prescription slip header for UI preview widgets.
    """
    if config is None:
        config = load_slip_config()

    page_w_mm, _ = _get_page_dimensions_mm(config)
    dpi = 150
    w_px = int(page_w_mm * dpi / 25.4)
    reserved_top_mm = float(config.get("reserved_top_area_mm", 0.0))
    h_mm = 85.0 + reserved_top_mm
    h_px = int(h_mm * dpi / 25.4)

    img = QImage(w_px, h_px, QImage.Format.Format_ARGB32)
    img.fill(QColor("#FFFFFF"))

    painter = QPainter(img)
    render_slip_on_painter(painter, dpi, patient, doctor, visit, config, is_preview=True)
    
    painter.setPen(QPen(QColor("#E2E8F0"), 1, Qt.DashLine))
    painter.drawLine(0, h_px - 2, w_px, h_px - 2)
    painter.end()

    pix = QPixmap.fromImage(img)
    if target_width and target_width != w_px:
        return pix.scaledToWidth(target_width, Qt.SmoothTransformation)
    return pix


def print_slip(patient=None, doctor=None, visit=None, show_preview: bool = True, config: dict = None):
    """
    Opens PrescriptionPrintDialog (with embedded real-time font and allocation adjustments)
    or prints directly using the configured page size.
    """
    if show_preview:
        from ui.prescription_print_dialog import PrescriptionPrintDialog
        dialog = PrescriptionPrintDialog(patient=patient, doctor=doctor, visit=visit)
        dialog.exec()
    else:
        if config is None:
            config = load_slip_config()
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        apply_page_settings(printer, config)
        printer.setFullPage(True)
        _render_slip_qt(printer, patient, doctor, visit, config)


# ─────────────────────────────────────────────────────────────────────────────
# REPORTLAB PDF GENERATION & PRINTING
# ─────────────────────────────────────────────────────────────────────────────
def _get_reportlab_font(family: str, style_str: str) -> str:
    """Maps configured font family and style to standard PDF fonts."""
    style_lower = (style_str or "Regular").lower()
    is_bold = "bold" in style_lower
    is_italic = "italic" in style_lower
    
    if "times" in family.lower():
        if is_bold and is_italic: return "Times-BoldItalic"
        if is_bold: return "Times-Bold"
        if is_italic: return "Times-Italic"
        return "Times-Roman"
    elif "courier" in family.lower():
        if is_bold and is_italic: return "Courier-BoldOblique"
        if is_bold: return "Courier-Bold"
        if is_italic: return "Courier-Oblique"
        return "Courier"
    else: # Helvetica / Arial
        if is_bold and is_italic: return "Helvetica-BoldOblique"
        if is_bold: return "Helvetica-Bold"
        if is_italic: return "Helvetica-Oblique"
        return "Helvetica"


def generate_prescription_pdf(patient=None, doctor=None, visit=None, config: dict = None) -> str:
    """
    Generates a PDF matching the exact prescription header layout using active config and paper settings.
    """
    if config is None:
        config = load_slip_config()

    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor

    pw_mm, ph_mm = _get_page_dimensions_mm(config)
    pw = pw_mm * mm
    ph = ph_mm * mm
    data = _extract_slip_data(patient, doctor, visit)
    
    filename = f"slip_token{data['token_number']}_{data['date_str']}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(filepath, pagesize=(pw, ph))
    
    font_fam = config.get("font_family", "Arial")
    margin_left = float(config.get("margin_left_mm", 12.0)) * mm
    margin_right = float(config.get("margin_right_mm", config.get("margin_left_mm", 12.0))) * mm
    x_left = margin_left
    x_right = pw - margin_right

    top_margin = float(config.get("top_margin_mm", 14.0)) * mm
    reserved_top = float(config.get("reserved_top_area_mm", 0.0)) * mm
    
    cur_y = ph - (top_margin + reserved_top)
    
    # 1. Doctor Name
    doc_size = float(config.get("doc_name_font_size", 15.0))
    doc_style = config.get("doc_name_font_style", "Bold")
    doc_line_spacing = float(config.get("doc_name_line_spacing_mm", 6.5))
    c.setFont(_get_reportlab_font(font_fam, doc_style), doc_size)
    c.setFillColor(HexColor(TEAL_COLOR))
    for line in data["doc_lines"]:
        cur_y -= (doc_line_spacing - 1.0) * mm
        c.drawString(margin_left, cur_y, line)
        
    cur_y -= 2.0 * mm
    
    # 2. Degrees
    deg_size = float(config.get("degrees_font_size", 8.5))
    deg_style = config.get("degrees_font_style", "Bold")
    deg_spacing = float(config.get("degrees_spacing_mm", 5.0))
    c.setFont(_get_reportlab_font(font_fam, deg_style), deg_size)
    c.setFillColor(HexColor(DARK_SLATE_COLOR))
    cur_y -= (deg_spacing - 1.0) * mm
    c.drawString(margin_left, cur_y, data["degrees"])
    
    # 3. Specialization
    spec_size = float(config.get("specialization_font_size", 7.5))
    spec_style = config.get("specialization_font_style", "Regular")
    c.setFont(_get_reportlab_font(font_fam, spec_style), spec_size)
    c.setFillColor(HexColor(GRAY_TEXT_COLOR))
    cur_y -= 3.5 * mm
    c.drawString(margin_left, cur_y, data["specialization"])
    
    # 4. Patient Information Row
    doc_bottom_gap = float(config.get("doctor_bottom_spacing_mm", 8.5))
    cur_y -= (doc_bottom_gap - 1.0) * mm
    pat_y_offset = float(config.get("patient_y_offset_mm", 0.0)) * mm
    
    line_pad_top = float(config.get("patient_line_padding_top_mm", 5.5)) * mm
    line_pad_bottom = float(config.get("patient_line_padding_bottom_mm", 3.5)) * mm

    top_line_y = cur_y - pat_y_offset
    row_y = top_line_y - line_pad_top
    bottom_line_y = row_y - line_pad_bottom

    # Measure item widths
    pat_font_size = float(config.get("patient_font_size", 9.0))
    pat_lbl_font = _get_reportlab_font(font_fam, config.get("patient_label_style", "Bold"))
    pat_val_font = _get_reportlab_font(font_fam, config.get("patient_value_style", "Regular"))

    w_lbl_name = c.stringWidth("Name: ", pat_lbl_font, pat_font_size)
    w_val_name = c.stringWidth(data["patient_name"], pat_val_font, pat_font_size)
    w1 = w_lbl_name + w_val_name

    w_lbl_gender = c.stringWidth("Gender: ", pat_lbl_font, pat_font_size)
    w_val_gender = c.stringWidth(data["gender"], pat_val_font, pat_font_size)
    w2 = w_lbl_gender + w_val_gender

    w_lbl_age = c.stringWidth("Age: ", pat_lbl_font, pat_font_size)
    w_val_age = c.stringWidth(data["age"], pat_val_font, pat_font_size)
    w3 = w_lbl_age + w_val_age

    tok_font_size = float(config.get("token_font_size", 9.0))
    tok_font = _get_reportlab_font(font_fam, config.get("token_font_style", "Bold"))
    tok_text = data["token_str"]
    pad_mm = float(config.get("token_badge_padding_mm", 3.5)) * mm
    w_tok_text = c.stringWidth(tok_text, tok_font, tok_font_size)
    w4 = w_tok_text + pad_mm if config.get("show_token_badge", True) else w_tok_text

    w_lbl_date = c.stringWidth("Date: ", pat_lbl_font, pat_font_size)
    w_val_date = c.stringWidth(data["date_str"], pat_val_font, pat_font_size)
    w5 = w_lbl_date + w_val_date

    # Position columns
    if config.get("auto_fit_patient_row", True):
        avail_w = x_right - x_left
        total_items_w = w1 + w2 + w3 + w4 + w5
        gap = (avail_w - total_items_w) / 4.0
        min_gap = 3.0 * mm
        if gap < min_gap:
            gap = min_gap
        x_name = x_left
        x_gender = x_name + w1 + gap
        x_age = x_gender + w2 + gap
        x_token = x_age + w3 + gap
        if avail_w >= total_items_w + 4 * min_gap:
            x_date = x_right - w5
        else:
            x_date = x_token + w4 + gap
    else:
        x_name = float(config.get("name_x_mm", 12.0)) * mm
        x_gender = float(config.get("gender_x_mm", 44.0)) * mm
        x_age = float(config.get("age_x_mm", 68.0)) * mm
        x_token = float(config.get("token_x_mm", 88.0)) * mm
        x_date = float(config.get("date_x_mm", 112.0)) * mm

    # Draw divider lines
    if config.get("show_patient_lines", True):
        lines_align = str(config.get("patient_line_alignment", "Full Width"))
        if "Match Content" in lines_align:
            line_x_start = x_name
            line_x_end = x_date + w5
        elif "Compact Inset" in lines_align:
            line_x_start = x_left + 10.0 * mm
            line_x_end = x_right - 10.0 * mm
        else:
            line_x_start = x_left
            line_x_end = x_right

        c.setStrokeColor(HexColor(config.get("patient_line_color", TEAL_COLOR)))
        c.setLineWidth(float(config.get("patient_line_thickness", 1.0)))
        c.line(line_x_start, top_line_y, line_x_end, top_line_y)
        c.line(line_x_start, bottom_line_y, line_x_end, bottom_line_y)
        if config.get("patient_lines_style", "Single") == "Double":
            offset = 1.2 * mm
            c.line(line_x_start, top_line_y + offset, line_x_end, top_line_y + offset)
            c.line(line_x_start, bottom_line_y - offset, line_x_end, bottom_line_y - offset)

    # Draw items
    # Name
    c.setFont(pat_lbl_font, pat_font_size)
    c.setFillColor(HexColor(DARK_SLATE_COLOR))
    c.drawString(x_name, row_y, "Name: ")
    c.setFont(pat_val_font, pat_font_size)
    c.drawString(x_name + w_lbl_name, row_y, data["patient_name"])
    
    # Gender
    c.setFont(pat_lbl_font, pat_font_size)
    c.drawString(x_gender, row_y, "Gender: ")
    c.setFont(pat_val_font, pat_font_size)
    c.drawString(x_gender + w_lbl_gender, row_y, data["gender"])
    
    # Age
    c.setFont(pat_lbl_font, pat_font_size)
    c.drawString(x_age, row_y, "Age: ")
    c.setFont(pat_val_font, pat_font_size)
    c.drawString(x_age + w_lbl_age, row_y, data["age"])
    
    # Token Badge
    c.setFont(tok_font, tok_font_size)
    bh = float(config.get("token_badge_height_mm", 5.2)) * mm
    if config.get("show_token_badge", True):
        c.setFillColor(HexColor(TEAL_COLOR))
        c.rect(x_token, row_y - 1.2 * mm, w4, bh, stroke=0, fill=1)
        c.setFillColor(HexColor(WHITE_COLOR))
        c.drawCentredString(x_token + w4 / 2.0, row_y, tok_text)
    else:
        c.setFillColor(HexColor(TEAL_COLOR))
        c.drawString(x_token, row_y, tok_text)
    
    # Date
    c.setFont(pat_lbl_font, pat_font_size)
    c.setFillColor(HexColor(DARK_SLATE_COLOR))
    c.drawString(x_date, row_y, "Date: ")
    c.setFont(pat_val_font, pat_font_size)
    c.drawString(x_date + w_lbl_date, row_y, data["date_str"])

    # 5. Vertical Divider Line on the Left 1/3rd of the Page
    if config.get("show_vertical_line", True):
        vert_align = str(config.get("vertical_line_alignment", "Left 1/3rd (33.3%)"))
        if "1/4" in vert_align or "25%" in vert_align:
            vert_ratio = 0.25
        elif "30%" in vert_align:
            vert_ratio = 0.30
        elif "1/3" in vert_align or "33" in vert_align:
            vert_ratio = 0.333
        elif "2/5" in vert_align or "40%" in vert_align:
            vert_ratio = 0.40
        elif "Center" in vert_align or "50%" in vert_align:
            vert_ratio = 0.50
        else:
            vert_ratio = float(config.get("vertical_line_ratio", 0.333))

        x_vert = x_left + (x_right - x_left) * vert_ratio

        y_vert_start = bottom_line_y
        if config.get("show_patient_lines", True) and config.get("patient_lines_style", "Single") == "Double":
            y_vert_start -= 1.2 * mm

        bottom_margin = float(config.get("bottom_margin_mm", 15.0)) * mm
        y_vert_end = bottom_margin

        if y_vert_start > y_vert_end:
            vert_color = config.get("vertical_line_color", config.get("patient_line_color", TEAL_COLOR))
            c.setStrokeColor(HexColor(vert_color))
            c.setLineWidth(float(config.get("vertical_line_thickness", config.get("patient_line_thickness", 1.0))))
            c.line(x_vert, y_vert_start, x_vert, y_vert_end)

            if config.get("show_rx_symbol", True):
                c.setFont("Times-BoldItalic", 15)
                c.setFillColor(HexColor(vert_color))
                c.drawString(x_vert + 4.0 * mm, y_vert_start - 7.0 * mm, "Rx")

    c.showPage()
    c.save()
    return filepath


def send_to_printer(filepath: str):
    """
    Sends the generated PDF file directly to the default system printer.
    """
    if sys.platform.startswith("win"):
        try:
            os.startfile(filepath, "print")  # type: ignore[attr-defined]
        except Exception as e:
            print(f"Error printing on Windows: {e}")
    else:
        import subprocess
        subprocess.run(["lp", filepath], check=False)
