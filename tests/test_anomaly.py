import numpy as np
import pandas as pd

from src.anomaly import detect_anomalies, moving_average_residuals


def test_moving_average_residuals_flat_series_is_near_zero():
    series = pd.Series([100.0] * 20)
    residuals = moving_average_residuals(series, window=5)
    assert np.allclose(residuals.to_numpy(), 0.0)


def test_detect_anomalies_flags_injected_spike():
    rng = np.random.default_rng(42)
    values = 100 + rng.normal(0, 1, size=60)
    values[30] = 200.0  # obvious injected outlier
    df = pd.DataFrame({"date": range(60), "value": values})

    flagged = detect_anomalies(df, "value", window=7, max_frac=0.1)

    assert 30 in flagged["date"].to_numpy()


def test_detect_anomalies_no_false_positive_on_pure_noise():
    rng = np.random.default_rng(7)
    values = 100 + rng.normal(0, 1, size=60)
    df = pd.DataFrame({"date": range(60), "value": values})

    flagged = detect_anomalies(df, "value", window=7, max_frac=0.05, alpha=0.01)

    assert len(flagged) <= 3
