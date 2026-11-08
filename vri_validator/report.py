"""CSV and self-contained HTML report writers."""

from __future__ import annotations

import csv
import html
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import __version__
from .model import Dataset
from .rules.engine import Finding, Findings

CSV_FIELDS = (
    "severity", "code", "polygon_id", "polygon_number", "objectid",
    "table", "field", "value", "layer_order", "species_order", "record_id",
    "message", "source",
)


def sorted_findings(findings: Findings) -> list[Finding]:
    order = {"error": 0, "warning": 1, "info": 2}
    return sorted(
        findings.items,
        key=lambda f: (order.get(f.severity, 3), f.code, f.polygon_number,
                       f.polygon_id or 0, f.table, f.layer_order or 0,
                       f.species_order or 0, f.message),
    )


def counts_by_code(findings: Findings) -> list[tuple[str, str, int]]:
    counter = Counter(f.code for f in findings.items)
    severity = {f.code: f.severity for f in findings.items}
    return sorted(((code, severity.get(code, "info"), n)
                   for code, n in counter.items()),
                  key=lambda item: (-item[2], item[0]))


def write_csv(findings: Findings, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for f in sorted_findings(findings):
            writer.writerow({
                "severity": f.severity,
                "code": f.code,
                "polygon_id": "" if f.polygon_id is None else f.polygon_id,
                "polygon_number": f.polygon_number,
                "objectid": "" if f.objectid is None else f.objectid,
                "table": f.table,
                "field": f.field,
                "value": f.value,
                "layer_order": "" if f.layer_order is None else f.layer_order,
                "species_order": "" if f.species_order is None else f.species_order,
                "record_id": "" if f.record_id is None else f.record_id,
                "message": f.message.replace("\n", " "),
                "source": f.source,
            })
    return path


def write_html(dataset: Dataset, findings: Findings, path: str | Path,
               title: str | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    counts = findings.counts()
    rows = sorted_findings(findings)
    codes = counts_by_code(findings)
    code_options = "\n".join(
        f'<option value="{html.escape(code)}">{html.escape(code)} ({n})</option>'
        for code, _severity, n in codes
    )
    rows_html = "\n".join(_row(r) for r in rows)
    code_rows = "\n".join(
        f"<tr><td><code>{html.escape(code)}</code></td><td>{severity}</td><td>{n}</td></tr>"
        for code, severity, n in codes
    )
    table_counts = "\n".join(
        f"<tr><td>{html.escape(name)}</td><td>{n:,}</td></tr>"
        for name, n in dataset.row_counts.items()
    )
    orphan_counts = "\n".join(
        f"<tr><td>{html.escape(name)}</td><td>{len(rows_):,}</td></tr>"
        for name, rows_ in dataset.orphans.items() if rows_
    ) or "<tr><td colspan='2'>none</td></tr>"
    generated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = title or "VRI validation report"
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: light dark; --bg:#f7f7f5; --card:#fff; --ink:#1d2328; --muted:#66707a;
         --line:#dfe3e6; --error:#b42318; --warning:#a15c00; --info:#1769aa; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#15191d; --card:#1d2328; --ink:#e8ecef; --muted:#9aa6b2; --line:#313a43;
           --error:#ff8a80; --warning:#ffc46b; --info:#7cc4ff; }}
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink);
        font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }}
main {{ max-width:1500px; margin:0 auto; padding:24px; }}
h1 {{ font-size:22px; margin:0 0 4px; }}
h2 {{ font-size:16px; margin:28px 0 10px; }}
.sub {{ color:var(--muted); margin:0 0 18px; overflow-wrap:anywhere; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:12px; }}
.card {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:12px 14px; }}
.card .num {{ font-size:24px; font-weight:700; }}
.card.error .num {{ color:var(--error); }}
.card.warning .num {{ color:var(--warning); }}
.card.info .num {{ color:var(--info); }}
.controls {{ display:flex; flex-wrap:wrap; gap:10px; margin:18px 0; align-items:center; }}
input, select, button {{ font:inherit; color:inherit; background:var(--card);
                         border:1px solid var(--line); border-radius:6px; padding:7px 9px; }}
input {{ min-width:260px; }}
button {{ cursor:pointer; }}
table {{ width:100%; border-collapse:collapse; background:var(--card);
         border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
th, td {{ text-align:left; padding:7px 9px; border-bottom:1px solid var(--line); vertical-align:top; }}
th {{ font-size:12px; text-transform:uppercase; letter-spacing:.04em; color:var(--muted);
      background:color-mix(in srgb, var(--card) 85%, var(--bg)); position:sticky; top:0; }}
tbody tr:last-child td {{ border-bottom:0; }}
tbody tr:hover {{ background:color-mix(in srgb, var(--card) 92%, var(--bg)); }}
code {{ font-size:12px; }}
.sev {{ font-weight:700; white-space:nowrap; }}
.sev.error {{ color:var(--error); }}
.sev.warning {{ color:var(--warning); }}
.sev.info {{ color:var(--info); }}
.small {{ color:var(--muted); font-size:12px; }}
.two {{ display:grid; grid-template-columns:minmax(0,2fr) minmax(260px,1fr); gap:20px; }}
@media (max-width:900px) {{ .two {{ grid-template-columns:1fr; }} }}
.empty {{ padding:24px; text-align:center; color:var(--muted); background:var(--card);
          border:1px solid var(--line); border-radius:8px; }}
footer {{ color:var(--muted); font-size:12px; margin-top:24px; }}
</style>
</head>
<body>
<main>
<h1>{html.escape(title)}</h1>
<p class="sub">{html.escape(dataset.path)} &middot; generated {generated} &middot; vri-validator {__version__}</p>
<div class="cards">
  <div class="card error"><div class="num" id="n-error">{counts['error']:,}</div><div>errors</div></div>
  <div class="card warning"><div class="num" id="n-warning">{counts['warning']:,}</div><div>warnings</div></div>
  <div class="card info"><div class="num" id="n-info">{counts['info']:,}</div><div>info</div></div>
  <div class="card"><div class="num">{len(dataset.polygons):,}</div><div>polygons</div></div>
</div>

<div class="two">
  <div>
    <h2>Findings</h2>
    <div class="controls">
      <input id="q" type="search" placeholder="Search polygon, field, message, value...">
      <select id="sev"><option value="">All severities</option>
        <option value="error">Errors</option><option value="warning">Warnings</option>
        <option value="info">Info</option></select>
      <select id="code"><option value="">All rule codes</option>{code_options}</select>
      <span class="small" id="shown"></span>
    </div>
    <table>
      <thead><tr><th>Sev</th><th>Code</th><th>Polygon</th><th>Table</th><th>Field</th>
      <th>Value</th><th>Layer</th><th>Species</th><th>Message</th><th>Source</th></tr></thead>
      <tbody id="rows">
      {rows_html or '<tr><td colspan="10" class="empty">No findings.</td></tr>'}
      </tbody>
    </table>
  </div>
  <aside>
    <h2>Rules triggered</h2>
    <table><thead><tr><th>Code</th><th>Severity</th><th>Count</th></tr></thead>
    <tbody>{code_rows or '<tr><td colspan="3">none</td></tr>'}</tbody></table>
    <h2>Rows read</h2>
    <table><tbody>{table_counts}</tbody></table>
    <h2>Orphan / duplicate rows</h2>
    <table><tbody>{orphan_counts}</tbody></table>
  </aside>
</div>
<footer>Read-only validation. Findings are rule-based and should be reviewed before correction.</footer>
</main>
<script>
const rows = Array.from(document.querySelectorAll('#rows tr[data-sev]'));
const q = document.getElementById('q');
const sev = document.getElementById('sev');
const code = document.getElementById('code');
const shown = document.getElementById('shown');
function apply() {{
  const needle = q.value.trim().toLowerCase();
  const s = sev.value, c = code.value;
  let visible = 0;
  for (const row of rows) {{
    const ok = (!s || row.dataset.sev === s) &&
               (!c || row.dataset.code === c) &&
               (!needle || row.dataset.text.includes(needle));
    row.style.display = ok ? '' : 'none';
    if (ok) visible++;
  }}
  shown.textContent = visible.toLocaleString() + ' of ' + rows.length.toLocaleString() + ' shown';
}}
for (const el of [q, sev, code]) el.addEventListener('input', apply);
apply();
</script>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")
    return path


def _row(f: Finding) -> str:
    text_value = " ".join((f.code, f.polygon_number, f.table, f.field, f.value,
                           f.message, f.source)).lower()
    layer = "" if f.layer_order is None else f.layer_order
    species = "" if f.species_order is None else f.species_order
    return (
        f'<tr data-sev="{f.severity}" data-code="{html.escape(f.code)}" '
        f'data-text="{html.escape(text_value, quote=True)}">'
        f'<td class="sev {f.severity}">{f.severity}</td>'
        f'<td><code>{html.escape(f.code)}</code></td>'
        f'<td>{html.escape(f.polygon_number or "—")}'
        f'<div class="small">FID {f.polygon_id if f.polygon_id is not None else "—"}</div></td>'
        f'<td class="small">{html.escape(f.table)}</td>'
        f'<td class="small">{html.escape(f.field)}</td>'
        f'<td class="small">{html.escape(f.value)}</td>'
        f'<td>{layer}</td><td>{species}</td>'
        f'<td>{html.escape(f.message)}</td>'
        f'<td class="small">{html.escape(f.source)}</td>'
        '</tr>'
    )
