"""
When does a deal end? Read it from the deal's own words.

Feeds rarely say (DealNews's <expires> field is the only structured one), but posts often do:
"Ends 12/1", "valid through December 20", "Deals of the Day 11/22-11/27", "Today only",
"Through 4:59 pm ET today", "ends Cyber Monday", "tentree: Cyber Monday Ends Dec 1".

find_end(text, posted) returns the end of that day in US Eastern time (as a UTC datetime), or None.
Words like "today" and "Sunday" count from the day the deal was POSTED, not from now, so a
"today only" post from yesterday has ended. Shipping cutoffs ("order by 12/20") are not deal ends:
"by" and "before" are not end words. A date more than a day before posting or more than 75 days
after it is ignored (it's a size, a fraction or another year's sale).
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

ET = timezone(timedelta(hours=-5))  # US Eastern Standard Time; deal end dates are US dates (Nov-Mar)
MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

# whole month words only ("Decor 3-5" is not December 5)
MON = (r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|"
       r"oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\.?")
DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
NUM = r"(\d{1,2})/(\d{1,2})(?:/(\d{2}|\d{4}))?"
END_WORD = (r"(?:ends?|ending|expires?|exp\.|valid (?:thru|through|until|till)|good (?:thru|through|until)|"
            r"through|thru|until|till|til|lasts until|runs through|runs until)")
GAP = r"\s+(?:(?:on|at|the|midnight|11:59\s*pm|[a-z]{2,9}day,?)\s+){0,3}"  # "ends at midnight on Monday, Dec 1"

RANGE_NUM = re.compile(r"\b" + NUM + r"\s*(?:-|–|—|to|thru|through)\s*" + NUM + r"\b", re.I)
RANGE_MON = re.compile(r"\b" + MON + r"\s*" + DAY + r"\s*(?:-|–|—|to|thru|through)\s*(?:" + MON + r"\s*)?" + DAY + r"\b", re.I)
END_NUM = re.compile(r"\b" + END_WORD + GAP + NUM + r"\b", re.I)
END_MON = re.compile(r"\b" + END_WORD + GAP + MON + r"\s*" + DAY + r"\b", re.I)
# "Ends 11.30" (CorePower Yoga, 2026-11-26): dotted month.day, only right after an end word, never "$11.30" or "11.30%"
END_DOT = re.compile(r"\b" + END_WORD + GAP + r"(1[0-2]|0?[1-9])\.([0-3]?\d)\b(?![.,]?\d|\s?%)", re.I)
ONLY_NUM = re.compile(r"\b" + NUM + r"\s+only\b", re.I)
# not "last day" alone: "+ Last Day for FREE Shipping" is about shipping, the sale ran three more days
TODAY = re.compile(r"\btoday only\b|\bone[- ]day only\b|\b24[- ]hours? only\b|\bends tonight\b|\btonight only\b|"
                   r"\bone last day\b|\bfinal hours\b|"
                   r"\b" + END_WORD + r"\s+(?:\S+\s+){0,4}?(?:today|tonight)\b", re.I)
IN_N = re.compile(r"\bends? in (\d{1,2}) (hours?|days?)\b", re.I)
# Days and holidays need a firm end word: "you don't need to wait until Black Friday" is not an end date.
FIRM = r"(?:ends?|ending|expires?|valid (?:thru|through)|good (?:thru|through)|through|thru|runs through)"
TOMORROW = re.compile(r"\b" + FIRM + r"\s+(?:\S+\s+){0,3}?tomorrow\b", re.I)
END_WEEKDAY = re.compile(r"\b" + FIRM + r"\s+(?:this\s+|at midnight\s+|midnight\s+)?(" + "|".join(WEEKDAYS) + r")\b(?!,?\s*" + MON + ")", re.I)
END_EVENT = re.compile(r"\b" + FIRM + r"\s+(?:the\s+end\s+of\s+|end\s+of\s+)?(black friday|cyber monday|thanksgiving)\b", re.I)


def thanksgiving(year: int) -> datetime:
    nov1 = datetime(year, 11, 1)
    return nov1 + timedelta(days=(3 - nov1.weekday()) % 7 + 21)  # fourth Thursday


def _eod(y: int, m: int, d: int) -> datetime | None:
    try:
        return datetime(y, m, d, 23, 59, tzinfo=ET).astimezone(timezone.utc)
    except ValueError:
        return None


def _date(posted: datetime, month: int, day: int, year: str | None = None) -> datetime | None:
    p = posted.astimezone(ET)
    y = (2000 + int(year) if len(year) == 2 else int(year)) if year else p.year
    d = _eod(y, month, day)
    if d and not year and d < posted - timedelta(days=30):
        d = _eod(y + 1, month, day)  # "ends 1/5" posted in December
    if d is None or d < posted - timedelta(days=1) or d > posted + timedelta(days=75):
        return None
    return d


def _mon(s: str) -> int:
    return MONTHS[s.lower()[:3]]


def find_end(title: str, posted: datetime, summary: str = "") -> datetime | None:
    """The title's end date if it states one, else the summary's. Summaries of daily-deal threads list
    earlier deals with their own dates ("Target Deals of the Day 11/22-11/27 ... Expires Nov 22")."""
    return _scan(title, posted) or _scan(summary, posted)


def _scan(text: str, posted: datetime) -> datetime | None:
    if not text:
        return None
    p = posted.astimezone(ET)
    found = []
    for m in RANGE_NUM.finditer(text):
        found.append(_date(posted, int(m.group(4)), int(m.group(5)), m.group(6)))
    for m in RANGE_MON.finditer(text):
        found.append(_date(posted, _mon(m.group(3) or m.group(1)), int(m.group(4))))
    for m in END_NUM.finditer(text):
        found.append(_date(posted, int(m.group(1)), int(m.group(2)), m.group(3)))
    for m in END_MON.finditer(text):
        found.append(_date(posted, _mon(m.group(1)), int(m.group(2))))
    for m in ONLY_NUM.finditer(text):
        found.append(_date(posted, int(m.group(1)), int(m.group(2)), m.group(3)))
    for m in END_DOT.finditer(text):
        found.append(_date(posted, int(m.group(1)), int(m.group(2))))
    dated = [d for d in found if d]
    if dated:
        # A stated date beats relative words: "Through November 29th ... free shipping ends today" is a Nov 29 sale
        return min(dated)  # the earliest stated end is the one that bites
    for m in END_EVENT.finditer(text):
        tg = thanksgiving(p.year)
        day = tg + timedelta(days={"thanksgiving": 0, "black friday": 1, "cyber monday": 4}[m.group(1).lower()])
        found.append(_date(posted, day.month, day.day))
    for m in END_WEEKDAY.finditer(text):
        ahead = (WEEKDAYS.index(m.group(1).lower()) - p.weekday()) % 7
        day = p + timedelta(days=ahead)
        found.append(_date(posted, day.month, day.day))
    for m in IN_N.finditer(text):
        n = int(m.group(1))
        day = p + (timedelta(hours=n) if m.group(2).lower().startswith("hour") else timedelta(days=n))
        found.append(_date(posted, day.month, day.day))
    if TOMORROW.search(text):
        day = p + timedelta(days=1)
        found.append(_date(posted, day.month, day.day))
    if TODAY.search(text):
        found.append(_date(posted, p.month, p.day))
    found = [d for d in found if d]
    return min(found) if found else None
