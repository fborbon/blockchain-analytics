"""Pulls Bitcoin on-chain fundamental time series from blockchain.info's free Charts API."""

import json
from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
BASE_URL = "https://api.blockchain.info/charts/{chart}?timespan=1year&format=json"

CHARTS = [
    "n-transactions",
    "n-unique-addresses",
    "hash-rate",
    "miners-revenue",
    "mempool-size",
    "market-cap",
    "estimated-transaction-volume-usd",
    "trade-volume",
]


def fetch_chart(chart: str) -> dict:
    resp = requests.get(BASE_URL.format(chart=chart), timeout=30)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for chart in CHARTS:
        data = fetch_chart(chart)
        out_path = RAW_DIR / f"onchain_{chart}.json"
        out_path.write_text(json.dumps(data))
        print(f"Wrote {out_path} ({len(data.get('values', []))} points, unit={data.get('unit')})")


if __name__ == "__main__":
    main()
