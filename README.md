# Personal Training and Fatigue Analyzer

A local fitness analytics and training intelligence system where users log
workouts and recovery data through Streamlit. Python performs all calculations,
statistics, and rule-based detection. SQLite stores every record locally.

**No machine learning, no CSV uploads, no cloud services, no AI recommendations.**

---

## Features

| Category | Capabilities |
|---|---|
| **User management** | Create and manage user profiles, store basic fitness info, per-user historical records |
| **Workout management** | Log sessions with sets, reps, weight, RPE; workout history; personal records |
| **Program management** | Custom training programs, PPL and Upper/Lower splits, exercise-to-day assignment |
| **Exercise library** | Categorize by muscle group and equipment; add custom exercises |
| **Recovery management** | Log sleep, body weight, soreness, energy — including rest days |
| **Data validation** | Reject invalid inputs (negative reps, RPE > 10, future dates, duplicates, etc.) |
| **Fitness metrics** | Training volume, estimated 1RM (Epley), strength progression, muscle-group workload, RPE, recovery metrics |
| **Detection** | Strength plateaus, excessive workload, accumulated fatigue, potential deload signals |
| **Reporting** | Daily, weekly, monthly summaries; detection alerts; textual explanations |
| **Visualization** | Strength progression, weekly volume, sleep, muscle-group workload, body weight, RPE charts |
| **Interface** | Streamlit app with 7 pages: Home, Train, Programs, Exercises, History, Recovery, Analysis |

---

## Tech Stack

| Technology | Purpose |
|---|---|
| Python 3.13 | Core programming and logic |
| NumPy | Mathematical calculations |
| Pandas | Data processing and analysis |
| SQLite / sqlite3 | Persistent local database |
| Matplotlib | Data visualization |
| Streamlit | User interface (presentation/input layer only) |
| SciPy | Statistical methods (correlation) |
| Pytest | Testing (181 tests) |

---

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | Python fundamentals and dataset understanding | done |
| 2 | Data validation and preprocessing | done |
| 3 | SQLite database design and integration | done |
| 4 | Workout and exercise management | done |
| 5 | Exploratory data analysis | done |
| 6 | Fitness metrics engine | done |
| 7 | Recovery analysis engine | done |
| 8 | Plateau / workload / fatigue / deload detection | done |
| 9 | Reporting and visualisation | done |
| 10 | Streamlit interface | done |
| 11 | Testing, debugging and documentation | done |

---

## Setup

```bash
# Clone the repository
git clone https://github.com/kamran-bisati/Personal_Training_And_Fatigue_Analyzer.git
cd Personal_Training_And_Fatigue_Analyzer

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # on macOS/Linux
# or: .venv\Scripts\activate  # on Windows

# Install dependencies
pip install -r requirements.txt
```

---

## How to Run

### Backend tests

```bash
.venv/bin/python -m pytest -q
```

### Streamlit application

```bash
.venv/bin/streamlit run streamlit_app/app.py
```

Then open http://localhost:8501 in your browser.

### Pages

| Page | Purpose |
|---|---|
| **Home** | Daily summary dashboard — headline metrics, recent sessions, recent recovery |
| **Train** | Log workouts — select date, duration, exercises, sets, reps, weight, RPE |
| **Programs** | Create custom programs or use PPL / Upper/Lower templates |
| **Exercises** | Browse and manage the exercise library |
| **History** | View past sessions and personal records per exercise |
| **Recovery** | Log daily sleep, body weight, soreness, energy |
| **Analysis** | Charts, detection alerts (plateau, workload, fatigue, deload), reports |

---

## Project Layout

```
.
├── .streamlit/
│   └── config.toml          # Streamlit theme and server config
├── database/
│   ├── __init__.py
│   ├── db_setup.py          # Connection, schema DDL, exercise seeding
│   └── repository.py        # CRUD layer (8 tables)
├── src/
│   ├── data/
│   │   ├── sample_dataset.py   # Phase 1: sample fitness dataset
│   │   ├── validation.py       # Phase 2: validation rules
│   │   └── data_cleaning.py    # Phase 2: cleaning pipeline
│   ├── management/
│   │   ├── exercise_manager.py   # Phase 4: exercise library operations
│   │   ├── workout_manager.py    # Phase 4: sessions, sets, history, PRs
│   │   └── program_manager.py    # Phase 4: programs, PPL/Upper-Lower templates
│   ├── analysis/
│   │   ├── eda.py                # Phase 5: exploratory data analysis
│   │   └── recovery.py           # Phase 7: recovery analysis engine
│   ├── metrics/
│   │   ├── training_volume.py    # Phase 6
│   │   ├── estimated_1rm.py      # Phase 6 (Epley formula)
│   │   ├── progression.py        # Phase 6
│   │   ├── muscle_workload.py    # Phase 6
│   │   ├── recovery_metrics.py   # Phase 6
│   │   └── average_rpe.py        # Phase 6
│   ├── config/
│   │   └── thresholds.py         # Phase 8: detection thresholds
│   ├── detection/
│   │   ├── plateau_detection.py  # Phase 8
│   │   ├── workload_detection.py # Phase 8
│   │   ├── fatigue_detection.py  # Phase 8
│   │   └── deload_detection.py   # Phase 8
│   └── reporting/
│       ├── report_generator.py   # Phase 9: daily/weekly/monthly reports
│       └── visualization.py      # Phase 9: matplotlib charts
├── streamlit_app/
│   ├── __init__.py
│   ├── app.py                    # Phase 10: entry point + navigation
│   ├── utils.py                  # Phase 10: DB → DataFrame helpers
│   └── pages/
│       ├── home.py               # Dashboard
│       ├── train.py              # Workout input
│       ├── programs.py           # Program management
│       ├── exercises.py          # Exercise library
│       ├── history.py            # Session history + PRs
│       ├── recovery.py           # Recovery input
│       └── analysis.py           # Charts, detection, reports
├── tests/
│   ├── test_validation.py
│   ├── test_cleaning.py
│   ├── test_database.py
│   ├── test_management.py
│   ├── test_detection.py
│   ├── test_eda.py
│   ├── test_metrics.py
│   ├── test_recovery.py
│   ├── test_reporting.py
│   └── test_streamlit.py         # Phase 11: Streamlit UI tests
├── main.py                     # Backend inspection entry point (Phases 1-3)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Database Schema (Phase 3)

8 tables with foreign keys and cascade deletes:

- **users** — profile basics (name, age, height, weight, goal)
- **exercises** — library (name, primary/secondary muscle group, equipment, custom flag)
- **workout_sessions** — one per user per date (date, duration, notes)
- **workout_sets** — one per set (session, exercise, set number, reps, weight, RPE)
- **recovery_logs** — one per user per date (sleep, body weight, soreness, energy)
- **training_programs** — user programs (name, split type, active flag)
- **program_days** — ordered days within a program
- **program_exercises** — exercises assigned to days (target sets, reps, weight)

Constraints: `PRAGMA foreign_keys = ON`, `ON DELETE CASCADE`,
`UNIQUE(user_id, session_date)`, `UNIQUE(user_id, log_date)`,
`CHECK` constraints on ranges (reps > 0, RPE 1–10, weight ≥ 0, etc.)

---

## Detection Thresholds (Phase 8)

All thresholds live in `src/config/thresholds.py` and are engineering rules —
not medically validated:

| Detection | Threshold |
|---|---|
| Plateau | < 2% e1RM improvement over 4–6 weeks, ≥ 4 sessions |
| Workload monitoring | > 10% week-over-week volume increase |
| Workload significant spike | > 20% week-over-week volume increase |
| Fatigue (RPE) | Average RPE ≥ 8.5 |
| Fatigue (sleep) | Average sleep < 6 hours |
| Fatigue (soreness) | Average soreness ≥ 7/10 |
| Fatigue (energy) | Average energy ≤ 4/10 |
| Fatigue (performance) | Declining e1RM trend |
| Fatigue elevated | ≥ 3 of 5 indicators flagged |
| Deload | Elevated fatigue + workload warning/spike over ≥ 2 weeks |

---

## Sample Dataset

`src/data/sample_dataset.py` generates 5 weeks (2026-10-05 to 2026-11-08)
of deterministic data. It intentionally includes:

- A **~34% volume spike** in weeks 4–5 (workload detection signal)
- A **bench press plateau** after week 3 (e1RM stuck at 99.2 kg)
- **Declining recovery**: sleep 7.5 → 6.4 h, soreness 3 → 6, energy 8 → 6
- **Dirty rows**: duplicate, negative reps, RPE 15, missing weight, missing sleep, energy 11

Call `load_dataset(include_anomalies=False)` for clean data.

---

## Disclaimer

This system provides **rule-based decision support only**. It is not a medical
diagnosis, not a substitute for professional medical advice, and not a
replacement for a qualified coach or trainer. Always consult a healthcare
professional before making significant changes to your training or recovery.

---

## Testing

```bash
# All tests (181)
.venv/bin/python -m pytest -q

# Streamlit UI tests only
.venv/bin/python -m pytest tests/test_streamlit.py -v

# Specific phase tests
.venv/bin/python -m pytest tests/test_validation.py tests/test_cleaning.py tests/test_database.py tests/test_management.py -v
```
