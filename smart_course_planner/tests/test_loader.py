"""
Tests for RoutineLoader, column detection, and data parsing.
"""

import os
import pytest
from core.loader import RoutineLoader
from core.models import Course, Section


@pytest.fixture
def sample_excel_path():
    p = os.path.join(os.path.dirname(__file__), "..", "data", "routine_sample.xlsx")
    return os.path.abspath(p)


@pytest.fixture
def changed_excel_path():
    p = os.path.join(os.path.dirname(__file__), "..", "data", "routine_changed.xlsx")
    return os.path.abspath(p)


def test_loader_sample_file(sample_excel_path):
    loader = RoutineLoader()
    courses, report = loader.load(sample_excel_path)

    assert len(courses) > 0, "Should load courses from sample file"
    assert report.valid_sections > 0, "Should load valid sections"
    assert len(report.bad_rows) > 0, "Should catch bad rows in ImportReport without crashing"

    # Check for CSE 1115
    course_codes = [c.code for c in courses]
    assert "CSE 1115" in course_codes
    assert "CSE 2215" in course_codes

    cse1115 = next(c for c in courses if c.code == "CSE 1115")
    sec_names = [s.section_name for s in cse1115.sections]

    # Check that extra space was stripped ('A ' -> 'A')
    assert "A" in sec_names

    # Check that (Dropped) was parsed properly
    dropped_sec = next((s for s in cse1115.sections if s.dropped), None)
    assert dropped_sec is not None, "Should identify dropped section"
    assert dropped_sec.dropped is True


def test_loader_multi_teacher(sample_excel_path):
    loader = RoutineLoader()
    courses, _ = loader.load(sample_excel_path)
    cse2215 = next(c for c in courses if c.code == "CSE 2215")
    sec_c = next(s for s in cse2215.sections if s.section_name == "C")

    # Up to 3 teachers parsed
    assert len(sec_c.teachers) == 3
    assert "Barbara Liskov" in sec_c.teachers


def test_loader_changed_sheet_with_day3(changed_excel_path):
    """Golden Rule 2: Changes in column positions and Day3 column must still work."""
    loader = RoutineLoader()
    courses, report = loader.load(changed_excel_path)

    assert len(courses) == 2
    codes = [c.code for c in courses]
    assert "CSE 3311" in codes
    assert "CSE 3421" in codes

    cse3311 = next(c for c in courses if c.code == "CSE 3311")
    sec_a = next(s for s in cse3311.sections if s.section_name == "A")
    # Section A has 3 meetings (Day 1 Sun, Day 2 Tue, Day 3 Thu)
    assert len(sec_a.meetings) == 3
