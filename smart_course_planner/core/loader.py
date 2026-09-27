"""
RoutineLoader and ImportReport for loading Excel routine schedules.
Handles column name matching, multi-day pattern detection, bad rows, and data cleaning.
Golden Rule 2: Never use column positions; detect Day1, Day2, Day3... automatically.
"""

import re
import os
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import pandas as pd

from config import (
    COLUMN_COURSE_CODE,
    COLUMN_COURSE_TITLE,
    COLUMN_SECTION,
    COLUMN_TEACHERS,
    COLUMN_CAPACITY,
    COLUMN_OCCUPIED,
    COLUMN_CREDITS,
    DAY_COLUMN_PATTERN,
    ROOM_COLUMN_PATTERN,
    DEFAULT_ACTIVE_DAYS,
)
from core.models import Course, Section, Meeting
from core.time_utils import parse_time_range, normalize_day


@dataclass
class BadRow:
    row_number: int
    raw_data: dict
    reason: str


@dataclass
class ImportReport:
    total_rows: int = 0
    valid_courses: int = 0
    valid_sections: int = 0
    bad_rows: List[BadRow] = field(default_factory=list)
    # BUG FIX: previously an unlabeled Day column silently became "Sunday"
    # with zero visibility. Now every such guess is recorded here so the
    # caller (CLI/GUI) can warn the user instead of trusting mislabeled data.
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        base = (
            f"Loaded {self.valid_courses} courses ({self.valid_sections} sections) "
            f"from {self.total_rows} rows. Bad rows skipped: {len(self.bad_rows)}."
        )
        if self.warnings:
            base += f" Warnings: {len(self.warnings)} (see report.warnings)."
        return base


class RoutineLoader:
    """
    Loads routine schedules from Excel files.
    """

    def load(self, path: str) -> Tuple[List[Course], ImportReport]:
        """
        Loads an Excel routine file and parses it into Course and Section models.
        Returns a tuple of (List[Course], ImportReport).
        """
        report = ImportReport()

        if not os.path.exists(path):
            report.bad_rows.append(BadRow(0, {}, f"File not found: {path}"))
            return [], report

        try:
            df = pd.read_excel(path, dtype=str, keep_default_na=False)
        except Exception as e:
            report.bad_rows.append(BadRow(0, {}, f"Failed to read Excel file: {str(e)}"))
            return [], report

        report.total_rows = len(df)

        # Build column index mapping by normalized names
        col_map = self._resolve_columns(df.columns.tolist())

        courses_dict: Dict[str, Course] = {}

        for idx, row in df.iterrows():
            row_num = int(idx) + 2  # 1-indexed plus header row

            course_code = self._get_val(row, col_map.get("code")).strip()
            course_title = self._get_val(row, col_map.get("title")).strip()
            section_raw = self._get_val(row, col_map.get("section")).strip()

            if not course_code:
                report.bad_rows.append(BadRow(row_num, row.to_dict(), "Missing Course Code"))
                continue

            if not section_raw:
                report.bad_rows.append(BadRow(row_num, row.to_dict(), "Missing Section Name"))
                continue

            # Check for (Dropped) in section name or status
            dropped = False
            if "(DROPPED)" in section_raw.upper() or "DROPPED" in section_raw.upper():
                dropped = True
                clean_sec_name = re.sub(r"\(?\bDROPPED\b\)?", "", section_raw, flags=re.I).strip()
            else:
                clean_sec_name = section_raw

            # Capacity and Occupied
            cap_val = self._get_val(row, col_map.get("capacity"))
            occ_val = self._get_val(row, col_map.get("occupied"))
            capacity = self._parse_int(cap_val, default=40)
            occupied = self._parse_int(occ_val, default=0)

            # Credits
            cred_val = self._get_val(row, col_map.get("credits"))
            credits = self._parse_float(cred_val, default=3.0)

            # Faculty (can have up to 3 teachers, separated by comma, slash, semicolon, or newline)
            faculty_raw = self._get_val(row, col_map.get("faculty")).strip()
            teachers = self._parse_teachers(faculty_raw)

            # Parse meetings across dynamic Day1, Day2, Day3... columns
            meetings = self._parse_meetings(row, col_map, report=report, row_num=row_num)

            # Build section
            section = Section(
                course_code=course_code,
                section_name=clean_sec_name,
                teachers=teachers,
                meetings=meetings,
                capacity=capacity,
                occupied=occupied,
                dropped=dropped,
                credits=credits,
            )

            # Add to course
            if course_code not in courses_dict:
                courses_dict[course_code] = Course(
                    code=course_code,
                    title=course_title or course_code,
                    credits=credits,
                    sections=[],
                )
            courses_dict[course_code].sections.append(section)
            report.valid_sections += 1

        courses_list = list(courses_dict.values())
        report.valid_courses = len(courses_list)
        return courses_list, report

    def _resolve_columns(self, columns: List[str]) -> dict:
        """
        Dynamically finds standard and multi-day columns using regex patterns.
        """
        col_map = {
            "code": None,
            "title": None,
            "section": None,
            "faculty": None,
            "capacity": None,
            "occupied": None,
            "credits": None,
            "days": [],  # List of (day_col, room_col or None)
        }

        # Day column map by index suffix (e.g. Day1 -> 1)
        day_cols: Dict[str, str] = {}
        room_cols: Dict[str, str] = {}

        for col in columns:
            c_clean = col.strip()
            c_lower = c_clean.lower()

            if c_lower == COLUMN_COURSE_CODE.lower() or "course" in c_lower and "code" in c_lower:
                col_map["code"] = col
            elif c_lower == COLUMN_COURSE_TITLE.lower() or "title" in c_lower:
                col_map["title"] = col
            elif c_lower == COLUMN_SECTION.lower() or "sec" in c_lower:
                col_map["section"] = col
            elif c_lower == COLUMN_TEACHERS.lower() or "faculty" in c_lower or "teacher" in c_lower or "instructor" in c_lower:
                col_map["faculty"] = col
            elif c_lower == COLUMN_CAPACITY.lower() or "cap" in c_lower:
                col_map["capacity"] = col
            elif c_lower == COLUMN_OCCUPIED.lower() or "occ" in c_lower or "enrolled" in c_lower:
                col_map["occupied"] = col
            elif c_lower == COLUMN_CREDITS.lower() or "cred" in c_lower:
                col_map["credits"] = col

            # Check for Day1, Day2, Day3 pattern
            day_match = re.search(DAY_COLUMN_PATTERN, c_clean, re.I)
            if day_match:
                day_num = day_match.group(1)
                day_cols[day_num] = col

            # Check for Room1, Room2, Room3 pattern
            room_match = re.search(ROOM_COLUMN_PATTERN, c_clean, re.I)
            if room_match:
                room_num = room_match.group(1)
                room_cols[room_num] = col

        # Pair day columns with room columns if available
        for num in sorted(day_cols.keys(), key=lambda x: int(x)):
            col_map["days"].append((day_cols[num], room_cols.get(num)))

        # Fallback if no Day1/Day2 pattern but standard 'Day' or day names exist
        if not col_map["days"]:
            for col in columns:
                if col.strip().lower() in ("day", "schedule", "time", "class timing"):
                    col_map["days"].append((col, None))

        return col_map

    def _get_val(self, row, col_name: Optional[str]) -> str:
        if not col_name or col_name not in row:
            return ""
        val = row[col_name]
        if pd.isna(val):
            return ""
        return str(val)

    def _parse_teachers(self, text: str) -> List[str]:
        if not text or text.strip().upper() in ("TBA", "N/A", "NONE", "-"):
            return ["TBA"]
        # Split by comma, semicolon, slash, or newline
        parts = re.split(r"[,;/|\n]+", text)
        teachers = [p.strip() for p in parts if p.strip()]
        return teachers if teachers else ["TBA"]

    def _parse_int(self, val: str, default: int = 0) -> int:
        try:
            return int(float(val.strip()))
        except (ValueError, TypeError):
            return default

    def _parse_float(self, val: str, default: float = 3.0) -> float:
        try:
            return float(val.strip())
        except (ValueError, TypeError):
            return default

    def _parse_meetings(
        self,
        row,
        col_map: dict,
        report: Optional[ImportReport] = None,
        row_num: int = 0,
    ) -> List[Meeting]:
        meetings: List[Meeting] = []
        day_columns = col_map.get("days", [])

        for idx, (day_col, room_col) in enumerate(day_columns):
            raw_cell = self._get_val(row, day_col).strip()
            room_val = self._get_val(row, room_col).strip() if room_col else ""

            if not raw_cell or raw_cell in ("-", "--", "TBA", "N/A"):
                continue

            # Check if cell contains Day name and Time range, e.g. "Sunday 08:30:AM - 09:50:AM"
            # or column name indicates the day (e.g. Day1 may have 'Sun 08:30:AM - 09:50:AM')
            day_name = None
            time_part = raw_cell

            # Try to extract day from cell content
            day_match = re.search(r"^(Sat(?:urday)?|Sun(?:day)?|Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?)\b[:\s]*(.*)$", raw_cell, re.I)
            if day_match:
                day_name = normalize_day(day_match.group(1))
                time_part = day_match.group(2).strip()
            else:
                # If column name has day (e.g. 'Sunday' or 'Day 1 (Sun)')
                header_match = re.search(r"(Sat(?:urday)?|Sun(?:day)?|Mon(?:day)?|Tue(?:sday)?|Wed(?:nesday)?|Thu(?:rsday)?|Fri(?:day)?)", day_col, re.I)
                if header_match:
                    day_name = normalize_day(header_match.group(1))
                else:
                    # BUG FIX: this used to silently hardcode "Sunday" for
                    # EVERY day column that had no weekday name in either
                    # the cell or the header (e.g. plain "Day 1"/"Day 2"
                    # columns), corrupting conflict detection with no
                    # warning at all. We now fall back to mapping the
                    # column's position onto the standard active-day order
                    # (config.DEFAULT_ACTIVE_DAYS: Sun, Mon, Tue, Wed, Thu),
                    # which is the intent the old comment described but
                    # never implemented, and we log a warning so the caller
                    # can surface it to the user instead of trusting a guess.
                    day_name = DEFAULT_ACTIVE_DAYS[idx % len(DEFAULT_ACTIVE_DAYS)]
                    if report is not None:
                        report.warnings.append(
                            f"Row {row_num}: column '{day_col}' has no weekday name in its "
                            f"header or cell value ('{raw_cell}'); assumed '{day_name}' based "
                            f"on column order. Please verify this routine file's day columns."
                        )

            time_range = parse_time_range(time_part)
            if time_range:
                start_min, end_min = time_range
                meetings.append(Meeting(day=day_name, start=start_min, end=end_min, room=room_val))

        return meetings
