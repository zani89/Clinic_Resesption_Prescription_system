"""
pdf_print.py — Generates the printable prescription overlay as a PDF.

Re-exports prescription PDF generation and printing functions from ui.print_slip.
"""

from ui.print_slip import (
    TEAL_COLOR,
    DARK_SLATE_COLOR,
    GRAY_TEXT_COLOR,
    OUTPUT_DIR,
    generate_prescription_pdf,
    send_to_printer,
    print_slip
)

__all__ = [
    "TEAL_COLOR",
    "DARK_SLATE_COLOR",
    "GRAY_TEXT_COLOR",
    "OUTPUT_DIR",
    "generate_prescription_pdf",
    "send_to_printer",
    "print_slip"
]

if __name__ == "__main__":
    sample_patient = {
        "name": "SIAL",
        "gender": "Male",
        "age": 15
    }
    sample_doctor = {
        "name": "Dr. Amjad Hussain Saddiqui",
        "specialization": "Child Specialist Pediatric Neurophysician"
    }
    sample_visit = {
        "token_number": 7,
        "visit_date": "2026-08-16"
    }
    pdf_path = generate_prescription_pdf(sample_patient, sample_doctor, sample_visit)
    print(f"Prescription PDF generated successfully at: {pdf_path}")
