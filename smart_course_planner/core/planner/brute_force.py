"""
Brute-force schedule planner.
Filters out sections breaking hard rules, checks all combinations for clashes,
scores valid schedules, and returns the top 5 plans.
"""

import itertools
from typing import List, Tuple, Dict, Optional
from core.models import Course, Section, Schedule
from core.planner.preference import Preference
from core.planner.scorer import Scorer
from core.conflict import ConflictChecker


class BruteForcePlanner:
    """
    Finds optimal schedules by enumerating all valid combinations of sections.
    """

    def __init__(self, courses: List[Course]):
        self.courses_dict: Dict[str, Course] = {c.code: c for c in courses}
        all_sections = [s for c in courses for s in c.sections]
        self.conflict_checker = ConflictChecker(all_sections)

    def plan(
        self,
        preference: Preference,
        top_k: int = 5,
    ) -> List[Tuple[Schedule, float]]:
        """
        Generates top_k valid schedules ranked by Scorer.score().
        Returns a list of tuples: [(schedule, score), ...]
        """
        preference.adjust_weights_for_priority()

        # 1. Filter sections for each wanted course based on hard rules
        course_sections: List[List[Section]] = []
        for code in preference.wanted_courses:
            course = self.courses_dict.get(code)
            if not course:
                return []

            valid_sec = []
            for sec in course.sections:
                if sec.dropped:
                    continue
                # Hard rule: no class before 10 AM
                if preference.no_early_class_hard:
                    if any(m.start < preference.no_class_before_minutes for m in sec.meetings):
                        continue
                valid_sec.append(sec)

            # If any wanted course has 0 valid sections, no plan is possible
            if not valid_sec:
                return []
            course_sections.append(valid_sec)

        # 2. Iterate through all Cartesian product combinations
        valid_plans: List[Tuple[Schedule, float]] = []

        for combo in itertools.product(*course_sections):
            sections = list(combo)

            # Check for clashes among sections in combo
            has_clash = False
            for i in range(len(sections)):
                for j in range(i + 1, len(sections)):
                    if sections[i].clashes_with(sections[j]):
                        has_clash = True
                        break
                if has_clash:
                    break

            if has_clash:
                continue

            sched = Schedule(sections=sections)
            score = Scorer.score(sched, preference)
            valid_plans.append((sched, score))

        # 3. Sort by score descending and return top_k
        valid_plans.sort(key=lambda item: item[1], reverse=True)
        return valid_plans[:top_k]
