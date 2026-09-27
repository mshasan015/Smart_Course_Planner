# Smart Course Planner

An intelligent academic course registration planner and schedule optimizer built in Python with **PySide6**, **Google OR-Tools (CP-SAT)**, **pandas**, and **openpyxl**.

---

## 🌟 Key Features

1. **Robust Excel Routine Ingestion (`RoutineLoader`)**:
   - Column-name based discovery (never hardcoded column positions).
   - Dynamic regex matching for multi-day schedules (`Day 1`, `Day 2`, `Day 3`, `Room 1`, etc.).
   - Clean handling of edge cases: trims trailing section whitespace (`"BA "`), flags `(Dropped)` sections, parses multi-instructor strings (up to 3 faculty), and records malformed rows into an `ImportReport` without crashing.

2. **Accurate Conflict & Clash Detection (`ConflictChecker`)**:
   - Stores all time intervals as minutes from midnight (`08:30 AM` = 510, `12:30 PM` = 750).
   - Strict clash rule: `same day and startA < endB and startB < endA`.
   - Classes touching back-to-back (`08:30-09:50` and `09:50-11:10`) **do not clash**.
   - Live greying-out and tooltip conflict indicators in the course browser.

3. **Secure Authentication (`AuthService`)**:
   - Salted password hashing via `hashlib.pbkdf2_hmac` (SHA-256 with 100,000 rounds and cryptographic salt).
   - Stored in `data/users.json` with zero plaintext passwords.

4. **Dual Optimization Engines**:
   - **BruteForcePlanner**: Exhaustive combinatorial search with hard-constraint pruning and multi-criteria scoring.
   - **CpSatPlanner (OR-Tools CP-SAT)**: High-performance boolean constraint satisfaction formulation yielding the top 5 optimal schedules.
   - Guaranteed score equivalence between CP-SAT and Brute Force.

5. **Smart Extras**:
   - **Infeasibility Explainer (`Explainer`)**: Identifies bottleneck courses when no schedule can be formed (e.g. isolating hard constraints like *"No class before 10 AM eliminates all sections of DS 1116"*).
   - **Backup Section Recommendations**: Automatically evaluates alternate sections for each course in your plan to ensure registration day readiness.

6. **Interactive Desktop GUI & Weekly Timetable Visualizer**:
   - Class-based **PySide6** architecture cleanly decoupled from `core/`.
   - Live color-coded weekly grid with mouse hover preview blocks and idle gap indicators.
   - Urgent red banner for deadlines within 3 days (reads `data/events.json`).
   - JSON plan persistence: save and reload your schedule anytime.

---

## 📂 Project Architecture

```
smart_course_planner/
├── main.py                  # Desktop application & CLI runner
├── config.py                # Column names, weights, colors, time constants
├── requirements.txt         # Dependencies
├── README.md                # Documentation & guide
├── data/
│   ├── routine_sample.xlsx  # Standard university class routine
│   ├── routine_changed.xlsx # Alternate 3-day format for format-change testing
│   ├── users.json           # Salted password hash user database
│   └── events.json          # Academic deadlines & countdowns
├── core/                    # Pure Python business logic (NEVER imports PySide6)
│   ├── models.py            # Meeting, Section, Course, Schedule dataclasses
│   ├── time_utils.py        # Odd format time parsing ("08:30:AM" -> 510)
│   ├── loader.py            # RoutineLoader, ImportReport, BadRow
│   ├── conflict.py          # ConflictChecker & pairwise clash index
│   ├── filters.py           # SectionFilter (faculty, time, seats, clashes)
│   ├── auth.py              # AuthService (pbkdf2_hmac salted authentication)
│   ├── storage.py           # PlanStorage JSON serializer/deserializer
│   └── planner/
│       ├── preference.py    # Preference dataclass & weight adjuster
│       ├── scorer.py        # Objective multi-criteria schedule scoring
│       ├── brute_force.py   # BruteForcePlanner (Top 5 plans)
│       ├── cpsat_planner.py # CpSatPlanner using Google OR-Tools CP-SAT
│       └── explain.py       # Failure Explainer & Backup Section Finder
├── gui/                     # PySide6 Desktop GUI components
│   ├── main_window.py       # QStackedWidget & top navigation bar
│   ├── login_page.py        # Student login & registration
│   ├── dashboard_page.py    # Welcome, credit limits & upcoming deadlines
│   ├── course_browser.py    # Filter panel, section table & timetable sync
│   ├── section_table_model.py # QAbstractTableModel with clash greying
│   ├── timetable_widget.py  # Weekly grid (days × time slots) with hover preview
│   ├── planner_page.py      # Preference form, CP-SAT/Brute-Force solvers & backups
│   └── style.qss            # Modern dark slate stylesheet
└── tests/                   # Pytest test suite
    ├── test_loader.py       # Tests file reading, bad rows & column shifts
    ├── test_conflict.py     # Tests time parsing & touching boundary conditions
    └── test_planner.py      # Tests solver score parity & explainer logic
```

---

## 🚀 Getting Started

### 1. Installation

Ensure Python 3.10+ is installed, then install the required dependencies:

```bash
pip install -r requirements.txt
```

### 2. Running the Desktop Application

```bash
python main.py
```

*Note: If running in a headless or server container without an active X11/Wayland display server, `main.py` automatically runs in CLI demonstration mode or you can explicitly pass `--cli`.*

```bash
python main.py --cli
```

### 3. Running the Test Suite

```bash
pytest tests/
```

All 11 unit and integration tests will verify the loader, conflict checker, and optimization engines.

### 4. Compiling a Standalone Executable (PyInstaller)

To package the application into a standalone `.exe` or Linux binary:

```bash
pip install pyinstaller
pyinstaller --name "SmartCoursePlanner" --windowed --onefile main.py
```

---

## 🏆 10-Day Build Guide Verification

| Day | Milestone | Implementation Status |
|:---|:---|:---|
| **Day 1** | Models & Time Parser | `@dataclass` models in `core/models.py`. Odd format `"08:30:AM"` -> 510, `" - "` -> None in `core/time_utils.py`. |
| **Day 2** | Dynamic Routine Loader | `core/loader.py` detects `Day 1..N` via regex; cleans `"BA "`, `(Dropped)`, and multi-faculty. |
| **Day 3** | Salted Auth & Login | `core/auth.py` with `hashlib.pbkdf2_hmac` salted hashing in `data/users.json`. |
| **Day 4** | Dashboard & Deadlines | `gui/dashboard_page.py` reads `data/events.json`, computes countdown, triggers red banner if $\le 3$ days. |
| **Day 5** | Browser & Clash Filter | `gui/course_browser.py` with `ConflictChecker`; greys out conflicts, recalculates credits. |
| **Day 6** | Timetable & JSON Save/Load | `gui/timetable_widget.py` weekly grid, hover preview blocks, and `PlanStorage` JSON export. |
| **Day 7** | Preferences & Brute Force | `core/planner/brute_force.py` finds top 5 combinations using weights from `config.py`. |
| **Day 8** | OR-Tools CP-SAT Solver | `core/planner/cpsat_planner.py` solves boolean model; exact score equality verified with Brute Force. |
| **Day 9** | Explainer & Backups | `core/planner/explain.py` isolates bottleneck courses on failure and suggests safe section alternates. |
| **Day 10** | Pytest Suite & Polish | Full 11-test suite in `tests/`, consistent `style.qss`, and clean modular structure. |
