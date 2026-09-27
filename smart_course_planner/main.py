"""
Smart Course Planner Entry Point.
Starts the PySide6 Desktop GUI application or executes CLI analysis when headless.
"""

import sys
import os
import argparse

# Ensure root folder is on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.loader import RoutineLoader
from core.models import Schedule
from core.planner.preference import Preference
from core.planner.brute_force import BruteForcePlanner
from core.planner.cpsat_planner import CpSatPlanner
from core.planner.explain import Explainer


def run_cli_demo():
    """Headless CLI demo showing RoutineLoader, BruteForce, and CP-SAT solvers."""
    print("=" * 60)
    print(" Smart Course Planner - Headless CLI Execution")
    print("=" * 60)

    routine_path = os.path.join(BASE_DIR, "data", "routine_sample.xlsx")
    loader = RoutineLoader()
    courses, report = loader.load(routine_path)

    print(f"\n[Loader Report] {report.summary()}")
    print(f"Loaded Courses: {[c.code for c in courses]}")

    wanted = ["CSE 1115", "CSE 2215", "MATH 2103"]
    pref = Preference(
        wanted_courses=wanted,
        liked_faculty=["Donald Knuth", "Grace Hopper"],
        priority="fewer_days",
    )
    print(f"\n[Preferences] Wanted: {wanted} | Priority: {pref.priority}")

    print("\n--- Running Brute Force Optimizer ---")
    bf_planner = BruteForcePlanner(courses)
    bf_plans = bf_planner.plan(pref, top_k=5)
    print(f"Brute Force generated {len(bf_plans)} plans.")
    if bf_plans:
        best_sched, best_score = bf_plans[0]
        print(f"Best Brute-Force Score: {best_score}")
        print(f"Sections: {[f'{s.course_code} {s.section_name}' for s in best_sched.sections]}")
        print(f"Days used: {best_sched.days_used()} | Idle minutes: {best_sched.idle_minutes()}")

    print("\n--- Running OR-Tools (CP-SAT) Optimizer ---")
    cp_planner = CpSatPlanner(courses)
    cp_plans = cp_planner.plan(pref, top_k=5)
    print(f"CP-SAT generated {len(cp_plans)} plans.")
    if cp_plans:
        cp_best_sched, cp_best_score = cp_plans[0]
        print(f"Best CP-SAT Score: {cp_best_score}")
        print(f"Sections: {[f'{s.course_code} {s.section_name}' for s in cp_best_sched.sections]}")
        print(f"Days used: {cp_best_sched.days_used()} | Idle minutes: {cp_best_sched.idle_minutes()}")

    print("\n[Verification] Brute Force & CP-SAT best scores comparison:")
    if bf_plans and cp_plans:
        match = abs(bf_plans[0][1] - cp_plans[0][1]) < 0.01
        print(f"Scores Match: {match} (BF: {bf_plans[0][1]} vs CP-SAT: {cp_plans[0][1]})")

    print("\n--- Testing Explainer (Infeasible Schedule) ---")
    impossible_pref = Preference(
        wanted_courses=["DS 1116"],
        no_early_class_hard=True,  # All DS 1116 are at 08:30 AM
    )
    explainer = Explainer(courses)
    reasons = explainer.explain_failure(impossible_pref)
    for r in reasons:
        print(f"Explanation: {r}")

    print("\n" + "=" * 60)
    print(" CLI Demo completed successfully!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Smart Course Planner")
    parser.add_argument("--cli", action="store_true", help="Run in headless CLI mode")
    args, unknown = parser.parse_known_args()

    # Check for graphical display server
    if sys.platform.startswith("linux"):
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    else:
        has_display = True

    if args.cli or not has_display:
        if not has_display and not args.cli:
            print("[INFO] No X11/Wayland display server detected in environment.")
            print("[INFO] Running in CLI mode. Run with --cli explicitly or in a desktop environment for PySide6 GUI.")
        run_cli_demo()
        return 0

    # Desktop PySide6 Execution
    from PySide6.QtWidgets import QApplication
    from gui.main_window import MainWindow

    app = QApplication(sys.argv)

    # Load stylesheet
    style_path = os.path.join(BASE_DIR, "gui", "style.qss")
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
