#!/usr/bin/env python3
"""Regenerate the profile's survey assets.

Visual language: monospace, hairline rules, letterspaced uppercase labels, a
single rust accent. Palette per mode:

              lines/labels   values      accent      paper
  light       #57606a        #24292f     #bc4c00     #ffffff
  dark        #8b949e        #c9d1d9     #f0883e     #0d1117

Run `./render_preview.py` for a browser preview of the README, and
`./check_svg.py` to see an asset exactly as GitHub renders it (as <img>, with
no page CSS to lean on).
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "assets"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

THEME = {
    "light": {"line": "#57606a", "val": "#24292f", "acc": "#bc4c00", "paper": "#ffffff"},
    "dark": {"line": "#8b949e", "val": "#c9d1d9", "acc": "#f0883e", "paper": "#0d1117"},
}

# --- readings, measured from the GitHub API over the trailing 12 months ----
# Plate columns are centred on the true midpoints between the hairline rules
# (0/208/415/622/830), not eyeballed, so every reading sits dead centre.
PLATE = [
    ("382", "COMMITS / 12 MO"),
    ("82", "ACTIVE DAYS"),
    ("25", "REPOS TOUCHED"),
    ("2020", "HERE SINCE"),
]
PLATE_X = [104.0, 311.5, 518.5, 726.0]

# Diurnal trace: commits per hour of the local day (UTC+8), 24 buckets.
# Source: GET /search/commits?q=author:volcanicll committer-date:>2025-10-02
# 382 commits across 82 distinct days and 25 repositories.
HOURS = [21, 10, 8, 3, 0, 0, 0, 0, 3, 41, 26, 18, 44, 17, 35, 18, 20, 18, 13, 10, 12, 13, 37, 15]
NIGHT = [(0, 4), (22, 23)]   # shaded bands: the small hours, at either end


def wrap(body: str, css: str, w: int, h: int) -> str:
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" fill="none">',
        "  <style>",
        css,
        "  </style>",
        body,
        "</svg>",
        "",
    ])


def plate(t: dict) -> str:
    """Four-column instrument readout: the headline counts."""
    body = []
    for x, (v, lab) in zip(PLATE_X, PLATE):
        body.append(f'  <text class="val" x="{x}" y="60">{v}</text>')
        body.append(f'  <text class="lbl" x="{x}" y="76">{lab}</text>')
    for x in PLATE_X[1:-1]:
        body.append(f'  <line class="div" x1="{x}" y1="42" x2="{x}" y2="82"/>')
    css = "\n".join([
        f"    .val {{ fill: {t['val']}; font-family: {MONO}; font-size: 22px; font-weight: 600; text-anchor: middle; }}",
        f"    .lbl {{ fill: {t['line']}; font-family: {MONO}; font-size: 7.5px; letter-spacing: 2.2px; text-anchor: middle; opacity: 0.8; }}",
        f"    .div {{ stroke: {t['line']}; stroke-width: 0.75; opacity: 0.18; }}",
    ])
    return wrap("\n".join(body), css, 830, 104)


def diurnal(t: dict) -> str:
    """Commits per hour of the day, drawn as a seismograph trace.

    One bar per hour, height proportional to the count. The night hours get a
    faint band so the shape of the day reads at a glance, and the busiest hour
    carries the accent so there is exactly one place the eye lands first.
    """
    W, H = 830, 196
    X0, X1 = 40.0, 800.0
    BASE, TOP, BAR_W = 148.0, 100.0, 17.0
    slot = (X1 - X0) / 24
    peak = max(HOURS)
    # every third hour, plus the evening spike so the caption can point at it,
    # plus the last hour so the scale reads to the end of the day
    SCALE = list(range(0, 24, 3)) + [22, 23]

    def bx(hour: float) -> float:
        """Left edge of the bar for an hour."""
        return X0 + hour * slot + (slot - BAR_W) / 2

    body = []

    # night bands first, so the bars sit on top of them
    for lo, hi in NIGHT:
        x = bx(lo) - 3
        body.append(f'  <rect class="night" x="{x:.1f}" y="{TOP - 8:.1f}" '
                    f'width="{(hi - lo + 1) * slot + 6:.1f}" height="{BASE - TOP + 8:.1f}"/>')

    body.append(f'  <line class="rule" x1="{X0}" y1="{BASE}" x2="{X1}" y2="{BASE}"/>')

    for hour, n in enumerate(HOURS):
        if n == 0:
            continue
        h = max(round(TOP * n / peak), 2)
        cls = "peak" if n == peak else "bar"
        body.append(f'  <rect class="{cls}" x="{bx(hour):.1f}" y="{BASE - h:.1f}" '
                    f'width="{BAR_W}" height="{h}"/>')

    # the busiest hour, called out above its bar
    peak_hour = HOURS.index(peak)
    px = bx(peak_hour) + BAR_W / 2
    body.append(f'  <text class="mark" x="{px:.1f}" y="{BASE - TOP - 14:.1f}">{peak}</text>')

    # hour scale
    for hour in SCALE:
        cx = bx(hour) + BAR_W / 2
        cls = "tick here" if hour == peak_hour else "tick"
        body.append(f'  <text class="{cls}" x="{cx:.1f}" y="{BASE + 16:.1f}">{hour:02d}</text>')

    # what the bars are, on the same line as the peak reading
    body.append(f'  <text class="axis" x="{X0:.1f}" y="{BASE - TOP - 14:.1f}">COMMITS / HOUR</text>')

    css = "\n".join([
        f"    .bar   {{ fill: {t['line']}; opacity: 0.6; }}",
        f"    .peak  {{ fill: {t['acc']}; opacity: 0.92; }}",
        f"    .night {{ fill: {t['line']}; opacity: 0.1; }}",
        f"    .rule  {{ stroke: {t['line']}; stroke-width: 0.75; opacity: 0.28; }}",
        f"    .tick  {{ fill: {t['line']}; font-family: {MONO}; font-size: 9px; letter-spacing: 1.4px; text-anchor: middle; opacity: 0.8; }}",
        f"    .here  {{ fill: {t['acc']}; opacity: 0.95; font-weight: 600; }}",
        f"    .mark  {{ fill: {t['acc']}; font-family: {MONO}; font-size: 9px; letter-spacing: 1px; font-weight: 600; text-anchor: middle; opacity: 0.95; }}",
        f"    .axis  {{ fill: {t['line']}; font-family: {MONO}; font-size: 7.5px; letter-spacing: 2.2px; opacity: 0.75; }}",
    ])
    return wrap("\n".join(body), css, W, H)


if __name__ == "__main__":
    for mode, t in THEME.items():
        (OUT / f"plate-{mode}.svg").write_text(plate(t))
        (OUT / f"diurnal-{mode}.svg").write_text(diurnal(t))
        print(f"  wrote plate-{mode}.svg  diurnal-{mode}.svg")
    print(f"\nplate: {' · '.join(f'{v} {l}' for v, l in PLATE)}")
    print(f"diurnal: {sum(HOURS)} commits, peak {max(HOURS)} at {HOURS.index(max(HOURS)):02d}:00")
