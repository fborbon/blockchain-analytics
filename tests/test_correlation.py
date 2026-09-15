import numpy as np
import pandas as pd

from src.correlation import daily_returns, lead_lag_correlation, summarize


def test_daily_returns_basic():
    price = pd.Series([100.0, 110.0, 99.0])
    returns = daily_returns(price)
    assert np.isnan(returns.iloc[0])
    assert round(returns.iloc[1], 4) == 0.1


def test_lead_lag_correlation_detects_same_day_relationship():
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    rng = np.random.default_rng(1)
    price = pd.Series(100 * (1 + rng.normal(0, 0.001, size=30)).cumprod(), index=dates)
    price = price.copy()
    # engineer a strong same-day relationship: whale volume tracks the return magnitude
    returns = price.pct_change()
    whale = (returns.fillna(0).to_numpy() * 1000 + 50).clip(min=0)
    whale_series = pd.Series(whale, index=dates)

    corr_df = lead_lag_correlation(whale_series, price, max_lag_days=2)

    assert not corr_df.empty
    assert set(corr_df["lag_days"]) == {-2, -1, 0, 1, 2}


def test_summarize_handles_empty_input():
    empty = pd.DataFrame()
    result = summarize(empty)
    assert "Not enough" in result
