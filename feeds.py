"""Fetching + RSS/Atom parsing."""
from __future__ import annotations

import html
import re
import time
import warnings
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from models import NOW, Item

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
session = requests.Session()
session.headers.update({"User-Agent": BROWSER_UA,
                        "Accept": "application/rss+xml, application/xml, text/xml, application/json, text/html, */*"})
adapter = requests.adapters.HTTPAdapter(pool_connections=40, pool_maxsize=40)
session.mount("https://", adapter)


def fetch(url: str, retries: int = 2, timeout: int = 25, max_wait: float = 8) -> bytes | None:
    for attempt in range(retries + 1):
        try:
            r = session.get(url, timeout=timeout)
            if r.status_code == 200 and r.content:
                return r.content
            if r.status_code in (429, 503, 502):
                try:
                    wait = float(r.headers.get("Retry-After") or 0)
                except ValueError:
                    wait = 0
                if wait > max_wait:
                    return None  # don't stall the whole run on one throttled host
                time.sleep(wait or (2 + attempt * 3))
                continue
            return None
        except requests.RequestException:
            time.sleep(1 + attempt)
    return None


def fetch_head(url: str, max_bytes: int = 60000) -> str | None:
    """Fetch only the first chunk of a page (enough for <title>/<meta>)."""
    try:
        with session.get(url, timeout=20, stream=True) as r:
            if r.status_code != 200:
                return None
            buf = b""
            for chunk in r.iter_content(8192):
                buf += chunk
                if len(buf) >= max_bytes or b"</title>" in buf:
                    break
            return buf.decode("utf-8", errors="replace")
    except requests.RequestException:
        return None


def clean_text(s: str, limit: int = 400) -> str:
    if not s:
        return ""
    txt = BeautifulSoup(s, "lxml").get_text(" ", strip=True) if "<" in s else s
    txt = html.unescape(re.sub(r"\s+", " ", txt)).strip()
    txt = re.sub(r"\[/?(?:LIST|\*|B|I|URL[^\]]*)\]", " ", txt)  # Slickdeals BBCode
    txt = re.sub(r"\s+", " ", txt).strip()
    return (txt[: limit - 1] + "…") if len(txt) > limit else txt


def parse_date(s: str) -> datetime | None:
    if not s:
        return None
    s = s.strip()
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        try:
            d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d


def normalize_link(url: str) -> str:
    try:
        p = urlsplit(url)
        q = [(k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(("utm_", "iref", "ref"))]
        return urlunsplit((p.scheme, p.netloc.lower().removeprefix("www."), p.path.rstrip("/"), urlencode(q), ""))
    except ValueError:
        return url


def first_img(htmlish: str) -> str:
    m = re.search(r"""<img[^>]+src=["']([^"']+)["']""", htmlish or "", re.I)
    if m and not m.group(1).endswith(".gif") and "pixel" not in m.group(1):
        return html.unescape(m.group(1))
    return ""


def _child_text(node, *names) -> str:
    for n in names:
        el = node.find(n)
        if el is not None and el.get_text().strip():
            return el.get_text()
    return ""


SD_THREAD = re.compile(r"slickdeals\.net/f/(\d+)")


def parse_feed(content: bytes, source: str, kind: str, boost: float) -> list[Item]:
    soup = BeautifulSoup(content, "xml")
    entries = soup.find_all("item") or soup.find_all("entry")
    out: list[Item] = []
    for e in entries:
        title = clean_text(_child_text(e, "title"), 300)
        if not title:
            continue
        link = _child_text(e, "link")
        if not link:
            l = e.find("link")
            link = l.get("href", "") if l is not None else ""
        link = link.strip()
        encoded = _child_text(e, "encoded", "content")
        desc_raw = _child_text(e, "description", "summary")
        pub = parse_date(_child_text(e, "pubDate", "published", "updated", "date"))
        tags = [c.get_text(strip=True) or c.get("term", "") for c in e.find_all("category")]
        tags = [t for t in tags if t]

        image = ""
        el = e.find("thumbnail-image")
        if el is not None and el.get_text(strip=True):
            image = el.get_text(strip=True)
        if not image:
            for el in e.find_all(["content", "thumbnail"]):
                if el.get("url") and (el.get("medium") in (None, "image") or el.name == "thumbnail"):
                    image = el["url"]
                    break
        if not image:
            enc = e.find("enclosure")
            if enc is not None and "image" in (enc.get("type") or ""):
                image = enc.get("url", "")
        if not image:
            image = first_img(encoded) or first_img(desc_raw)

        it = Item(title=title, link=link, source=source, kind=kind, boost=boost,
                  summary=clean_text(desc_raw or encoded, 420), image=image, feed_tags=tags[:12])
        if pub:
            it.published = pub.isoformat()
            it.age_days = max(0.0, (NOW - pub).total_seconds() / 86400)
        m = SD_THREAD.search(link)
        if m:
            it.thread_id = m.group(1)
        m = re.search(r"Thumb Score:\s*([+-]?\d+)", encoded or "")
        if m:
            it.votes = int(m.group(1))
        r_el = e.find("retailer")
        if r_el is not None:
            it.store = r_el.get_text(strip=True)
        p_el = e.find("price")
        if p_el is not None:
            try:
                it.price = float(p_el.get_text(strip=True)) or None
            except ValueError:
                pass
        sp = e.find("staffPick")
        if sp is not None and sp.get_text(strip=True).lower() == "true":
            it.staff_pick = True
        ex = e.find("expires")
        if ex is not None and ex.get_text(strip=True):
            it.expires = ex.get_text(strip=True)
        for c in e.find_all("comments"):
            t = c.get_text(strip=True)
            if t.isdigit():
                it.comments = int(t)
        out.append(it)
    return out
