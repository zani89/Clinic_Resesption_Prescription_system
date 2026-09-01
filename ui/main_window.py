from PySide6.QtWidgets import QMainWindow, QTabWidget
from PySide6.QtGui import QGuiApplication
from ui.intake_screen import IntakeScreen
from ui.analytics_screen import AnalyticsScreen


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Alees Medical Center — Receptionist Desk")

        # Set window size to 80% of screen and center it
        screen = QGuiApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            width = int(geo.width() * 0.8)
            height = int(geo.height() * 0.8)
            x = geo.x() + (geo.width() - width) // 2
            y = geo.y() + (geo.height() - height) // 2
            self.setGeometry(x, y, width, height)

        tabs = QTabWidget()
        tabs.addTab(IntakeScreen(), "  📋  Prescription  ")
        tabs.addTab(AnalyticsScreen(), "  📊  Analytics  ")
        self.setCentralWidget(tabs)
