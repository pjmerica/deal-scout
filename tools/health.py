#!/usr/bin/env python3
"""
Site health check (runs as the last CI step, even when earlier steps failed).

Reads the fresh site/deals.json and the CI step outcomes, and decides whether a human needs
to look. With --issue (in CI) it keeps ONE GitHub issue titled "Site health: needs attention":
  - opens it when something is wrong (GitHub then emails the repo owner),
  - updates it (and comments) when the list of problems changes,
  - closes it with a comment when everything passes again.
Locally: `python tools/health.py` just prints the report.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SITE = Path(__file__).resolve().parents[1] / "site"
TITLE = "Site health: needs attention"

# Thresholds: well below a normal run (~2,400 deals, ~1,350 clothing, 81 brand stores, ~220/223 sources)
MIN_SOURCE_SHARE = 0.85
MIN_BRAND_STORES = 60
MIN_DEALS = 1000
MIN_CLOTHING = 400
CRITICAL_SOURCES = ["Slickdeals Frontpage", "Slickdeals Popular", "DealNews", "DealNews Clothing", "Hip2Save"]


def check() -> tuple[list[str], list[str]]:
    problems, notes = [], []
    for step in ("TESTS", "SCRAPE", "SMOKE"):
        outcome = os.environ.get(f"{step}_OUTCOME", "")
        if outcome and outcome != "success":
            problems.append(f"CI step **{step.lower()}** {outcome}")
    path = SITE / "deals.json"
    if not path.exists():
        problems.append("`site/deals.json` was not produced (the scrape crashed before writing output)")
        return problems, notes
    d = json.loads(path.read_text(encoding="utf-8"))
    c = d["counts"]
    # Reddit stays off until API keys are added, so it never counts against health
    srcs = [s for s in d["sources"] if not s["name"].startswith("Reddit (needs")]
    ok = sum(1 for s in srcs if s["ok"])
    if ok < MIN_SOURCE_SHARE * len(srcs):
        down = [s["name"] for s in srcs if not s["ok"]][:15]
        problems.append(f"Only {ok}/{len(srcs)} sources online. Down: {', '.join(down)}")
    scanned = sum(1 for s in d.get("brand_sales", []) if s.get("scanned"))
    if scanned < MIN_BRAND_STORES:
        problems.append(f"Only {scanned}/81 brand stores readable (Shopify throttling or a store change)")
    if c["deals"] < MIN_DEALS:
        problems.append(f"Only {c['deals']} deals ranked (normally ~2,400)")
    if c["clothing"] < MIN_CLOTHING:
        problems.append(f"Only {c['clothing']} clothing deals (normally ~1,300)")
    by_name = {s["name"]: s for s in d["sources"]}
    for name in CRITICAL_SOURCES:
        s = by_name.get(name)
        if not s or not s["ok"] or not s["count"]:
            problems.append(f"Critical source **{name}** returned nothing")
    if not c.get("runs_tracked"):
        notes.append("History was reset (the previous history.json couldn't be loaded); NEW/price signals restart.")
    if not c.get("stack_stores"):
        notes.append("Card Scout stack data unavailable this run (no Rakuten/card-offer badges).")
    return problems, notes


def render(problems: list[str], notes: list[str]) -> str:
    repo, run = os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_RUN_ID", "")
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    sig = hashlib.sha1("\n".join(sorted(problems)).encode()).hexdigest()[:12]
    lines = [f"Automatic check from the site build ({when}). This issue closes itself when the next build passes.", ""]
    if run:
        lines += [f"Run: https://github.com/{repo}/actions/runs/{run}", ""]
    lines += ["### Problems"] + [f"- {p}" for p in problems]
    if notes:
        lines += ["", "### Notes"] + [f"- {n}" for n in notes]
    lines += ["", "What usually fixes it: a source changed its page or feed (update the parser in the repo), or a "
              "temporary block/throttle (wait for the next run). The live site keeps its last good version "
              "whenever tests fail.", "", f"<!-- health-sig: {sig} -->"]
    return "\n".join(lines)


def gh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def sync_issue(problems: list[str], notes: list[str]) -> None:
    repo = os.environ["GITHUB_REPOSITORY"]
    r = gh("issue", "list", "--repo", repo, "--state", "open", "--search", f'"{TITLE}" in:title',
           "--json", "number,title,body")
    issues = [i for i in json.loads(r.stdout or "[]") if i["title"] == TITLE]
    body = render(problems, notes)
    if problems:
        if not issues:
            out = gh("issue", "create", "--repo", repo, "--title", TITLE, "--body", body)
            print("opened issue:", out.stdout.strip() or out.stderr.strip())
            return
        num, old = issues[0]["number"], issues[0]["body"] or ""
        new_sig = body.rsplit("health-sig: ", 1)[-1]
        changed = ("health-sig: " + new_sig) not in old
        gh("issue", "edit", str(num), "--repo", repo, "--body", body)
        if changed:
            gh("issue", "comment", str(num), "--repo", repo, "--body",
               "The problem list changed:\n\n" + "\n".join(f"- {p}" for p in problems))
        print(f"updated issue #{num} (changed={changed})")
    else:
        for i in issues:
            gh("issue", "close", str(i["number"]), "--repo", repo, "--comment",
               f"All checks pass again ({datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}). Closing automatically.")
            print(f"closed issue #{i['number']}")


def main() -> int:
    problems, notes = check()
    print("HEALTH:", "needs attention" if problems else "OK")
    for p in problems:
        print("  problem:", p)
    for n in notes:
        print("  note:", n)
    if "--issue" in sys.argv:
        try:
            sync_issue(problems, notes)
        except Exception as ex:  # noqa: BLE001 - never fail the build because of the issue sync
            print("issue sync failed:", ex)
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write("### Site health: " + ("needs attention" if problems else "OK") + "\n")
            f.writelines(f"- {p}\n" for p in problems + notes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
