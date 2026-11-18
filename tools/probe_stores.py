#!/usr/bin/env python3
"""
Check candidate Shopify stores before adding them to brands.SHOPIFY_STORES.

Run it from CI (`gh workflow run probe.yml`): Shopify rate-limits by IP across all its stores, so a
PC that just ran the scraper gets HTTP 429 from every store, even ones it never touched.

For each "Name | domain | audience" line in tools/store_candidates.txt (or domains given as
arguments) it reports whether /products.json is open, how many items in the first page are on
sale and in stock, and which sale collection the scanner would pick. Output goes to stdout and,
in CI, to the job summary as a table plus ready-to-paste SHOPIFY_STORES lines.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import shopify  # noqa: E402
from feeds import session  # noqa: E402

HERE = Path(__file__).resolve().parent


def load(args: list[str]) -> list[tuple[str, str, str]]:
    if args:
        return [(d, d, "Everyone") for d in args]
    out = []
    for line in (HERE / "store_candidates.txt").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            name, domain, aud = [x.strip() for x in line.split("|")]
            out.append((name, domain, aud))
    return out


def probe(c: tuple[str, str, str]) -> dict:
    name, domain, aud = c
    row = {"name": name, "domain": domain, "audience": aud, "status": "", "products": 0, "on_sale": 0, "handles": ""}
    try:
        r = session.get(f"https://{domain}/products.json?limit=250", timeout=20)
        if r.status_code != 200 or not r.text.lstrip().startswith("{"):
            row["status"] = f"closed ({r.status_code})"
            return row
        prods = r.json().get("products", [])
        row["products"] = len(prods)
        for p in prods:
            if shopify._product_item(name, domain, p):
                row["on_sale"] += 1
        row["handles"] = ", ".join(shopify.pick_sale_handles(domain)) or "-"
        row["status"] = "OPEN" if prods else "open but empty"
    except Exception as ex:  # noqa: BLE001
        row["status"] = f"error {type(ex).__name__}"
    return row


def main() -> int:
    cands = load(sys.argv[1:])
    rows = []
    with cf.ThreadPoolExecutor(max_workers=4) as ex:  # gentle: 4 at a time
        for row in ex.map(probe, cands):
            rows.append(row)
            print(f"{row['status']:16} {row['domain']:28} products={row['products']:3} on_sale={row['on_sale']:3} sale={row['handles']}")
            time.sleep(0.2)
    good = [r for r in rows if r["status"] == "OPEN"]
    print(f"\n{len(good)}/{len(rows)} open")
    lines = ["| Store | Domain | Status | Products | On sale (page 1) | Sale collections |", "|---|---|---|---|---|---|"]
    lines += [f"| {r['name']} | {r['domain']} | {r['status']} | {r['products']} | {r['on_sale']} | {r['handles']} |" for r in rows]
    paste = [f'    "{r["name"]}": "{r["domain"]}",' for r in good]
    (HERE.parent / "probe_results.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    if "GITHUB_STEP_SUMMARY" in os.environ:
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(f"### Store probe: {len(good)}/{len(rows)} open\n\n" + "\n".join(lines) +
                    "\n\n```python\n" + "\n".join(paste) + "\n```\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
