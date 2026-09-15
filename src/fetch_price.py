"""Pulls BTC/USD daily price, market cap and volume from CoinGecko's free public API."""

import json
import time
from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
COINGECKO_URL = (
    "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
    "?vs_currency=usd&days=365&interval=daily"
)


def fetch_price_history(days: int = 365, retries: int = 3) -> dict:
    for attempt in range(retries):
        resp = requests.get(COINGECKO_URL, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 429 and attempt < retries - 1:
            time.sleep(15)
            continue
        resp.raise_for_status()
    raise RuntimeError("CoinGecko request failed after retries")


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    data = fetch_price_history()
    out_path = RAW_DIR / "btc_price.json"
    out_path.write_text(json.dumps(data))
    print(f"Wrote {out_path} ({len(data.get('prices', []))} daily points)")


if __name__ == "__main__":
    main()
