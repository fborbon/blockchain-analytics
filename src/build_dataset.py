"""Loads the raw fetched data, joins it into daily tables, runs the anomaly and
correlation analyses, and writes the processed artifacts consumed by the dashboard.
"""

import json
from pathlib import Path

import pandas as pd

from src.anomaly import detect_anomalies
from src.correlation import daily_returns, lead_lag_correlation, summarize

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def _load_json(name: str) -> dict:
    return json.loads((RAW_DIR / name).read_text())


def build_price_df() -> pd.DataFrame:
    raw = _load_json("btc_price.json")
    prices = pd.DataFrame(raw["prices"], columns=["ts_ms", "price_usd"])
    caps = pd.DataFrame(raw["market_caps"], columns=["ts_ms", "market_cap_usd"])
    vols = pd.DataFrame(raw["total_volumes"], columns=["ts_ms", "volume_usd"])
    df = prices.merge(caps, on="ts_ms").merge(vols, on="ts_ms")
    df["date"] = pd.to_datetime(df["ts_ms"], unit="ms").dt.date
    df = df.groupby("date", as_index=False).last().drop(columns="ts_ms")
    return df


def build_onchain_df() -> pd.DataFrame:
    chart_cols = {
        "onchain_n-transactions.json": "n_transactions",
        "onchain_n-unique-addresses.json": "n_active_addresses",
        "onchain_hash-rate.json": "hash_rate_ths",
        "onchain_miners-revenue.json": "miners_revenue_usd",
        "onchain_mempool-size.json": "mempool_bytes",
        "onchain_estimated-transaction-volume-usd.json": "onchain_volume_usd",
    }
    merged = None
    for filename, col in chart_cols.items():
        raw = _load_json(filename)
        df = pd.DataFrame(raw["values"])
        df["date"] = pd.to_datetime(df["x"], unit="s").dt.date
        df = df.rename(columns={"y": col})[["date", col]]
        df = df.groupby("date", as_index=False).last()
        merged = df if merged is None else merged.merge(df, on="date", how="outer")
    return merged.sort_values("date")


def build_whale_daily_df() -> tuple[pd.DataFrame, pd.DataFrame]:
    whale_txs = _load_json("whale_transactions.json")
    block_summaries = _load_json("block_summaries.json")

    tx_df = pd.DataFrame(whale_txs)
    if not tx_df.empty:
        tx_df["date"] = pd.to_datetime(tx_df["block_time"], unit="s").dt.date
        daily = tx_df.groupby("date").agg(
            whale_tx_count=("tx_hash", "count"), whale_volume_btc=("value_btc", "sum")
        ).reset_index()
    else:
        daily = pd.DataFrame(columns=["date", "whale_tx_count", "whale_volume_btc"])

    blocks_df = pd.DataFrame(block_summaries)
    return daily.sort_values("date"), blocks_df.sort_values("height")


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    price_df = build_price_df()
    onchain_df = build_onchain_df()
    whale_daily_df, blocks_df = build_whale_daily_df()

    daily_df = price_df.merge(onchain_df, on="date", how="left")
    daily_df.to_csv(PROCESSED_DIR / "daily_metrics.csv", index=False)
    whale_daily_df.to_csv(PROCESSED_DIR / "whale_daily.csv", index=False)
    blocks_df.to_csv(PROCESSED_DIR / "block_summaries.csv", index=False)

    price_series = daily_df.set_index("date")["price_usd"]

    price_anomalies = detect_anomalies(daily_df, "price_usd", window=7)
    addr_anomalies = detect_anomalies(
        daily_df.dropna(subset=["n_active_addresses"]), "n_active_addresses", window=7
    )

    whale_indexed = whale_daily_df.set_index("date")["whale_volume_btc"]
    corr_df = lead_lag_correlation(whale_indexed, price_series.reindex(whale_indexed.index))
    correlation_summary = summarize(corr_df)
    corr_df.to_csv(PROCESSED_DIR / "whale_price_correlation.csv", index=False)

    returns = daily_returns(price_series)

    dashboard_data = {
        "generated_at": pd.Timestamp.now("UTC").isoformat(),
        "price_series": [
            {"date": str(d), "price_usd": p}
            for d, p in zip(daily_df["date"], daily_df["price_usd"], strict=True)
        ],
        "active_addresses_series": [
            {"date": str(row["date"]), "n_active_addresses": row["n_active_addresses"]}
            for _, row in daily_df.dropna(subset=["n_active_addresses"]).iterrows()
        ],
        "whale_daily_series": [
            {
                "date": str(row["date"]),
                "whale_tx_count": int(row["whale_tx_count"]),
                "whale_volume_btc": round(float(row["whale_volume_btc"]), 2),
            }
            for _, row in whale_daily_df.iterrows()
        ],
        "price_anomalies": [
            {"date": str(row["date"]), "price_usd": row["price_usd"]}
            for _, row in price_anomalies.iterrows()
        ],
        "active_address_anomalies": [
            {"date": str(row["date"]), "n_active_addresses": row["n_active_addresses"]}
            for _, row in addr_anomalies.iterrows()
        ],
        "correlation": {
            "table": corr_df.to_dict(orient="records"),
            "summary": correlation_summary,
        },
        "kpis": {
            "latest_price_usd": round(float(daily_df["price_usd"].iloc[-1]), 2),
            "price_30d_change_pct": round(
                float(
                    (daily_df["price_usd"].iloc[-1] / daily_df["price_usd"].iloc[-31] - 1) * 100
                ),
                2,
            ) if len(daily_df) > 31 else None,
            "whale_window_days": int(
                (whale_daily_df["date"].max() - whale_daily_df["date"].min()).days + 1
            ) if not whale_daily_df.empty else 0,
            "whale_total_btc": round(float(whale_daily_df["whale_volume_btc"].sum()), 2),
            "whale_tx_count": int(whale_daily_df["whale_tx_count"].sum()),
            "blocks_scanned": len(blocks_df),
            "price_anomaly_count": len(price_anomalies),
            "active_address_anomaly_count": len(addr_anomalies),
            "mean_daily_return_pct": round(float(returns.mean() * 100), 3),
            "volatility_annualized_pct": round(
                float(returns.std() * (365**0.5) * 100), 2
            ),
        },
    }

    (PROCESSED_DIR / "dashboard_data.json").write_text(json.dumps(dashboard_data, indent=2))
    print("Wrote data/processed/dashboard_data.json")
    print(json.dumps(dashboard_data["kpis"], indent=2))


if __name__ == "__main__":
    main()
