"""
Data models for Smart Course Planner.
Defines Meeting, Section, Course, and Schedule.
Golden Rule: Core must NEVER import PySide6.
"""

from dataclasses import dataclass, field
from typing import List, Set, Dict


@dataclass
class Meeting:
    """
    Represents a single class meeting slot.
    start and end times are stored as minutes from midnight (e.g. 08:30 AM = 510).
    """
    day: str
    start: int   # minutes from midnight
    end: int     # minutes from midnight
    room: str = ""

    def overlaps(self, other: "Meeting") -> bool:
        """
        Clash rule: same day and startA < endB and startB < endA.
        Touching end-to-start (startA == endB or startB == endA) does NOT clash.
        """
        if self.day.strip().lower() != other.day.strip().lower():
            return False
        return self.start < other.end and other.start < self.end

    def to_dict(self) -> dict:
        return {
            "day": self.day,
            "start": self.start,
            "end": self.end,
            "room": self.room,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Meeting":
        return cls(
            day=data["day"],
            start=int(data["start"]),
            end=int(data["end"]),
            room=data.get("room", ""),
        )


@dataclass
class Section:
    """
    Represents a course section with meetings, faculty, and enrollment info.
    """
    course_code: str
    section_name: str
    teachers: List[str] = field(default_factory=list)
    meetings: List[Meeting] = field(default_factory=list)
    capacity: int = 0
    occupied: int = 0
    dropped: bool = False
    credits: float = 3.0

    def seats_left(self) -> int:
        """Returns remaining available seats."""
        if self.dropped:
            return 0
        return max(0, self.capacity - self.occupied)

    def clashes_with(self, other: "Section") -> bool:
        """
        Checks if this section clashes with another section
        (any meeting overlapping another meeting).
        """
        if self.course_code == other.course_code and self.section_name == other.section_name:
            return True
        for m1 in self.meetings:
            for m2 in other.meetings:
                if m1.overlaps(m2):
                    return True
        return False

    def to_dict(self) -> dict:
        return {
            "course_code": self.course_code,
            "section_name": self.section_name,
            "teachers": self.teachers,
            "meetings": [m.to_dict() for m in self.meetings],
            "capacity": self.capacity,
            "occupied": self.occupied,
            "dropped": self.dropped,
            "credits": self.credits,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Section":
        return cls(
            course_code=data["course_code"],
            section_name=data["section_name"],
            teachers=data.get("teachers", []),
            meetings=[Meeting.from_dict(m) for m in data.get("meetings", [])],
            capacity=int(data.get("capacity", 0)),
            occupied=int(data.get("occupied", 0)),
            dropped=bool(data.get("dropped", False)),
            credits=float(data.get("credits", 3.0)),
        )


@dataclass
class Course:
    """
    Represents an academic course offering multiple sections.
    """
    code: str
    title: str
    credits: float
    sections: List[Section] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "title": self.title,
            "credits": self.credits,
            "sections": [s.to_dict() for s in self.sections],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Course":
        return cls(
            code=data["code"],
            title=data["title"],
            credits=float(data.get("credits", 3.0)),
            sections=[Section.from_dict(s) for s in data.get("sections", [])],
        )


@dataclass
class Schedule:
    """
    A planned schedule consisting of selected sections.
    """
    sections: List[Section] = field(default_factory=list)

    def total_credits(self) -> float:
        """Returns total credits of all selected sections."""
        return sum(s.credits for s in self.sections)

    def days_used(self) -> List[str]:
        """Returns list of distinct days on which classes meet, sorted by standard week."""
        day_order = {
            "saturday": 0,
            "sunday": 1,
            "monday": 2,
            "tuesday": 3,
            "wednesday": 4,
            "thursday": 5,
            "friday": 6,
        }
        seen_days = set()
        for s in self.sections:
            for m in s.meetings:
                seen_days.add(m.day.strip().title())
        return sorted(list(seen_days), key=lambda d: day_order.get(d.lower(), 99))

    def idle_minutes(self) -> int:
        """
        Calculates total idle gap minutes between consecutive classes on the same day.
        """
        # Group meetings by day
        day_meetings: Dict[str, List[Meeting]] = {}
        for s in self.sections:
            for m in s.meetings:
                d = m.day.strip().title()
                day_meetings.setdefault(d, []).append(m)

        total_idle = 0
        for d, meetings in day_meetings.items():
            if len(meetings) < 2:
                continue
            # Sort meetings by start time
            sorted_m = sorted(meetings, key=lambda m: m.start)
            for i in range(len(sorted_m) - 1):
                gap = sorted_m[i + 1].start - sorted_m[i].end
                if gap > 0:
                    total_idle += gap
        return total_idle

    def has_conflict(self) -> bool:
        """Returns True if any pair of sections in the schedule clashes."""
        n = len(self.sections)
        for i in range(n):
            for j in range(i + 1, n):
                if self.sections[i].clashes_with(self.sections[j]):
                    return True
        return False

    def to_dict(self) -> dict:
        return {
            "sections": [s.to_dict() for s in self.sections],
            "total_credits": self.total_credits(),
            "days_used": self.days_used(),
            "idle_minutes": self.idle_minutes(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Schedule":
        return cls(
            sections=[Section.from_dict(s) for s in data.get("sections", [])]
        )
