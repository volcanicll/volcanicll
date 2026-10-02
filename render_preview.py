#!/usr/bin/env python3
"""Render the profile README the way GitHub does, for previewing.

Uses pandoc's GFM reader rather than python-markdown: pandoc mirrors GitHub's
handling of markdown inside raw HTML blocks, which python-markdown's
md_in_html does not — it silently drops the content.

Then wraps the result in GitHub's article container (1012px sheet, 832px
content column) and screenshot the whole page with Chrome, trimmed of the
trailing background. Both palettes are rendered, since the assets are
light/dark pairs selected by prefers-color-scheme.

Pass `--html` to only write the HTML, `--png` to only screenshot.
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
OUT = pathlib.Path(tempfile.gettempdir()) / "profile-preview"
CHROME = os.environ.get(
    "CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
SCALE = 2

THEME = {
    "light": dict(bg="#ffffff", fg="#1f2328", sub="#f6f8fa", border="#d1d9e0"),
    "dark": dict(bg="#0d1117", fg="#e6edf3", sub="#151b23", border="#3d444d"),
}


def to_body(mode: str) -> str:
    src = re.sub(r"assets/([a-z-]+)-(?:light|dark)\.svg", rf"assets/\1-{mode}.svg",
                 (ROOT / "README.md").read_text())
    body = subprocess.run(["pandoc", "-f", "gfm", "-t", "html5"],
                          input=src, capture_output=True, text=True, check=True).stdout
    return re.sub(r'((?:src|srcset)=")assets/', rf"\g<1>{ASSETS.as_uri()}/", body)


def page(mode: str) -> str:
    t = THEME[mode]
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><style>
  * {{ box-sizing: border-box; }}
  body {{ margin:0; background:{t['bg']}; color:{t['fg']};
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans",Helvetica,Arial,sans-serif;
         font-size:16px; line-height:1.5; }}
  .sheet {{ max-width:1012px; margin:0 auto; padding:24px 45px 32px; }}
  .sheet > * {{ max-width:832px; margin-left:auto; margin-right:auto; }}
  h1 {{ font-size:2em; font-weight:600; margin:0 0 16px; padding-bottom:.3em;
        border-bottom:1px solid {t['border']}; }}
  h2 {{ font-size:1.5em; font-weight:600; margin:24px 0 16px; padding-bottom:.3em;
        border-bottom:1px solid {t['border']}; }}
  p {{ margin:0 0 16px; }}
  img {{ max-width:100%; height:auto; }}
  a {{ color:{'#0969da' if mode == 'light' else '#4493f8'}; text-decoration:none; }}
  sub {{ font-size:12px; }}
  div[align=center] {{ text-align:center; }}
</style></head><body><div class="sheet">
{to_body(mode)}
</div></body></html>"""


def trim(png: pathlib.Path) -> None:
    """Cut the trailing page background so the shot ends where the content does."""
    from PIL import Image
    im = Image.open(png).convert("RGB")
    w, h = im.size
    bg = im.getpixel((2, 2))
    px = im.load()
    last = 0
    for y in range(h - 1, -1, -1):
        if any(px[x, y] != bg for x in range(0, w, 7)):
            last = y
            break
    im.crop((0, 0, w, min(h, last + 40))).save(png)
    print(f"  {png.name}: {w}x{last + 40}")


def main() -> None:
    only = {a.lstrip("-") for a in sys.argv[1:]}
    OUT.mkdir(parents=True, exist_ok=True)
    for mode in ("light", "dark"):
        html = OUT / f"readme-{mode}.html"
        html.write_text(page(mode))
        print("wrote", html)
        if only and "png" not in only:
            continue
        png = OUT / f"readme-{mode}.png"
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
             f"--force-device-scale-factor={SCALE}", f"--screenshot={png}",
             "--window-size=1100,2600", html.as_uri()],
            capture_output=True, check=True,
        )
        trim(png)


main()
