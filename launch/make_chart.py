"""README comparison chart, light and dark: python3 launch/make_chart.py -> docs/providers-{light,dark}.svg

One request (the docs example), measured once per model through this plugin. Not a benchmark.
Drawn from launch/measurements.json.
"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
THEMES = {"light": dict(bg="#ffffff", ink="#1f2328", muted="#59636e", track="#eff2f5", bar="#1f2328",
                        red="#d1242f", green="#1a7f37"),
          "dark": dict(bg="#0d1117", ink="#f0f6fc", muted="#9198a1", track="#151b23", bar="#f0f6fc",
                       red="#f85149", green="#3fb950")}


def cost(usd):
    return "$0, local" if usd == 0 else "$" + f"{float(f'{usd:.3g}'):.10f}".rstrip("0")


def latency(ms):
    return f"{ms / 1000:.1f} s" if ms >= 1000 else f"{ms} ms"


def svg(theme, m):
    t = THEMES[theme]
    rows = m["rows"]
    W, left, barw, rowh = 880, 200, 250, 44
    H = 92 + len(rows) * rowh + 34
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
         "<title>Same request on every provider: probability of the billing team, latency and cost</title>",
         f'<rect width="{W}" height="{H}" fill="{t["bg"]}"/>',
         f'<g font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif" font-size="15" fill="{t["ink"]}">',
         '<text x="0" y="22" font-size="17" font-weight="600">Same request, same code. Only the provider setting changed.</text>',
         f'<text x="0" y="46" fill="{t["muted"]}">“{escape(m["request"])}” → which team? Bar = probability of billing.</text>',
         f'<text x="{left}" y="78" font-size="13" fill="{t["muted"]}">0</text>',
         f'<text x="{left + barw}" y="78" font-size="13" text-anchor="end" fill="{t["muted"]}">1</text>',
         f'<text x="{left + barw + 16}" y="78" font-size="13" fill="{t["muted"]}">top pick · latency · cost</text>']
    y = 92
    for r in rows:
        ok = r["top"] == "billing"
        s.append(f'<text x="0" y="{y + 17}" font-weight="600">{escape(r["label"])}</text>')
        s.append(f'<text x="0" y="{y + 35}" font-size="13" fill="{t["muted"]}">{escape(r["where"])}</text>')
        s.append(f'<rect x="{left}" y="{y + 6}" width="{barw}" height="18" rx="3" fill="{t["track"]}"/>')
        s.append(f'<rect x="{left}" y="{y + 6}" width="{barw * r["p_billing"]:.1f}" height="18" rx="3" fill="{t["bar"]}"/>')
        pick = f'{r["top"]} {r["p_top"]:.2f}'
        col = t["green"] if ok else t["red"]
        s.append(f'<text x="{left + barw + 16}" y="{y + 20}"><tspan fill="{col}" font-weight="600">{escape(pick)}</tspan>'
                 f'<tspan fill="{t["muted"]}"> · {latency(r["ms"])} · {cost(r["usd"])}</tspan></text>')
        y += rowh
    s.append(f'<text x="0" y="{y + 18}" font-size="13" fill="{t["muted"]}">One request, measured once per model on '
             f'{m["measured"]} (MacBook, Apple Silicon). Not a benchmark: test on your own labelled data.</text>')
    s.append("</g></svg>")
    return "\n".join(s) + "\n"


if __name__ == "__main__":
    m = json.loads((ROOT / "launch" / "measurements.json").read_text())
    for theme in THEMES:
        (ROOT / "docs" / f"providers-{theme}.svg").write_text(svg(theme, m))
        print("wrote", f"docs/providers-{theme}.svg")
