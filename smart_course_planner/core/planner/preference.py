"""
Preference model for student schedule optimization.
Specifies wanted courses, liked/avoided faculty, timing preferences, and priority weights.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import config


@dataclass
class Preference:
    """
    User configuration for automatic schedule generation.
    """
    wanted_courses: List[str] = field(default_factory=list)
    liked_faculty: List[str] = field(default_factory=list)
    avoided_faculty: List[str] = field(default_factory=list)

    # "No class before 10 AM" (threshold in minutes, e.g. 600)
    no_class_before_minutes: int = config.EARLY_CLASS_THRESHOLD_MINUTES
    no_early_class_hard: bool = False  # Hard constraint: completely remove sections before 10 AM
    no_early_class_soft: bool = False  # Soft constraint: penalize sections before 10 AM

    # Priority: "fewer_days", "fewer_gaps", or "balanced"
    priority: str = "balanced"

    # Custom weights (fall back to config defaults)
    weight_liked_faculty: int = config.WEIGHT_LIKED_FACULTY
    weight_avoided_faculty: int = config.WEIGHT_AVOIDED_FACULTY
    weight_day_penalty: int = config.WEIGHT_DAY_PENALTY
    weight_idle_hour_penalty: int = config.WEIGHT_IDLE_HOUR_PENALTY
    weight_early_class_penalty: int = config.WEIGHT_EARLY_CLASS_PENALTY

    def adjust_weights_for_priority(self) -> None:
        """Adjusts weights based on student's chosen priority."""
        if self.priority == "fewer_days":
            self.weight_day_penalty = config.WEIGHT_DAY_PENALTY * 2
            self.weight_idle_hour_penalty = int(config.WEIGHT_IDLE_HOUR_PENALTY * 0.5)
        elif self.priority == "fewer_gaps":
            self.weight_idle_hour_penalty = config.WEIGHT_IDLE_HOUR_PENALTY * 2
            self.weight_day_penalty = int(config.WEIGHT_DAY_PENALTY * 0.5)
