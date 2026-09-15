"""Scans a real, recent, bounded window of Bitcoin blocks for "whale" transactions.

Uses blockchain.info's free `rawblock` endpoint, which returns a full block (all
transactions, with their output values) in a single HTTP call. Scanning a full year
of blocks this way (~52,000 blocks) is not practical for a demo, so this walks back
a fixed number of blocks from the current tip instead. See README "Data sources" for
why this is an honest, bounded scope rather than a full-history dataset.
"""

import json
import time
from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
SATOSHIS_PER_BTC = 100_000_000
WHALE_THRESHOLD_BTC = 50
DEFAULT_BLOCK_COUNT = 150  # roughly the last ~25 hours of blocks


def fetch_latest_block_hash() -> str:
    resp = requests.get("https://blockchain.info/latestblock", timeout=30)
    resp.raise_for_status()
    return resp.json()["hash"]


def fetch_block(block_hash: str, retries: int = 5) -> dict:
    last_error = None
    for attempt in range(retries):
        try:
            resp = requests.get(f"https://blockchain.info/rawblock/{block_hash}", timeout=60)
            resp.raise_for_status()
            return resp.json()
        except (requests.exceptions.RequestException, ValueError) as exc:
            last_error = exc
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch block {block_hash} after {retries} attempts") from last_error


def scan_blocks(block_count: int = DEFAULT_BLOCK_COUNT) -> tuple[list[dict], list[dict]]:
    """Walks back from the chain tip, returns (whale_transactions, block_summaries)."""
    whale_txs = []
    block_summaries = []
    block_hash = fetch_latest_block_hash()

    for i in range(block_count):
        block = fetch_block(block_hash)
        block_total_btc = 0.0
        block_whale_count = 0

        for tx in block["tx"]:
            out_value_sat = sum(o.get("value", 0) for o in tx.get("out", []))
            out_value_btc = out_value_sat / SATOSHIS_PER_BTC
            block_total_btc += out_value_btc
            if out_value_btc >= WHALE_THRESHOLD_BTC:
                block_whale_count += 1
                top_addr = next(
                    (o.get("addr") for o in tx["out"] if o.get("value", 0) > 0), None
                )
                whale_txs.append(
                    {
                        "block_height": block["height"],
                        "block_time": block["time"],
                        "tx_hash": tx["hash"],
                        "value_btc": round(out_value_btc, 4),
                        "top_output_addr": top_addr,
                    }
                )

        block_summaries.append(
            {
                "height": block["height"],
                "time": block["time"],
                "n_tx": block["n_tx"],
                "total_out_btc": round(block_total_btc, 4),
                "whale_tx_count": block_whale_count,
            }
        )

        print(f"[{i + 1}/{block_count}] block {block['height']}: "
              f"{block['n_tx']} tx, {block_whale_count} whale tx")

        block_hash = block["prev_block"]
        time.sleep(0.2)  # be polite to the free public API

        if (i + 1) % 10 == 0:
            _checkpoint(whale_txs, block_summaries)

    return whale_txs, block_summaries


def _checkpoint(whale_txs: list[dict], block_summaries: list[dict]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (RAW_DIR / "whale_transactions.json").write_text(json.dumps(whale_txs))
    (RAW_DIR / "block_summaries.json").write_text(json.dumps(block_summaries))


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    whale_txs, block_summaries = scan_blocks()
    _checkpoint(whale_txs, block_summaries)
    print(f"Found {len(whale_txs)} whale transactions across {len(block_summaries)} blocks")


if __name__ == "__main__":
    main()
