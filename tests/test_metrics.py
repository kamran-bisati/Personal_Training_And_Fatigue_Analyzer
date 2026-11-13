"""Tests for the Phase 6 Fitness Metrics Engine."""

from __future__ import annotations

import pandas as pd
import pytest

from src.metrics.average_rpe import average_rpe, bulk_average_rpe
from src.metrics.estimated_1rm import estimated_1rm, bulk_estimated_1rm
from src.metrics.muscle_workload import (
    aggregate_muscle_workload,
    bulk_muscle_workload,
    muscle_workload,
)
from src.metrics.progression import (
    bulk_strength_progression,
    strength_progression,
)
from src.metrics.recovery_metrics import (
    bulk_recovery_summary,
    recovery_summary,
)
from src.metrics.training_volume import (
    bulk_training_volume,
    total_volume,
    training_volume,
)


# ------------------------------------------------------------------ training volume


def test_training_volume_basic():
    assert training_volume(3, 10, 50.0) == 1500.0


def test_training_volume_zero_weight():
    # Bodyweight movements (e.g. pull-ups) use 0 kg
    assert training_volume(3, 10, 0.0) == 0.0


def test_training_volume_invalid_sets():
    with pytest.raises(ValueError, match="sets must be positive"):
        training_volume(0, 10, 50.0)
    with pytest.raises(ValueError, match="sets must be positive"):
        training_volume(-1, 10, 50.0)


def test_training_volume_invalid_reps():
    with pytest.raises(ValueError, match="reps must be positive"):
        training_volume(3, 0, 50.0)


def test_training_volume_negative_weight():
    with pytest.raises(ValueError, match="weight_kg must be non-negative"):
        training_volume(3, 10, -5.0)


def test_training_volume_type_errors():
    with pytest.raises(TypeError):
        training_volume("3", 10, 50.0)
    with pytest.raises(TypeError):
        training_volume(3, "10", 50.0)
    with pytest.raises(TypeError):
        training_volume(3, 10, "50")


def test_total_volume_sums():
    assert total_volume([100.0, 200.0, 300.0]) == 600.0


def test_total_volume_empty():
    assert total_volume([]) == 0.0


def test_total_volume_negative():
    with pytest.raises(ValueError, match="volume must be non-negative"):
        total_volume([100.0, -50.0])


def test_bulk_training_volume_adds_column():
    df = pd.DataFrame(
        {
            "sets": [3, 4, 3],
            "reps": [10, 8, 12],
            "weight_kg": [50.0, 60.0, 30.0],
        }
    )
    result = bulk_training_volume(df)
    assert "volume_kg" in result.columns
    assert result["volume_kg"].tolist() == [1500.0, 1920.0, 1080.0]


def test_bulk_training_volume_missing_column():
    df = pd.DataFrame({"sets": [3], "reps": [10]})
    with pytest.raises(ValueError, match="missing required column"):
        bulk_training_volume(df)


def test_bulk_training_volume_non_numeric():
    df = pd.DataFrame(
        {"sets": [3], "reps": ["10"], "weight_kg": [50.0]}
    )
    with pytest.raises(TypeError, match="must be numeric"):
        bulk_training_volume(df)


# ------------------------------------------------------------------ estimated 1RM


def test_estimated_1rm_epley():
    # Epley: 100 kg x 5 reps = 100 * (1 + 5/30) = 116.67
    result = estimated_1rm(100.0, 5)
    assert abs(result - 116.66666666666667) < 0.01


def test_estimated_1rm_one_rep():
    # Epley: 100 kg x 1 rep = 100 * (1 + 1/30) = 103.33
    result = estimated_1rm(100.0, 1)
    assert abs(result - 103.33333333333334) < 0.01


def test_estimated_1rm_zero_weight():
    assert estimated_1rm(0.0, 10) == 0.0


def test_estimated_1rm_invalid():
    with pytest.raises(ValueError, match="weight_kg must be non-negative"):
        estimated_1rm(-10.0, 5)
    with pytest.raises(ValueError, match="reps must be positive"):
        estimated_1rm(100.0, 0)
    with pytest.raises(TypeError):
        estimated_1rm("100", 5)


def test_bulk_estimated_1rm_adds_column():
    df = pd.DataFrame({"weight_kg": [100.0, 50.0], "reps": [5, 10]})
    result = bulk_estimated_1rm(df)
    assert "e1rm_kg" in result.columns
    assert abs(result["e1rm_kg"].iloc[0] - 116.67) < 0.01
    assert abs(result["e1rm_kg"].iloc[1] - 66.67) < 0.01


# ------------------------------------------------------------------ average RPE


def test_average_rpe_basic():
    assert average_rpe([7.0, 8.0, 9.0]) == 8.0


def test_average_rpe_empty():
    assert average_rpe([]) == 0.0


def test_average_rpe_negative():
    with pytest.raises(ValueError, match="non-negative"):
        average_rpe([7.0, -1.0])


def test_bulk_average_rpe_overall():
    df = pd.DataFrame({"rpe": [7.0, 8.0, 9.0, 6.0]})
    result = bulk_average_rpe(df)
    assert len(result) == 1
    assert abs(result["avg_rpe"].iloc[0] - 7.5) < 0.01


def test_bulk_average_rpe_grouped():
    df = pd.DataFrame(
        {
            "week": [1, 1, 2, 2],
            "rpe": [7.0, 8.0, 8.5, 9.0],
        }
    )
    result = bulk_average_rpe(df, group_col="week")
    assert len(result) == 2
    assert abs(result.loc[result["week"] == 1, "avg_rpe"].iloc[0] - 7.5) < 0.01
    assert abs(result.loc[result["week"] == 2, "avg_rpe"].iloc[0] - 8.75) < 0.01


def test_bulk_average_rpe_missing_column():
    df = pd.DataFrame({"sets": [3]})
    with pytest.raises(ValueError, match="missing required column"):
        bulk_average_rpe(df)


# ------------------------------------------------------------------ strength progression


def test_strength_progression_improvement():
    # 100 -> 110 kg is +10%
    result = strength_progression(100.0, 110.0)
    assert abs(result - 10.0) < 0.01


def test_strength_progression_decline():
    # 100 -> 90 kg is -10%
    result = strength_progression(100.0, 90.0)
    assert abs(result - (-10.0)) < 0.01


def test_strength_progression_no_change():
    assert strength_progression(100.0, 100.0) == 0.0


def test_strength_progression_invalid():
    with pytest.raises(ValueError, match="previous_e1rm_kg must be positive"):
        strength_progression(0.0, 100.0)
    with pytest.raises(ValueError, match="current_e1rm_kg must be non-negative"):
        strength_progression(100.0, -5.0)
    with pytest.raises(TypeError):
        strength_progression("100", 110.0)


def test_bulk_strength_progression_adds_column():
    df = pd.DataFrame(
        {
            "date": ["2026-01-01", "2026-01-08", "2026-01-15"],
            "e1rm_kg": [100.0, 110.0, 105.0],
        }
    )
    result = bulk_strength_progression(df)
    assert "progression_pct" in result.columns
    assert pd.isna(result["progression_pct"].iloc[0])  # first row has no previous
    assert abs(result["progression_pct"].iloc[1] - 10.0) < 0.01
    assert abs(result["progression_pct"].iloc[2] - (-4.55)) < 0.01


# ------------------------------------------------------------------ muscle workload


def test_muscle_workload_tuple():
    assert muscle_workload(1500.0, "Chest") == ("Chest", 1500.0)


def test_muscle_workload_invalid():
    with pytest.raises(ValueError, match="non-negative"):
        muscle_workload(-100.0, "Chest")
    with pytest.raises(TypeError):
        muscle_workload("1500", "Chest")


def test_aggregate_muscle_workload():
    contributions = [("Chest", 1500.0), ("Back", 2000.0), ("Chest", 500.0)]
    result = aggregate_muscle_workload(contributions)
    assert result == {"Chest": 2000.0, "Back": 2000.0}


def test_aggregate_muscle_workload_empty():
    assert aggregate_muscle_workload([]) == {}


def test_bulk_muscle_workload():
    df = pd.DataFrame(
        {
            "muscle_group": ["Chest", "Back", "Chest", "Legs"],
            "volume_kg": [1500.0, 2000.0, 500.0, 3000.0],
        }
    )
    result = bulk_muscle_workload(df)
    assert len(result) == 3
    assert result.loc[result["muscle_group"] == "Legs", "total_volume_kg"].iloc[0] == 3000.0
    assert abs(result["share_pct"].sum() - 100.0) < 0.1


# ------------------------------------------------------------------ recovery metrics


def test_recovery_summary_basic():
    result = recovery_summary(
        sleep_hours=[7.0, 8.0, 6.0],
        soreness=[3.0, 4.0, 5.0],
        energy=[8.0, 7.0, 6.0],
        body_weight_kg=[78.0, 78.5, 79.0],
    )
    assert abs(result["avg_sleep_h"] - 7.0) < 0.01
    assert abs(result["avg_soreness"] - 4.0) < 0.01
    assert abs(result["avg_energy"] - 7.0) < 0.01
    assert abs(result["avg_body_weight_kg"] - 78.5) < 0.01
    assert result["latest_body_weight_kg"] == 79.0
    assert result["body_weight_change_kg"] == 1.0


def test_recovery_summary_empty():
    result = recovery_summary([], [], [], [])
    assert all(v == 0.0 for v in result.values())


def test_recovery_summary_mismatched_lengths():
    with pytest.raises(ValueError, match="same length"):
        recovery_summary([7.0, 8.0], [3.0], [8.0], [78.0])


def test_bulk_recovery_summary():
    df = pd.DataFrame(
        {
            "date": ["2026-10-05", "2026-10-12", "2026-10-19"],
            "sleep_hours": [7.0, 6.5, 6.0],
            "soreness": [3.0, 5.0, 7.0],
            "energy": [8.0, 6.0, 5.0],
            "body_weight_kg": [78.0, 78.5, 79.0],
        }
    )
    result = bulk_recovery_summary(df)
    assert len(result) == 1
    assert abs(result["avg_sleep_h"].iloc[0] - 6.5) < 0.01
    assert result["latest_body_weight_kg"].iloc[0] == 79.0


def test_bulk_recovery_summary_grouped():
    df = pd.DataFrame(
        {
            "week": [1, 1, 2, 2],
            "sleep_hours": [7.0, 8.0, 6.0, 5.5],
            "soreness": [3.0, 3.0, 6.0, 7.0],
            "energy": [8.0, 8.0, 5.0, 4.0],
            "body_weight_kg": [78.0, 78.0, 79.0, 79.0],
        }
    )
    result = bulk_recovery_summary(df, group_col="week")
    assert len(result) == 2
    assert abs(result.loc[result["week"] == 1, "avg_sleep_h"].iloc[0] - 7.5) < 0.01
    assert abs(result.loc[result["week"] == 2, "avg_sleep_h"].iloc[0] - 5.75) < 0.01
