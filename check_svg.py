#!/usr/bin/env python3
"""Render SVGs the way GitHub does — <img src="...svg">, no page CSS.

The profile's assets are consumed as <img>, so a standalone page with real
page CSS is not a faithful preview: anything that only works because the
hosting page styled it would look fine here and break on GitHub.
"""
import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = pathlib.Path(tempfile.gettempdir()) / "profile-preview"
CHROME = os.environ.get(
    "CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def harness(name: str) -> pathlib.Path:
    light = (ASSETS / f"{name}-light.svg").as_uri()
    dark = (ASSETS / f"{name}-dark.svg").as_uri()
    html = f"""<!doctype html><html><head><meta charset="utf-8"><style>
  body {{ margin:0; font-family:ui-monospace,Menlo,monospace; }}
  .row {{ display:flex; align-items:flex-start; }}
  .cell {{ padding:10px; }}
  .light {{ background:#ffffff; }}
  .dark  {{ background:#0d1117; }}
  img {{ display:block; }}
</style></head><body>
<div class="row">
  <div class="cell light"><img src="{light}"></div>
  <div class="cell dark"><img src="{dark}"></div>
</div>
</body></html>"""
    p = OUT / f"harness-{name}.html"
    p.write_text(html)
    return p


def shoot(html: pathlib.Path, png: pathlib.Path) -> None:
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
         "--force-device-scale-factor=2", f"--screenshot={png}",
         "--window-size=1700,600", html.as_uri()],
        capture_output=True, check=True,
    )


for name in sys.argv[1:] or ["plate", "diurnal"]:
    OUT.mkdir(parents=True, exist_ok=True)
    h = harness(name)
    png = OUT / f"harness-{name}.png"
    shoot(h, png)
    print("wrote", png)
