"""
DashboardPage for PySide6 GUI.
Displays student welcome, semester credit summaries, and reads events.json for upcoming deadlines,
displaying a red banner if any deadline is within 3 days.
"""

import os
import json
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import config


class DashboardPage(QWidget):
    """
    Dashboard overview page.
    """

    navigate_browser = Signal()
    navigate_planner = Signal()
    routine_loaded = Signal(str)

    def __init__(self, events_file_path: str = "data/events.json", parent=None):
        super().__init__(parent)
        self.events_file_path = events_file_path
        self.user_data: Dict[str, Any] = {}
        self.registered_credits: float = 0.0
        self.max_credits: float = config.DEFAULT_MAX_CREDITS
        self._init_ui()

    def set_user(self, user_data: Dict[str, Any]):
        self.user_data = user_data
        self.max_credits = float(user_data.get("max_credits", config.DEFAULT_MAX_CREDITS))
        self.welcome_label.setText(f"Welcome back, {user_data.get('full_name', 'Student')}!")
        self.semester_label.setText(f"Current Semester: {user_data.get('current_semester', config.CURRENT_SEMESTER)} | ID: {user_data.get('student_id', '')}")
        self.update_credit_stats(self.registered_credits)
        self.reload_events()

    def update_credit_stats(self, registered_credits: float):
        self.registered_credits = registered_credits
        avail = max(0.0, self.max_credits - self.registered_credits)
        self.reg_credits_val.setText(f"{self.registered_credits:.1f}")
        self.avail_credits_val.setText(f"{avail:.1f}")
        self.max_credits_val.setText(f"{self.max_credits:.1f}")

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(18)

        # Header with user welcome
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.welcome_label = QLabel("Welcome, Student!")
        self.welcome_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #F8FAFC;")
        header_layout.addWidget(self.welcome_label)

        self.semester_label = QLabel(f"Current Semester: {config.CURRENT_SEMESTER}")
        self.semester_label.setStyleSheet("color: #94A3B8; font-size: 14px;")
        header_layout.addWidget(self.semester_label)
        main_layout.addWidget(header_frame)

        # Urgent Banner (shown if any deadline <= 3 days)
        self.banner = QFrame()
        self.banner.setObjectName("urgentBanner")
        self.banner_layout = QHBoxLayout(self.banner)
        self.banner_text = QLabel()
        self.banner_text.setStyleSheet("color: #FEE2E2; font-weight: bold;")
        self.banner_layout.addWidget(self.banner_text)
        self.banner.setVisible(False)
        main_layout.addWidget(self.banner)

        # Quick Stats Cards Row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)

        def create_stat_card(title: str, default_val: str):
            card = QFrame()
            card.setObjectName("statBox")
            cl = QVBoxLayout(card)
            val_lbl = QLabel(default_val)
            val_lbl.setObjectName("statNumber")
            t_lbl = QLabel(title)
            t_lbl.setObjectName("statLabel")
            cl.addWidget(val_lbl)
            cl.addWidget(t_lbl)
            return card, val_lbl

        card_reg, self.reg_credits_val = create_stat_card("Registered Credits", "0.0")
        card_avail, self.avail_credits_val = create_stat_card("Available Credits", f"{config.DEFAULT_MAX_CREDITS:.1f}")
        card_max, self.max_credits_val = create_stat_card("Maximum Limit", f"{config.DEFAULT_MAX_CREDITS:.1f}")

        stats_layout.addWidget(card_reg)
        stats_layout.addWidget(card_avail)
        stats_layout.addWidget(card_max)
        main_layout.addLayout(stats_layout)

        # Upcoming Events Box (reads events.json)
        events_card = QFrame()
        events_card.setProperty("class", "card")
        events_layout = QVBoxLayout(events_card)

        events_header = QLabel("Upcoming Deadlines & Academic Events")
        events_header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8; margin-bottom: 8px;")
        events_layout.addWidget(events_header)

        self.events_container = QVBoxLayout()
        self.events_container.setSpacing(8)
        events_layout.addLayout(self.events_container)

        main_layout.addWidget(events_card)

        # Action Buttons Row
        actions_layout = QHBoxLayout()
        self.browse_btn = QPushButton("Open Course Browser")
        self.browse_btn.clicked.connect(self.navigate_browser.emit)

        self.plan_btn = QPushButton("Open Smart Optimizer")
        self.plan_btn.setStyleSheet("background-color: #059669;")
        self.plan_btn.clicked.connect(self.navigate_planner.emit)

        self.load_excel_btn = QPushButton("Import Routine Excel...")
        self.load_excel_btn.setStyleSheet("background-color: #475569;")
        self.load_excel_btn.clicked.connect(self._select_routine_excel)

        actions_layout.addWidget(self.browse_btn)
        actions_layout.addWidget(self.plan_btn)
        actions_layout.addWidget(self.load_excel_btn)
        main_layout.addLayout(actions_layout)

        main_layout.addStretch()
        self.reload_events()

    def reload_events(self):
        """
        Reads events.json, computes days left, updates UI, and displays red banner if <= 3 days.
        """
        # Clear existing items
        while self.events_container.count():
            item = self.events_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not os.path.exists(self.events_file_path):
            lbl = QLabel("No events.json found.")
            self.events_container.addWidget(lbl)
            self.banner.setVisible(False)
            return

        try:
            with open(self.events_file_path, "r", encoding="utf-8") as f:
                events: List[Dict[str, Any]] = json.load(f)
        except Exception:
            lbl = QLabel("Error loading events.")
            self.events_container.addWidget(lbl)
            self.banner.setVisible(False)
            return

        today = date.today()
        # In testing / simulated semester, use fixed anchor if today is past or future
        # Reference anchor: 2026-09-21
        reference_today = date(2026, 9, 21) if today.year != 2026 else today

        urgent_events = []

        for evt in events:
            date_str = evt.get("date", "")
            title = evt.get("title", "Event")
            try:
                evt_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                days_left = (evt_date - reference_today).days
            except Exception:
                days_left = None

            item_frame = QFrame()
            item_frame.setStyleSheet("background-color: #0F172A; border-radius: 6px; padding: 10px;")
            il = QHBoxLayout(item_frame)

            desc = evt.get("description", "")
            info_lbl = QLabel(f"<b>{title}</b> - {desc}")
            il.addWidget(info_lbl)

            if days_left is not None:
                if days_left < 0:
                    badge = QLabel(f"Passed ({abs(days_left)} days ago)")
                    badge.setStyleSheet("color: #64748B; font-weight: bold;")
                elif days_left == 0:
                    badge = QLabel("TODAY!")
                    badge.setStyleSheet("color: #EF4444; font-weight: bold;")
                    urgent_events.append((title, 0))
                elif days_left <= 3:
                    badge = QLabel(f"{days_left} day{'s' if days_left > 1 else ''} left!")
                    badge.setStyleSheet("color: #EF4444; font-weight: bold;")
                    urgent_events.append((title, days_left))
                else:
                    badge = QLabel(f"{days_left} days left")
                    badge.setStyleSheet("color: #10B981; font-weight: bold;")
            else:
                badge = QLabel(date_str)

            il.addWidget(badge)
            self.events_container.addWidget(item_frame)

        # Red banner condition: deadline within 3 days
        if urgent_events:
            event_titles = [f"{t} ({d} day{'s' if d > 1 else ''} left)" for t, d in urgent_events]
            self.banner_text.setText(f"URGENT DEADLINE: {', '.join(event_titles)}")
            self.banner.setVisible(True)
        else:
            self.banner.setVisible(False)

    def _select_routine_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Routine Excel File", "", "Excel Files (*.xlsx *.xls)"
        )
        if file_path:
            self.routine_loaded.emit(file_path)
