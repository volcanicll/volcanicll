#!/usr/bin/env python3
"""Regenerate the profile's survey assets from readings.json.

Visual language: monospace, hairline rules, letterspaced uppercase labels, a
single rust accent. Palette per mode:

              lines/labels   values      accent      paper
  light       #57606a        #24292f     #bc4c00     #ffffff
  dark        #8b949e        #c9d1d9     #f0883e     #0d1117

readings.json — written by measure.py from the GitHub API — is the only
input: no network, no gh, no clock. That purity is what the CI guard leans
on: `gen_assets.py --check` rebuilds everything in memory and fails if any
file on disk differs, so a hand-edited number cannot outlive the next push.

Alongside the four SVGs, this script owns the generated fragments of
README.md: the plate and diurnal alt attributes, and the caption's readings
span between the <!-- survey:readings --> markers. The alt text is drawn
from the same readings as the picture, so the two cannot drift apart again.

Run `./render_preview.py` for a browser preview of the README, and
`./check_svg.py` to see an asset exactly as GitHub renders it (as <img>, with
no page CSS to lean on).
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / "assets"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
READINGS = ROOT / "readings.json"
README = ROOT / "README.md"
SPAN = "survey:readings"   # the README fragment this script rewrites

HERE_SINCE = 2020   # the one fixed fact on the plate; everything else is measured

# Plate columns are centred on the true midpoints between the hairline rules
# (0/208/415/622/830), not eyeballed, so every reading sits dead centre.
PLATE_X = [104.0, 311.5, 518.5, 726.0]

NIGHT = [(0, 4), (22, 23)]   # shaded bands: the small hours, at either end

THEME = {
    "light": {"line": "#57606a", "val": "#24292f", "acc": "#bc4c00", "paper": "#ffffff"},
    "dark": {"line": "#8b949e", "val": "#c9d1d9", "acc": "#f0883e", "paper": "#0d1117"},
}


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


def plate(t: dict, r: dict) -> str:
    """Four-column instrument readout: the headline counts."""
    cols = [
        (str(r["total"]), "COMMITS / 12 MO"),
        (str(r["active_days"]), "ACTIVE DAYS"),
        (str(r["repos"]), "REPOS TOUCHED"),
        (str(HERE_SINCE), "HERE SINCE"),
    ]
    body = []
    for x, (v, lab) in zip(PLATE_X, cols):
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


def sleep_run(hours: list[int]) -> tuple[int, int] | None:
    """Longest run of empty hours after the first night band — the sleep gap.

    The band starting at hour 0 is shading, not sleep, so runs must start
    later; returns None when there is no interior gap to report.
    """
    best = None
    start = None
    for h, n in enumerate(hours + [1]):   # sentinel flushes a run that ends at 23
        if n == 0 and start is None:
            start = h
        elif n != 0 and start is not None:
            if start > 0 and (best is None or h - start > best[1] - best[0]):
                best = (start, h)
            start = None
    return best


def diurnal(t: dict, r: dict) -> str:
    """Commits per hour of the day, drawn as a seismograph trace.

    One bar per hour, height proportional to the count. The night hours get a
    faint band so the shape of the day reads at a glance, and the busiest hour
    carries the accent so there is exactly one place the eye lands first.
    """
    hours = r["hours"]
    W, H = 830, 196
    X0, X1 = 40.0, 800.0
    BASE, TOP, BAR_W = 148.0, 100.0, 17.0
    slot = (X1 - X0) / 24
    peak = max(hours)
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

    for hour, n in enumerate(hours):
        if n == 0:
            continue
        h = max(round(TOP * n / peak), 2)
        cls = "peak" if n == peak else "bar"
        body.append(f'  <rect class="{cls}" x="{bx(hour):.1f}" y="{BASE - h:.1f}" '
                    f'width="{BAR_W}" height="{h}"/>')

    # the busiest hour, called out above its bar
    peak_hour = hours.index(peak)
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


# --- the generated fragments of README.md ----------------------------------

def alt_plate(r: dict) -> str:
    return (f"Survey plate: {r['total']} commits in the last twelve months, "
            f"{r['active_days']} days with commits, {r['repos']} repositories touched, "
            f"here since {HERE_SINCE}")


def alt_diurnal(r: dict) -> str:
    hours = r["hours"]
    peak, peak_hour = max(hours), hours.index(max(hours))
    when = {0: "at midnight", 12: "in the noon hour"}.get(peak_hour, f"at {peak_hour:02d}:00")
    alt = f"Commits per hour across a day, peaking at {peak} commit{'s' if peak != 1 else ''} {when}"
    gap = sleep_run(hours)
    if gap:
        alt += f" and empty between {gap[0]:02d}:00 and {gap[1] % 24:02d}:00"
    return alt


def caption(r: dict) -> str:
    """The caption's opening sentence: the readings, and how they moved.

    A delta is stated only when there is one — "0 since the last survey" is
    not worth a sentence.
    """
    late = r["hours"][22] + r["hours"][23]
    prev = r.get("previous")
    delta = ""
    if prev:
        d = r["total"] - prev["total"]
        if d > 0:
            delta = f" — {d} more than the last survey"
        elif d < 0:
            delta = f" — {-d} fewer than the last survey"
    if late:
        n = round(r["total"] / late)
        words = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven",
                 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}
        share = f"{' and ' if delta else '; '}one in {words.get(n, n)} of them after 22:00"
    else:
        share = ""
    return f"{r['total']} commits over the last twelve months, local time{delta}{share}."


def set_alt(md: str, name: str, alt: str) -> str:
    """Regenerate the alt attribute of the survey <img> whose src names it."""
    tag = re.search(rf'<img\b[^>]*\bsrc="assets/{name}-light\.svg"[^>]*>', md)
    if not tag:
        raise SystemExit(f"gen_assets: no <img> for assets/{name}-light.svg in README.md")
    new, n = re.subn(r'\balt="[^"]*"', lambda _: f'alt="{alt}"', tag.group(0), count=1)
    if n != 1:
        raise SystemExit(f"gen_assets: the {name} <img> carries no alt attribute")
    return md[:tag.start()] + new + md[tag.end():]


def set_span(md: str, text: str) -> str:
    """Rewrite the one marked readings span in the README."""
    pat = re.compile(rf"<!-- {SPAN} -->.*?<!-- /{SPAN} -->", re.DOTALL)
    md, n = pat.subn(f"<!-- {SPAN} -->{text}<!-- /{SPAN} -->", md)
    if n != 1:
        raise SystemExit(f"gen_assets: expected exactly one <!-- {SPAN} --> span in README.md, found {n}")
    return md


def readme(md: str, r: dict) -> str:
    return set_span(set_alt(set_alt(md, "plate", alt_plate(r)), "diurnal", alt_diurnal(r)), caption(r))


def build(r: dict) -> dict[str, str]:
    """Everything this script owns, as path -> content."""
    return {
        "assets/plate-light.svg": plate(THEME["light"], r),
        "assets/plate-dark.svg": plate(THEME["dark"], r),
        "assets/diurnal-light.svg": diurnal(THEME["light"], r),
        "assets/diurnal-dark.svg": diurnal(THEME["dark"], r),
        "README.md": readme(README.read_text(), r),
    }


def main() -> None:
    check = "--check" in sys.argv[1:]
    r = json.loads(READINGS.read_text())
    stale = {}
    for rel, want in build(r).items():
        if (ROOT / rel).read_text() == want:
            print(f"  {rel}: ok")
        else:
            stale[rel] = want

    if check:
        if stale:
            for rel in stale:
                print(f"  {rel}: stale — differs from what readings.json draws")
            print("\nrun `python3 gen_assets.py` and commit the result")
            sys.exit(1)
        print("\nall generated files match readings.json")
        return

    for rel, want in stale.items():
        (ROOT / rel).write_text(want)
        print(f"  {rel}: wrote")

    peak, peak_hour = max(r["hours"]), r["hours"].index(max(r["hours"]))
    print(f"\nplate: {r['total']} COMMITS / 12 MO · {r['active_days']} ACTIVE DAYS · "
          f"{r['repos']} REPOS TOUCHED · {HERE_SINCE} HERE SINCE")
    print(f"diurnal: {r['total']} commits, peak {peak} at {peak_hour:02d}:00")


if __name__ == "__main__":
    sys.exit(main())
