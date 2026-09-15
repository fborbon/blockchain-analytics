"""Generalized ESD (Extreme Studentized Deviate) outlier detection, applied to the
residuals of a series against its own moving average.

Adapted from an outlier-detection approach the author wrote for a prior take-home
challenge (moving-average residuals + Rosner's 1983 generalized ESD test), reimplemented
here in a plain functional style rather than a stateful class.

Reference: Rosner, B. (1983), "Percentage Points for a Generalized ESD Many-Outlier
Procedure", Technometrics. https://www.itl.nist.gov/div898/handbook/eda/section3/eda35h3.htm
"""

import numpy as np
import pandas as pd
from scipy import stats


def moving_average_residuals(series: pd.Series, window: int = 7) -> pd.Series:
    rolling_mean = series.rolling(window=window, center=True, min_periods=1).mean()
    return series - rolling_mean


def esd_test(residuals: pd.Series, max_outliers: int, alpha: float = 0.05) -> list[int]:
    """Returns the positional indices of residuals flagged as outliers."""
    values = list(residuals.to_numpy(dtype=float))
    positions = list(range(len(values)))
    n = len(values)
    flagged: list[int] = []

    for i in range(1, max_outliers + 1):
        mean, std = np.mean(values), np.std(values, ddof=1)
        if std == 0:
            break
        deviations = np.abs((np.array(values) - mean) / std)
        max_idx = int(np.argmax(deviations))
        test_stat = deviations[max_idx]

        p = 1 - alpha / (2 * (n - i + 1))
        t_crit = stats.t.ppf(p, n - i - 1)
        critical_value = ((n - i) * t_crit) / np.sqrt((n - i - 1 + t_crit**2) * (n - i + 1))

        if test_stat > critical_value:
            flagged.append(positions.pop(max_idx))
            values.pop(max_idx)
        else:
            break

    return sorted(flagged)


def detect_anomalies(
    df: pd.DataFrame, value_col: str, window: int = 7, alpha: float = 0.05, max_frac: float = 0.1
) -> pd.DataFrame:
    """Flags anomalous rows in df[value_col]. Returns the flagged rows, unmodified."""
    residuals = moving_average_residuals(df[value_col], window=window)
    max_outliers = max(1, int(len(df) * max_frac))
    flagged_positions = esd_test(residuals, max_outliers=max_outliers, alpha=alpha)
    return df.iloc[flagged_positions]
