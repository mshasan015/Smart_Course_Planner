"""
SectionFilter module for filtering sections by courses, faculty, time, seats, and clashes.
"""

from typing import List, Optional, Set
from core.models import Section
from core.conflict import ConflictChecker


class SectionFilter:
    """
    Applies search and filtering rules to a collection of sections.
    """

    def __init__(self, conflict_checker: Optional[ConflictChecker] = None):
        self.conflict_checker = conflict_checker or ConflictChecker()

    def filter(
        self,
        sections: List[Section],
        course_code: Optional[str] = None,
        faculty: Optional[str] = None,
        days: Optional[List[str]] = None,
        earliest_start_minutes: Optional[int] = None,
        free_seats_only: bool = False,
        hide_dropped: bool = True,
        selected_sections: Optional[List[Section]] = None,
        hide_clashing: bool = False,
        query: Optional[str] = None,
    ) -> List[Section]:
        """
        Filters sections according to given criteria.
        """
        results: List[Section] = []
        days_set = {d.strip().lower() for d in days} if days else None
        q = query.strip().lower() if query else None

        for sec in sections:
            # 1. Hide dropped
            if hide_dropped and sec.dropped:
                continue

            # 2. Free seats only
            if free_seats_only and sec.seats_left() <= 0:
                continue

            # 3. Course code filter
            if course_code and course_code.lower() != "all":
                if sec.course_code.strip().lower() != course_code.strip().lower():
                    continue

            # 4. Faculty filter
            if faculty and faculty.lower() != "all":
                target_fac = faculty.strip().lower()
                has_fac = any(target_fac in t.strip().lower() for t in sec.teachers)
                if not has_fac:
                    continue

            # 5. Day filter (section must meet only on allowed days or meet on at least one allowed day)
            if days_set:
                sec_days = {m.day.strip().lower() for m in sec.meetings}
                # If section meetings fall outside allowed days
                if not sec_days.issubset(days_set):
                    continue

            # 6. Earliest start time filter
            if earliest_start_minutes is not None:
                has_early_meeting = any(m.start < earliest_start_minutes for m in sec.meetings)
                if has_early_meeting:
                    continue

            # 7. Hide clashing with selected sections
            if hide_clashing and selected_sections:
                has_clash, _ = self.conflict_checker.does_clash_with_selection(sec, selected_sections)
                if has_clash:
                    continue

            # 8. Query text search
            if q:
                match_code = q in sec.course_code.lower()
                match_sec = q in sec.section_name.lower()
                match_fac = any(q in t.lower() for t in sec.teachers)
                if not (match_code or match_sec or match_fac):
                    continue

            results.append(sec)

        return results
