"""
Tests for time parsing, meeting overlaps, and conflict detection.
"""

import pytest
from core.time_utils import parse_time_to_minutes, parse_time_range
from core.models import Meeting, Section
from core.conflict import ConflictChecker


def test_time_parser_minutes():
    """Day 1 Done When requirement: '08:30:AM' gives 510 and '12:30:PM' gives 750."""
    assert parse_time_to_minutes("08:30:AM") == 510
    assert parse_time_to_minutes("12:30:PM") == 750
    assert parse_time_to_minutes("01:00:PM") == 780
    assert parse_time_to_minutes("12:00:AM") == 0


def test_time_range_no_class_marker():
    """Day 1 Done When requirement: Treat ' - ' as 'no class', not as an error."""
    assert parse_time_range(" - ") is None
    assert parse_time_range("-") is None
    assert parse_time_range("") is None

    # Valid range
    tr = parse_time_range("08:30:AM - 09:50:AM")
    assert tr == (510, 590)


def test_touching_classes_do_not_clash():
    """Day 10 requirement: two classes touching end-to-start do NOT clash."""
    # Meeting 1: 08:30 - 09:50 (510 to 590)
    m1 = Meeting(day="Sunday", start=510, end=590, room="UB101")
    # Meeting 2: 09:50 - 11:10 (590 to 670)
    m2 = Meeting(day="Sunday", start=590, end=670, room="UB102")

    assert not m1.overlaps(m2), "Classes touching end-to-start must NOT overlap"
    assert not m2.overlaps(m1), "Symmetry check"


def test_overlapping_classes_clash():
    """Overlap rule: same day and startA < endB and startB < endA."""
    m1 = Meeting(day="Sunday", start=510, end=590)  # 08:30 - 09:50
    m2 = Meeting(day="Sunday", start=550, end=630)  # 09:10 - 10:30 (overlaps by 40 mins)

    assert m1.overlaps(m2) is True
    assert m2.overlaps(m1) is True

    # Different days do not clash
    m3 = Meeting(day="Monday", start=510, end=590)
    assert m1.overlaps(m3) is False


def test_conflict_checker_selection():
    m1 = Meeting(day="Sunday", start=600, end=680)
    m2 = Meeting(day="Sunday", start=600, end=680)
    m3 = Meeting(day="Sunday", start=700, end=780)

    s1 = Section(course_code="CSE 1115", section_name="B", meetings=[m1])
    s2 = Section(course_code="CSE 2215", section_name="A", meetings=[m2])
    s3 = Section(course_code="MATH 2103", section_name="A", meetings=[m3])

    checker = ConflictChecker([s1, s2, s3])

    clash, reason = checker.does_clash_with_selection(s2, [s1])
    assert clash is True
    assert reason == s1

    clash, reason = checker.does_clash_with_selection(s3, [s1])
    assert clash is False
    assert reason is None
