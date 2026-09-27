"""
SectionTableModel for PySide6 QTableView.
Subclasses QAbstractTableModel to present course sections, seats left, and clash state.
"""

from typing import List, Optional, Set
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush

from core.models import Section
from core.time_utils import minutes_to_time_str
from core.conflict import ConflictChecker


class SectionTableModel(QAbstractTableModel):
    """
    Feeds course sections to a Qt table view with clash awareness.
    """

    COLUMNS = ["Course", "Section", "Faculty", "Timing", "Seats Left", "Credits", "Status"]

    def __init__(self, sections: Optional[List[Section]] = None, parent=None):
        super().__init__(parent)
        self.sections: List[Section] = sections or []
        self.selected_sections: List[Section] = []
        self.conflict_checker = ConflictChecker()
        self.clash_status: List[Optional[Section]] = [None] * len(self.sections)

    def set_sections(self, sections: List[Section]) -> None:
        self.beginResetModel()
        self.sections = sections
        self.conflict_checker.precompute_clashes(sections)
        self._recompute_clashes()
        self.endResetModel()

    def set_selected_sections(self, selected: List[Section]) -> None:
        self.beginResetModel()
        self.selected_sections = selected
        self._recompute_clashes()
        self.endResetModel()

    def _recompute_clashes(self) -> None:
        self.clash_status = []
        for sec in self.sections:
            if sec in self.selected_sections:
                self.clash_status.append(None)
                continue
            has_clash, clashing_with = self.conflict_checker.does_clash_with_selection(
                sec, self.selected_sections
            )
            self.clash_status.append(clashing_with if has_clash else None)

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self.sections)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLUMNS)

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.ItemDataRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole):
        if not index.isValid() or not (0 <= index.row() < len(self.sections)):
            return None

        sec = self.sections[index.row()]
        col = index.column()
        is_clashing = self.clash_status[index.row()] is not None
        is_selected = sec in self.selected_sections

        # Text Display Role
        if role == Qt.ItemDataRole.DisplayRole:
            if col == 0:
                return sec.course_code
            elif col == 1:
                return sec.section_name
            elif col == 2:
                return ", ".join(sec.teachers) if sec.teachers else "TBA"
            elif col == 3:
                timing_strs = [
                    f"{m.day[:3]} {minutes_to_time_str(m.start)}-{minutes_to_time_str(m.end)}"
                    for m in sec.meetings
                ]
                return " | ".join(timing_strs) if timing_strs else "No Meetings"
            elif col == 4:
                return f"{sec.seats_left()} / {sec.capacity}"
            elif col == 5:
                return f"{sec.credits:.1f}"
            elif col == 6:
                if sec.dropped:
                    return "DROPPED"
                if is_selected:
                    return "SELECTED"
                if is_clashing:
                    clash_with = self.clash_status[index.row()]
                    return f"Clashes with {clash_with.course_code} [{clash_with.section_name}]"
                return "AVAILABLE"

        # Foreground Text Color
        if role == Qt.ItemDataRole.ForegroundRole:
            if is_clashing:
                return QBrush(QColor("#94A3B8"))  # Greyed out
            if sec.dropped:
                return QBrush(QColor("#EF4444"))
            if is_selected:
                return QBrush(QColor("#38BDF8"))
            return QBrush(QColor("#F8FAFC"))

        # Background Color
        if role == Qt.ItemDataRole.BackgroundRole:
            if is_selected:
                return QBrush(QColor("#0F3D6E"))
            if is_clashing:
                return QBrush(QColor("#1E232F"))
            return None

        # Tooltip with details
        if role == Qt.ItemDataRole.ToolTipRole:
            if is_clashing:
                clash_sec = self.clash_status[index.row()]
                return f"Time Clash with selected: {clash_sec.course_code} {clash_sec.section_name}"
            return f"{sec.course_code} Sec {sec.section_name} ({sec.seats_left()} seats left)"

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        sec = self.sections[index.row()]
        if sec.dropped or self.clash_status[index.row()] is not None:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
