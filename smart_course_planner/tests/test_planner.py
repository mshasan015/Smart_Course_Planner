"""
Tests for Brute Force planner, OR-Tools CP-SAT planner, Explainer, and Scorer.
"""

import os
import pytest
from core.loader import RoutineLoader
from core.planner.preference import Preference
from core.planner.brute_force import BruteForcePlanner
from core.planner.cpsat_planner import CpSatPlanner
from core.planner.explain import Explainer


@pytest.fixture
def sample_courses():
    p = os.path.join(os.path.dirname(__file__), "..", "data", "routine_sample.xlsx")
    loader = RoutineLoader()
    courses, _ = loader.load(os.path.abspath(p))
    return courses


def test_brute_force_and_cpsat_same_best_score(sample_courses):
    """
    Day 8 & Day 10 Done When:
    OR-Tools best score equals brute-force best score.
    """
    pref = Preference(
        wanted_courses=["CSE 1115", "CSE 2215", "MATH 2103"],
        liked_faculty=["Donald Knuth", "Grace Hopper"],
        priority="fewer_days",
    )

    bf_planner = BruteForcePlanner(sample_courses)
    bf_plans = bf_planner.plan(pref, top_k=5)

    cp_planner = CpSatPlanner(sample_courses)
    cp_plans = cp_planner.plan(pref, top_k=5)

    assert len(bf_plans) > 0, "Brute force should find valid plans"
    assert len(cp_plans) > 0, "CP-SAT should find valid plans"

    bf_best_score = bf_plans[0][1]
    cp_best_score = cp_plans[0][1]

    # Scores must be equal
    assert abs(bf_best_score - cp_best_score) < 0.01, (
        f"Brute force best score ({bf_best_score}) must equal CP-SAT best score ({cp_best_score})"
    )


def test_explainer_on_infeasible_hard_rule(sample_courses):
    """
    Day 9 requirement:
    'No class before 10 AM removes all sections of DS 1116.'
    """
    pref = Preference(
        wanted_courses=["DS 1116"],
        no_early_class_hard=True,  # DS 1116 only has 08:30 AM sections in sample
    )

    explainer = Explainer(sample_courses)
    reasons = explainer.explain_failure(pref)

    assert len(reasons) > 0
    # Must explain that the 10:00 AM rule eliminates all sections of DS 1116
    assert any("10:00 AM" in r and "DS 1116" in r for r in reasons)


def test_backup_sections(sample_courses):
    """
    Day 9 requirement:
    Backup section: for each chosen section, find the best other section that fits the rest of the plan.
    """
    pref = Preference(wanted_courses=["CSE 1115", "CSE 2215"])
    planner = BruteForcePlanner(sample_courses)
    plans = planner.plan(pref, top_k=1)
    assert len(plans) > 0

    best_sched = plans[0][0]
    explainer = Explainer(sample_courses)
    backups = explainer.find_backup_sections(best_sched, pref)

    assert "CSE 1115" in backups
    assert "CSE 2215" in backups
