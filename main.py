import sys
from pathlib import Path

# Resolve base directory whether running from source or frozen (PyInstaller)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent
    APP_DIR = BASE_DIR

sys.path.append(str(BASE_DIR))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from ui.main_window import MainWindow
from db.database import init_db

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Enforce crisp light theme palette
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#F0F7FB"))         # Light soft blue
    palette.setColor(QPalette.WindowText, QColor("#0F172A"))     # Slate 900
    palette.setColor(QPalette.Base, QColor("#FFFFFF"))           # White input background
    palette.setColor(QPalette.AlternateBase, QColor("#F0F9FF"))   # Light blue alternate
    palette.setColor(QPalette.ToolTipBase, QColor("#FFFFFF"))
    palette.setColor(QPalette.ToolTipText, QColor("#0F172A"))
    palette.setColor(QPalette.Text, QColor("#0F172A"))
    palette.setColor(QPalette.Button, QColor("#E0F2FE"))         # Light blue button base
    palette.setColor(QPalette.ButtonText, QColor("#0F172A"))
    palette.setColor(QPalette.BrightText, QColor("#EF4444"))
    palette.setColor(QPalette.Link, QColor("#0284C7"))
    palette.setColor(QPalette.Highlight, QColor("#0284C7"))      # Sky blue highlight
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    app.setPalette(palette)
    
    # Initialize DB (creates connection/validates config)
    init_db()
    
    # Apply stylesheet
    style_path = BASE_DIR / "resources" / "style.qss"
    if not style_path.exists():
        style_path = APP_DIR / "resources" / "style.qss"

    if style_path.exists():
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            print(f"Could not load stylesheet: {e}")
        
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
