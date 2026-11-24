# Personal Training and Fatigue Analyzer

A team project for analyzing personal training and fatigue.

## Project Status

| Stage | Area | Status |
|-------|------|--------|
| 1 | Dataset (Python + pandas sample data) | Done |
| 2 | Input validation + cleaning pipeline | Done |
| 3 | SQLite database + CRUD layer | Done |
| 4 | Workout and exercise management | Done |
| 5 | Exploratory data analysis (EDA) | Done |
| 6 | Fitness metrics engine | Planned |
| 7 | Recovery analysis engine | Planned |
| 8 | Pattern detection (plateau, workload, fatigue, deload) | Planned |
| 9 | Reporting and visualization | Planned |
| 10 | Streamlit UI | Planned |
| 11 | Packaging and deployment | Planned |

## Running the CLI Demo

`main.py` is a pure-Python CLI entry point that demonstrates Stages 1–5:

```powershell
python main.py
```

It builds the sample dataset, runs validation and cleaning, exercises the
workout/exercise/program management layer against a demo database
(`database/demo_eval.db`), and prints EDA results. The real multi-user
database (`database/fitness.db`) is never modified by `main.py`.

## Running Tests

The project includes 105 pytest tests covering Stages 1–5:

```powershell
python -m pytest -v
```

Test files:
- `tests/test_validation.py` — Phase 2 input validation
- `tests/test_cleaning.py` — Phase 2 cleaning pipeline
- `tests/test_database.py` — Phase 3 SQLite schema + CRUD
- `tests/test_management.py` — Phase 4 workout/exercise/program management
- `tests/test_regression.py` — Regression tests for stabilization bugs
- `tests/test_eda.py` — Phase 5 exploratory data analysis

## Directory Layout (Stages 1–5)

```
database/          SQLite schema, connection, CRUD layer
src/data/          Sample dataset, validation, cleaning
src/management/    Workout, exercise, and program managers
src/analysis/      EDA module (Phase 5)
tests/             pytest suite (105 tests)
main.py            CLI demo entry point
```

## Not Yet Implemented (Stages 6–11)

The following are planned but not implemented on this branch:
- Metrics engine (`src/metrics/`)
- Recovery analysis (`src/analysis/recovery.py`)
- Detection (`src/detection/`)
- Reporting (`src/reporting/`)
- Streamlit UI (`streamlit_app/`)
