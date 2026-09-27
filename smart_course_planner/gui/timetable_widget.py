"""
TimetableWidget for PySide6.
Weekly visual grid of days × time slots.
Assigns distinct color per course, renders meetings, and supports hover preview blocks.
"""

from typing import List, Optional, Dict
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QFrame, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QColor, QBrush, QPen, QFont

import config
from core.models import Section, Meeting
from core.time_utils import minutes_to_time_str


class TimetableWidget(QWidget):
    """
    Weekly schedule timetable canvas.
    Renders time slots along Y axis (08:00 to 18:00) and days along X axis.
    """

    # BUG FIX: previously hardcoded to only 5 days (Sun-Thu), which silently
    # dropped any Saturday/Friday meeting from the grid (paintEvent's
    # draw_meeting() returns early when a day isn't in this list) even though
    # config.py, loader.py and time_utils.py all treat Saturday/Friday as
    # normal, valid class days. Pulling the full week from config keeps this
    # widget in sync with the rest of the app so no class ever disappears.
    DAYS = list(config.DAYS_OF_WEEK)  # ["Saturday", "Sunday", ... "Friday"]
    START_HOUR = 8   # 08:00 AM (480 mins)
    END_HOUR = 18    # 06:00 PM (1080 mins)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(450)
        self.setMinimumWidth(600)
        self.sections: List[Section] = []
        self.preview_section: Optional[Section] = None
        self.course_colors: Dict[str, str] = {}

    def set_sections(self, sections: List[Section]) -> None:
        self.sections = sections
        self._assign_colors()
        self.update()

    def set_preview_section(self, section: Optional[Section]) -> None:
        self.preview_section = section
        self.update()

    def _assign_colors(self) -> None:
        codes = sorted(list({s.course_code for s in self.sections}))
        self.course_colors = {}
        for idx, code in enumerate(codes):
            self.course_colors[code] = config.COURSE_COLORS[idx % len(config.COURSE_COLORS)]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        left_margin = 60
        top_margin = 35
        bottom_margin = 20
        right_margin = 20

        grid_w = width - left_margin - right_margin
        grid_h = height - top_margin - bottom_margin

        num_days = len(self.DAYS)
        day_col_w = grid_w / num_days if num_days > 0 else grid_w

        total_minutes = (self.END_HOUR - self.START_HOUR) * 60
        start_minute = self.START_HOUR * 60

        # Background
        painter.fillRect(self.rect(), QColor("#0F172A"))

        # Draw Day Headers
        header_font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(header_font)
        painter.setPen(QColor("#94A3B8"))

        for i, day in enumerate(self.DAYS):
            x = left_margin + i * day_col_w
            rect = QRect(int(x), 5, int(day_col_w), top_margin - 5)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, day)

        # Draw Hour Lines & Labels
        time_font = QFont("Segoe UI", 8)
        painter.setFont(time_font)

        for h in range(self.START_HOUR, self.END_HOUR + 1):
            min_from_start = (h - self.START_HOUR) * 60
            y = top_margin + (min_from_start / total_minutes) * grid_h

            # Label
            meridiem = "AM" if h < 12 else "PM"
            disp_h = h if h <= 12 else h - 12
            time_str = f"{disp_h:02d}:00 {meridiem}"

            painter.setPen(QColor("#64748B"))
            painter.drawText(5, int(y + 4), left_margin - 10, 15, Qt.AlignmentFlag.AlignRight, time_str)

            # Grid Line
            painter.setPen(QPen(QColor("#334155"), 1, Qt.PenStyle.DashLine))
            painter.drawLine(left_margin, int(y), width - right_margin, int(y))

        # Vertical day column dividers
        painter.setPen(QPen(QColor("#334155"), 1, Qt.PenStyle.SolidLine))
        for i in range(num_days + 1):
            x = left_margin + i * day_col_w
            painter.drawLine(int(x), top_margin, int(x), int(top_margin + grid_h))

        # Helper to draw a section meeting block
        def draw_meeting(sec: Section, meeting: Meeting, is_preview: bool = False):
            day_clean = meeting.day.strip().title()
            if day_clean not in self.DAYS:
                return

            day_idx = self.DAYS.index(day_clean)
            x = left_margin + day_idx * day_col_w + 2
            w = day_col_w - 4

            start_m = max(start_minute, meeting.start)
            end_m = min(start_minute + total_minutes, meeting.end)

            if end_m <= start_m:
                return

            y = top_margin + ((start_m - start_minute) / total_minutes) * grid_h
            h = ((end_m - start_m) / total_minutes) * grid_h

            block_rect = QRect(int(x), int(y), int(w), int(h))

            # Color
            hex_color = self.course_colors.get(sec.course_code, "#2563EB")
            color = QColor(hex_color)

            if is_preview:
                color.setAlpha(120)  # Light preview transparency
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(QColor("#38BDF8"), 2, Qt.PenStyle.DashLine))
            else:
                color.setAlpha(220)
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(QColor("#1E293B"), 1))

            painter.drawRoundedRect(block_rect, 4, 4)

            # Text inside block
            painter.setPen(QColor("#FFFFFF"))
            sec_font = QFont("Segoe UI", 8, QFont.Weight.Bold)
            painter.setFont(sec_font)

            text_str = f"{sec.course_code} [{sec.section_name}]"
            room_str = meeting.room if meeting.room else ""
            timing_str = f"{minutes_to_time_str(meeting.start)}-{minutes_to_time_str(meeting.end)}"

            text_rect = QRect(int(x + 4), int(y + 2), int(w - 8), int(h - 4))
            display_full = f"{text_str}\n{timing_str}\n{room_str}".strip()
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, display_full)

        # Draw committed sections
        for sec in self.sections:
            for m in sec.meetings:
                draw_meeting(sec, m, is_preview=False)

        # Draw hover preview section if any
        if self.preview_section and self.preview_section not in self.sections:
            for m in self.preview_section.meetings:
                draw_meeting(self.preview_section, m, is_preview=True)
