"""
slip_settings_dialog.py — Interactive layout, font style, reserved area, and font adjustment dialog with real-time live preview.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel,
    QDoubleSpinBox, QCheckBox, QComboBox, QPushButton, QFrame,
    QTabWidget, QWidget, QMessageBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor, QPixmap
from models.slip_config import load_slip_config, save_slip_config, reset_slip_config_to_defaults, DEFAULT_CONFIG
from ui.print_slip import render_preview_pixmap, print_slip

FONT_STYLES = ["Bold", "Regular", "Italic", "Bold Italic"]


class SlipSettingsDialog(QDialog):
    settings_saved = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Prescription Header — Font Style, Reserved Area & Allocation Settings")
        self.resize(1100, 720)
        self.setMinimumSize(960, 620)

        # Load active settings
        self.config = load_slip_config()

        # Build UI
        self._build_ui()
        self._load_values_into_ui()
        self._update_preview()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # ── Header Description ─────────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setStyleSheet(
            "QFrame { background: #E8F4FD; border: 1px solid #BAD9F1; border-radius: 8px; padding: 6px; }"
        )
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(12, 6, 12, 6)
        
        info_lbl = QLabel(
            "<b>Prescription Slip Customizer:</b> Adjust font styles (Bold, Regular, Italic), font sizes, "
            "pre-printed letterhead reserved areas, margins, and horizontal column allocations in real-time."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #1A5276; font-size: 13px; border: none; background: transparent;")
        h_layout.addWidget(info_lbl)
        main_layout.addWidget(header_frame)

        # ── Main Content Split (Controls Left | Live Preview Right) ─────────
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # ── Left: Tabs for settings controls ────────────────────────────────
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane { border: 1px solid #BAD9F1; background: white; border-radius: 6px; }"
        )
        self.tabs.addTab(self._create_doctor_tab(), "👨‍⚕️ Doctor Info")
        self.tabs.addTab(self._create_patient_tab(), "👤 Patient & Columns")
        self.tabs.addTab(self._create_reserved_and_page_tab(), "🏛 Reserved Area & Margins")
        
        content_layout.addWidget(self.tabs, 1)

        # ── Right: Live Preview Panel ───────────────────────────────────────
        preview_container = QFrame()
        preview_container.setStyleSheet(
            "QFrame { background: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 8px; }"
        )
        prev_vbox = QVBoxLayout(preview_container)
        prev_vbox.setContentsMargins(14, 12, 14, 12)
        prev_vbox.setSpacing(10)

        prev_title = QLabel("🔍  Real-Time Header Preview (A5 Size)")
        prev_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #1E293B; border: none; background: transparent;")
        prev_vbox.addWidget(prev_title)

        # Scroll area for the preview image
        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setStyleSheet(
            "QScrollArea { background: white; border: 1px solid #E2E8F0; border-radius: 6px; }"
        )
        
        self.preview_lbl = QLabel()
        self.preview_lbl.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.preview_lbl.setStyleSheet("background: white; padding: 10px; border: none;")
        self.preview_scroll.setWidget(self.preview_lbl)
        prev_vbox.addWidget(self.preview_scroll, 1)

        # Preview toolbar / Test print button
        prev_bar = QHBoxLayout()
        sample_info = QLabel("<i>Sample preview with Dr. Amjad Hussain & Token #7</i>")
        sample_info.setStyleSheet("color: #64748B; font-size: 11px; border: none; background: transparent;")
        prev_bar.addWidget(sample_info)
        prev_bar.addStretch()

        self.test_print_btn = QPushButton("🖨  Open Print Screen")
        self.test_print_btn.setStyleSheet(
            "background: #0284C7; color: white; padding: 6px 14px; font-weight: bold; border-radius: 5px;"
        )
        self.test_print_btn.clicked.connect(self._on_test_print)
        prev_bar.addWidget(self.test_print_btn)
        prev_vbox.addLayout(prev_bar)

        content_layout.addWidget(preview_container, 1)
        main_layout.addLayout(content_layout, 1)

        # ── Bottom Action Bar ───────────────────────────────────────────────
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 8, 0, 0)
        bottom_bar.setSpacing(12)

        self.reset_btn = QPushButton("🔄  Reset to Recommended Defaults")
        self.reset_btn.setStyleSheet(
            "background: #E2E8F0; color: #334155; padding: 8px 16px; font-weight: 600; border-radius: 6px;"
        )
        self.reset_btn.clicked.connect(self._on_reset_defaults)
        bottom_bar.addWidget(self.reset_btn)

        bottom_bar.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet(
            "background: #94A3B8; color: white; padding: 8px 20px; font-weight: 600; border-radius: 6px;"
        )
        self.cancel_btn.clicked.connect(self.reject)
        bottom_bar.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("💾  Save & Apply Settings")
        self.save_btn.setStyleSheet(
            "background: #27AE60; color: white; padding: 9px 24px; font-weight: bold; font-size: 13px; border-radius: 6px;"
        )
        self.save_btn.clicked.connect(self._on_save)
        bottom_bar.addWidget(self.save_btn)

        main_layout.addLayout(bottom_bar)

    # ── TAB CREATION HELPERS ─────────────────────────────────────────────────
    def _create_doctor_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        grid = QGridLayout()
        grid.setVerticalSpacing(8)
        grid.setHorizontalSpacing(12)

        row = 0
        # Doctor Name Font Size & Style
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
        # Bottom Gap to Patient Row
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

    def _create_patient_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        # ── 1. Patient Row Divider Lines ──────────────────────────────────
        sec_lines = QLabel("<b>📏 Patient Row Divider Lines:</b>")
        sec_lines.setStyleSheet("color: #1A5276; font-size: 12px;")
        layout.addWidget(sec_lines)

        grid_lines = QGridLayout()
        grid_lines.setVerticalSpacing(6)
        grid_lines.setHorizontalSpacing(12)

        self.chk_show_patient_lines = QCheckBox("Show Lines at Top & Bottom of Patient Details")
        self.chk_show_patient_lines.setStyleSheet("font-weight: 600; color: #0F172A;")
        self.chk_show_patient_lines.stateChanged.connect(self._on_control_changed)
        grid_lines.addWidget(self.chk_show_patient_lines, 0, 0, 1, 2)

        grid_lines.addWidget(QLabel("Lines Style:"), 1, 0)
        self.combo_lines_style = QComboBox()
        self.combo_lines_style.addItems(["Single", "Double"])
        self.combo_lines_style.currentTextChanged.connect(self._on_control_changed)
        grid_lines.addWidget(self.combo_lines_style, 1, 1)

        grid_lines.addWidget(QLabel("Line Thickness:"), 2, 0)
        self.spin_line_thickness = QDoubleSpinBox()
        self.spin_line_thickness.setRange(0.5, 4.0)
        self.spin_line_thickness.setSingleStep(0.5)
        self.spin_line_thickness.setSuffix(" pt")
        self.spin_line_thickness.valueChanged.connect(self._on_control_changed)
        grid_lines.addWidget(self.spin_line_thickness, 2, 1)

        grid_lines.addWidget(QLabel("Line Color:"), 3, 0)
        self.combo_line_color = QComboBox()
        self.combo_line_color.addItems([
            "Teal (#00677F)",
            "Dark Slate (#1E293B)",
            "Charcoal (#0F172A)",
            "Gray (#94A3B8)"
        ])
        self.combo_line_color.currentTextChanged.connect(self._on_control_changed)
        grid_lines.addWidget(self.combo_line_color, 3, 1)

        grid_lines.addWidget(QLabel("Line Alignment:"), 4, 0)
        self.combo_lines_align = QComboBox()
        self.combo_lines_align.addItems([
            "Full Width",
            "Match Content",
            "Compact Inset"
        ])
        self.combo_lines_align.currentTextChanged.connect(self._on_control_changed)
        grid_lines.addWidget(self.combo_lines_align, 4, 1)

        layout.addLayout(grid_lines)

        div0 = QFrame()
        div0.setFrameShape(QFrame.HLine)
        div0.setStyleSheet("border: 1px solid #E2E8F0; margin: 4px 0;")
        layout.addWidget(div0)

        # ── 2. General Font & Styles ──────────────────────────────────────
        sec1_lbl = QLabel("<b>✏️ Patient Row Typography & Styles:</b>")
        sec1_lbl.setStyleSheet("color: #1A5276; font-size: 12px;")
        layout.addWidget(sec1_lbl)

        grid1 = QGridLayout()
        grid1.setVerticalSpacing(7)
        grid1.setHorizontalSpacing(12)

        grid1.addWidget(QLabel("Patient Font Size:"), 0, 0)
        self.spin_pat_size = QDoubleSpinBox()
        self.spin_pat_size.setRange(5.0, 18.0)
        self.spin_pat_size.setSingleStep(0.5)
        self.spin_pat_size.setSuffix(" pt")
        self.spin_pat_size.valueChanged.connect(self._on_control_changed)
        grid1.addWidget(self.spin_pat_size, 0, 1)

        grid1.addWidget(QLabel("Labels Style (Name, Gender, Age):"), 1, 0)
        self.combo_pat_lbl_style = QComboBox()
        self.combo_pat_lbl_style.addItems(FONT_STYLES)
        self.combo_pat_lbl_style.currentTextChanged.connect(self._on_control_changed)
        grid1.addWidget(self.combo_pat_lbl_style, 1, 1)

        grid1.addWidget(QLabel("Values Style (Patient details):"), 2, 0)
        self.combo_pat_val_style = QComboBox()
        self.combo_pat_val_style.addItems(FONT_STYLES)
        self.combo_pat_val_style.currentTextChanged.connect(self._on_control_changed)
        grid1.addWidget(self.combo_pat_val_style, 2, 1)

        grid1.addWidget(QLabel("Vertical Shift / Offset:"), 3, 0)
        self.spin_pat_y_offset = QDoubleSpinBox()
        self.spin_pat_y_offset.setRange(-20.0, 40.0)
        self.spin_pat_y_offset.setSingleStep(0.5)
        self.spin_pat_y_offset.setSuffix(" mm")
        self.spin_pat_y_offset.valueChanged.connect(self._on_control_changed)
        grid1.addWidget(self.spin_pat_y_offset, 3, 1)

        layout.addLayout(grid1)

        # ── 3. Horizontal Allocations & Page Fit ─────────────────────────
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("border: 1px solid #E2E8F0; margin: 4px 0;")
        layout.addWidget(div)

        sec2_lbl = QLabel("<b>↔ Horizontal Column Spacing & Page Fit:</b>")
        sec2_lbl.setStyleSheet("color: #1A5276; font-size: 12px;")
        layout.addWidget(sec2_lbl)

        self.chk_auto_fit = QCheckBox("✨ Auto-fit Spacing to Page Width (Recommended)")
        self.chk_auto_fit.setStyleSheet("font-weight: 600; color: #0284C7;")
        self.chk_auto_fit.toggled.connect(self._on_auto_fit_toggled)
        layout.addWidget(self.chk_auto_fit)

        # Container for manual spinboxes
        self.manual_alloc_container = QWidget()
        manual_layout = QVBoxLayout(self.manual_alloc_container)
        manual_layout.setContentsMargins(0, 0, 0, 0)
        manual_layout.setSpacing(4)

        grid2 = QGridLayout()
        grid2.setVerticalSpacing(6)
        grid2.setHorizontalSpacing(12)

        # Name X
        grid2.addWidget(QLabel("Name Column:"), 0, 0)
        self.spin_name_x = QDoubleSpinBox()
        self.spin_name_x.setRange(0.0, 220.0)
        self.spin_name_x.setSingleStep(1.0)
        self.spin_name_x.setSuffix(" mm")
        self.spin_name_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_name_x, 0, 1)

        # Gender X
        grid2.addWidget(QLabel("Gender Column:"), 1, 0)
        self.spin_gender_x = QDoubleSpinBox()
        self.spin_gender_x.setRange(0.0, 220.0)
        self.spin_gender_x.setSingleStep(1.0)
        self.spin_gender_x.setSuffix(" mm")
        self.spin_gender_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_gender_x, 1, 1)

        # Age X
        grid2.addWidget(QLabel("Age Column:"), 2, 0)
        self.spin_age_x = QDoubleSpinBox()
        self.spin_age_x.setRange(0.0, 220.0)
        self.spin_age_x.setSingleStep(1.0)
        self.spin_age_x.setSuffix(" mm")
        self.spin_age_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_age_x, 2, 1)

        # Token Badge X
        grid2.addWidget(QLabel("Token Badge:"), 3, 0)
        self.spin_token_x = QDoubleSpinBox()
        self.spin_token_x.setRange(0.0, 220.0)
        self.spin_token_x.setSingleStep(1.0)
        self.spin_token_x.setSuffix(" mm")
        self.spin_token_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_token_x, 3, 1)

        # Date X
        grid2.addWidget(QLabel("Date Column:"), 4, 0)
        self.spin_date_x = QDoubleSpinBox()
        self.spin_date_x.setRange(0.0, 220.0)
        self.spin_date_x.setSingleStep(1.0)
        self.spin_date_x.setSuffix(" mm")
        self.spin_date_x.valueChanged.connect(self._on_control_changed)
        grid2.addWidget(self.spin_date_x, 4, 1)

        manual_layout.addLayout(grid2)
        layout.addWidget(self.manual_alloc_container)

        # Token Badge Box Details
        div2 = QFrame()
        div2.setFrameShape(QFrame.HLine)
        div2.setStyleSheet("border: 1px solid #E2E8F0; margin: 4px 0;")
        layout.addWidget(div2)

        self.chk_show_badge = QCheckBox("Show Teal Background Box on Token")
        self.chk_show_badge.stateChanged.connect(self._on_control_changed)
        layout.addWidget(self.chk_show_badge)

        # ── 4. Vertical Divider Line (Page Body) ──────────────────────────
        div3 = QFrame()
        div3.setFrameShape(QFrame.HLine)
        div3.setStyleSheet("border: 1px solid #E2E8F0; margin: 4px 0;")
        layout.addWidget(div3)

        sec3_lbl = QLabel("<b>📐 Vertical Divider Line (Page Body):</b>")
        sec3_lbl.setStyleSheet("color: #1A5276; font-size: 12px;")
        layout.addWidget(sec3_lbl)

        grid_v = QGridLayout()
        grid_v.setVerticalSpacing(6)
        grid_v.setHorizontalSpacing(12)

        self.chk_show_vertical_line = QCheckBox("Show Vertical Line on Left 1/3rd of Page")
        self.chk_show_vertical_line.setStyleSheet("font-weight: 600; color: #0F172A;")
        self.chk_show_vertical_line.stateChanged.connect(self._on_control_changed)
        grid_v.addWidget(self.chk_show_vertical_line, 0, 0, 1, 2)

        grid_v.addWidget(QLabel("Line Alignment:"), 1, 0)
        self.combo_vert_align = QComboBox()
        self.combo_vert_align.addItems([
            "Left 1/3rd (33.3%)",
            "Left 1/4th (25.0%)",
            "Left 30%",
            "Left 2/5th (40.0%)",
            "Center (50.0%)",
            "Custom Position"
        ])
        self.combo_vert_align.currentTextChanged.connect(self._on_vert_align_changed)
        grid_v.addWidget(self.combo_vert_align, 1, 1)

        grid_v.addWidget(QLabel("Line Ratio (%):"), 2, 0)
        self.spin_vert_ratio = QDoubleSpinBox()
        self.spin_vert_ratio.setRange(15.0, 60.0)
        self.spin_vert_ratio.setSingleStep(1.0)
        self.spin_vert_ratio.setSuffix(" %")
        self.spin_vert_ratio.valueChanged.connect(self._on_vert_ratio_changed)
        grid_v.addWidget(self.spin_vert_ratio, 2, 1)

        grid_v.addWidget(QLabel("Line Thickness:"), 3, 0)
        self.spin_vert_thickness = QDoubleSpinBox()
        self.spin_vert_thickness.setRange(0.5, 4.0)
        self.spin_vert_thickness.setSingleStep(0.5)
        self.spin_vert_thickness.setSuffix(" pt")
        self.spin_vert_thickness.valueChanged.connect(self._on_control_changed)
        grid_v.addWidget(self.spin_vert_thickness, 3, 1)

        self.chk_show_rx = QCheckBox("Show 'Rx' Symbol Beside Vertical Line")
        self.chk_show_rx.stateChanged.connect(self._on_control_changed)
        grid_v.addWidget(self.chk_show_rx, 4, 0, 1, 2)

        layout.addLayout(grid_v)

        layout.addStretch()
        scroll.setWidget(tab)
        return scroll

    def _create_reserved_and_page_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Reserved Pre-printed Area
        sec_res = QLabel("<b>🏛 Pre-Printed Letterhead / Reserved Area:</b>")
        sec_res.setStyleSheet("color: #1A5276; font-size: 12px;")
        layout.addWidget(sec_res)

        grid_res = QGridLayout()
        grid_res.setVerticalSpacing(8)
        grid_res.setHorizontalSpacing(12)

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

        # Margins & Font
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("border: 1px solid #E2E8F0; margin: 4px 0;")
        layout.addWidget(div)

        sec_marg = QLabel("<b>📄 Margins & Font Family:</b>")
        sec_marg.setStyleSheet("color: #1A5276; font-size: 12px;")
        layout.addWidget(sec_marg)

        grid_marg = QGridLayout()
        grid_marg.setVerticalSpacing(8)
        grid_marg.setHorizontalSpacing(12)

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
        cfg = self.config

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

        # Patient Divider Lines
        self.chk_show_patient_lines.setChecked(bool(cfg.get("show_patient_lines", True)))
        self._set_combo(self.combo_lines_style, cfg.get("patient_lines_style", "Single"))
        self.spin_line_thickness.setValue(float(cfg.get("patient_line_thickness", 1.0)))
        self._set_line_color_combo(cfg.get("patient_line_color", "#00677F"))
        self._set_combo(self.combo_lines_align, cfg.get("patient_line_alignment", "Full Width"))

        # Patient Auto-fit Spacing
        is_autofit = bool(cfg.get("auto_fit_patient_row", True))
        self.chk_auto_fit.setChecked(is_autofit)
        self.manual_alloc_container.setEnabled(not is_autofit)
        
        self.spin_name_x.setValue(float(cfg.get("name_x_mm", 12.0)))
        self.spin_gender_x.setValue(float(cfg.get("gender_x_mm", 44.0)))
        self.spin_age_x.setValue(float(cfg.get("age_x_mm", 68.0)))
        self.spin_token_x.setValue(float(cfg.get("token_x_mm", 88.0)))
        self.spin_date_x.setValue(float(cfg.get("date_x_mm", 112.0)))
        self.chk_show_badge.setChecked(bool(cfg.get("show_token_badge", True)))

        # Vertical Divider Line
        self.chk_show_vertical_line.setChecked(bool(cfg.get("show_vertical_line", True)))
        self._set_combo(self.combo_vert_align, cfg.get("vertical_line_alignment", "Left 1/3rd (33.3%)"))
        self.spin_vert_ratio.setValue(float(cfg.get("vertical_line_ratio", 0.333)) * 100.0)
        self.spin_vert_thickness.setValue(float(cfg.get("vertical_line_thickness", 1.0)))
        self.chk_show_rx.setChecked(bool(cfg.get("show_rx_symbol", True)))

        # Reserved & Margins
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

    def _on_vert_align_changed(self, text: str):
        self.spin_vert_ratio.blockSignals(True)
        if "1/3" in text or "33.3" in text:
            self.spin_vert_ratio.setValue(33.3)
        elif "1/4" in text or "25" in text:
            self.spin_vert_ratio.setValue(25.0)
        elif "30%" in text:
            self.spin_vert_ratio.setValue(30.0)
        elif "2/5" in text or "40" in text:
            self.spin_vert_ratio.setValue(40.0)
        elif "Center" in text or "50" in text:
            self.spin_vert_ratio.setValue(50.0)
        self.spin_vert_ratio.blockSignals(False)
        self._on_control_changed()

    def _on_vert_ratio_changed(self, val: float):
        self.combo_vert_align.blockSignals(True)
        if abs(val - 33.3) < 0.3:
            self._set_combo(self.combo_vert_align, "Left 1/3rd (33.3%)")
        elif abs(val - 25.0) < 0.3:
            self._set_combo(self.combo_vert_align, "Left 1/4th (25.0%)")
        elif abs(val - 30.0) < 0.3:
            self._set_combo(self.combo_vert_align, "Left 30%")
        elif abs(val - 40.0) < 0.3:
            self._set_combo(self.combo_vert_align, "Left 2/5th (40.0%)")
        elif abs(val - 50.0) < 0.3:
            self._set_combo(self.combo_vert_align, "Center (50.0%)")
        else:
            self._set_combo(self.combo_vert_align, "Custom Position")
        self.combo_vert_align.blockSignals(False)
        self._on_control_changed()

    def _on_auto_fit_toggled(self, checked: bool):
        self.manual_alloc_container.setEnabled(not checked)
        self._on_control_changed()

    def _get_line_color_hex(self) -> str:
        text = self.combo_line_color.currentText()
        if "Dark Slate" in text:
            return "#1E293B"
        elif "Charcoal" in text:
            return "#0F172A"
        elif "Gray" in text:
            return "#94A3B8"
        return "#00677F"

    def _set_line_color_combo(self, color_hex: str):
        color_hex = str(color_hex).upper()
        if "1E293B" in color_hex:
            self.combo_line_color.setCurrentIndex(1)
        elif "0F172A" in color_hex:
            self.combo_line_color.setCurrentIndex(2)
        elif "94A3B8" in color_hex:
            self.combo_line_color.setCurrentIndex(3)
        else:
            self.combo_line_color.setCurrentIndex(0)

    def _collect_config_from_ui(self) -> dict:
        return {
            "font_family": self.combo_font.currentText(),
            "margin_left_mm": self.spin_margin_left.value(),
            "margin_right_mm": self.spin_margin_left.value(),
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

            # Patient Divider Lines
            "show_patient_lines": self.chk_show_patient_lines.isChecked(),
            "patient_lines_style": self.combo_lines_style.currentText(),
            "patient_line_thickness": self.spin_line_thickness.value(),
            "patient_line_color": self._get_line_color_hex(),
            "patient_line_alignment": self.combo_lines_align.currentText(),
            "patient_line_padding_top_mm": 5.5,
            "patient_line_padding_bottom_mm": 3.5,

            # Patient Auto-fit Spacing
            "auto_fit_patient_row": self.chk_auto_fit.isChecked(),

            # Vertical Divider Line (Page Body)
            "show_vertical_line": self.chk_show_vertical_line.isChecked(),
            "vertical_line_alignment": self.combo_vert_align.currentText(),
            "vertical_line_ratio": self.spin_vert_ratio.value() / 100.0,
            "vertical_line_thickness": self.spin_vert_thickness.value(),
            "show_rx_symbol": self.chk_show_rx.isChecked(),

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
        """Called whenever any control value changes to update the live preview instantly."""
        self._update_preview()

    def _update_preview(self):
        """Renders live pixmap with current configuration."""
        current_cfg = self._collect_config_from_ui()
        pix = render_preview_pixmap(config=current_cfg, target_width=520)
        self.preview_lbl.setPixmap(pix)

    def _on_test_print(self):
        """Opens full print screen with currently edited settings."""
        current_cfg = self._collect_config_from_ui()
        save_slip_config(current_cfg)
        print_slip(patient=None, doctor=None, visit=None, show_preview=True, config=current_cfg)

    def _on_reset_defaults(self):
        """Restores default values."""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "Are you sure you want to reset all font styles, sizes, reserved area, and allocations to recommended defaults?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.config = DEFAULT_CONFIG.copy()
            self._load_values_into_ui()
            self._update_preview()

    def _on_save(self):
        """Saves active configuration to disk and closes dialog."""
        current_cfg = self._collect_config_from_ui()
        if save_slip_config(current_cfg):
            QMessageBox.information(
                self, "Saved",
                "Prescription slip font styles, reserved area, and layout adjustments have been saved successfully!"
            )
            self.settings_saved.emit()
            self.accept()
        else:
            QMessageBox.critical(self, "Error", "Could not save configuration file.")
