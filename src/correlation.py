"""Lead-lag correlation between daily whale activity and BTC price returns."""

import pandas as pd
from scipy import stats


def daily_returns(price: pd.Series) -> pd.Series:
    return price.pct_change()


def lead_lag_correlation(
    whale_series: pd.Series, price_series: pd.Series, max_lag_days: int = 3
) -> pd.DataFrame:
    """For lag in [-max_lag_days, max_lag_days], correlates whale_series[t] against
    price return at t+lag. Positive lag = whale activity leading price by `lag` days.
    """
    returns = daily_returns(price_series)
    rows = []
    for lag in range(-max_lag_days, max_lag_days + 1):
        shifted_returns = returns.shift(-lag)
        paired = pd.concat([whale_series, shifted_returns], axis=1).dropna()
        if len(paired) < 5:
            continue
        pearson_r, pearson_p = stats.pearsonr(paired.iloc[:, 0], paired.iloc[:, 1])
        spearman_r, spearman_p = stats.spearmanr(paired.iloc[:, 0], paired.iloc[:, 1])
        rows.append(
            {
                "lag_days": lag,
                "n_obs": len(paired),
                "pearson_r": round(float(pearson_r), 4),
                "pearson_p": round(float(pearson_p), 4),
                "spearman_r": round(float(spearman_r), 4),
                "spearman_p": round(float(spearman_p), 4),
            }
        )
    return pd.DataFrame(rows)


def best_lag(corr_df: pd.DataFrame) -> dict:
    if corr_df.empty:
        return {}
    idx = corr_df["pearson_r"].abs().idxmax()
    return corr_df.loc[idx].to_dict()


def summarize(corr_df: pd.DataFrame, significance: float = 0.05) -> str:
    """Plain-language, honest summary. No overclaiming when nothing is significant."""
    if corr_df.empty:
        return "Not enough overlapping days between whale activity and price data to test correlation."

    top = best_lag(corr_df)
    if not top or top["pearson_p"] >= significance:
        return (
            f"No statistically significant lead-lag correlation was found in this window "
            f"(strongest |r|={abs(top.get('pearson_r', 0))} at lag={top.get('lag_days')} days, "
            f"p={top.get('pearson_p')}, not below {significance}). With only a few days of real "
            f"whale-scan data, this should be read as inconclusive, not as evidence that whale "
            f"activity has no effect on price."
        )

    direction = "leads" if top["lag_days"] > 0 else ("lags" if top["lag_days"] < 0 else "is same-day with")
    return (
        f"Whale activity {direction} price returns by {abs(top['lag_days'])} day(s) "
        f"(Pearson r={top['pearson_r']}, p={top['pearson_p']}, n={top['n_obs']}). "
        f"Treat this as a preliminary signal from a short, real but bounded data window, not a "
        f"validated trading rule."
    )
