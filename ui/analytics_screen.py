from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QDateEdit, QComboBox, QSizePolicy
)
from PySide6.QtCore import QDate, Qt
from models.visit import get_visit_stats
from db.database import get_supabase


class StatCard(QFrame):
    def __init__(self, title: str, value: str = "—", color: str = "#20B2AA"):
        super().__init__()
        self.setStyleSheet(
            "QFrame { background: white; border-radius: 8px; border: 1px solid #BAD9F1; }"
        )
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)

        t = QLabel(title)
        t.setStyleSheet("font-size: 12px; color: #5D6D7E; font-weight: 600; border: none;")
        self.val = QLabel(value)
        self.val.setStyleSheet(
            f"font-size: 32px; font-weight: bold; color: {color}; border: none;"
        )
        layout.addWidget(t)
        layout.addWidget(self.val)

    def set_value(self, v: str):
        self.val.setText(v)


class AnalyticsScreen(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 10, 14, 10)
        root.setSpacing(10)

        # ── Title ─────────────────────────────────────────────────────────
        title = QLabel("Doctor Analytics Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #1A5276;")
        root.addWidget(title)

        # ── Summary Cards ─────────────────────────────────────────────────
        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.card_today = StatCard("Total Patients Today",  "—", "#20B2AA")
        self.card_week  = StatCard("This Week",             "—", "#2E8B57")
        self.card_month = StatCard("This Month",            "—", "#1F618D")
        for c in (self.card_today, self.card_week, self.card_month):
            cards.addWidget(c)
        root.addLayout(cards)

        # ── Toggle + Date range row ───────────────────────────────────────
        ctrl = QFrame()
        ctrl.setStyleSheet(
            "QFrame { background: white; border: 1px solid #BAD9F1; border-radius: 8px; }"
        )
        ctrl_layout = QHBoxLayout(ctrl)
        ctrl_layout.setContentsMargins(12, 8, 12, 8)
        ctrl_layout.setSpacing(10)

        # Toggle buttons
        self.btn_daily   = QPushButton("Daily")
        self.btn_monthly = QPushButton("Monthly")
        for btn in (self.btn_daily, self.btn_monthly):
            btn.setCheckable(True)
            btn.setStyleSheet(
                "QPushButton { background: #D6EAF8; color: #1A5276; border-radius: 5px; "
                "padding: 6px 16px; font-weight: 600; border: none; }"
                "QPushButton:checked { background: #1A5276; color: white; }"
                "QPushButton:hover:!checked { background: #AED6F1; }"
            )
        self.btn_daily.setChecked(True)
        self.btn_daily.clicked.connect(lambda: self._set_toggle("daily"))
        self.btn_monthly.clicked.connect(lambda: self._set_toggle("monthly"))
        ctrl_layout.addWidget(self.btn_daily)
        ctrl_layout.addWidget(self.btn_monthly)

        ctrl_layout.addWidget(QLabel(" "))

        # Custom date range
        range_lbl = QLabel("Custom range:")
        range_lbl.setStyleSheet("color: #475569; font-weight: 600;")
        ctrl_layout.addWidget(range_lbl)

        self.from_date = QDateEdit(QDate.currentDate().addDays(-7))
        self.from_date.setCalendarPopup(True)
        self.from_date.setDisplayFormat("dd MMM yyyy")
        ctrl_layout.addWidget(self.from_date)

        ctrl_layout.addWidget(QLabel("to"))

        self.till_date = QDateEdit(QDate.currentDate())
        self.till_date.setCalendarPopup(True)
        self.till_date.setDisplayFormat("dd MMM yyyy")
        ctrl_layout.addWidget(self.till_date)

        self.search_btn = QPushButton("Search")
        self.search_btn.clicked.connect(self._custom_search)
        ctrl_layout.addWidget(self.search_btn)
        ctrl_layout.addStretch()

        root.addWidget(ctrl)

        # ── Breakdown table ───────────────────────────────────────────────
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Doctor Name", "Specialization", "Patients Seen"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        root.addWidget(self.table, 1)

        self._load_summary_cards()
        self._load_table_for_range("daily")

    # ── Helpers ────────────────────────────────────────────────────────

    def _set_toggle(self, mode: str):
        self.btn_daily.setChecked(mode == "daily")
        self.btn_monthly.setChecked(mode == "monthly")
        self._load_table_for_range(mode)

    def _load_summary_cards(self):
        today = QDate.currentDate()
        today_s = today.toString("yyyy-MM-dd")
        week_s  = today.addDays(-today.dayOfWeek() + 1).toString("yyyy-MM-dd")
        month_s = QDate(today.year(), today.month(), 1).toString("yyyy-MM-dd")
        try:
            sb = get_supabase()
            t = sb.table("visits").select("id", count="exact").eq("visit_date", today_s).execute().count
            w = sb.table("visits").select("id", count="exact").gte("visit_date", week_s).lte("visit_date", today_s).execute().count
            m = sb.table("visits").select("id", count="exact").gte("visit_date", month_s).lte("visit_date", today_s).execute().count
            self.card_today.set_value(str(t or 0))
            self.card_week.set_value(str(w or 0))
            self.card_month.set_value(str(m or 0))
        except Exception:
            for c in (self.card_today, self.card_week, self.card_month):
                c.set_value("—")

    def _load_table_for_range(self, mode: str):
        today = QDate.currentDate()
        end   = today
        start = today if mode == "daily" else QDate(today.year(), today.month(), 1)
        self._fill_table(start.toString("yyyy-MM-dd"), end.toString("yyyy-MM-dd"))

    def _custom_search(self):
        start = self.from_date.date().toString("yyyy-MM-dd")
        end   = self.till_date.date().toString("yyyy-MM-dd")
        # Uncheck both toggles to show custom mode is active
        self.btn_daily.setChecked(False)
        self.btn_monthly.setChecked(False)
        self._fill_table(start, end)

    def _fill_table(self, start: str, end: str):
        try:
            stats = get_visit_stats(start, end)
        except Exception as e:
            stats = []

        self.table.setRowCount(len(stats))
        if not stats:
            self.table.setRowCount(1)
            no = QTableWidgetItem("No visits found for this period.")
            no.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(0, 0, no)
            self.table.setSpan(0, 0, 1, 3)
            return

        for i, row in enumerate(stats):
            self.table.setItem(i, 0, QTableWidgetItem(row["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(row["specialization"]))
            cnt = QTableWidgetItem(str(row["total"]))
            cnt.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(i, 2, cnt)
            self.table.setRowHeight(i, 38)
