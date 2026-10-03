#!/usr/bin/env python3
"""Measure the profile's readings from the GitHub API and write readings.json.

Query, verbatim:

    gh api 'search/commits?q=author:volcanicll+committer-date:>YYYY-MM-DD' \
      --paginate --per_page=100

Timestamps come back UTC; the readings are bucketed in local time (CST,
UTC+8), which is the whole point of the diurnal trace — an hour axis in UTC
would put the evening spike at lunchtime. The window starts 365 days before
today in that same local time, so a local run and a CI run agree.

readings.json is the only thing this script writes; the drawing lives in
gen_assets.py, which stays a pure function of that file. The readings being
replaced are kept under "previous" — that is what lets the README say how the
survey moved. A run whose readings match the file's leaves readings.json
untouched: a daily commit that says "no change" is noise.

Note that GitHub's commit search only indexes default branches, and lags
fresh commits slightly, so two runs hours apart can disagree by a commit or
two. That is search catching up, not this script drifting.
"""
import datetime
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
READINGS = ROOT / "readings.json"
AUTHOR = "volcanicll"
LOCAL = datetime.timezone(datetime.timedelta(hours=8))

# The readings that are drawn; a change in any of these is worth a commit.
WATCHED = ("total", "active_days", "repos", "hours")
# What a "previous" survey keeps: everything measured, none of the provenance.
SNAPSHOT = ("measured_at", "total", "active_days", "repos", "hours", "peak", "peak_hour")


def gh_api(path: str) -> dict:
    out = subprocess.run(
        ["gh", "api", path, "--paginate"],
        capture_output=True, text=True, check=True,
    ).stdout
    dec = json.JSONDecoder()
    merged = {"items": []}
    i = 0
    while i < len(out):
        while i < len(out) and out[i] in " \n\r\t":
            i += 1
        if i >= len(out):
            break
        obj, j = dec.raw_decode(out, i)
        i = j
        merged["items"].extend(obj.get("items", []))
    return merged


def measure() -> dict:
    today = datetime.datetime.now(LOCAL).date()
    since = (today - datetime.timedelta(days=365)).isoformat()
    data = gh_api(f"search/commits?q=author:{AUTHOR}+committer-date:>{since}&per_page=100")

    total = 0
    days: set[str] = set()
    repos: set[str] = set()
    hours = [0] * 24
    for it in data["items"]:
        total += 1
        stamp = it["commit"]["committer"]["date"]
        repos.add(it["repository"]["full_name"])
        dt = datetime.datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        loc = dt.astimezone(LOCAL)
        days.add(loc.date().isoformat())
        hours[loc.hour] += 1

    return {
        "measured_at": datetime.datetime.now(LOCAL).isoformat(timespec="seconds"),
        "since": since,
        "total": total,
        "active_days": len(days),
        "repos": len(repos),
        "hours": hours,
        "peak": max(hours),
        "peak_hour": hours.index(max(hours)),
    }


def main() -> None:
    fresh = measure()
    old = json.loads(READINGS.read_text()) if READINGS.exists() else None

    if old and all(old.get(k) == fresh[k] for k in WATCHED):
        print("readings unchanged; readings.json left alone")
        print(json.dumps(fresh, indent=2))
        return

    fresh["previous"] = {k: old.get(k) for k in SNAPSHOT} if old else None
    READINGS.write_text(json.dumps(fresh, indent=2) + "\n")
    print("readings moved; readings.json rewritten")
    print(json.dumps(fresh, indent=2))


if __name__ == "__main__":
    sys.exit(main())
