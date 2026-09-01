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
from PySide6.QtGui import QPainter, QFont, QPageSize, QColor, QPen, QBrush, QImage, QPixmap
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
    
    # Doctor Info
    raw_doc_name = str(_get_val(doctor, "name", "DR. AMJAD HUSSAIN SADDIQUI") if doctor else "DR. AMJAD HUSSAIN SADDIQUI").strip().upper()
    if not raw_doc_name.startswith("DR.") and not raw_doc_name.startswith("DR "):
        doc_display_name = f"DR. {raw_doc_name}"
    else:
        doc_display_name = raw_doc_name

    # Check if Dr. Amjad Hussain Saddiqui or custom doctor
    if "AMJAD HUSSAIN" in doc_display_name or "SADDIQUI" in doc_display_name:
        doc_lines = ["DR. AMJAD HUSSAIN", "SADDIQUI"]
        degrees = "MBBS DCH DCN JAPAN"
        specialization = "CONSULTANT CHILD SPECIALIST PEDIATRIC NEUROPHYSICIAN"
    else:
        words = doc_display_name.split()
        if len(words) >= 4:
            mid = len(words) // 2
            doc_lines = [" ".join(words[:mid]), " ".join(words[mid:])]
        else:
            doc_lines = [doc_display_name]
        
        doc_spec = str(_get_val(doctor, "specialization", "")).strip().upper() if doctor else ""
        degrees = DEFAULT_DEGREES
        specialization = f"CONSULTANT {doc_spec}" if doc_spec else DEFAULT_SPECIALIZATION

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
    margin_left = mm2px(config.get("margin_left_mm", 12.0))
    top_margin_px = mm2px(config.get("top_margin_mm", 14.0))
    reserved_top_mm = float(config.get("reserved_top_area_mm", 0.0))
    reserved_top_px = mm2px(reserved_top_mm)

    # ── Reserved Letterhead Guide (Rendered only on preview if enabled) ─────
    if is_preview and reserved_top_mm > 0 and config.get("show_reserved_area_guide", True):
        res_rect = QRectF(0, 0, mm2px(148.0), reserved_top_px)
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
    row_baseline = cur_y + mm2px(3.5 + y_offset)

    # 4a. Name: <NAME>
    x_name = mm2px(config.get("name_x_mm", 12.0))
    painter.setFont(font_lbl)
    painter.setPen(QColor(DARK_SLATE_COLOR))
    painter.drawText(x_name, row_baseline, "Name: ")
    lbl_w = painter.fontMetrics().horizontalAdvance("Name: ")
    painter.setFont(font_val)
    painter.drawText(x_name + lbl_w, row_baseline, data["patient_name"])

    # 4b. Gender: <GENDER>
    x_gender = mm2px(config.get("gender_x_mm", 44.0))
    painter.setFont(font_lbl)
    painter.drawText(x_gender, row_baseline, "Gender: ")
    lbl_w = painter.fontMetrics().horizontalAdvance("Gender: ")
    painter.setFont(font_val)
    painter.drawText(x_gender + lbl_w, row_baseline, data["gender"])

    # 4c. Age: <AGE>
    x_age = mm2px(config.get("age_x_mm", 68.0))
    painter.setFont(font_lbl)
    painter.drawText(x_age, row_baseline, "Age: ")
    lbl_w = painter.fontMetrics().horizontalAdvance("Age: ")
    painter.setFont(font_val)
    painter.drawText(x_age + lbl_w, row_baseline, data["age"])

    # 4d. Token Badge: [Token #: N]
    x_token = mm2px(config.get("token_x_mm", 88.0))
    tok_font_size = float(config.get("token_font_size", 9.0))
    tok_style = config.get("token_font_style", "Bold")
    font_tok = _make_qfont(font_fam, tok_font_size, tok_style)
    painter.setFont(font_tok)
    tok_text = data["token_str"]
    
    pad_mm = float(config.get("token_badge_padding_mm", 3.5))
    h_mm = float(config.get("token_badge_height_mm", 5.2))
    bw = painter.fontMetrics().horizontalAdvance(tok_text) + mm2px(pad_mm)
    bh = mm2px(h_mm)
    badge_rect = QRectF(x_token, row_baseline - bh + mm2px(1.0), bw, bh)

    if config.get("show_token_badge", True):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(TEAL_COLOR)))
        painter.drawRect(badge_rect)
        painter.setPen(QColor(WHITE_COLOR))
        painter.drawText(badge_rect, Qt.AlignCenter, tok_text)
    else:
        painter.setPen(QColor(TEAL_COLOR))
        painter.drawText(x_token, row_baseline, tok_text)

    # 4e. Date: <DATE>
    x_date = mm2px(config.get("date_x_mm", 112.0))
    painter.setFont(font_lbl)
    painter.setPen(QColor(DARK_SLATE_COLOR))
    painter.drawText(x_date, row_baseline, "Date: ")
    lbl_w = painter.fontMetrics().horizontalAdvance("Date: ")
    painter.setFont(font_val)
    painter.drawText(x_date + lbl_w, row_baseline, data["date_str"])


def _render_slip_qt(printer: QPrinter, patient=None, doctor=None, visit=None, config: dict = None):
    """
    Renders the exact prescription header onto QPrinter using PySide6 QPainter.
    """
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

    dpi = 150
    w_px = int(148 * dpi / 25.4)  # 874 px
    reserved_top_mm = float(config.get("reserved_top_area_mm", 0.0))
    h_mm = 80.0 + reserved_top_mm
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
    or prints directly on A5 prescription paper.
    """
    if show_preview:
        from ui.prescription_print_dialog import PrescriptionPrintDialog
        dialog = PrescriptionPrintDialog(patient=patient, doctor=doctor, visit=visit)
        dialog.exec()
    else:
        if config is None:
            config = load_slip_config()
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A5))
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
    Generates an A5 PDF matching the exact prescription header layout using active config.
    """
    if config is None:
        config = load_slip_config()

    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor

    pw, ph = A5
    data = _extract_slip_data(patient, doctor, visit)
    
    filename = f"slip_token{data['token_number']}_{data['date_str']}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(filepath, pagesize=A5)
    
    font_fam = config.get("font_family", "Arial")
    margin_left = float(config.get("margin_left_mm", 12.0)) * mm
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
    row_y = cur_y - pat_y_offset
    
    pat_font_size = float(config.get("patient_font_size", 9.0))
    pat_lbl_font = _get_reportlab_font(font_fam, config.get("patient_label_style", "Bold"))
    pat_val_font = _get_reportlab_font(font_fam, config.get("patient_value_style", "Regular"))

    # Name: <NAME>
    x_name = float(config.get("name_x_mm", 12.0)) * mm
    c.setFont(pat_lbl_font, pat_font_size)
    c.setFillColor(HexColor(DARK_SLATE_COLOR))
    c.drawString(x_name, row_y, "Name: ")
    x_val = x_name + c.stringWidth("Name: ", pat_lbl_font, pat_font_size)
    c.setFont(pat_val_font, pat_font_size)
    c.drawString(x_val, row_y, data["patient_name"])
    
    # Gender: <GENDER>
    x_gender = float(config.get("gender_x_mm", 44.0)) * mm
    c.setFont(pat_lbl_font, pat_font_size)
    c.drawString(x_gender, row_y, "Gender: ")
    x_val = x_gender + c.stringWidth("Gender: ", pat_lbl_font, pat_font_size)
    c.setFont(pat_val_font, pat_font_size)
    c.drawString(x_val, row_y, data["gender"])
    
    # Age: <AGE>
    x_age = float(config.get("age_x_mm", 68.0)) * mm
    c.setFont(pat_lbl_font, pat_font_size)
    c.drawString(x_age, row_y, "Age: ")
    x_val = x_age + c.stringWidth("Age: ", pat_lbl_font, pat_font_size)
    c.setFont(pat_val_font, pat_font_size)
    c.drawString(x_val, row_y, data["age"])
    
    # Token Badge: [Token #: N]
    x_token = float(config.get("token_x_mm", 88.0)) * mm
    tok_font_size = float(config.get("token_font_size", 9.0))
    tok_font = _get_reportlab_font(font_fam, config.get("token_font_style", "Bold"))
    c.setFont(tok_font, tok_font_size)
    tok_text = data["token_str"]
    pad_mm = float(config.get("token_badge_padding_mm", 3.5)) * mm
    bw = c.stringWidth(tok_text, tok_font, tok_font_size) + pad_mm
    bh = float(config.get("token_badge_height_mm", 5.2)) * mm
    
    if config.get("show_token_badge", True):
        c.setFillColor(HexColor(TEAL_COLOR))
        c.rect(x_token, row_y - 1.2 * mm, bw, bh, stroke=0, fill=1)
        c.setFillColor(HexColor(WHITE_COLOR))
        c.drawCentredString(x_token + bw / 2.0, row_y, tok_text)
    else:
        c.setFillColor(HexColor(TEAL_COLOR))
        c.drawString(x_token, row_y, tok_text)
    
    # Date: <DATE>
    x_date = float(config.get("date_x_mm", 112.0)) * mm
    c.setFont(pat_lbl_font, pat_font_size)
    c.setFillColor(HexColor(DARK_SLATE_COLOR))
    c.drawString(x_date, row_y, "Date: ")
    x_val = x_date + c.stringWidth("Date: ", pat_lbl_font, pat_font_size)
    c.setFont(pat_val_font, pat_font_size)
    c.drawString(x_val, row_y, data["date_str"])
    
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
