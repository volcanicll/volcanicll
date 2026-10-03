#!/usr/bin/env python3
"""Guards for the generated survey fragments.

Run directly (`python3 scripts/test_gen_assets.py`) — the repo has no test
runner and this stays stdlib-only. CI runs it in the guard job.

The bug these exist for: `sleep_run` returned the first *busy* hour as the end
of the empty run, and the caption rendered it as a closed range. The page then
claimed 04:00–08:00 was empty while the 08:00 bar stood at 8 commits. Both the
off-by-one and the fact that the prose was hand-written outside the generated
span let it ship.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import gen_assets  # noqa: E402


def check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}{'' if ok else ' — ' + detail}")
    return ok


def main() -> int:
    readings = json.loads((ROOT / "readings.json").read_text())
    hours = readings["hours"]
    readme = (ROOT / "README.md").read_text()
    passed = True

    # The gap must name empty hours only, and both ends must be empty.
    gap = gen_assets.sleep_run(hours)
    passed &= check("a sleep gap is found", gap is not None)
    if gap:
        lo, hi = gap
        passed &= check(
            f"the gap {lo:02d}:00-{hi:02d}:00 is entirely empty",
            all(hours[h] == 0 for h in range(lo, hi + 1)),
            f"hours {[(h, hours[h]) for h in range(lo, hi + 1)]}",
        )
        # The hour after the run must be busy, or the run was cut short.
        nxt = (hi + 1) % 24
        passed &= check(
            f"{nxt:02d}:00 (the hour after the gap) is busy",
            hours[nxt] > 0,
            f"got {hours[nxt]}",
        )

    # Every hour the README names as empty must actually be empty. This is the
    # assertion that would have caught the shipped bug.
    for m in re.finditer(r"(\d{2}):00[–-](\d{2}):00 is empty", readme):
        lo, hi = int(m.group(1)), int(m.group(2))
        bad = [h for h in range(lo, hi + 1) if hours[h] != 0]
        passed &= check(
            f"README's '{lo:02d}:00-{hi:02d}:00 is empty' is true",
            not bad,
            f"but {[(h, hours[h]) for h in bad]} have commits",
        )

    # Same for the alt text, which uses the other separator.
    for m in re.finditer(r"empty between (\d{2}):00 and (\d{2}):00", readme):
        lo, hi = int(m.group(1)), int(m.group(2))
        bad = [h for h in range(lo, hi + 1) if hours[h] != 0]
        passed &= check(
            f"alt text's 'empty between {lo:02d}:00 and {hi:02d}:00' is true",
            not bad,
            f"but {[(h, hours[h]) for h in bad]} have commits",
        )

    # The peak named in prose must be the real peak.
    peak, peak_hour = max(hours), hours.index(max(hours))
    passed &= check(
        f"the README's peak ({peak} at {peak_hour:02d}:00) is the real peak",
        f"peaking at {peak} commit" in readme and f"at {peak_hour:02d}:00" in readme,
    )

    # The ratio claim must hold at the stated precision.
    late = hours[22] + hours[23]
    if late:
        ratio = readings["total"] / late
        passed &= check(
            f"'one in {round(ratio)}' matches {readings['total']}/{late} = 1 in {ratio:.2f}",
            abs(ratio - round(ratio)) < 0.5,
        )

    print("\n" + ("all checks passed" if passed else "FAILURES above"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
