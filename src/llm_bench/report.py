"""Generates a self-contained static HTML dashboard from a results JSON file.

The page embeds the run's data directly (no server, no build step) and
draws three charts with Chart.js (loaded from a CDN — the only external
dependency): an accuracy leaderboard, a latency/cost/accuracy bubble chart,
and a per-category accuracy breakdown. Colors are the three categorical
slots that this project's palette validates for both adjacent (bar) and
all-pairs (bubble) use with up to three series, which is exactly the model
count the bundled demo ships with — add a fourth model and re-check that
palette slot before shipping the page.
"""

from __future__ import annotations

import json
from pathlib import Path

from .runner import ModelSummary, TaskResult, summarize

_SERIES_COLORS_LIGHT = ["#2a78d6", "#eb6834", "#1baf7a"]
_SERIES_COLORS_DARK = ["#3987e5", "#d95926", "#199e70"]

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="LLM Benchmark Panel — accuracy, latency, and cost comparison across models.">
<title>LLM Benchmark Panel</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.4/chart.umd.min.js"></script>
<!-- Chart.js loaded from CDN. For offline use, bundle it locally:
     npm install chart.js && copy node_modules/chart.js/dist/chart.umd.min.js here -->
<script>if(typeof Chart==='undefined'){document.body.insertAdjacentHTML('afterbegin','<p style="color:red;padding:1rem;font-family:system-ui">Chart.js failed to load from CDN. Charts will not render.</p>');}</script>
<style>
  :root {
    color-scheme: light;
    --surface-1: #fcfcfb;
    --page: #f9f9f7;
    --text-primary: #0b0b0b;
    --text-secondary: #52514e;
    --muted: #898781;
    --grid: #e1e0d9;
    --border: rgba(11,11,11,0.10);
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      color-scheme: dark;
      --surface-1: #1a1a19;
      --page: #0d0d0d;
      --text-primary: #ffffff;
      --text-secondary: #c3c2b7;
      --muted: #898781;
      --grid: #2c2c2a;
      --border: rgba(255,255,255,0.10);
    }
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: var(--page);
    color: var(--text-primary);
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    padding: 24px;
  }
  h1 { font-size: 1.4rem; margin: 0 0 4px; }
  .meta { color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 24px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 16px; }
  .card {
    background: var(--surface-1);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
  }
  .card h2 { font-size: 0.95rem; margin: 0 0 12px; color: var(--text-primary); }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--grid); }
  th { color: var(--muted); font-weight: 600; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  .swatch { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; }
  canvas { max-width: 100%; }
  footer { margin-top: 20px; color: var(--muted); font-size: 0.75rem; }
</style>
</head>
<body>
  <h1>LLM Benchmark Panel</h1>
  <div class="meta">Suites: __SUITES__ &middot; Models: __MODELS__ &middot; Generated: __GENERATED_AT__</div>

  <div class="grid">
    <div class="card">
      <h2>Leaderboard</h2>
      <table aria-label="Model leaderboard sorted by accuracy">
        <thead>
          <tr><th>Model</th><th class="num">Accuracy</th><th class="num">Avg. Latency (ms)</th><th class="num">Total Cost ($)</th></tr>
        </thead>
        <tbody id="leaderboard-body"></tbody>
      </table>
    </div>

    <div class="card">
      <h2>Accuracy (%)</h2>
      <canvas id="accuracyChart" height="220" role="img" aria-label="Bar chart showing accuracy percentage per model"></canvas>
    </div>

    <div class="card">
      <h2>Latency vs. Accuracy (bubble size = cost)</h2>
      <canvas id="tradeoffChart" height="220" role="img" aria-label="Bubble chart showing latency versus accuracy with cost as bubble size"></canvas>
    </div>

    <div class="card">
      <h2>Accuracy by Category</h2>
      <canvas id="categoryChart" height="220" role="img" aria-label="Bar chart showing accuracy per category broken down by model"></canvas>
    </div>
  </div>

  <footer>Generated dashboard — data sourced from data/results/*.json. mock:* models are deterministic simulations requiring no API key (see README).</footer>

<script>
if (typeof Chart !== 'undefined') {
const DATA = __DATA_JSON__;
const COLORS = __COLORS_JSON__;
const BUBBLE_COST_SCALE = 4000;  // pixels per USD; adjust if cost range changes
const isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
  && document.documentElement.getAttribute('data-theme') !== 'light';
const palette = isDark ? COLORS.dark : COLORS.light;
const gridColor = isDark ? '#2c2c2a' : '#e1e0d9';
const textColor = isDark ? '#c3c2b7' : '#52514e';

Chart.defaults.color = textColor;
Chart.defaults.borderColor = gridColor;
Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', sans-serif";

const leaderboardBody = document.getElementById('leaderboard-body');
DATA.summaries.forEach((s, i) => {
  const tr = document.createElement('tr');
  tr.innerHTML = `<td><span class="swatch" style="background:${palette[i % palette.length]}"></span>${s.model_id}</td>` +
    `<td class="num">${(s.accuracy * 100).toFixed(0)}%</td>` +
    `<td class="num">${s.avg_latency_ms.toFixed(0)}</td>` +
    `<td class="num">${s.total_cost_usd.toFixed(4)}</td>`;
  leaderboardBody.appendChild(tr);
});

new Chart(document.getElementById('accuracyChart'), {
  type: 'bar',
  data: {
    labels: DATA.summaries.map(s => s.model_id),
    datasets: [{
      data: DATA.summaries.map(s => +(s.accuracy * 100).toFixed(1)),
      backgroundColor: DATA.summaries.map((_, i) => palette[i % palette.length]),
      borderRadius: 4,
      maxBarThickness: 48,
    }]
  },
  options: {
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: gridColor } },
      x: { grid: { display: false } }
    }
  }
});

new Chart(document.getElementById('tradeoffChart'), {
  type: 'bubble',
  data: {
    datasets: DATA.summaries.map((s, i) => ({
      label: s.model_id,
      data: [{ x: s.avg_latency_ms, y: +(s.accuracy * 100).toFixed(1), r: Math.max(6, s.total_cost_usd * BUBBLE_COST_SCALE) }],
      backgroundColor: palette[i % palette.length] + 'cc',
      borderColor: palette[i % palette.length],
      borderWidth: 1,
    }))
  },
  options: {
    plugins: { legend: { position: 'bottom' } },
    scales: {
      x: { title: { display: true, text: 'Average Latency (ms)' }, grid: { color: gridColor } },
      y: { title: { display: true, text: 'Accuracy (%)' }, min: 0, max: 100, grid: { color: gridColor } }
    }
  }
});

const categories = [...new Set(DATA.results.map(r => r.category))].sort();
const models = DATA.summaries.map(s => s.model_id);
new Chart(document.getElementById('categoryChart'), {
  type: 'bar',
  data: {
    labels: categories,
    datasets: models.map((m, i) => ({
      label: m,
      data: categories.map(cat => {
        const rows = DATA.results.filter(r => r.model_id === m && r.category === cat);
        const correct = rows.filter(r => r.correct).length;
        return rows.length ? +(100 * correct / rows.length).toFixed(1) : 0;
      }),
      backgroundColor: palette[i % palette.length],
      borderRadius: 4,
      maxBarThickness: 28,
    }))
  },
  options: {
    plugins: { legend: { position: 'bottom' } },
    scales: {
      y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' }, grid: { color: gridColor } },
      x: { grid: { display: false } }
    }
  }
});
} // end Chart guard
</script>
</body>
</html>
"""


def generate_dashboard_html(data: dict) -> str:
    results: list[TaskResult] = [
        TaskResult(**{k: v for k, v in row.items() if k in TaskResult.__dataclass_fields__})
        for row in data["results"]
    ]
    summaries: list[ModelSummary] = summarize(results)

    payload = {
        "results": [r.to_dict() for r in results],
        "summaries": [s.to_dict() for s in summaries],
    }

    html = _TEMPLATE
    html = html.replace("__DATA_JSON__", json.dumps(payload, ensure_ascii=False))
    html = html.replace(
        "__COLORS_JSON__",
        json.dumps({"light": _SERIES_COLORS_LIGHT, "dark": _SERIES_COLORS_DARK}),
    )
    html = html.replace("__SUITES__", ", ".join(data.get("suites", [])) or "?")
    html = html.replace("__MODELS__", ", ".join(data.get("models", [])) or "?")
    html = html.replace("__GENERATED_AT__", data.get("generated_at", "?"))
    return html


def write_dashboard(results_path: Path, output_path: Path) -> None:
    data = json.loads(Path(results_path).read_text(encoding="utf-8"))
    html = generate_dashboard_html(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
