# Personal Training and Fatigue Analyzer

A local fitness analytics and training intelligence system.

Users log workouts and recovery data through Streamlit. Python performs all
calculations, statistics and rule-based detection. SQLite stores every record
locally. No machine learning, no CSV uploads, no cloud services.

**Stack:** Python, NumPy, Pandas, SQLite, Matplotlib, Streamlit, SciPy, Pytest

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
| 11 | Testing, debugging and documentation | next |

---

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run the current build

```bash
# Backend tests
python -m pytest -q

# Streamlit app
.venv/bin/streamlit run streamlit_app/app.py
```

This builds the sample dataset in memory, prints an inspection report,
runs the Phase 2 validation and cleaning pipeline on the dirty sample, then
builds `database/fitness.db`, seeds it, inserts the sample data and prints
row counts plus sample queries (workout history, personal records).
Then launch the Streamlit interface at http://localhost:8501.

## Run tests

```bash
.venv/bin/python -m pytest -q
```

---

## Validation rules (Phase 2)

Severity is either `error` (record rejected) or `warning` (record kept, user
informed). Outliers are always warnings and are never auto-deleted.

* required columns present; numeric fields parse as numbers
* ranges: sets 1-20, reps 1-100, weight 0-500 kg, RPE 1-10,
  sleep 0-24 h, soreness 1-10, energy 1-10, body weight 30-300 kg
* RPE must be a multiple of 0.5 (warning)
* sets and reps must be whole numbers (warning)
* dates parse, are not in the future, and are not before 2020-01-01
* exact duplicate rows and same-date/same-exercise records (warnings)
* duplicate recovery dates (warning)
* barbell exercise logged at 0 kg (warning)
* sets x reps > 200 in one record (warning)
* body weight changing more than 3 kg between entries (warning)
* sleep below 3 h or above 12 h (warning)
* IQR outliers on volume (per exercise) and sleep

Cleaning strategies: `keep` (leave missing values), `drop` (remove rows with
missing required fields), `median` (fill missing numeric values with the column
median). The pipeline returns cleaned data, rejected rows, and a log.

---

## Project layout

```
.
├── database/
│   ├── __init__.py
│   ├── db_setup.py          # Phase 3: connection, schema DDL, seeding
│   └── repository.py        # Phase 3: CRUD layer
├── src/
│   ├── data/
│   │   ├── sample_dataset.py   # Phase 1 sample data builder
│   │   ├── validation.py       # Phase 2 validation rules
│   │   └── data_cleaning.py    # Phase 2 cleaning pipeline
│   ├── management/
│   │   ├── __init__.py
│   │   ├── exercise_manager.py   # Phase 4: exercise library operations
│   │   ├── workout_manager.py    # Phase 4: sessions, sets, history, PRs
│   │   └── program_manager.py    # Phase 4: programs, PPL/Upper-Lower templates
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── eda.py                # Phase 5: exploratory data analysis
│   │   └── recovery.py           # Phase 7: recovery analysis engine
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── training_volume.py    # Phase 6
│   │   ├── estimated_1rm.py      # Phase 6
│   │   ├── progression.py        # Phase 6
│   │   ├── muscle_workload.py    # Phase 6
│   │   ├── recovery_metrics.py   # Phase 6
│   │   └── average_rpe.py        # Phase 6
│   ├── config/
│   │   ├── __init__.py
│   │   └── thresholds.py         # Phase 8 detection thresholds
│   ├── detection/
│   │   ├── __init__.py
│   │   ├── plateau_detection.py  # Phase 8
│   │   ├── workload_detection.py # Phase 8
│   │   ├── fatigue_detection.py  # Phase 8
│   │   └── deload_detection.py   # Phase 8
│   └── reporting/
│       ├── __init__.py
│       ├── report_generator.py   # Phase 9
│       └── visualization.py      # Phase 9
├── streamlit_app/
│   ├── __init__.py
│   ├── app.py                    # Phase 10: main entry + navigation
│   ├── utils.py                  # Phase 10: DB → DataFrame helpers
│   └── pages/
│       ├── __init__.py
│       ├── home.py               # Dashboard / daily summary
│       ├── train.py              # Daily workout input
│       ├── programs.py           # Program management
│       ├── exercises.py          # Exercise library
│       ├── history.py            # Previous sessions & PRs
│       ├── recovery.py           # Daily recovery input
│       └── analysis.py           # Charts, metrics, detection, reports
├── tests/
│   ├── test_validation.py
│   ├── test_cleaning.py
│   ├── test_database.py        # Phase 3 database tests
│   ├── test_management.py      # Phase 4 management tests
│   ├── test_detection.py       # Phase 8 detection tests
│   ├── test_eda.py             # Phase 5 EDA tests
│   ├── test_metrics.py         # Phase 6 metrics tests
│   ├── test_recovery.py        # Phase 7 recovery tests
│   └── test_reporting.py       # Phase 9 reporting tests
├── main.py                     # backend inspection entry point
├── requirements.txt
└── README.md
```

Folders for `analysis/`, `metrics/`, `detection/`, `management/`, `reporting/`,
and `streamlit_app/` are added in the phase that needs them.

## Database schema (Phase 3)

8 tables: `users`, `exercises`, `workout_sessions`, `workout_sets`,
`recovery_logs`, `training_programs`, `program_days`, `program_exercises`.

Key rules enforced by the schema:

* `PRAGMA foreign_keys = ON` on every connection
* `ON DELETE CASCADE`: user → sessions/recovery/programs; session → sets
* `UNIQUE(user_id, session_date)` and `UNIQUE(user_id, log_date)` block duplicate days
* `CHECK` constraints mirror Phase 2 ranges (reps > 0, RPE 1–10, weight ≥ 0)
* Dates stored as ISO text (`YYYY-MM-DD`)
* `database/fitness.db` is gitignored; tests use `:memory:`

---

## Sample dataset

`src/data/sample_dataset.py` generates five weeks (2026-10-05 to 2026-11-08)
of deterministic data across two tables:

* `workout_sets` - one row per exercise performed in a session
  (`date`, `week`, `exercise`, `muscle_group`, `equipment`, `sets`, `reps`,
  `weight_kg`, `rpe`, `session_duration_min`)
* `recovery_logs` - one row per calendar day, rest days included
  (`date`, `week`, `day_type`, `sleep_hours`, `body_weight_kg`, `soreness`,
  `energy`)

Intentional characteristics:

* training load and RPE rise week over week, sleep and energy fall, soreness rises
* weeks 4-5 add one extra set to every exercise, a ~34% jump in weekly volume
  (the excessive-workload signal for Phase 8)
* bench press stops progressing after week 3 (a plateau for Phase 8 to find)
* a handful of dirty rows (duplicate, negative reps, RPE 15, missing weight,
  missing sleep, energy 11) for Phase 2 validation to catch
* `session_duration_min` repeats on every row of a session - never sum it
* bodyweight movements (pull-ups) are stored as `weight_kg = 0.0`

Call `load_dataset(include_anomalies=False)` for clean data.

**Rule-based decision support only - not a medical diagnosis.**
