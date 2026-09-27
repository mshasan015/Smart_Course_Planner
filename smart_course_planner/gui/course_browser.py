"""
CourseBrowser view for PySide6 GUI.
Features:
- Left filter panel: Course, Faculty, Day, Earliest Start, Free Seats, Hide Dropped, Hide Clashing.
- Right section table using SectionTableModel.
- Live selection tracking, credit calculation, clash detection & grey-out.
- Timetable synchronization and hover preview block.
"""

from typing import List, Optional, Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QFrame, QTableView, QHeaderView, QSplitter,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal

from core.models import Course, Section, Meeting, Schedule
from core.filters import SectionFilter
from core.conflict import ConflictChecker
from core.storage import PlanStorage
from gui.section_table_model import SectionTableModel
from gui.timetable_widget import TimetableWidget
import config


class CourseBrowser(QWidget):
    """
    Interactive course and section browser with conflict checking.
    """

    plan_updated = Signal(list)  # Emits list of selected Section objects

    def __init__(self, parent=None):
        super().__init__(parent)
        self.all_courses: List[Course] = []
        self.all_sections: List[Section] = []
        self.selected_sections: List[Section] = []

        self.conflict_checker = ConflictChecker()
        self.section_filter = SectionFilter(self.conflict_checker)

        self._init_ui()

    def set_data(self, courses: List[Course]):
        self.all_courses = courses
        self.all_sections = [sec for c in courses for sec in c.sections]
        self.conflict_checker.precompute_clashes(self.all_sections)

        # Populate course filter dropdown
        self.course_combo.clear()
        self.course_combo.addItem("All Courses", None)
        for c in sorted(courses, key=lambda x: x.code):
            self.course_combo.addItem(f"{c.code} - {c.title}", c.code)

        # Populate faculty filter dropdown
        faculties = sorted(list({
            t.strip()
            for s in self.all_sections
            for t in s.teachers
            if t.strip() and t.strip().upper() != "TBA"
        }))
        self.faculty_combo.clear()
        self.faculty_combo.addItem("All Faculty", None)
        for f in faculties:
            self.faculty_combo.addItem(f, f)

        self._apply_filters()

    def set_selected_sections(self, sections: List[Section]):
        self.selected_sections = list(sections)
        self.table_model.set_selected_sections(self.selected_sections)
        self.timetable_widget.set_sections(self.selected_sections)
        self._update_credits_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # Splitter: Left (Filters) vs Right (Table & Timetable)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT: Filter Panel ---
        left_panel = QFrame()
        left_panel.setProperty("class", "card")
        left_panel.setFixedWidth(280)
        filter_layout = QVBoxLayout(left_panel)
        filter_layout.setSpacing(12)

        filter_title = QLabel("Filters & Search")
        filter_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #38BDF8;")
        filter_layout.addWidget(filter_title)

        # Search Query
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search course, faculty, code...")
        self.search_input.textChanged.connect(self._apply_filters)
        filter_layout.addWidget(QLabel("Search"))
        filter_layout.addWidget(self.search_input)

        # Course Combo
        self.course_combo = QComboBox()
        self.course_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(QLabel("Filter by Course"))
        filter_layout.addWidget(self.course_combo)

        # Faculty Combo
        self.faculty_combo = QComboBox()
        self.faculty_combo.currentIndexChanged.connect(self._apply_filters)
        filter_layout.addWidget(QLabel("Filter by Faculty"))
        filter_layout.addWidget(self.faculty_combo)

        # Checkboxes
        self.free_seats_cb = QCheckBox("Only show available seats")
        self.free_seats_cb.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.free_seats_cb)

        self.hide_dropped_cb = QCheckBox("Hide dropped sections")
        self.hide_dropped_cb.setChecked(True)
        self.hide_dropped_cb.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.hide_dropped_cb)

        self.hide_clashing_cb = QCheckBox("Hide sections that clash")
        self.hide_clashing_cb.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.hide_clashing_cb)

        self.no_early_cb = QCheckBox("No classes before 10:00 AM")
        self.no_early_cb.stateChanged.connect(self._apply_filters)
        filter_layout.addWidget(self.no_early_cb)

        filter_layout.addStretch()

        # Selected Credits Status Card
        status_card = QFrame()
        status_card.setStyleSheet("background-color: #0F172A; border-radius: 6px; padding: 12px;")
        sc_layout = QVBoxLayout(status_card)

        sc_title = QLabel("Selected Plan Status")
        sc_title.setStyleSheet("font-weight: bold; color: #38BDF8;")
        sc_layout.addWidget(sc_title)

        self.credit_count_label = QLabel("Credits: 0.0 / 15.0")
        self.credit_count_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #F8FAFC;")
        sc_layout.addWidget(self.credit_count_label)

        self.selected_count_label = QLabel("0 sections chosen")
        self.selected_count_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        sc_layout.addWidget(self.selected_count_label)

        self.clear_btn = QPushButton("Clear Selection")
        self.clear_btn.setStyleSheet("background-color: #475569; margin-top: 6px;")
        self.clear_btn.clicked.connect(self._clear_selection)
        sc_layout.addWidget(self.clear_btn)

        filter_layout.addWidget(status_card)
        splitter.addWidget(left_panel)

        # --- RIGHT: Table and Live Timetable ---
        right_panel = QFrame()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        # Section Table
        self.table_view = QTableView()
        self.table_model = SectionTableModel()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setMouseTracking(True)
        self.table_view.entered.connect(self._on_table_hover)
        self.table_view.doubleClicked.connect(self._on_table_double_clicked)

        right_layout.addWidget(self.table_view, stretch=3)

        # Selection Control Row
        sel_row = QHBoxLayout()
        self.toggle_btn = QPushButton("Toggle Selected Section")
        self.toggle_btn.clicked.connect(self._toggle_current_selected_row)
        sel_row.addWidget(self.toggle_btn)

        tip_lbl = QLabel("Double-click a row to add or remove it from your plan.")
        tip_lbl.setStyleSheet("color: #94A3B8; font-style: italic;")
        sel_row.addWidget(tip_lbl)
        sel_row.addStretch()

        right_layout.addLayout(sel_row)

        # Live Timetable Widget
        self.timetable_widget = TimetableWidget()
        right_layout.addWidget(self.timetable_widget, stretch=2)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 4)

        main_layout.addWidget(splitter)

    def _apply_filters(self):
        course_code = self.course_combo.currentData()
        faculty = self.faculty_combo.currentData()
        free_seats = self.free_seats_cb.isChecked()
        hide_dropped = self.hide_dropped_cb.isChecked()
        hide_clashing = self.hide_clashing_cb.isChecked()
        earliest_start = config.EARLY_CLASS_THRESHOLD_MINUTES if self.no_early_cb.isChecked() else None
        query = self.search_input.text()

        filtered = self.section_filter.filter(
            self.all_sections,
            course_code=course_code,
            faculty=faculty,
            earliest_start_minutes=earliest_start,
            free_seats_only=free_seats,
            hide_dropped=hide_dropped,
            selected_sections=self.selected_sections,
            hide_clashing=hide_clashing,
            query=query,
        )

        self.table_model.set_sections(filtered)

    def _on_table_hover(self, index):
        if not index.isValid():
            self.timetable_widget.set_preview_section(None)
            return
        sec = self.table_model.sections[index.row()]
        self.timetable_widget.set_preview_section(sec)

    def leaveEvent(self, event):
        self.timetable_widget.set_preview_section(None)
        super().leaveEvent(event)

    def _on_table_double_clicked(self, index):
        if not index.isValid():
            return
        sec = self.table_model.sections[index.row()]
        self._toggle_section(sec)

    def _toggle_current_selected_row(self):
        selected_indexes = self.table_view.selectionModel().selectedRows()
        if not selected_indexes:
            QMessageBox.information(self, "Select Row", "Please click on a section row in the table first.")
            return
        sec = self.table_model.sections[selected_indexes[0].row()]
        self._toggle_section(sec)

    def _toggle_section(self, sec: Section):
        if sec in self.selected_sections:
            self.selected_sections.remove(sec)
        else:
            if sec.dropped:
                QMessageBox.warning(self, "Section Dropped", "Cannot select a dropped section.")
                return

            # Clash check rule: same day and startA < endB and startB < endA
            has_clash, clashing_sec = self.conflict_checker.does_clash_with_selection(
                sec, self.selected_sections
            )
            if has_clash and clashing_sec:
                QMessageBox.warning(
                    self,
                    "Schedule Clash Detected",
                    f"Cannot select {sec.course_code} [{sec.section_name}]:\n"
                    f"It clashes with currently selected {clashing_sec.course_code} [{clashing_sec.section_name}]!",
                )
                return

            # Check credit limit
            new_total = sum(s.credits for s in self.selected_sections) + sec.credits
            if new_total > config.DEFAULT_MAX_CREDITS:
                QMessageBox.warning(
                    self,
                    "Credit Limit Exceeded",
                    f"Selecting this section would bring total credits to {new_total:.1f}, "
                    f"exceeding maximum limit of {config.DEFAULT_MAX_CREDITS:.1f}.",
                )
                return

            self.selected_sections.append(sec)

        self.table_model.set_selected_sections(self.selected_sections)
        self.timetable_widget.set_sections(self.selected_sections)
        self._update_credits_ui()
        self.plan_updated.emit(self.selected_sections)

    def _clear_selection(self):
        self.selected_sections.clear()
        self.table_model.set_selected_sections([])
        self.timetable_widget.set_sections([])
        self._update_credits_ui()
        self.plan_updated.emit([])

    def _update_credits_ui(self):
        total_cred = sum(s.credits for s in self.selected_sections)
        self.credit_count_label.setText(f"Credits: {total_cred:.1f} / {config.DEFAULT_MAX_CREDITS:.1f}")
        self.selected_count_label.setText(f"{len(self.selected_sections)} section(s) chosen")
