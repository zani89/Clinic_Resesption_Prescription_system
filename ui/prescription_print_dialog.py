"""
prescription_print_dialog.py — Full-featured Prescription Print & Preview Screen with live Font, Font Style, Reserved Area, and Allocation Adjustments.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QDoubleSpinBox, QCheckBox, QComboBox, QPushButton, QFrame,
    QTabWidget, QWidget, QMessageBox, QScrollArea, QSplitter,
    QToolBar, QSizePolicy
)
from PySide6.QtPrintSupport import QPrinter, QPrintPreviewWidget, QPrintDialog
from PySide6.QtGui import QPageSize, QAction, QIcon, QFont, QColor
from PySide6.QtCore import Qt, Signal

from models.slip_config import load_slip_config, save_slip_config, reset_slip_config_to_defaults, DEFAULT_CONFIG
from ui.print_slip import render_slip_on_painter, generate_prescription_pdf, send_to_printer, _extract_slip_data

FONT_STYLES = ["Bold", "Regular", "Italic", "Bold Italic"]


class PrescriptionPrintDialog(QDialog):
    def __init__(self, patient=None, doctor=None, visit=None, parent=None):
        super().__init__(parent)
        self.patient = patient
        self.doctor = doctor
        self.visit = visit
        
        self.setWindowTitle("🖨 Print Prescription Slip — Preview & Layout Customizer")
        self.resize(1180, 820)
        self.setMinimumSize(980, 680)

        # Active configuration
        self.active_config = load_slip_config()
        self.slip_data = _extract_slip_data(self.patient, self.doctor, self.visit)

        # Setup Printer instance
        self.printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        self.printer.setPageSize(QPageSize(QPageSize.PageSizeId.A5))
        self.printer.setFullPage(True)

        self._build_ui()
        self._load_values_into_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # ── TOP SUMMARY & ACTIONS BAR ──────────────────────────────────────
        top_bar = QFrame()
        top_bar.setStyleSheet(
            "QFrame { background: #1A5276; border-radius: 8px; }"
        )
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(14, 10, 14, 10)
        top_layout.setSpacing(12)

        # Patient summary badge
        pat_name = self.slip_data.get("patient_name", "UNKNOWN")
        gender = self.slip_data.get("gender", "")
        age = self.slip_data.get("age", "")
        token = self.slip_data.get("token_number", 1)
        doc_display = " ".join(self.slip_data.get("doc_lines", ["DOCTOR"]))

        info_lbl = QLabel(
            f"<span style='color:#AED6F1; font-size:13px;'>Patient:</span> "
            f"<b style='color:#FFFFFF; font-size:14px;'>{pat_name}</b> "
            f"<span style='color:#A9DFBF;'>({gender}, {age})</span> &nbsp;·&nbsp; "
            f"<span style='color:#AED6F1;'>Token:</span> <b style='color:#F39C12; font-size:14px;'>#{token}</b> &nbsp;·&nbsp; "
            f"<span style='color:#AED6F1;'>Doctor:</span> <b style='color:#FFFFFF;'>{doc_display}</b>"
        )
        info_lbl.setTextFormat(Qt.RichText)
        top_layout.addWidget(info_lbl, 1)

        # Toggle Settings Panel Button
        self.btn_toggle_settings = QPushButton("⚙️  Hide / Show Settings")
        self.btn_toggle_settings.setCheckable(True)
        self.btn_toggle_settings.setChecked(True)
        self.btn_toggle_settings.setStyleSheet(
            "QPushButton { background: #0284C7; color: white; padding: 7px 12px; font-weight: 600; border-radius: 5px; } "
            "QPushButton:checked { background: #0369A1; }"
        )
        self.btn_toggle_settings.toggled.connect(self._toggle_settings_panel)
        top_layout.addWidget(self.btn_toggle_settings)

        # Save PDF Button
        self.btn_export_pdf = QPushButton("📄  Save PDF")
        self.btn_export_pdf.setStyleSheet(
            "background: #475569; color: white; padding: 7px 14px; font-weight: 600; border-radius: 5px;"
        )
        self.btn_export_pdf.clicked.connect(self._on_export_pdf)
        top_layout.addWidget(self.btn_export_pdf)

        # Primary Print Button
        self.btn_print_now = QPushButton("🖨  Print Prescription")
        self.btn_print_now.setStyleSheet(
            "background: #27AE60; color: white; font-size: 14px; font-weight: bold; padding: 8px 22px; border-radius: 6px;"
        )
        self.btn_print_now.clicked.connect(self._on_print_now)
        top_layout.addWidget(self.btn_print_now)

        main_layout.addWidget(top_bar)

        # ── MAIN SPLITTER (Preview on Left, Adjustments Panel on Right) ─────
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # ── LEFT: Print Preview Widget & Zoom Toolbar ───────────────────────
        preview_container = QFrame()
        preview_container.setStyleSheet(
            "QFrame { background: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 8px; }"
        )
        prev_layout = QVBoxLayout(preview_container)
        prev_layout.setContentsMargins(8, 8, 8, 8)
        prev_layout.setSpacing(6)

        # Toolbar for preview controls
        zoom_bar = QHBoxLayout()
        zoom_bar.setContentsMargins(4, 2, 4, 2)
        zoom_bar.setSpacing(8)

        lbl_prev_hint = QLabel("<b>A5 Prescription Slip Preview:</b>")
        lbl_prev_hint.setStyleSheet("color: #1E293B; font-size: 12px; border: none; background: transparent;")
        zoom_bar.addWidget(lbl_prev_hint)
        zoom_bar.addStretch()

        btn_fit_width = QPushButton("↔  Fit Width")
        btn_fit_width.setStyleSheet("padding: 4px 10px; font-size: 11px; background: white; color: #1E293B; border: 1px solid #CBD5E1; border-radius: 4px;")
        btn_fit_width.clicked.connect(lambda: self.preview_widget.fitToWidth())
        zoom_bar.addWidget(btn_fit_width)

        btn_fit_page = QPushButton("📄  Fit Page")
        btn_fit_page.setStyleSheet("padding: 4px 10px; font-size: 11px; background: white; color: #1E293B; border: 1px solid #CBD5E1; border-radius: 4px;")
        btn_fit_page.clicked.connect(lambda: self.preview_widget.fitInView())
        zoom_bar.addWidget(btn_fit_page)

        btn_zoom_in = QPushButton("🔍 +")
        btn_zoom_in.setStyleSheet("padding: 4px 8px; font-size: 11px; font-weight: bold; background: white; color: #1E293B; border: 1px solid #CBD5E1; border-radius: 4px;")
        btn_zoom_in.clicked.connect(lambda: self.preview_widget.zoomIn())
        zoom_bar.addWidget(btn_zoom_in)

        btn_zoom_out = QPushButton("🔍 -")
        btn_zoom_out.setStyleSheet("padding: 4px 8px; font-size: 11px; font-weight: bold; background: white; color: #1E293B; border: 1px solid #CBD5E1; border-radius: 4px;")
        btn_zoom_out.clicked.connect(lambda: self.preview_widget.zoomOut())
        zoom_bar.addWidget(btn_zoom_out)

        prev_layout.addLayout(zoom_bar)

        # Print Preview Widget
        self.preview_widget = QPrintPreviewWidget(self.printer)
        self.preview_widget.setStyleSheet("background: #64748B; border: 1px solid #94A3B8; border-radius: 4px;")
        self.preview_widget.paintRequested.connect(self._on_paint_requested)
        prev_layout.addWidget(self.preview_widget, 1)

        self.splitter.addWidget(preview_container)

        # ── RIGHT: Adjustments Sidebar ──────────────────────────────────────
        self.settings_panel = QFrame()
        self.settings_panel.setMinimumWidth(380)
        self.settings_panel.setMaximumWidth(460)
        self.settings_panel.setStyleSheet(
            "QFrame { background: white; border: 1px solid #BAD9F1; border-radius: 8px; }"
        )
        settings_layout = QVBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(12, 12, 12, 12)
        settings_layout.setSpacing(10)

        panel_title = QLabel("⚙️  Font, Style & Reserved Area Adjustments")
        panel_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1A5276; border: none; background: transparent;")
        settings_layout.addWidget(panel_title)

        # Tabs for categorized controls
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #BAD9F1; background: white; border-radius: 6px; }"
        )
        self.tabs.addTab(self._create_doctor_controls(), "👨‍⚕️ Doctor Info")
        self.tabs.addTab(self._create_patient_controls(), "👤 Patient & Columns")
        self.tabs.addTab(self._create_reserved_and_margins_controls(), "🏛 Reserved Area & Margins")
        settings_layout.addWidget(self.tabs, 1)

        # Bottom actions for sidebar
        side_bottom = QVBoxLayout()
        side_bottom.setSpacing(6)

        self.btn_save_defaults = QPushButton("💾  Save as Default Settings")
        self.btn_save_defaults.setStyleSheet(
            "background: #0284C7; color: white; font-size: 12px; font-weight: bold; padding: 8px 12px; border-radius: 5px;"
        )
        self.btn_save_defaults.clicked.connect(self._on_save_defaults)
        side_bottom.addWidget(self.btn_save_defaults)

        self.btn_reset_defaults = QPushButton("🔄  Reset to Recommended Defaults")
        self.btn_reset_defaults.setStyleSheet(
            "background: #E2E8F0; color: #334155; font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 5px;"
        )
        self.btn_reset_defaults.clicked.connect(self._on_reset_defaults)
        side_bottom.addWidget(self.btn_reset_defaults)

        settings_layout.addLayout(side_bottom)

        self.splitter.addWidget(self.settings_panel)
        self.splitter.setStretchFactor(0, 6)
        self.splitter.setStretchFactor(1, 4)

        main_layout.addWidget(self.splitter, 1)

    # ── CONTROL TABS ─────────────────────────────────────────────────────────
    def _create_doctor_controls(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        grid = QGridLayout()
        grid.setVerticalSpacing(7)
        grid.setHorizontalSpacing(8)

        row = 0
        # Doctor Name Size & Style
        grid.addWidget(QLabel("Doctor Name Size:"), row, 0)
        self.spin_doc_size = QDoubleSpinBox()
        self.spin_doc_size.setRange(8.0, 30.0)
        self.spin_doc_size.setSingleStep(0.5)
        self.spin_doc_size.setSuffix(" pt")
        self.spin_doc_size.valueChanged.connect(self._on_control_changed)
        grid.addWidget(self.spin_doc_size, row, 1)

        row += 1
        grid.addWidget(QLabel("Doctor Name Style:"), row, 0)
        self.combo_doc_style = QComboBox()
        self.combo_doc_style.addItems(FONT_STYLES)
        self.combo_doc_style.currentTextChanged.connect(self._on_control_changed)
        grid.addWidget(self.combo_doc_style, row, 1)

        row += 1
        # Line Spacing
        grid.addWidget(QLabel("Doctor Line Spacing:"), row, 0)
        self.spin_doc_line_spacing = QDoubleSpinBox()
        self.spin_doc_line_spacing.setRange(3.0, 18.0)
        self.spin_doc_line_spacing.setSingleStep(0.5)
        self.spin_doc_line_spacing.setSuffix(" mm")
        self.spin_doc_line_spacing.valueChanged.connect(self._on_control_changed)
        grid.addWidget(self.spin_doc_line_spacing, row, 1)

        row += 1
        # Qualifications Font Size & Style
        grid.addWidget(QLabel("Qualifications Size:"), row, 0)
        self.spin_deg_size = QDoubleSpinBox()
        self.spin_deg_size.setRange(5.0, 20.0)
        self.spin_deg_size.setSingleStep(0.5)
        self.spin_deg_size.setSuffix(" pt")
        self.spin_deg_size.valueChanged.connect(self._on_control_changed)
        grid.addWidget(self.spin_deg_size, row, 1)

        row += 1
        grid.addWidget(QLabel("Qualifications Style:"), row, 0)
        self.combo_deg_style = QComboBox()
        self.combo_deg_style.addItems(FONT_STYLES)
        self.combo_deg_style.currentTextChanged.connect(self._on_control_changed)
        grid.addWidget(self.combo_deg_style, row, 1)

        row += 1
        grid.addWidget(QLabel("Qualifications Spacing:"), row, 0)
        self.spin_deg_spacing = QDoubleSpinBox()
        self.spin_deg_spacing.setRange(2.0, 15.0)
        self.spin_deg_spacing.setSingleStep(0.5)
        self.spin_deg_spacing.setSuffix(" mm")
        self.spin_deg_spacing.valueChanged.connect(self._on_control_changed)
        grid.addWidget(self.spin_deg_spacing, row, 1)

        row += 1
        # Specialization Font Size & Style
        grid.addWidget(QLabel("Specialization Size:"), row, 0)
        self.spin_spec_size = QDoubleSpinBox()
        self.spin_spec_size.setRange(5.0, 20.0)
        self.spin_spec_size.setSingleStep(0.5)
        self.spin_spec_size.setSuffix(" pt")
        self.spin_spec_size.valueChanged.connect(self._on_control_changed)
        grid.addWidget(self.spin_spec_size, row, 1)

        row += 1
        grid.addWidget(QLabel("Specialization Style:"), row, 0)
        self.combo_spec_style = QComboBox()
        self.combo_spec_style.addItems(FONT_STYLES)
        self.combo_spec_style.currentTextChanged.connect(self._on_control_changed)
        grid.addWidget(self.combo_spec_style, row, 1)

        row += 1
        # Doctor Bottom Gap
        grid.addWidget(QLabel("Gap Below Doctor Info:"), row, 0)
        self.spin_doc_bottom_gap = QDoubleSpinBox()
        self.spin_doc_bottom_gap.setRange(2.0, 35.0)
        self.spin_doc_bottom_gap.setSingleStep(0.5)
        self.spin_doc_bottom_gap.setSuffix(" mm")
        self.spin_doc_bottom_gap.valueChanged.connect(self._on_control_changed)
        grid.addWidget(self.spin_doc_bottom_gap, row, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return tab

    def _create_patient_controls(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        # Patient Typography & Styles
        grid1 = QGridLayout()
        grid1.setVerticalSpacing(6)
        grid1.setHorizontalSpacing(8)

        grid1.addWidget(QLabel("Patient Font Size:"), 0, 0)
        self.spin_pat_size = QDoubleSpinBox()
        self.spin_pat_size.setRange(5.0, 18.0)
        self.spin_pat_size.setSingleStep(0.5)
        self.spin_pat_size.setSuffix(" pt")
        self.spin_pat_size.valueChanged.connect(self._on_control_changed)
        grid1.addWidget(self.spin_pat_size, 0, 1)

        grid1.addWidget(QLabel("Labels Style (Name, Age):"), 1, 0)
        self.combo_pat_lbl_style = QComboBox()
        self.combo_pat_lbl_style.addItems(FONT_STYLES)
        self.combo_pat_lbl_style.currentTextChanged.connect(self._on_control_changed)
        grid1.addWidget(self.combo_pat_lbl_style, 1, 1)

        grid1.addWidget(QLabel("Values Style (Patient Text):"), 2, 0)
        self.combo_pat_val_style = QComboBox()
        self.combo_pat_val_style.addItems(FONT_STYLES)
        self.combo_pat_val_style.currentTextChanged.connect(self._on_control_changed)
        grid1.addWidget(self.combo_pat_val_style, 2, 1)

        grid1.addWidget(QLabel("Row Vertical Offset:"), 3, 0)
        self.spin_pat_y_offset = QDoubleSpinBox()
        self.spin_pat_y_offset.setRange(-20.0, 40.0)
        self.spin_pat_y_offset.setSingleStep(0.5)
        self.spin_pat_y_offset.setSuffix(" mm")
        self.spin_pat_y_offset.valueChanged.connect(self._on_control_changed)
        grid1.addWidget(self.spin_pat_y_offset, 3, 1)

        layout.addLayout(grid1)

        # Horizontal Allocations Section
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("border: 1px solid #E2E8F0; margin: 2px 0;")
        layout.addWidget(div)

        sec2_lbl = QLabel("<b>Horizontal Column Allocations (X mm from Left):</b>")
        sec2_lbl.setStyleSheet("color: #1A5276; font-size: 11px;")
        layout.addWidget(sec2_lbl)

        grid2 = QGridLayout()
        grid2.setVerticalSpacing(5)
        grid2.setHorizontalSpacing(8)

        grid2.addWidget(QLabel("Name Column:"), 0, 0)
        self.spin_name_x = QDoubleSpinBox()
        self.spin_name_x.setRange(0.0, 140.0)
        self.spin_name_x.setSingleStep(1.0)
        self.spin_name_x.setSuffix(" mm")
        self.spin_name_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_name_x, 0, 1)

        grid2.addWidget(QLabel("Gender Column:"), 1, 0)
        self.spin_gender_x = QDoubleSpinBox()
        self.spin_gender_x.setRange(0.0, 140.0)
        self.spin_gender_x.setSingleStep(1.0)
        self.spin_gender_x.setSuffix(" mm")
        self.spin_gender_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_gender_x, 1, 1)

        grid2.addWidget(QLabel("Age Column:"), 2, 0)
        self.spin_age_x = QDoubleSpinBox()
        self.spin_age_x.setRange(0.0, 140.0)
        self.spin_age_x.setSingleStep(1.0)
        self.spin_age_x.setSuffix(" mm")
        self.spin_age_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_age_x, 2, 1)

        grid2.addWidget(QLabel("Token Badge:"), 3, 0)
        self.spin_token_x = QDoubleSpinBox()
        self.spin_token_x.setRange(0.0, 140.0)
        self.spin_token_x.setSingleStep(1.0)
        self.spin_token_x.setSuffix(" mm")
        self.spin_token_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_token_x, 3, 1)

        grid2.addWidget(QLabel("Date Column:"), 4, 0)
        self.spin_date_x = QDoubleSpinBox()
        self.spin_date_x.setRange(0.0, 140.0)
        self.spin_date_x.setSingleStep(1.0)
        self.spin_date_x.setSuffix(" mm")
        self.spin_date_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_date_x, 4, 1)

        layout.addLayout(grid2)

        # Token Badge Box Options
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet("border: 1px solid #E2E8F0; margin: 2px 0;")
        layout.addWidget(div2)

        self.chk_show_badge = QCheckBox("Show Teal Background Box on Token")
        self.chk_show_badge.stateChanged.connect(self._on_control_changed)
        layout.addWidget(self.chk_show_badge)

        layout.addStretch()
        return tab

    def _create_reserved_and_margins_controls(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Reserved Letterhead Area
        sec_res_lbl = QLabel("<b>🏛 Pre-Printed Letterhead / Reserved Area:</b>")
        sec_res_lbl.setStyleSheet("color: #1A5276; font-size: 12px;")
        layout.addWidget(sec_res_lbl)

        grid_res = QGridLayout()
        grid_res.setVerticalSpacing(7)
        grid_res.setHorizontalSpacing(8)

        grid_res.addWidget(QLabel("Reserved Top Space:"), 0, 0)
        self.spin_reserved_top = QDoubleSpinBox()
        self.spin_reserved_top.setRange(0.0, 100.0)
        self.spin_reserved_top.setSingleStep(1.0)
        self.spin_reserved_top.setSuffix(" mm")
        self.spin_reserved_top.valueChanged.connect(self._on_control_changed)
        grid_res.addWidget(self.spin_reserved_top, 0, 1)

        self.chk_show_guide = QCheckBox("Show Reserved Area Guide Shading in Preview")
        self.chk_show_guide.stateChanged.connect(self._on_control_changed)
        grid_res.addWidget(self.chk_show_guide, 1, 0, 1, 2)

        layout.addLayout(grid_res)

        # Page Margins & Global Font
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("border: 1px solid #E2E8F0; margin: 4px 0;")
        layout.addWidget(div)

        sec_marg_lbl = QLabel("<b>📄 General Margins & Font Family:</b>")
        sec_marg_lbl.setStyleSheet("color: #1A5276; font-size: 12px;")
        layout.addWidget(sec_marg_lbl)

        grid_marg = QGridLayout()
        grid_marg.setVerticalSpacing(7)
        grid_marg.setHorizontalSpacing(8)

        # Font Family
        grid_marg.addWidget(QLabel("Font Family:"), 0, 0)
        self.combo_font = QComboBox()
        self.combo_font.addItems([
            "Arial", "Segoe UI", "Calibri", "Helvetica", "Times New Roman", "Tahoma", "Verdana"
        ])
        self.combo_font.currentTextChanged.connect(self._on_control_changed)
        grid_marg.addWidget(self.combo_font, 0, 1)

        # Left Margin
        grid_marg.addWidget(QLabel("Page Left Margin:"), 1, 0)
        self.spin_margin_left = QDoubleSpinBox()
        self.spin_margin_left.setRange(0.0, 40.0)
        self.spin_margin_left.setSingleStep(0.5)
        self.spin_margin_left.setSuffix(" mm")
        self.spin_margin_left.valueChanged.connect(self._on_control_changed)
        grid_marg.addWidget(self.spin_margin_left, 1, 1)

        # Top Margin
        grid_marg.addWidget(QLabel("Base Top Margin:"), 2, 0)
        self.spin_margin_top = QDoubleSpinBox()
        self.spin_margin_top.setRange(0.0, 50.0)
        self.spin_margin_top.setSingleStep(0.5)
        self.spin_margin_top.setSuffix(" mm")
        self.spin_margin_top.valueChanged.connect(self._on_control_changed)
        grid_marg.addWidget(self.spin_margin_top, 2, 1)

        layout.addLayout(grid_marg)
        layout.addStretch()
        return tab

    # ── VALUES & SYNCHRONIZATION ─────────────────────────────────────────────
    def _load_values_into_ui(self):
        cfg = self.active_config

        # Doctor
        self.spin_doc_size.setValue(float(cfg.get("doc_name_font_size", 15.0)))
        self._set_combo(self.combo_doc_style, cfg.get("doc_name_font_style", "Bold"))
        self.spin_doc_line_spacing.setValue(float(cfg.get("doc_name_line_spacing_mm", 6.5)))
        
        self.spin_deg_size.setValue(float(cfg.get("degrees_font_size", 8.5)))
        self._set_combo(self.combo_deg_style, cfg.get("degrees_font_style", "Bold"))
        self.spin_deg_spacing.setValue(float(cfg.get("degrees_spacing_mm", 5.0)))
        
        self.spin_spec_size.setValue(float(cfg.get("specialization_font_size", 7.5)))
        self._set_combo(self.combo_spec_style, cfg.get("specialization_font_style", "Regular"))
        self.spin_doc_bottom_gap.setValue(float(cfg.get("doctor_bottom_spacing_mm", 8.5)))

        # Patient
        self.spin_pat_size.setValue(float(cfg.get("patient_font_size", 9.0)))
        self._set_combo(self.combo_pat_lbl_style, cfg.get("patient_label_style", "Bold"))
        self._set_combo(self.combo_pat_val_style, cfg.get("patient_value_style", "Regular"))
        self.spin_pat_y_offset.setValue(float(cfg.get("patient_y_offset_mm", 0.0)))
        
        self.spin_name_x.setValue(float(cfg.get("name_x_mm", 12.0)))
        self.spin_gender_x.setValue(float(cfg.get("gender_x_mm", 44.0)))
        self.spin_age_x.setValue(float(cfg.get("age_x_mm", 68.0)))
        self.spin_token_x.setValue(float(cfg.get("token_x_mm", 88.0)))
        self.spin_date_x.setValue(float(cfg.get("date_x_mm", 112.0)))
        self.chk_show_badge.setChecked(bool(cfg.get("show_token_badge", True)))

        # Reserved Area & Margins
        self.spin_reserved_top.setValue(float(cfg.get("reserved_top_area_mm", 0.0)))
        self.chk_show_guide.setChecked(bool(cfg.get("show_reserved_area_guide", True)))
        self._set_combo(self.combo_font, cfg.get("font_family", "Arial"))
        self.spin_margin_left.setValue(float(cfg.get("margin_left_mm", 12.0)))
        self.spin_margin_top.setValue(float(cfg.get("top_margin_mm", 14.0)))

    def _set_combo(self, combo: QComboBox, text: str):
        idx = combo.findText(text)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentText(text)

    def _collect_config_from_ui(self) -> dict:
        return {
            "font_family": self.combo_font.currentText(),
            "margin_left_mm": self.spin_margin_left.value(),
            "top_margin_mm": self.spin_margin_top.value(),
            "reserved_top_area_mm": self.spin_reserved_top.value(),
            "show_reserved_area_guide": self.chk_show_guide.isChecked(),

            "doc_name_font_size": self.spin_doc_size.value(),
            "doc_name_font_style": self.combo_doc_style.currentText(),
            "doc_name_line_spacing_mm": self.spin_doc_line_spacing.value(),
            
            "degrees_font_size": self.spin_deg_size.value(),
            "degrees_font_style": self.combo_deg_style.currentText(),
            "degrees_spacing_mm": self.spin_deg_spacing.value(),
            
            "specialization_font_size": self.spin_spec_size.value(),
            "specialization_font_style": self.combo_spec_style.currentText(),
            "doctor_bottom_spacing_mm": self.spin_doc_bottom_gap.value(),

            "patient_font_size": self.spin_pat_size.value(),
            "patient_label_style": self.combo_pat_lbl_style.currentText(),
            "patient_value_style": self.combo_pat_val_style.currentText(),
            "patient_y_offset_mm": self.spin_pat_y_offset.value(),

            "name_x_mm": self.spin_name_x.value(),
            "gender_x_mm": self.spin_gender_x.value(),
            "age_x_mm": self.spin_age_x.value(),
            "token_x_mm": self.spin_token_x.value(),
            "date_x_mm": self.spin_date_x.value(),

            "show_token_badge": self.chk_show_badge.isChecked(),
            "token_font_size": 9.0,
            "token_font_style": "Bold",
            "token_badge_padding_mm": 3.5,
            "token_badge_height_mm": 5.2
        }

    def _on_control_changed(self):
        """Refreshes the live preview immediately when any slider/spinbox changes."""
        self.active_config = self._collect_config_from_ui()
        self.preview_widget.updatePreview()

    def _on_paint_requested(self, printer: QPrinter):
        """Renders prescription header directly onto QPrintPreviewWidget."""
        from PySide6.QtGui import QPainter
        painter = QPainter(printer)
        dpi = printer.resolution()
        render_slip_on_painter(
            painter, dpi,
            patient=self.patient,
            doctor=self.doctor,
            visit=self.visit,
            config=self.active_config,
            is_preview=True
        )
        painter.end()

    def _toggle_settings_panel(self, checked: bool):
        self.settings_panel.setVisible(checked)

    def _on_save_defaults(self):
        """Persists active settings into slip_config.json."""
        self.active_config = self._collect_config_from_ui()
        if save_slip_config(self.active_config):
            QMessageBox.information(
                self, "Saved",
                "These font styles, sizes, and reserved area adjustments are now saved as your default settings!"
            )

    def _on_reset_defaults(self):
        """Resets to defaults."""
        reply = QMessageBox.question(
            self, "Reset Defaults",
            "Reset all font styles, sizes, reserved area, and column allocations to recommended defaults?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.active_config = DEFAULT_CONFIG.copy()
            self._load_values_into_ui()
            self.preview_widget.updatePreview()

    def _on_export_pdf(self):
        """Generates PDF slip with current settings."""
        self.active_config = self._collect_config_from_ui()
        pdf_path = generate_prescription_pdf(self.patient, self.doctor, self.visit, self.active_config)
        QMessageBox.information(
            self, "PDF Saved",
            f"Prescription PDF saved successfully:\n\n{pdf_path}"
        )

    def _on_print_now(self):
        """Prints directly to the printer using current adjusted configuration."""
        self.active_config = self._collect_config_from_ui()
        # Save as defaults automatically
        save_slip_config(self.active_config)

        # Show standard system print dialog
        print_dialog = QPrintDialog(self.printer, self)
        print_dialog.setWindowTitle("Print Prescription Slip")
        if print_dialog.exec() == QPrintDialog.Accepted:
            from PySide6.QtGui import QPainter
            painter = QPainter(self.printer)
            dpi = self.printer.resolution()
            render_slip_on_painter(
                painter, dpi,
                patient=self.patient,
                doctor=self.doctor,
                visit=self.visit,
                config=self.active_config,
                is_preview=False
            )
            painter.end()
            self.accept()
