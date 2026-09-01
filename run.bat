@echo off
if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Setting it up...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

echo Starting Clinic Receptionist...
python main.py
