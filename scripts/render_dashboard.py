"""Renders static/index.html from data/processed/dashboard_data.json.

This is the single source of truth for the dashboard's HTML/CSS/JS. Edit this file,
not static/index.html directly, since re-running this script overwrites it (and so
does the sync-to-Landing CI workflow, which copies whatever this produces).
"""

import json
from pathlib import Path

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

CHART_JS_URL = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"


def fmt_usd(n: float) -> str:
    return f"${n:,.0f}"


def build_html(data: dict) -> str:
    kpis = data["kpis"]
    corr_summary = data["correlation"]["summary"]
    corr_table = data["correlation"]["table"]

    change_pct = kpis.get("price_30d_change_pct")
    change_str = f"{change_pct:+.1f}%" if change_pct is not None else "n/a"

    corr_rows_html = "\n".join(
        f"<tr><td class='num'>{row['lag_days']:+d}d</td>"
        f"<td class='num'>{row['pearson_r']:+.3f}</td>"
        f"<td class='num'>{row['pearson_p']:.3f}</td>"
        f"<td class='num'>{row['n_obs']}</td></tr>"
        for row in corr_table
    )

    dashboard_json = json.dumps(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Blockchain Analytics</title>
<meta name="description" content="Bitcoin on-chain trend and whale-influence analytics: real price and on-chain fundamentals, a real bounded window of whale transactions scanned from the live chain, ESD anomaly detection, and lead-lag correlation.">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap">
<script src="{CHART_JS_URL}"></script>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  :root {{
    --gold: #E1C340; --bg: #0c0c12; --card: #13131f; --card-2: #191927;
    --border: #1e1e2e; --text: #e8e8f0; --muted: #7a7a9a;
    --green: #34d399; --indigo: #818cf8; --warn: #e0ac2b;
  }}
  body {{ background: var(--bg); color: var(--text); font-family: 'Segoe UI', system-ui, sans-serif; }}
  header {{ display: flex; align-items: center; gap: 14px; padding: 20px 40px; border-bottom: 1px solid var(--border); flex-wrap: wrap; }}
  h1 {{ font-family: "Big Shoulders Display", sans-serif; font-size: 1.3rem; font-weight: 700; color: var(--gold); }}
  .subtitle {{ font-size: .8rem; color: var(--muted); margin-top: 2px; }}
  header .links {{ margin-left: auto; display: flex; gap: 18px; }}
  header .links a {{ color: var(--muted); text-decoration: none; font-size: .85rem; }}
  header .links a:hover {{ color: var(--gold); }}

  .page {{ max-width: 1080px; margin: 0 auto; padding: 36px 24px 80px; }}
  .eyebrow {{ font: 600 12px "IBM Plex Mono", monospace; letter-spacing: .1em; text-transform: uppercase; color: var(--gold); margin-bottom: 10px; }}
  .hero h2 {{ font-family: "Big Shoulders Display", sans-serif; font-size: 2.2rem; color: #fff; margin-bottom: 10px; }}
  .hero p {{ color: var(--muted); max-width: 68ch; line-height: 1.6; font-size: 1rem; }}

  .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 32px 0; }}
  .kpi {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 18px; }}
  .kpi .n {{ font: 700 24px "IBM Plex Mono", monospace; color: #fff; }}
  .kpi .l {{ font-size: .75rem; color: var(--muted); margin-top: 4px; }}

  h3.section {{ font-family: "Big Shoulders Display", sans-serif; font-size: 1.5rem; color: #fff; margin: 44px 0 16px; }}
  p.lead {{ color: var(--muted); max-width: 72ch; line-height: 1.65; margin-bottom: 18px; }}

  .chart-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; margin-bottom: 20px; }}
  .chart-card canvas {{ max-height: 320px; }}

  table.metrics-table {{ width: 100%; border-collapse: collapse; margin: 18px 0; font-size: .92rem; }}
  table.metrics-table th, table.metrics-table td {{ padding: 10px 14px; border-bottom: 1px solid var(--border); text-align: left; }}
  table.metrics-table th {{ color: var(--muted); font-weight: 600; font-size: .8rem; text-transform: uppercase; letter-spacing: .04em; }}
  table.metrics-table td.num {{ font-family: "IBM Plex Mono", monospace; }}

  .note {{ background: var(--card); border-left: 3px solid var(--gold); border-radius: 0 10px 10px 0; padding: 16px 20px; margin: 20px 0; font-size: .92rem; color: var(--text); line-height: 1.6; }}

  .stack-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 18px 0; }}
  .stack-item {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
  .stack-item b {{ display: block; font: 600 13px "IBM Plex Mono", monospace; color: var(--gold); margin-bottom: 4px; }}
  .stack-item span {{ font-size: 12.5px; color: var(--text); line-height: 1.5; }}

  footer {{ text-align: center; padding: 24px; color: var(--muted); font-size: .82rem; border-top: 1px solid var(--border); margin-top: 40px; }}
  footer a {{ color: var(--muted); }}

  @media (max-width: 760px) {{
    header, .page {{ padding-left: 20px; padding-right: 20px; }}
    .kpi-row {{ grid-template-columns: repeat(2, 1fr); }}
    .stack-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<header>
  <div>
    <h1>Blockchain Analytics</h1>
    <div class="subtitle">Bitcoin on-chain trends and whale influence</div>
  </div>
  <div class="links">
    <a href="https://www.forwardforecasting.eu/">Projects</a>
    <a href="https://education.forwardforecasting.eu/blockchain-analytics/">Field Notes</a>
    <a href="https://github.com/fborbon/blockchain-analytics" target="_blank" rel="noopener">GitHub</a>
  </div>
</header>

<div class="page">

  <section class="hero">
    <div class="eyebrow">Bitcoin On-Chain Demo</div>
    <h2>Do whale transactions actually move the price?</h2>
    <p>Real BTC/USD price and on-chain fundamentals (CoinGecko, blockchain.info), a real
       bounded window of whale transactions scanned directly from recent Bitcoin blocks
       (blockchain.info rawblock API, no key), a generalized ESD anomaly detector applied
       to price and active addresses, and a lead-lag correlation test between whale
       activity and price returns, reported honestly whether or not it turns up a signal.</p>
  </section>

  <div class="kpi-row">
    <div class="kpi"><div class="n">{fmt_usd(kpis['latest_price_usd'])}</div><div class="l">BTC/USD (latest)</div></div>
    <div class="kpi"><div class="n">{change_str}</div><div class="l">30-day price change</div></div>
    <div class="kpi"><div class="n">{kpis['whale_total_btc']:,.0f} BTC</div><div class="l">whale volume, {kpis['whale_window_days']}-day scan</div></div>
    <div class="kpi"><div class="n">{kpis['whale_tx_count']}</div><div class="l">whale tx (&ge;50 BTC), {kpis['blocks_scanned']} blocks scanned</div></div>
  </div>
  <div class="kpi-row">
    <div class="kpi"><div class="n">{kpis['price_anomaly_count']}</div><div class="l">price anomalies (ESD test)</div></div>
    <div class="kpi"><div class="n">{kpis['active_address_anomaly_count']}</div><div class="l">active-address anomalies</div></div>
    <div class="kpi"><div class="n">{kpis['volatility_annualized_pct']:.1f}%</div><div class="l">annualized volatility</div></div>
    <div class="kpi"><div class="n">{kpis['mean_daily_return_pct']:+.2f}%</div><div class="l">mean daily return</div></div>
  </div>

  <h3 class="section">BTC price, with detected anomalies</h3>
  <p class="lead">Red points are days flagged by a generalized ESD test on the residuals of price against its own 7-day moving average (Rosner 1983), not a fixed percentage threshold.</p>
  <div class="chart-card"><canvas id="priceChart"></canvas></div>

  <h3 class="section">Active addresses trend</h3>
  <p class="lead">Unique active on-chain addresses per day (blockchain.info), the same ESD test applied independently.</p>
  <div class="chart-card"><canvas id="addressChart"></canvas></div>

  <h3 class="section">Whale activity, real bounded window</h3>
  <p class="lead">Every block in the scan window was fully downloaded and every transaction's total output value checked; transactions moving &ge;50 BTC in outputs are counted as whale transactions. This is a real, recent {kpis['whale_window_days']}-day window, not a full year, scanning a year of blocks (roughly 52,000) block-by-block is not practical for a demo (see README).</p>
  <div class="chart-card"><canvas id="whaleChart"></canvas></div>

  <h3 class="section">Does whale activity lead the price?</h3>
  <p class="lead">Pearson correlation between daily whale BTC volume and price returns at different lags. Positive lag = whale activity that day correlates with a price return `lag` days later.</p>
  <table class="metrics-table">
    <thead><tr><th>Lag</th><th>Pearson r</th><th>p-value</th><th>n</th></tr></thead>
    <tbody>{corr_rows_html}</tbody>
  </table>
  <div class="note">{corr_summary}</div>

  <h3 class="section">Why statistical methods, not ML</h3>
  <div class="stack-grid">
    <div class="stack-item"><b>Data scope</b><span>A {kpis['whale_window_days']}-day whale window and a one-year daily price/on-chain series is far too little data to train a model that generalizes, but plenty to run a well-understood statistical test correctly.</span></div>
    <div class="stack-item"><b>Interpretability</b><span>An ESD test and a Pearson/Spearman correlation table are auditable line by line. A black-box model's "whale influence score" would not be, and this project's whole point is showing the actual evidence.</span></div>
    <div class="stack-item"><b>Honesty over sophistication</b><span>A fancier model fit to this little data would likely just overfit noise and report a confident-looking but meaningless signal, worse than reporting "inconclusive" plainly.</span></div>
  </div>

  <p class="lead" style="margin-top:28px;">Full pipeline, data sources, and honest limitations: <a href="https://github.com/fborbon/blockchain-analytics" style="color:var(--gold)" target="_blank" rel="noopener">github.com/fborbon/blockchain-analytics</a>.</p>

</div>

<footer>
  <a href="https://github.com/fborbon/blockchain-analytics" target="_blank" rel="noopener">github.com/fborbon/blockchain-analytics</a>
</footer>

<script id="dashboard-data" type="application/json">{dashboard_json}</script>
<script>
(function() {{
  const data = JSON.parse(document.getElementById('dashboard-data').textContent);
  const gold = '#E1C340', muted = '#7a7a9a', green = '#34d399', warn = '#e0ac2b';
  Chart.defaults.color = muted;
  Chart.defaults.borderColor = '#1e1e2e';

  const priceDates = data.price_series.map(p => p.date);
  const priceValues = data.price_series.map(p => p.price_usd);
  const anomalyDates = new Set(data.price_anomalies.map(a => a.date));
  const priceAnomalyPoints = data.price_series.map(p => anomalyDates.has(p.date) ? p.price_usd : null);

  new Chart(document.getElementById('priceChart'), {{
    type: 'line',
    data: {{
      labels: priceDates,
      datasets: [
        {{ label: 'BTC/USD', data: priceValues, borderColor: gold, backgroundColor: 'transparent', pointRadius: 0, borderWidth: 2, tension: 0.15 }},
        {{ label: 'Anomaly', data: priceAnomalyPoints, borderColor: warn, backgroundColor: warn, pointRadius: 5, showLine: false }}
      ]
    }},
    options: {{ responsive: true, interaction: {{ mode: 'index', intersect: false }}, scales: {{ x: {{ ticks: {{ maxTicksLimit: 10 }} }} }} }}
  }});

  const addrDates = data.active_addresses_series.map(p => p.date);
  const addrValues = data.active_addresses_series.map(p => p.n_active_addresses);
  const addrAnomalyDates = new Set(data.active_address_anomalies.map(a => a.date));
  const addrAnomalyPoints = data.active_addresses_series.map(p => addrAnomalyDates.has(p.date) ? p.n_active_addresses : null);

  new Chart(document.getElementById('addressChart'), {{
    type: 'line',
    data: {{
      labels: addrDates,
      datasets: [
        {{ label: 'Active addresses', data: addrValues, borderColor: green, backgroundColor: 'transparent', pointRadius: 0, borderWidth: 2, tension: 0.15 }},
        {{ label: 'Anomaly', data: addrAnomalyPoints, borderColor: warn, backgroundColor: warn, pointRadius: 5, showLine: false }}
      ]
    }},
    options: {{ responsive: true, interaction: {{ mode: 'index', intersect: false }}, scales: {{ x: {{ ticks: {{ maxTicksLimit: 10 }} }} }} }}
  }});

  const whaleDates = data.whale_daily_series.map(p => p.date);
  const whaleVolume = data.whale_daily_series.map(p => p.whale_volume_btc);
  const whaleCount = data.whale_daily_series.map(p => p.whale_tx_count);

  new Chart(document.getElementById('whaleChart'), {{
    type: 'bar',
    data: {{
      labels: whaleDates,
      datasets: [
        {{ label: 'Whale BTC volume', data: whaleVolume, backgroundColor: gold, yAxisID: 'y' }},
        {{ label: 'Whale tx count', data: whaleCount, type: 'line', borderColor: '#818cf8', backgroundColor: 'transparent', yAxisID: 'y1', tension: 0.2 }}
      ]
    }},
    options: {{
      responsive: true,
      scales: {{
        y: {{ position: 'left', title: {{ display: true, text: 'BTC' }} }},
        y1: {{ position: 'right', grid: {{ drawOnChartArea: false }}, title: {{ display: true, text: 'tx count' }} }}
      }}
    }}
  }});
}})();
</script>
<script defer src="https://www.forwardforecasting.eu/assets/translate-widget.js"></script>
</body>
</html>
"""


def main() -> None:
    data = json.loads((PROCESSED_DIR / "dashboard_data.json").read_text())
    html = build_html(data)
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    (STATIC_DIR / "index.html").write_text(html)
    print(f"Wrote {STATIC_DIR / 'index.html'} ({len(html)} bytes)")


if __name__ == "__main__":
    main()
