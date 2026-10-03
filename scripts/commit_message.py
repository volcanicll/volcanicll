#!/usr/bin/env python3
"""Build the scheduled-refresh commit message from the readings diff.

The daily job commits only when a reading moved, and the message should say
what moved — a history of "update assets" commits is noise, while one that
reads "+3 commits, busiest hour 12:00 → 09:00" is a log of surveys. The
previous readings come from HEAD's readings.json, the fresh ones from the
working tree, so the message describes exactly the diff being committed.

Prints the message on stdout; meant for `git commit -m "$(...)"`.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent   # the repo, not scripts/
READINGS = ROOT / "readings.json"

COUNTS = (
    ("total", "commit", "commits"),
    ("active_days", "active day", "active days"),
    ("repos", "repo", "repos"),
)


def head_readings() -> dict | None:
    """readings.json as of HEAD — None when the file is being added."""
    p = subprocess.run(["git", "show", "HEAD:readings.json"],
                       capture_output=True, text=True, cwd=ROOT)
    return json.loads(p.stdout) if p.returncode == 0 else None


def main() -> None:
    new = json.loads(READINGS.read_text())
    old = head_readings()
    if not old:
        print("Add the survey readings record\n\n"
              "measure.py now writes readings.json and gen_assets.py draws from\n"
              "it; this file is the record the scheduled refresh updates.")
        return

    parts = []
    for key, one, many in COUNTS:
        d = new[key] - old[key]
        if d:
            parts.append(f"{'+' if d > 0 else '-'}{abs(d)} {one if abs(d) == 1 else many}")

    peak_moved = (new["peak"], new["peak_hour"]) != (old["peak"], old["peak_hour"])
    if parts:
        subject = "Survey refresh: " + ", ".join(parts)
    elif peak_moved:
        subject = f"Survey refresh: busiest hour {old['peak_hour']:02d}:00 → {new['peak_hour']:02d}:00"
    elif new["hours"] != old["hours"]:
        # same totals, but commits landed in different hours — the trace moved
        subject = "Survey refresh: same totals, the day's shape moved"
    else:
        subject = "Survey refresh: readings re-measured, nothing moved"

    body = ("Scheduled re-survey of the trailing twelve months; the plate, the\n"
            "diurnal trace and the README's generated readings are redrawn from\n"
            "readings.json.")
    if peak_moved:
        body += (f"\n\nThe busiest hour moved from {old['peak_hour']:02d}:00 ({old['peak']} commits) "
                 f"to {new['peak_hour']:02d}:00 ({new['peak']}).")
    print(subject + "\n\n" + body)


if __name__ == "__main__":
    sys.exit(main())
