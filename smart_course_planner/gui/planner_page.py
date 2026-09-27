"""
PlannerPage for PySide6 GUI.
Features:
- Preference settings: wanted courses, liked/avoided faculty, timing constraints, priority.
- Solvers: BruteForcePlanner and CpSatPlanner (OR-Tools).
- Top 5 ranked plans display with score, days used, and idle gap times.
- Explainer for infeasible schedules (bottleneck isolation).
- Backup section finder for registration day safety.
"""

from typing import List, Tuple, Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox,
    QPushButton, QFrame, QScrollArea, QListWidget, QListWidgetItem,
    QMessageBox, QSplitter, QRadioButton, QButtonGroup, QGroupBox
)
from PySide6.QtCore import Qt, Signal

from core.models import Course, Section, Schedule
from core.planner.preference import Preference
from core.planner.brute_force import BruteForcePlanner
from core.planner.cpsat_planner import CpSatPlanner
from core.planner.explain import Explainer
from gui.timetable_widget import TimetableWidget
import config


class PlannerPage(QWidget):
    """
    Automated course scheduling optimizer view.
    """

    plan_selected = Signal(list)  # Emits selected Section objects

    def __init__(self, parent=None):
        super().__init__(parent)
        self.courses: List[Course] = []
        self.top_plans: List[Tuple[Schedule, float]] = []
        self.current_schedule: Optional[Schedule] = None
        self._init_ui()

    def set_data(self, courses: List[Course]):
        self.courses = courses

        # Populate wanted courses checkbox list
        self.course_list.clear()
        for c in sorted(courses, key=lambda x: x.code):
            item = QListWidgetItem(f"{c.code} - {c.title} ({c.credits:.1f} cr)")
            item.setData(Qt.ItemDataRole.UserRole, c.code)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.course_list.addItem(item)

        # Populate faculty multi-selection list
        all_teachers = sorted(list({
            t.strip()
            for c in courses
            for s in c.sections
            for t in s.teachers
            if t.strip() and t.strip().upper() != "TBA"
        }))

        self.liked_faculty_list.clear()
        self.avoided_faculty_list.clear()

        for fac in all_teachers:
            item1 = QListWidgetItem(fac)
            item1.setData(Qt.ItemDataRole.UserRole, fac)
            item1.setFlags(item1.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item1.setCheckState(Qt.CheckState.Unchecked)
            self.liked_faculty_list.addItem(item1)

            item2 = QListWidgetItem(fac)
            item2.setData(Qt.ItemDataRole.UserRole, fac)
            item2.setFlags(item2.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item2.setCheckState(Qt.CheckState.Unchecked)
            self.avoided_faculty_list.addItem(item2)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT: Preference Configuration ---
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(340)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(14)

        title = QLabel("Schedule Optimizer")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #38BDF8;")
        left_layout.addWidget(title)

        # 1. Wanted Courses
        left_layout.addWidget(QLabel("<b>1. Select Wanted Courses:</b>"))
        self.course_list = QListWidget()
        self.course_list.setFixedHeight(140)
        left_layout.addWidget(self.course_list)

        # 2. Timing Preferences
        left_layout.addWidget(QLabel("<b>2. Class Timing Constraints:</b>"))
        self.early_none_rb = QRadioButton("No restrictions on start time")
        self.early_soft_rb = QRadioButton("Prefer no class before 10 AM (Soft)")
        self.early_hard_rb = QRadioButton("Strict: No class before 10 AM (Hard)")
        self.early_none_rb.setChecked(True)

        timing_group = QButtonGroup(self)
        timing_group.addButton(self.early_none_rb)
        timing_group.addButton(self.early_soft_rb)
        timing_group.addButton(self.early_hard_rb)

        left_layout.addWidget(self.early_none_rb)
        left_layout.addWidget(self.early_soft_rb)
        left_layout.addWidget(self.early_hard_rb)

        # 3. Schedule Priority
        left_layout.addWidget(QLabel("<b>3. Optimization Priority:</b>"))
        self.prio_balanced = QRadioButton("Balanced (Days & Gaps)")
        self.prio_days = QRadioButton("Fewer Days (Compact week)")
        self.prio_gaps = QRadioButton("Fewer Gaps (Min idle time)")
        self.prio_balanced.setChecked(True)

        prio_group = QButtonGroup(self)
        prio_group.addButton(self.prio_balanced)
        prio_group.addButton(self.prio_days)
        prio_group.addButton(self.prio_gaps)

        left_layout.addWidget(self.prio_balanced)
        left_layout.addWidget(self.prio_days)
        left_layout.addWidget(self.prio_gaps)

        # 4. Faculty Preferences
        left_layout.addWidget(QLabel("<b>4. Liked Faculty (Bonus points):</b>"))
        self.liked_faculty_list = QListWidget()
        self.liked_faculty_list.setFixedHeight(90)
        left_layout.addWidget(self.liked_faculty_list)

        left_layout.addWidget(QLabel("<b>Avoided Faculty (Penalty):</b>"))
        self.avoided_faculty_list = QListWidget()
        self.avoided_faculty_list.setFixedHeight(90)
        left_layout.addWidget(self.avoided_faculty_list)

        # Solver Action Buttons
        btn_box = QVBoxLayout()
        self.cpsat_btn = QPushButton("Solve with OR-Tools (CP-SAT)")
        self.cpsat_btn.setStyleSheet("background-color: #0284C7; font-weight: bold; padding: 10px;")
        self.cpsat_btn.clicked.connect(lambda: self._run_optimizer("cpsat"))

        self.brute_btn = QPushButton("Solve with Brute Force")
        self.brute_btn.setStyleSheet("background-color: #475569; font-weight: bold; padding: 8px;")
        self.brute_btn.clicked.connect(lambda: self._run_optimizer("brute"))

        btn_box.addWidget(self.cpsat_btn)
        btn_box.addWidget(self.brute_btn)
        left_layout.addLayout(btn_box)

        left_scroll.setWidget(left_widget)
        splitter.addWidget(left_scroll)

        # --- RIGHT: Results & Timetable View ---
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(12, 0, 0, 0)
        right_layout.setSpacing(12)

        # Plans Header & Results Selector
        results_header = QHBoxLayout()
        self.results_title = QLabel("Generated Plans")
        self.results_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        results_header.addWidget(self.results_title)

        self.apply_btn = QPushButton("Apply to My Current Schedule")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_current_plan)
        results_header.addWidget(self.apply_btn)

        right_layout.addLayout(results_header)

        # Top 5 Plan Cards Row
        self.plan_buttons_layout = QHBoxLayout()
        self.plan_buttons_layout.setSpacing(8)
        right_layout.addLayout(self.plan_buttons_layout)

        # Plan Info summary
        self.plan_info_label = QLabel("Select your preferences on the left and click Solve.")
        self.plan_info_label.setStyleSheet("color: #94A3B8; font-size: 13px;")
        right_layout.addWidget(self.plan_info_label)

        # Timetable Preview
        self.timetable = TimetableWidget()
        right_layout.addWidget(self.timetable, stretch=2)

        # Extras: Infeasibility Explanation / Backup Sections Box
        self.extras_card = QFrame()
        self.extras_card.setProperty("class", "card")
        self.extras_card.setFixedHeight(140)
        extras_layout = QVBoxLayout(self.extras_card)
        extras_layout.setContentsMargins(10, 10, 10, 10)

        self.extras_title = QLabel("Smart Analysis & Backup Recommendations")
        self.extras_title.setStyleSheet("font-weight: bold; color: #38BDF8;")
        extras_layout.addWidget(self.extras_title)

        self.extras_scroll = QScrollArea()
        self.extras_scroll.setWidgetResizable(True)
        self.extras_content = QLabel("Ready to optimize. No conflicts detected yet.")
        self.extras_content.setWordWrap(True)
        self.extras_content.setStyleSheet("color: #E2E8F0; font-size: 12px;")
        self.extras_scroll.setWidget(self.extras_content)
        extras_layout.addWidget(self.extras_scroll)

        right_layout.addWidget(self.extras_card)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    def _collect_preference(self) -> Preference:
        wanted = []
        for i in range(self.course_list.count()):
            item = self.course_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                wanted.append(item.data(Qt.ItemDataRole.UserRole))

        liked = []
        for i in range(self.liked_faculty_list.count()):
            item = self.liked_faculty_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                liked.append(item.data(Qt.ItemDataRole.UserRole))

        avoided = []
        for i in range(self.avoided_faculty_list.count()):
            item = self.avoided_faculty_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                avoided.append(item.data(Qt.ItemDataRole.UserRole))

        prio = "balanced"
        if self.prio_days.isChecked():
            prio = "fewer_days"
        elif self.prio_gaps.isChecked():
            prio = "fewer_gaps"

        return Preference(
            wanted_courses=wanted,
            liked_faculty=liked,
            avoided_faculty=avoided,
            no_early_class_hard=self.early_hard_rb.isChecked(),
            no_early_class_soft=self.early_soft_rb.isChecked(),
            priority=prio,
        )

    def _run_optimizer(self, solver_type: str):
        pref = self._collect_preference()

        if not pref.wanted_courses:
            QMessageBox.warning(self, "No Courses Selected", "Please check at least one wanted course.")
            return

        if solver_type == "cpsat":
            solver = CpSatPlanner(self.courses)
        else:
            solver = BruteForcePlanner(self.courses)

        self.top_plans = solver.plan(pref, top_k=5)

        # Clear existing plan selector buttons
        while self.plan_buttons_layout.count():
            item = self.plan_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.top_plans:
            self.current_schedule = None
            self.timetable.set_sections([])
            self.apply_btn.setEnabled(False)
            self.plan_info_label.setText("No valid clash-free plan found satisfying all constraints.")

            # Run Explainer (Day 9 requirement)
            explainer = Explainer(self.courses)
            reasons = explainer.explain_failure(pref)
            msg = "<b style='color: #EF4444;'>No Plan Possible:</b><br/>"
            msg += "<br/>".join(f"• {r}" for r in reasons)
            self.extras_content.setText(msg)
            return

        # Render Plan Selector Buttons
        for idx, (sched, score) in enumerate(self.top_plans):
            btn = QPushButton(f"Plan #{idx + 1}\nScore: {score:.1f}")
            btn.setStyleSheet(
                "background-color: #1E293B; border: 1px solid #334155; padding: 6px; font-size: 11px;"
            )
            btn.clicked.connect(lambda checked=False, i=idx: self._select_plan(i))
            self.plan_buttons_layout.addWidget(btn)

        self.apply_btn.setEnabled(True)
        self._select_plan(0, pref)

    def _select_plan(self, idx: int, pref: Optional[Preference] = None):
        if not (0 <= idx < len(self.top_plans)):
            return

        sched, score = self.top_plans[idx]
        self.current_schedule = sched
        self.timetable.set_sections(sched.sections)

        days_str = ", ".join(sched.days_used())
        idle_h = sched.idle_minutes() / 60.0
        self.plan_info_label.setText(
            f"<b>Plan #{idx + 1} Selected</b> | Score: <b>{score:.1f}</b> | "
            f"Days: <b>{len(sched.days_used())}</b> ({days_str}) | Idle Time: <b>{sched.idle_minutes()} mins</b> ({idle_h:.1f} hrs) | "
            f"Total Credits: <b>{sched.total_credits():.1f}</b>"
        )

        # Update Backup Sections (Day 9 requirement)
        if not pref:
            pref = self._collect_preference()
        explainer = Explainer(self.courses)
        backups = explainer.find_backup_sections(sched, pref)

        backup_text = "<b style='color: #10B981;'>Backup Section Analysis (Registration Day):</b><br/>"
        has_any_backup = False
        for code, b_list in backups.items():
            if b_list:
                has_any_backup = True
                b_str = ", ".join(f"Sec {sec.section_name} ({note})" for sec, note in b_list)
                backup_text += f"• <b>{code}</b> alternatives: {b_str}<br/>"
            else:
                backup_text += f"• <b>{code}</b>: No alternate sections fit without timing clashes.<br/>"

        self.extras_content.setText(backup_text)

    def _apply_current_plan(self):
        if not self.current_schedule:
            return
        self.plan_selected.emit(self.current_schedule.sections)
        QMessageBox.information(
            self,
            "Plan Applied",
            f"Plan with {len(self.current_schedule.sections)} sections successfully applied to your course schedule!",
        )
