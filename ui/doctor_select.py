from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel, QFrame
)
from PySide6.QtCore import Signal, QTimer, Qt
from models.doctor import search_doctors, get_specializations, Doctor


class DoctorSelect(QWidget):
    doctor_selected = Signal(Doctor)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # ── Search / filter row ───────────────────────────────────────────────
        search_layout = QHBoxLayout()
        search_layout.setSpacing(10)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("🔍  Search doctor by name…")
        self.search_edit.setMinimumHeight(38)

        self.spec_combo = QComboBox()
        self.spec_combo.setMinimumHeight(38)
        self.spec_combo.addItem("All Specializations")
        try:
            self.spec_combo.addItems(get_specializations())
        except Exception:
            pass  # no connection yet

        search_layout.addWidget(self.search_edit, 2)
        search_layout.addWidget(self.spec_combo, 1)
        layout.addLayout(search_layout)

        # ── Status label (shown when empty) ───────────────────────────────────
        self.status_label = QLabel("Loading doctors…")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #94A3B8; font-size: 13px; padding: 8px;")
        layout.addWidget(self.status_label)

        # ── Doctors table ─────────────────────────────────────────────────────
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Doctor Name", "Specialization"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(220)         # always visible even when few rows
        self.table.setStyleSheet("""
            QTableWidget {
                border: 1.5px solid #BAE6FD;
                border-radius: 8px;
                background-color: #FFFFFF;
                font-size: 14px;
            }
            QTableWidget::item { padding: 10px 12px; }
            QTableWidget::item:selected { background-color: #E0F2FE; color: #0369A1; font-weight: bold; }
            QTableWidget::item:hover:!selected { background-color: #F0F9FF; }
        """)
        self.table.itemSelectionChanged.connect(self.on_selection)
        layout.addWidget(self.table)

        # ── Debounce timer ────────────────────────────────────────────────────
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.load_doctors)

        self.search_edit.textChanged.connect(lambda: self.timer.start(350))
        self.spec_combo.currentIndexChanged.connect(self.load_doctors)

        self.current_doctors = []
        self.load_doctors()

    # ── Load / display ────────────────────────────────────────────────────────

    def load_doctors(self):
        query = self.search_edit.text().strip()
        spec = self.spec_combo.currentText()
        if spec == "All Specializations":
            spec = ""

        try:
            self.current_doctors = search_doctors(query, spec)
        except Exception as e:
            self.status_label.setText(f"⚠️  Could not load doctors: {e}")
            self.status_label.show()
            return

        self.table.setRowCount(len(self.current_doctors))

        if not self.current_doctors:
            self.status_label.setText("No doctors found. Try a different search or check your Supabase data.")
            self.status_label.show()
        else:
            self.status_label.hide()

        for i, doc in enumerate(self.current_doctors):
            name_item = QTableWidgetItem(f"  {doc.name}")
            name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            spec_item = QTableWidgetItem(f"  {doc.specialization}")
            spec_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)

            self.table.setItem(i, 0, name_item)
            self.table.setItem(i, 1, spec_item)
            self.table.setRowHeight(i, 40)

    def on_selection(self):
        selected = self.table.selectedItems()
        if selected:
            row = selected[0].row()
            if 0 <= row < len(self.current_doctors):
                self.doctor_selected.emit(self.current_doctors[row])
