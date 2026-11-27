#!/usr/bin/env python3
"""
Keep Deal Scout (every ~3 h) and Card Scout (every ~4 h) on their refresh cadence from the owner's PC.
Set up 2026-11-27 for Deal Scout (owner: "yeah set it up"); Card Scout added the same day ("yeah do that").

GitHub's scheduler is best-effort for these repos: scheduled runs came 6-14 hours apart (Card Scout 8-13), and none
started for 4+ hours after Deal Scout's cron was made hourly. This script is run by the Windows scheduled task
"DealScout-Refresh" every 30 minutes and at logon (only while the owner is logged in; no window: pyw.exe). For each
site it starts the build workflow only when the live data is that site's max age old or older and no run of it is
already queued or running, so scrapes stay at the owner's cadence (hourly scrapes were declined). It does nothing
after END_DATE.

    py tools/pc_refresh.py --dry-run                 # say what it would do
    py tools/pc_refresh.py --max-age 0 --dry-run     # force the "start" path (dry run)
    py tools/pc_refresh.py --site "Card Scout"       # one site only

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

# max_age: just under each workflow's cadence. Deal Scout's matches scout.yml's guard (170 min).
SITES = [
    {"name": "Deal Scout", "repo": "pjmerica/deal-scout", "workflow": "scout.yml",
     "data": "https://pjmerica.github.io/deal-scout/deals.json", "max_age": 170},
    {"name": "Card Scout", "repo": "pjmerica/card-scout", "workflow": "cards.yml",
     "data": "https://pjmerica.github.io/card-scout/cards.json", "max_age": 230},
]
END_DATE = date(2027, 1, 17)   # both sites' planned end (HANDOFF §1); their workflows' guards have the same date
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


def data_age_min(url: str) -> float | None:
    """Minutes since the site's live data was generated (its first key), or None if it can't be read."""
    req = urllib.request.Request(url, headers={"Range": "bytes=0-399", "User-Agent": "deal-scout-pc-refresh"})
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


def run_pending(site: dict) -> bool:
    r = gh("run", "list", "--repo", site["repo"], "--workflow", site["workflow"], "--limit", "3", "--json", "status")
    if r.returncode != 0:
        return False
    return any(x.get("status") in ("queued", "in_progress", "waiting", "pending") for x in json.loads(r.stdout or "[]"))


def refresh(site: dict, dry_run: bool, max_age: float | None) -> int:
    name, limit = site["name"], site["max_age"] if max_age is None else max_age
    age = data_age_min(site["data"])
    if age is not None and age < limit:
        log(f"{name}: fresh, data is {age:.0f} min old, skip")
        return 0
    why = "data unreadable" if age is None else f"data is {age:.0f} min old"
    if run_pending(site):
        log(f"{name}: {why}, but a run is already queued or running: skip")
        return 0
    if dry_run:
        log(f"{name}: {why}: would start {site['workflow']} (dry run)")
        return 0
    r = gh("workflow", "run", site["workflow"], "--repo", site["repo"])
    log(f"{name}: {why}: started {site['workflow']}" if r.returncode == 0
        else f"{name}: {why}: gh failed: {(r.stderr or r.stdout).strip()[:200]}")
    return r.returncode


def main() -> int:
    # Hard stop: a run started in a brief wake and frozen by sleep stayed "Running" for hours and blocked the next
    # trigger (0x800710E0, 2026-11-27). A normal run takes a few seconds.
    watchdog = threading.Timer(120, lambda: (log("gave up after 120 s"), os._exit(1)))
    watchdog.daemon = True  # never keeps the process alive by itself
    watchdog.start()
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-age", type=float, default=None, help="override every site's max age (minutes)")
    ap.add_argument("--site", default="", help="only this site (name as in SITES)")
    a = ap.parse_args()
    if date.today() > END_DATE:
        log(f"past the planned end ({END_DATE}): nothing to do; remove the DealScout-Refresh task")
        return 0
    codes = [refresh(s, a.dry_run, a.max_age) for s in SITES if not a.site or s["name"].lower() == a.site.lower()]
    return max(codes, default=0)


if __name__ == "__main__":
    code = main()
    if sys.stdout:  # None under pyw.exe (no console): flushing it crashed and left the run hanging (2026-11-27)
        sys.stdout.flush()
    os._exit(code)
