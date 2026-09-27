"""
MainWindow for PySide6 GUI.
Contains a QStackedWidget switching between LoginPage, DashboardPage, CourseBrowser, and PlannerPage.
Provides navigation header, plan JSON save/load, and routine file loader.
"""

import os
from typing import List, Optional
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt

from core.auth import AuthService
from core.loader import RoutineLoader
from core.models import Course, Section, Schedule
from core.storage import PlanStorage

from gui.login_page import LoginPage
from gui.dashboard_page import DashboardPage
from gui.course_browser import CourseBrowser
from gui.planner_page import PlannerPage
import config


class MainWindow(QMainWindow):
    """
    Main application window hosting stacked pages and global navigation.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Smart Course Planner - Academic Schedule Optimizer")
        self.resize(1200, 780)

        self.auth_service = AuthService()
        self.routine_loader = RoutineLoader()

        self.courses: List[Course] = []
        self.current_user: Optional[dict] = None
        self.selected_sections: List[Section] = []

        self._init_ui()
        self._load_default_routine()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Top Navigation Bar ---
        self.nav_bar = QWidget()
        self.nav_bar.setObjectName("navBar")
        nav_layout = QHBoxLayout(self.nav_bar)
        nav_layout.setContentsMargins(16, 8, 16, 8)

        app_title = QLabel("Smart Course Planner")
        app_title.setObjectName("navTitle")
        nav_layout.addWidget(app_title)

        nav_layout.addSpacing(24)

        self.btn_dash = QPushButton("Dashboard")
        self.btn_dash.setObjectName("navBtn")
        self.btn_dash.setCheckable(True)
        self.btn_dash.clicked.connect(lambda: self.switch_page(1))
        nav_layout.addWidget(self.btn_dash)

        self.btn_browser = QPushButton("Course Browser")
        self.btn_browser.setObjectName("navBtn")
        self.btn_browser.setCheckable(True)
        self.btn_browser.clicked.connect(lambda: self.switch_page(2))
        nav_layout.addWidget(self.btn_browser)

        self.btn_planner = QPushButton("Optimizer Planner")
        self.btn_planner.setObjectName("navBtn")
        self.btn_planner.setCheckable(True)
        self.btn_planner.clicked.connect(lambda: self.switch_page(3))
        nav_layout.addWidget(self.btn_planner)

        nav_layout.addStretch()

        # Plan File Actions (Day 6: Save and load selected plan as JSON)
        self.btn_save_plan = QPushButton("Save Plan JSON")
        self.btn_save_plan.setStyleSheet("background-color: #0284C7; font-size: 11px;")
        self.btn_save_plan.clicked.connect(self._save_plan_json)
        nav_layout.addWidget(self.btn_save_plan)

        self.btn_load_plan = QPushButton("Load Plan JSON")
        self.btn_load_plan.setStyleSheet("background-color: #475569; font-size: 11px;")
        self.btn_load_plan.clicked.connect(self._load_plan_json)
        nav_layout.addWidget(self.btn_load_plan)

        nav_layout.addSpacing(16)

        self.user_lbl = QLabel("")
        self.user_lbl.setStyleSheet("color: #38BDF8; font-weight: bold;")
        nav_layout.addWidget(self.user_lbl)

        self.btn_logout = QPushButton("Logout")
        self.btn_logout.setStyleSheet("background-color: #7F1D1D; font-size: 11px;")
        self.btn_logout.clicked.connect(self._handle_logout)
        nav_layout.addWidget(self.btn_logout)

        main_layout.addWidget(self.nav_bar)

        # --- QStackedWidget (Page 4 Main Requirement) ---
        self.stack = QStackedWidget()

        # Page 0: Login
        self.login_page = LoginPage(self.auth_service)
        self.login_page.login_successful.connect(self._on_login_successful)
        self.stack.addWidget(self.login_page)

        # Page 1: Dashboard
        self.dashboard_page = DashboardPage()
        self.dashboard_page.navigate_browser.connect(lambda: self.switch_page(2))
        self.dashboard_page.navigate_planner.connect(lambda: self.switch_page(3))
        self.dashboard_page.routine_loaded.connect(self._load_routine_file)
        self.stack.addWidget(self.dashboard_page)

        # Page 2: Course Browser
        self.course_browser = CourseBrowser()
        self.course_browser.plan_updated.connect(self._on_plan_updated)
        self.stack.addWidget(self.course_browser)

        # Page 3: Planner Page
        self.planner_page = PlannerPage()
        self.planner_page.plan_selected.connect(self._on_plan_applied_from_optimizer)
        self.stack.addWidget(self.planner_page)

        main_layout.addWidget(self.stack)

        # Start on Login Page, hide nav bar initially
        self.nav_bar.setVisible(False)
        self.stack.setCurrentIndex(0)

    def _load_default_routine(self):
        sample_path = "smart_course_planner/data/routine_sample.xlsx"
        if not os.path.exists(sample_path):
            sample_path = "data/routine_sample.xlsx"
        if os.path.exists(sample_path):
            self._load_routine_file(sample_path)

    def _load_routine_file(self, path: str):
        courses, report = self.routine_loader.load(path)
        if not courses:
            QMessageBox.warning(self, "Import Warning", f"Could not load courses:\n{report.summary()}")
            return

        self.courses = courses
        self.course_browser.set_data(courses)
        self.planner_page.set_data(courses)

    def _on_login_successful(self, user_data: dict):
        self.current_user = user_data
        self.user_lbl.setText(f"{user_data.get('full_name', 'Student')} ({user_data.get('username')})")
        self.dashboard_page.set_user(user_data)
        self.nav_bar.setVisible(True)
        self.switch_page(1)  # Switch to Dashboard

    def _handle_logout(self):
        self.current_user = None
        self.selected_sections.clear()
        self.course_browser.set_selected_sections([])
        self.nav_bar.setVisible(False)
        self.stack.setCurrentIndex(0)

    def switch_page(self, index: int):
        self.stack.setCurrentIndex(index)
        self.btn_dash.setChecked(index == 1)
        self.btn_browser.setChecked(index == 2)
        self.btn_planner.setChecked(index == 3)

    def _on_plan_updated(self, sections: List[Section]):
        self.selected_sections = sections
        total_cred = sum(s.credits for s in sections)
        self.dashboard_page.update_credit_stats(total_cred)

    def _on_plan_applied_from_optimizer(self, sections: List[Section]):
        self.selected_sections = sections
        self.course_browser.set_selected_sections(sections)
        total_cred = sum(s.credits for s in sections)
        self.dashboard_page.update_credit_stats(total_cred)
        self.switch_page(2)  # Switch to Course Browser to view applied plan

    def _save_plan_json(self):
        if not self.selected_sections:
            QMessageBox.warning(self, "Empty Plan", "No sections currently selected to save.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Course Plan as JSON", "my_course_plan.json", "JSON Files (*.json)"
        )
        if file_path:
            sched = Schedule(sections=self.selected_sections)
            success = PlanStorage.save_plan(sched, file_path)
            if success:
                QMessageBox.information(self, "Saved", f"Plan saved successfully to:\n{file_path}")
            else:
                QMessageBox.warning(self, "Save Failed", "Could not save plan file.")

    def _load_plan_json(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Course Plan from JSON", "", "JSON Files (*.json)"
        )
        if file_path:
            sched = PlanStorage.load_plan(file_path)
            if sched and sched.sections:
                self._on_plan_applied_from_optimizer(sched.sections)
                QMessageBox.information(
                    self, "Loaded", f"Loaded {len(sched.sections)} sections from JSON!"
                )
            else:
                QMessageBox.warning(self, "Load Failed", "Could not load plan or file is empty.")
