"""
CP-SAT Planner using Google OR-Tools.
Implements constraint satisfaction optimization:
1. One yes/no variable for each section.
2. For each wanted course, exactly one section is "yes".
3. For each clashing pair, at most one is "yes".
4. For each day, a day variable is "yes" if any chosen section meets on that day.
5. Maximize: liked faculty points - days penalty - idle time penalty.
6. For next best plan, add 'not this same plan again' and solve again (up to 5 times).
"""

from typing import List, Tuple, Dict, Optional, Set
from ortools.sat.python import cp_model
from core.models import Course, Section, Schedule, Meeting
from core.planner.preference import Preference
from core.planner.scorer import Scorer


class CpSatPlanner:
    """
    CP-SAT (Constraint Programming) optimizer for course scheduling.
    """

    def __init__(self, courses: List[Course]):
        self.courses_dict: Dict[str, Course] = {c.code: c for c in courses}

    def _section_key(self, sec: Section) -> str:
        return f"{sec.course_code}_{sec.section_name}"

    def plan(
        self,
        preference: Preference,
        top_k: int = 5,
    ) -> List[Tuple[Schedule, float]]:
        """
        Solves the course scheduling problem using OR-Tools CP-SAT.
        Returns top_k solutions: [(Schedule, score), ...].
        """
        preference.adjust_weights_for_priority()

        # 1. Filter sections that violate hard constraints
        filtered_course_sections: Dict[str, List[Section]] = {}
        candidate_sections: List[Section] = []

        for code in preference.wanted_courses:
            course = self.courses_dict.get(code)
            if not course:
                return []

            valid_sec = []
            for sec in course.sections:
                if sec.dropped:
                    continue
                if preference.no_early_class_hard:
                    if any(m.start < preference.no_class_before_minutes for m in sec.meetings):
                        continue
                valid_sec.append(sec)

            if not valid_sec:
                return []
            filtered_course_sections[code] = valid_sec
            candidate_sections.extend(valid_sec)

        # 2. Build CP-SAT Model
        model = cp_model.CpModel()

        # Map section key to boolean variable
        sec_vars: Dict[str, cp_model.IntVar] = {}
        sec_by_key: Dict[str, Section] = {}

        for sec in candidate_sections:
            k = self._section_key(sec)
            sec_vars[k] = model.NewBoolVar(f"sec_{k}")
            sec_by_key[k] = sec

        # Constraint 1: For each wanted course, exactly one section is chosen
        for code in preference.wanted_courses:
            course_sec_keys = [self._section_key(s) for s in filtered_course_sections[code]]
            model.AddExactlyOne([sec_vars[k] for k in course_sec_keys])

        # Constraint 2: For each clashing pair of sections, at most one can be chosen
        num_candidates = len(candidate_sections)
        clash_pairs_added: Set[Tuple[str, str]] = set()

        for i in range(num_candidates):
            s1 = candidate_sections[i]
            k1 = self._section_key(s1)
            for j in range(i + 1, num_candidates):
                s2 = candidate_sections[j]
                k2 = self._section_key(s2)

                # Skip if from same course (already handled by AddExactlyOne)
                if s1.course_code == s2.course_code:
                    continue

                if s1.clashes_with(s2):
                    pair = (min(k1, k2), max(k1, k2))
                    if pair not in clash_pairs_added:
                        clash_pairs_added.add(pair)
                        model.Add(sec_vars[k1] + sec_vars[k2] <= 1)

        # Constraint 3: Day usage variables
        # Distinct days in all candidate sections
        all_days = {m.day.strip().title() for sec in candidate_sections for m in sec.meetings}
        day_vars: Dict[str, cp_model.IntVar] = {}

        for day in all_days:
            day_var = model.NewBoolVar(f"day_{day}")
            day_vars[day] = day_var

            # Sections that have a meeting on this day
            secs_on_day = [
                sec_vars[self._section_key(s)]
                for s in candidate_sections
                if any(m.day.strip().title() == day for m in s.meetings)
            ]

            # If any section is chosen on this day, day_var must be 1
            for s_var in secs_on_day:
                model.Add(day_var >= s_var)

        # Objective: Maximize score components
        liked_set = {f.strip().lower() for f in preference.liked_faculty if f.strip()}
        avoided_set = {f.strip().lower() for f in preference.avoided_faculty if f.strip()}

        objective_terms = []

        # Faculty and soft timing preferences per section
        for sec in candidate_sections:
            k = self._section_key(sec)
            var = sec_vars[k]
            sec_teachers = {t.strip().lower() for t in sec.teachers}

            # Faculty points
            if liked_set and bool(liked_set.intersection(sec_teachers)):
                objective_terms.append(var * preference.weight_liked_faculty)
            if avoided_set and bool(avoided_set.intersection(sec_teachers)):
                objective_terms.append(var * preference.weight_avoided_faculty)

            # Soft early class penalty
            if preference.no_early_class_soft:
                if any(m.start < preference.no_class_before_minutes for m in sec.meetings):
                    objective_terms.append(var * (-preference.weight_early_class_penalty))

        # Day penalty: subtract weight_day_penalty for each day used
        for day, d_var in day_vars.items():
            objective_terms.append(d_var * (-preference.weight_day_penalty))

        # Idle gap penalty between sections on the same day.
        #
        # BUG FIX: the old code penalized the gap between EVERY pair of
        # non-overlapping meetings on a shared day, not just meetings that
        # end up *consecutive* once a schedule is chosen. E.g. with 3 chosen
        # classes on the same day at 8:30-9:50, 10:00-11:20 and 11:30-12:50,
        # the true idle time (Schedule.idle_minutes(), also used by
        # Scorer.score()) is only the two 10-minute adjacent gaps = 20 min.
        # The old objective additionally penalized the 8:30-9:50 vs
        # 11:30-12:50 pair (a 100-minute "gap" that a student never actually
        # experiences, since the 10:00-11:20 class sits in between). That
        # mismatch between what CP-SAT searches for and what Scorer.score()
        # actually rewards meant CP-SAT could report a schedule as "optimal"
        # that a full brute-force search would score lower than another
        # option -- silently breaking the "guaranteed score equivalence"
        # this planner promises.
        #
        # Fix: only penalize a pair (m1 before m2, same day) if no OTHER
        # candidate meeting on that day would end up sitting between them
        # when chosen. That is exactly "m1 and m2 are consecutive in the
        # sorted list of chosen meetings for that day" -- the same
        # adjacency rule Schedule.idle_minutes() uses.
        scale_gap = max(1, int(preference.weight_idle_hour_penalty))

        # Group (section_key, meeting) by day so we can find what could sit
        # between any two meetings on that day.
        day_meeting_list: Dict[str, List[Tuple[str, "Meeting"]]] = {}
        for sec in candidate_sections:
            k = self._section_key(sec)
            for m in sec.meetings:
                d = m.day.strip().title()
                day_meeting_list.setdefault(d, []).append((k, m))

        gap_var_idx = 0
        for day, day_meetings in day_meeting_list.items():
            for k1, m1 in day_meetings:
                for k2, m2 in day_meetings:
                    if k1 == k2:
                        continue
                    s1 = sec_by_key[k1]
                    s2 = sec_by_key[k2]
                    if s1.course_code == s2.course_code:
                        continue  # mutually exclusive via AddExactlyOne already
                    if m1.start >= m2.start:
                        continue  # only consider each ordered pair once (m1 before m2)
                    if m1.overlaps(m2):
                        continue  # shouldn't happen given the clash constraints, but guard

                    gap = m2.start - m1.end
                    if gap <= 0:
                        continue

                    # Any other candidate meeting on this same day that would
                    # sit strictly between m1 and m2 if its section is chosen.
                    between_vars = [
                        sec_vars[k3]
                        for k3, m3 in day_meetings
                        if k3 not in (k1, k2) and m1.end <= m3.start and m3.end <= m2.start
                    ]

                    adjacent = model.NewBoolVar(f"adjacent_{gap_var_idx}")
                    gap_var_idx += 1

                    and_conditions = [sec_vars[k1], sec_vars[k2]] + [v.Not() for v in between_vars]
                    model.AddBoolAnd(and_conditions).OnlyEnforceIf(adjacent)
                    or_conditions = [sec_vars[k1].Not(), sec_vars[k2].Not()] + between_vars
                    model.AddBoolOr(or_conditions).OnlyEnforceIf(adjacent.Not())

                    gap_penalty = int(round((gap / 60.0) * scale_gap))
                    if gap_penalty > 0:
                        objective_terms.append(adjacent * (-gap_penalty))

        model.Maximize(sum(objective_terms))

        # 3. Iteratively solve for top_k plans using exclusion cuts
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 5.0
        # Optional deterministic search
        solver.parameters.num_search_workers = 1

        solutions: List[Tuple[Schedule, float]] = []

        for _ in range(top_k):
            status = solver.Solve(model)
            if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                break

            chosen_sections: List[Section] = []
            chosen_vars: List[cp_model.IntVar] = []

            for k, var in sec_vars.items():
                if solver.Value(var) == 1:
                    chosen_sections.append(sec_by_key[k])
                    chosen_vars.append(var)

            sched = Schedule(sections=chosen_sections)
            exact_score = Scorer.score(sched, preference)
            solutions.append((sched, exact_score))

            # Add exclusion constraint: cannot pick the exact same set of sections again
            # sum(1 - var for var in chosen_vars) >= 1  <=> sum(chosen_vars) <= len(chosen_vars) - 1
            model.Add(sum(chosen_vars) <= len(chosen_vars) - 1)

        # Sort solutions by exact score descending
        solutions.sort(key=lambda item: item[1], reverse=True)
        return solutions
