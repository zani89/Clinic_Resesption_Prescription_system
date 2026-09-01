from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QFrame, QListWidget, QListWidgetItem,
    QPushButton, QMessageBox, QSizePolicy
)
from PySide6.QtCore import QTimer, QDate, QTime, Qt
from models.patient import find_by_contact, Patient
from models.visit import create_visit, Visit
from models.doctor import search_doctors, get_specializations, Doctor
from ui.patient_form import PatientForm
from ui.print_slip import print_slip
from ui.slip_settings_dialog import SlipSettingsDialog

MAX_VISIBLE_PATIENTS = 5   # cap before showing "+N more"
MAX_VISIBLE_DOCTORS  = 8   # show at most 8 doctors without scrolling


def _panel(title: str) -> tuple:
    """Return a styled white panel frame + its inner QVBoxLayout."""
    frame = QFrame()
    frame.setStyleSheet(
        "QFrame { background: white; border: 1px solid #BAD9F1; border-radius: 8px; }"
    )
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(6)

    header = QLabel(title)
    header.setStyleSheet(
        "font-weight: bold; font-size: 13px; color: #1A5276; "
        "border: none; background: transparent;"
    )
    layout.addWidget(header)

    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet("border: 1px solid #D6EAF8;")
    layout.addWidget(sep)

    return frame, layout


class IntakeScreen(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(8)

        # ── TOP STRIP: contact number + slip settings button ──────────────
        top = QFrame()
        top.setStyleSheet(
            "QFrame { background: white; border: 1px solid #BAD9F1; border-radius: 8px; }"
        )
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(12, 8, 12, 8)
        top_layout.setSpacing(10)

        lbl = QLabel("📞  Contact:")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px; border: none; background: transparent;")
        top_layout.addWidget(lbl)

        self.contact_edit = QLineEdit()
        self.contact_edit.setPlaceholderText("Enter 11-digit number (spaces ignored)…")
        self.contact_edit.setMaxLength(15)
        self.contact_edit.setStyleSheet("font-size: 15px; padding: 7px 12px;")
        top_layout.addWidget(self.contact_edit, 1)

        self.digit_lbl = QLabel("0 / 11")
        self.digit_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; min-width: 50px; border: none; background: transparent;")
        top_layout.addWidget(self.digit_lbl)

        self.settings_btn = QPushButton("⚙️  Slip Font & Allocation Settings")
        self.settings_btn.setStyleSheet(
            "background: #0284C7; color: white; font-size: 13px; font-weight: 600; padding: 7px 14px; border-radius: 6px;"
        )
        self.settings_btn.clicked.connect(self._open_slip_settings)
        top_layout.addWidget(self.settings_btn)

        root.addWidget(top)

        # ── MIDDLE: split panels ───────────────────────────────────────────
        middle = QHBoxLayout()
        middle.setSpacing(10)

        # ── LEFT PANEL: linked patients + quick add form ───────────────────
        left_frame, left_layout = _panel("Linked Patients")

        self.patient_list = QListWidget()
        self.patient_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.patient_list.setMaximumHeight(MAX_VISIBLE_PATIENTS * 42)
        self.patient_list.itemClicked.connect(self._on_patient_clicked)
        left_layout.addWidget(self.patient_list)

        self.more_lbl = QLabel("")
        self.more_lbl.setAlignment(Qt.AlignCenter)
        self.more_lbl.setStyleSheet("color: #5D8AA8; font-size: 12px; border: none; background: transparent;")
        self.more_lbl.hide()
        left_layout.addWidget(self.more_lbl)

        self.no_pat_lbl = QLabel("Type a contact number above to search.")
        self.no_pat_lbl.setAlignment(Qt.AlignCenter)
        self.no_pat_lbl.setWordWrap(True)
        self.no_pat_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; border: none; background: transparent;")
        left_layout.addWidget(self.no_pat_lbl)

        # quick-add divider
        div = QFrame()
        div.setFrameShape(QFrame.HLine)
        div.setStyleSheet("border: 1px solid #D6EAF8; margin-top: 4px;")
        left_layout.addWidget(div)

        add_lbl = QLabel("Quick Add Patient")
        add_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #27AE60; border: none; background: transparent;")
        left_layout.addWidget(add_lbl)

        self.patient_form = PatientForm()
        self.patient_form.patient_saved.connect(self._on_patient_created)
        left_layout.addWidget(self.patient_form)
        left_layout.addStretch()

        middle.addWidget(left_frame, 1)

        # ── RIGHT PANEL: doctor selection ──────────────────────────────────
        right_frame, right_layout = _panel("Select Doctor")

        self.doc_search = QLineEdit()
        self.doc_search.setPlaceholderText("🔍  Search by name…")
        right_layout.addWidget(self.doc_search)

        self.doc_list = QListWidget()
        self.doc_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.doc_list.setMaximumHeight(MAX_VISIBLE_DOCTORS * 42)
        self.doc_list.itemClicked.connect(self._on_doctor_clicked)
        right_layout.addWidget(self.doc_list)

        self.no_doc_lbl = QLabel("No doctors found.")
        self.no_doc_lbl.setAlignment(Qt.AlignCenter)
        self.no_doc_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; border: none; background: transparent;")
        self.no_doc_lbl.hide()
        right_layout.addWidget(self.no_doc_lbl)
        right_layout.addStretch()

        middle.addWidget(right_frame, 1)
        root.addLayout(middle, 1)

        # ── BOTTOM BAR: summary + print button ────────────────────────────
        bar = QFrame()
        bar.setStyleSheet(
            "QFrame { background: #1A5276; border-radius: 8px; }"
        )
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(16, 10, 16, 10)
        bar_layout.setSpacing(20)

        self.summary_lbl = QLabel("Select a patient and a doctor to continue…")
        self.summary_lbl.setStyleSheet("color: #AED6F1; font-size: 13px; border: none; background: transparent;")
        self.summary_lbl.setWordWrap(True)
        bar_layout.addWidget(self.summary_lbl, 1)

        self.token_lbl = QLabel("")
        self.token_lbl.setStyleSheet(
            "color: white; font-size: 20px; font-weight: bold; border: none; background: transparent;"
        )
        bar_layout.addWidget(self.token_lbl)

        self.print_btn = QPushButton("🖨  Save & Print Prescription")
        self.print_btn.setObjectName("printBtn")
        self.print_btn.setEnabled(False)
        self.print_btn.clicked.connect(self._save_and_print)
        bar_layout.addWidget(self.print_btn)

        root.addWidget(bar)

        # ── State ──────────────────────────────────────────────────────────
        self.selected_patient: Patient | None = None
        self.selected_doctor:  Doctor  | None = None
        self.current_patients: list[Patient] = []
        self.current_doctors:  list[Doctor]  = []

        # ── Timers ─────────────────────────────────────────────────────────
        self._contact_timer = QTimer()
        self._contact_timer.setSingleShot(True)
        self._contact_timer.timeout.connect(self._search_patients)

        self._doc_timer = QTimer()
        self._doc_timer.setSingleShot(True)
        self._doc_timer.timeout.connect(self._load_doctors)

        self.contact_edit.textChanged.connect(self._on_contact_changed)
        self.doc_search.textChanged.connect(lambda: self._doc_timer.start(350))

        self._load_doctors()

    # ── Helpers ──────────────────────────────────────────────────────────

    def _clean_contact(self) -> str:
        return self.contact_edit.text().replace(" ", "")

    def _on_contact_changed(self):
        digits = self._clean_contact()
        count = len(digits)

        if count > 11:
            self.contact_edit.blockSignals(True)
            self.contact_edit.setText(digits[:11])
            self.contact_edit.blockSignals(False)
            digits = digits[:11]
            count = 11

        self.digit_lbl.setText(f"{count} / 11")
        color = "#20B2AA" if count == 11 else "#94A3B8"
        self.digit_lbl.setStyleSheet(
            f"color: {color}; font-size: 12px; min-width: 50px; "
            "border: none; background: transparent;"
        )

        self.patient_form.set_contact(digits)
        self.selected_patient = None
        self._update_bar()

        if count >= 3:
            self._contact_timer.start(400)
        else:
            self._clear_patient_list()

    def _clear_patient_list(self):
        self.patient_list.clear()
        self.current_patients = []
        self.more_lbl.hide()
        self.no_pat_lbl.setText("Type a contact number above to search.")
        self.no_pat_lbl.show()

    def _search_patients(self):
        contact = self._clean_contact()
        if not contact:
            self._clear_patient_list()
            return

        self.current_patients = find_by_contact(contact)
        self.patient_list.clear()
        self.more_lbl.hide()

        visible = self.current_patients[:MAX_VISIBLE_PATIENTS]
        extra = len(self.current_patients) - MAX_VISIBLE_PATIENTS

        if visible:
            self.no_pat_lbl.hide()
            for p in visible:
                age_str = f"{p.age}y" if p.age else "?"
                item = QListWidgetItem(
                    f"👤  {p.name}   ·   {age_str}   ·   {str(p.gender).capitalize()}"
                )
                item.setData(Qt.UserRole, p.id)
                self.patient_list.addItem(item)

            if extra > 0:
                self.more_lbl.setText(f"+ {extra} more patient(s) on this number")
                self.more_lbl.show()
        else:
            self.no_pat_lbl.setText(
                "No patients found for this number.\n"
                "Use the Quick Add form on the left to register one."
            )
            self.no_pat_lbl.show()

        self.selected_patient = None
        self._update_bar()

    def _on_patient_clicked(self, item: QListWidgetItem):
        idx = self.patient_list.row(item)
        if 0 <= idx < len(self.current_patients):
            self.selected_patient = self.current_patients[idx]
            self._update_bar()

    def _on_patient_created(self, patient_id: int):
        contact = self._clean_contact()
        self.current_patients = find_by_contact(contact)
        self.patient_list.clear()
        self.more_lbl.hide()

        visible = self.current_patients[:MAX_VISIBLE_PATIENTS]
        extra   = len(self.current_patients) - MAX_VISIBLE_PATIENTS
        sel_idx = 0

        for i, p in enumerate(visible):
            age_str = f"{p.age}y" if p.age else "?"
            item = QListWidgetItem(
                f"👤  {p.name}   ·   {age_str}   ·   {str(p.gender).capitalize()}"
            )
            item.setData(Qt.UserRole, p.id)
            self.patient_list.addItem(item)
            if p.id == patient_id:
                sel_idx = i
                self.selected_patient = p

        if extra > 0:
            self.more_lbl.setText(f"+ {extra} more patient(s) on this number")
            self.more_lbl.show()

        self.no_pat_lbl.hide()
        self.patient_list.setCurrentRow(sel_idx)
        self.patient_form.clear_fields()
        self._update_bar()

    def _load_doctors(self):
        query = self.doc_search.text().strip()
        try:
            self.current_doctors = search_doctors(query)
        except Exception:
            self.current_doctors = []

        self.doc_list.clear()
        visible = self.current_doctors[:MAX_VISIBLE_DOCTORS]

        if visible:
            self.no_doc_lbl.hide()
            for doc in visible:
                item = QListWidgetItem(
                    f"👨‍⚕️  {doc.name}   ·   {doc.specialization}"
                )
                item.setData(Qt.UserRole, doc.id)
                self.doc_list.addItem(item)
        else:
            self.no_doc_lbl.show()

    def _on_doctor_clicked(self, item: QListWidgetItem):
        idx = self.doc_list.row(item)
        if 0 <= idx < len(self.current_doctors):
            self.selected_doctor = self.current_doctors[idx]
            self._update_bar()

    def _update_bar(self):
        if self.selected_patient and self.selected_doctor:
            p, d = self.selected_patient, self.selected_doctor
            age_str = f"{p.age}y" if p.age else "?"
            self.summary_lbl.setText(
                f"Patient: {p.name}  ({age_str}, {str(p.gender).capitalize()})   →   "
                f"Dr. {d.name}  [{d.specialization}]"
            )
            self.summary_lbl.setStyleSheet(
                "color: #A9DFBF; font-size: 13px; font-weight: bold; border: none; background: transparent;"
            )
            self.token_lbl.setText("")
            self.print_btn.setEnabled(True)
        else:
            self.summary_lbl.setText("Select a patient and a doctor to continue…")
            self.summary_lbl.setStyleSheet(
                "color: #AED6F1; font-size: 13px; border: none; background: transparent;"
            )
            self.token_lbl.setText("")
            self.print_btn.setEnabled(False)

    def _save_and_print(self):
        if not self.selected_patient or not self.selected_doctor:
            return
        today = QDate.currentDate().toString("yyyy-MM-dd")
        now   = QTime.currentTime().toString("HH:mm:ss")
        try:
            visit_id = create_visit(
                self.selected_patient.id,
                self.selected_doctor.id,
                today, now
            )
            from db.database import get_supabase
            sb = get_supabase()
            v_row = sb.table("visits").select("*").eq("id", visit_id).execute().data[0]
            visit = Visit(**v_row)

            self.token_lbl.setText(f"Token #{visit.token_number}")

            print_slip(self.selected_patient, self.selected_doctor, visit)

            QMessageBox.information(
                self, "Done",
                f"Visit saved — Token #{visit.token_number} for {self.selected_patient.name}"
            )

            # Reset for next patient
            self.contact_edit.clear()
            self.patient_list.clear()
            self.patient_form.clear_fields()
            self.doc_list.clearSelection()
            self.selected_patient = None
            self.selected_doctor  = None
            self.no_pat_lbl.setText("Type a contact number above to search.")
            self.no_pat_lbl.show()
            self._update_bar()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _open_slip_settings(self):
        dialog = SlipSettingsDialog(self)
        dialog.exec()
