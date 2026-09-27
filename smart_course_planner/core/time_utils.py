"""
Time and day parsing utilities for Smart Course Planner.
Golden Rule 3: Store time as minutes from midnight (08:30 AM = 510).
"""

import re
from typing import Optional, Tuple

import config


def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """
    Parses a time string into minutes from midnight.
    Handles formats such as:
      - '08:30:AM' -> 510
      - '12:30:PM' -> 750
      - '08:30 AM' -> 510
      - '8:30' (assumes AM if < 7, else PM context, or standard 24h)
      - '01:00:PM' -> 780
      - '12:00:AM' -> 0
    Returns None if empty or invalid.
    """
    if not time_str:
        return None
    cleaned = time_str.strip().upper()

    # Special case / no class marker
    if cleaned in ("-", "--", "N/A", "TBA", "NONE", ""):
        return None

    # Match patterns like 08:30:AM, 08:30 AM, 8:30AM, 08:30
    match = re.match(r"^(\d{1,2}):(\d{2})(?::)?\s*([AP]M)?$", cleaned)
    if not match:
        return None

    hours = int(match.group(1))
    minutes = int(match.group(2))
    meridiem = match.group(3)

    if meridiem == "PM" and hours != 12:
        hours += 12
    elif meridiem == "AM" and hours == 12:
        hours = 0
    elif not meridiem:
        # BUG FIX: previously only hours 1-6 were assumed PM when no AM/PM
        # marker was present, so "6:45" -> 6:45 PM but "7:00" -> 7:00 AM,
        # an inconsistent jump right across a common evening-class boundary.
        # Now uses the shared, documented config.AM_PM_GUESS_PM_HOURS set
        # (1-7) so the guess is consistent. Hour 12 is left as-is (treated
        # as 12:00 PM / noon), matching prior behavior.
        if hours in config.AM_PM_GUESS_PM_HOURS:
            hours += 12

    return hours * 60 + minutes


def parse_time_range(range_str: str) -> Optional[Tuple[int, int]]:
    """
    Parses a time range string, e.g. '08:30:AM - 09:50:AM'.
    Treats ' - ' as 'no class' (returns None), not an error.
    Returns (start_minutes, end_minutes) or None if invalid or no class.
    """
    if not range_str:
        return None

    cleaned = range_str.strip()
    if cleaned in ("-", "--", "- -", " - ", "TBA", "N/A", ""):
        return None

    # Split on hyphen / dash
    parts = re.split(r"\s*[-–—]\s*", cleaned)
    if len(parts) != 2:
        return None

    start_min = parse_time_to_minutes(parts[0])
    end_min = parse_time_to_minutes(parts[1])

    if start_min is None or end_min is None:
        return None

    # If end time is before start time, it might cross noon (e.g. 11:30 AM - 1:00 PM without PM on first)
    if end_min <= start_min and end_min < 720:
        end_min += 720

    return (start_min, end_min)


def minutes_to_time_str(minutes: int) -> str:
    """
    Converts minutes from midnight back to readable 12-hour format 'HH:MM AM/PM'.
    e.g. 510 -> '08:30 AM', 750 -> '12:30 PM'.
    """
    if minutes < 0:
        minutes = 0
    hours = (minutes // 60) % 24
    mins = minutes % 60
    meridiem = "AM" if hours < 12 else "PM"
    display_hour = hours % 12
    if display_hour == 0:
        display_hour = 12
    return f"{display_hour:02d}:{mins:02d} {meridiem}"


def normalize_day(day_str: str) -> str:
    """
    Normalizes day strings to full title case ('Sunday', 'Monday', etc.).
    """
    d = day_str.strip().lower()
    day_map = {
        "sat": "Saturday",
        "saturday": "Saturday",
        "sun": "Sunday",
        "sunday": "Sunday",
        "mon": "Monday",
        "monday": "Monday",
        "tue": "Tuesday",
        "tues": "Tuesday",
        "tuesday": "Tuesday",
        "wed": "Wednesday",
        "wednesday": "Wednesday",
        "thu": "Thursday",
        "thur": "Thursday",
        "thurs": "Thursday",
        "thursday": "Thursday",
        "fri": "Friday",
        "friday": "Friday",
    }
    return day_map.get(d, day_str.strip().title())
