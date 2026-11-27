#!/usr/bin/env python3
"""
Keep the site on its 3-hour refresh from the owner's PC (set up 2026-11-27, owner: "yeah set it up").

GitHub's scheduler is best-effort for this repo: scheduled runs came 6-14 hours apart, and none started for 4+ hours
after the cron was made hourly. This script is run by the Windows scheduled task "DealScout-Refresh" every 30 minutes
and at logon (only while the owner is logged in; no window: pyw.exe). It starts the "Scrape deals & deploy Pages"
workflow only when the live data is MAX_AGE_MIN old or older and no run is already queued or running, so scrapes
stay about 3 hours apart (the owner's cadence; hourly scrapes were declined). It does nothing after END_DATE.

    py tools/pc_refresh.py --dry-run          # say what it would do
    py tools/pc_refresh.py --max-age 0 --dry-run

Log: %LOCALAPPDATA%\\DealScout\\pc_refresh.log (last 300 lines). Remove the task:
    Unregister-ScheduledTask -TaskName DealScout-Refresh -Confirm:$false
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

REPO = "pjmerica/deal-scout"
WORKFLOW = "scout.yml"
DATA_URL = "https://pjmerica.github.io/deal-scout/deals.json"
END_DATE = date(2027, 1, 17)   # the site's planned end (HANDOFF §1); scout.yml's guard has the same date
MAX_AGE_MIN = 170              # same threshold as scout.yml's guard
LOG = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "DealScout" / "pc_refresh.log"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # pyw has no console; don't flash one for gh


def log(msg: str) -> None:
    line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        lines = LOG.read_text(encoding="utf-8").splitlines()[-299:] if LOG.exists() else []
        LOG.write_text("\n".join(lines + [line]) + "\n", encoding="utf-8")
    except OSError:
        pass


def data_age_min() -> float | None:
    """Minutes since the live deals.json was generated (its first key), or None if it can't be read."""
    req = urllib.request.Request(DATA_URL, headers={"Range": "bytes=0-399", "User-Agent": "deal-scout-pc-refresh"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            head = r.read(400).decode("utf-8", "replace")
    except OSError:
        return None
    m = re.search(r'"generated":\s*"([^"]+)"', head)
    if not m:
        return None
    gen = datetime.fromisoformat(m.group(1))
    return (datetime.now(timezone.utc) - gen).total_seconds() / 60


def gh(*args: str) -> subprocess.CompletedProcess:
    exe = shutil.which("gh") or r"C:\Program Files\GitHub CLI\gh.exe"
    return subprocess.run([exe, *args], capture_output=True, text=True, timeout=60, creationflags=NO_WINDOW)


def run_pending() -> bool:
    r = gh("run", "list", "--repo", REPO, "--workflow", WORKFLOW, "--limit", "3", "--json", "status")
    if r.returncode != 0:
        return False
    return any(x.get("status") in ("queued", "in_progress", "waiting", "pending") for x in json.loads(r.stdout or "[]"))


def main() -> int:
    # Hard stop: a run started in a brief wake and frozen by sleep stayed "Running" for hours and blocked the next
    # trigger (0x800710E0, 2026-11-27). A normal run takes a few seconds.
    threading.Timer(120, lambda: (log("gave up after 120 s"), os._exit(1))).start()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-age", type=float, default=MAX_AGE_MIN)
    a = ap.parse_args()
    if date.today() > END_DATE:
        log(f"past the planned end ({END_DATE}): nothing to do; remove the DealScout-Refresh task")
        return 0
    age = data_age_min()
    if age is not None and age < a.max_age:
        log(f"fresh: data is {age:.0f} min old, skip")
        return 0
    if run_pending():
        log(f"data {'unreadable' if age is None else f'{age:.0f} min old'}, but a run is already queued or running: skip")
        return 0
    why = "data unreadable" if age is None else f"data is {age:.0f} min old"
    if a.dry_run:
        log(f"{why}: would start {WORKFLOW} (dry run)")
        return 0
    r = gh("workflow", "run", WORKFLOW, "--repo", REPO)
    log(f"{why}: started {WORKFLOW}" if r.returncode == 0 else f"{why}: gh failed: {(r.stderr or r.stdout).strip()[:200]}")
    return r.returncode


if __name__ == "__main__":
    code = main()
    sys.stdout.flush()
    os._exit(code)  # don't wait for the watchdog timer
