"""
Smart Course Planner Configuration
Contains column mappings, scoring weights, color schemes, and app constants.
"""

# Expected Column Names in Excel Sheet
COLUMN_COURSE_CODE = "Course Code"
COLUMN_COURSE_TITLE = "Course Title"
COLUMN_SECTION = "Section"
COLUMN_TEACHERS = "Faculty"
COLUMN_CAPACITY = "Capacity"
COLUMN_OCCUPIED = "Occupied"
COLUMN_CREDITS = "Credits"

# Day Column Regex / Prefix Pattern (detects Day1, Day2, Day3, Day 1, etc.)
DAY_COLUMN_PATTERN = r"Day\s*(\d+)"
ROOM_COLUMN_PATTERN = r"Room\s*(\d+)"

# Time constants
EARLY_CLASS_THRESHOLD_MINUTES = 600  # 10:00 AM = 10 * 60 = 600 minutes

# BUG FIX: when a time has no AM/PM marker at all (e.g. a malformed cell like
# "6:45" or "7:00"), time_utils.parse_time_to_minutes() has to guess. It used
# to only guess PM for hours 1-6, so "6:45" (no marker) became 6:45 PM but
# "7:00" (no marker) became 7:00 AM -- an inconsistent jump right at the
# boundary between two very common evening class hours. Hours 1-7 (1 PM-7 PM)
# are now treated consistently as afternoon/evening; hours 8-11 stay morning
# (8 AM-11 AM), matching typical university timetable hours. This is still a
# guess, not a fix for missing data -- routine files should always include
# explicit AM/PM to avoid ambiguity.
AM_PM_GUESS_PM_HOURS = set(range(1, 8))  # 1,2,3,4,5,6,7 -> assumed PM if unmarked

# Scoring Weights for Planner
WEIGHT_LIKED_FACULTY = 50       # Points added per section with liked faculty
WEIGHT_AVOIDED_FACULTY = -100   # Penalty points for avoided faculty (soft)
WEIGHT_DAY_PENALTY = 30         # Penalty per day used (encourages compact schedules)
WEIGHT_IDLE_HOUR_PENALTY = 10   # Penalty per 60 minutes of idle gaps between classes
WEIGHT_EARLY_CLASS_PENALTY = 20 # Penalty for classes before 10 AM (soft rule)

# Distinct palette of colors for courses in Timetable
COURSE_COLORS = [
    "#3B82F6",  # Blue
    "#10B981",  # Emerald Green
    "#F59E0B",  # Amber
    "#8B5CF6",  # Purple
    "#EC4899",  # Pink
    "#06B6D4",  # Cyan
    "#F97316",  # Orange
    "#6366F1",  # Indigo
    "#14B8A6",  # Teal
    "#84CC16",  # Lime
    "#E11D48",  # Rose
    "#0EA5E9",  # Sky
]

# Days of the week standard order
DAYS_OF_WEEK = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DEFAULT_ACTIVE_DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday"]

# Semester defaults
CURRENT_SEMESTER = "Fall 2026"
DEFAULT_MAX_CREDITS = 15.0
DEFAULT_MIN_CREDITS = 3.0
