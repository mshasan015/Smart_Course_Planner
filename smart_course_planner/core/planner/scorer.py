"""
Scorer module for evaluating and ranking schedules.
Gives a single numeric score for a schedule based on student preferences and config weights.
"""

from typing import Dict, Any
from core.models import Schedule
from core.planner.preference import Preference


class Scorer:
    """
    Computes a numerical score for a given schedule according to student preferences.
    Higher score is better.
    """

    @staticmethod
    def score(schedule: Schedule, preference: Preference) -> float:
        """
        Returns a single floating point score for a schedule.
        Formula:
          + Liked faculty bonus
          - Avoided faculty penalty
          - Days used penalty
          - Idle time penalty
          - Early class penalty (if soft constraint enabled)
        """
        score = 100.0  # Base score

        # 1. Faculty preferences
        liked_set = {f.strip().lower() for f in preference.liked_faculty if f.strip()}
        avoided_set = {f.strip().lower() for f in preference.avoided_faculty if f.strip()}

        for sec in schedule.sections:
            sec_teachers = {t.strip().lower() for t in sec.teachers}

            # Liked faculty
            if liked_set and bool(liked_set.intersection(sec_teachers)):
                score += preference.weight_liked_faculty

            # Avoided faculty
            if avoided_set and bool(avoided_set.intersection(sec_teachers)):
                score += preference.weight_avoided_faculty  # negative value

            # Early class soft penalty
            if preference.no_early_class_soft:
                if any(m.start < preference.no_class_before_minutes for m in sec.meetings):
                    score -= preference.weight_early_class_penalty

        # 2. Days used penalty
        days_count = len(schedule.days_used())
        score -= days_count * preference.weight_day_penalty

        # 3. Idle minutes penalty
        idle_mins = schedule.idle_minutes()
        score -= (idle_mins / 60.0) * preference.weight_idle_hour_penalty

        return round(score, 2)

    @staticmethod
    def get_score_breakdown(schedule: Schedule, preference: Preference) -> Dict[str, Any]:
        """
        Provides detailed breakdown of score components for UI display.
        """
        liked_set = {f.strip().lower() for f in preference.liked_faculty if f.strip()}
        avoided_set = {f.strip().lower() for f in preference.avoided_faculty if f.strip()}

        liked_count = 0
        avoided_count = 0
        early_count = 0

        for sec in schedule.sections:
            sec_teachers = {t.strip().lower() for t in sec.teachers}
            if liked_set and bool(liked_set.intersection(sec_teachers)):
                liked_count += 1
            if avoided_set and bool(avoided_set.intersection(sec_teachers)):
                avoided_count += 1
            if preference.no_early_class_soft and any(m.start < preference.no_class_before_minutes for m in sec.meetings):
                early_count += 1

        days_count = len(schedule.days_used())
        idle_mins = schedule.idle_minutes()

        faculty_score = (liked_count * preference.weight_liked_faculty) + (avoided_count * preference.weight_avoided_faculty)
        days_penalty = days_count * preference.weight_day_penalty
        idle_penalty = round((idle_mins / 60.0) * preference.weight_idle_hour_penalty, 2)
        early_penalty = early_count * preference.weight_early_class_penalty

        total = round(100.0 + faculty_score - days_penalty - idle_penalty - early_penalty, 2)

        return {
            "total_score": total,
            "liked_teachers_matched": liked_count,
            "avoided_teachers_matched": avoided_count,
            "days_count": days_count,
            "days_penalty": days_penalty,
            "idle_minutes": idle_mins,
            "idle_penalty": idle_penalty,
            "early_classes": early_count,
            "early_penalty": early_penalty,
        }
