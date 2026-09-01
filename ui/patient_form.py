from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QPushButton, QMessageBox, QLabel
)
from PySide6.QtCore import Signal, Qt
from models.patient import create_patient


class PatientForm(QWidget):
    """Compact inline patient form — contact is set externally."""
    patient_saved = Signal(int)

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        form = QFormLayout()
        form.setSpacing(6)

        self.contact_edit = QLineEdit()
        self.contact_edit.setReadOnly(True)
        self.contact_edit.setPlaceholderText("Auto-filled")

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Full name…")

        row = QHBoxLayout()
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["male", "female", "other"])
        self.age_spin = QSpinBox()
        self.age_spin.setRange(0, 150)
        self.age_spin.setSpecialValueText("—")
        row.addWidget(self.gender_combo, 1)
        row.addWidget(self.age_spin, 1)

        form.addRow("Contact:", self.contact_edit)
        form.addRow("Name:", self.name_edit)
        form.addRow("Gender / Age:", row)
        layout.addLayout(form)

        self.save_btn = QPushButton("＋  Add Patient")
        self.save_btn.setObjectName("addPatBtn")
        self.save_btn.clicked.connect(self.save_patient)
        layout.addWidget(self.save_btn)

    def set_contact(self, contact: str):
        self.contact_edit.setText(contact)

    def clear_fields(self):
        self.name_edit.clear()
        self.age_spin.setValue(0)

    def save_patient(self):
        contact = self.contact_edit.text().strip()
        name = self.name_edit.text().strip()
        gender = self.gender_combo.currentText()
        age = self.age_spin.value()

        if not contact:
            QMessageBox.warning(self, "No Contact", "Please enter a contact number first.")
            return
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter the patient's name.")
            return
        try:
            new_id = create_patient(contact, name, gender, age=age if age > 0 else None)
            self.patient_saved.emit(new_id)
        except Exception as e:
            QMessageBox.critical(self, "Database Error", str(e))
