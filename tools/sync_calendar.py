#!/usr/bin/env python3
"""Turn the Google Calendar into calendar.json for the NetWorth Routine rail.

Two ways in, because the useful one depends on what's authenticated:

  --events FILE   a Google Calendar API "events" payload (what the connected
                  calendar tool returns). Used by the scheduled sync.
  --ics URL       a Google Calendar "Secret address in iCal format" feed.
                  No OAuth, no API project — works from cron on its own.
                  Put the URL in ~/.config/networth-routine/calendar.conf
                  as  ICS_URL=https://calendar.google.com/calendar/ical/...
                  and it will be picked up automatically.

Output is calendar.json in the app folder. That file is git-ignored on purpose:
it carries client names and live Google Meet join links.
"""
import argparse, json, os, re, sys, urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "calendar.json")
CONF = os.path.expanduser("~/.config/networth-routine/calendar.conf")
TZ   = timezone(timedelta(hours=9, minutes=30))     # Australia/Adelaide
SELF = "admin@networth-digital.com"

# Booking types, most specific first — "Proposal/Strategy Call" must not be
# caught by a looser rule, and onboarding must beat the generic meeting test.
TYPE_RULES = [
    ("onboarding", re.compile(r"\bonboard", re.I)),
    ("proposal",   re.compile(r"proposal|strategy", re.I)),
    ("intro",      re.compile(r"\bintro\b|discovery", re.I)),
]

def classify(summary, has_guests, has_conference):
    for name, rx in TYPE_RULES:
        if rx.search(summary or ""):
            return name
    # Anything else with an external guest and a video link is still a booking.
    if has_guests and has_conference:
        return "meeting"
    return "other"

def clean_title(summary):
    """'NetWorth Digital – Intro Call with Lewis ' -> 'Intro Call with Lewis'."""
    s = (summary or "Untitled").strip()
    s = re.sub(r"^NetWorth Digital\s*[–—-]\s*", "", s)
    return re.sub(r"\s+", " ", s).strip()

# ---------------------------------------------------------------- sources
def from_events_payload(path):
    data = json.load(open(path))
    out = []
    for ev in data.get("events", []):
        if ev.get("status") == "cancelled":
            continue
        start, end = ev.get("start", {}), ev.get("end", {})
        if "dateTime" not in start:
            continue                                   # all-day: not a time block
        s = datetime.fromisoformat(start["dateTime"]).astimezone(TZ)
        e = datetime.fromisoformat(end["dateTime"]).astimezone(TZ)
        guests = [a for a in ev.get("attendees", []) if not a.get("self")]
        # A guest who said no isn't taking up your day.
        if guests and all(a.get("responseStatus") == "declined" for a in guests):
            continue
        link = ev.get("conferenceUrl") or (
            ev.get("location") if str(ev.get("location", "")).startswith("http") else None)
        out.append({
            "date":  s.strftime("%Y-%m-%d"),
            "start": s.strftime("%H:%M"),
            "end":   e.strftime("%H:%M"),
            "mins":  int((e - s).total_seconds() // 60),
            "title": clean_title(ev.get("summary")),
            "type":  classify(ev.get("summary"), bool(guests), bool(link)),
            "link":  link,
        })
    return out

def unfold(text):
    """iCal folds long lines with a leading space; join them back up."""
    return re.sub(r"\r?\n[ \t]", "", text)

def ics_dt(val):
    val = val.strip()
    if val.endswith("Z"):
        return datetime.strptime(val, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone(TZ)
    if "T" in val:
        return datetime.strptime(val, "%Y%m%dT%H%M%S").replace(tzinfo=TZ)
    return None                                        # date-only == all-day

def from_ics(url, days=21):
    raw = urllib.request.urlopen(url, timeout=30).read().decode("utf-8", "replace")
    now = datetime.now(TZ)
    lo, hi = now - timedelta(days=2), now + timedelta(days=days)
    out = []
    for chunk in unfold(raw).split("BEGIN:VEVENT")[1:]:
        body = chunk.split("END:VEVENT")[0]
        def field(name):
            m = re.search(rf"^{name}(?:;[^:\n]*)?:(.*)$", body, re.M)
            return m.group(1).strip() if m else None
        if (field("STATUS") or "").upper() == "CANCELLED":
            continue
        s, e = ics_dt(field("DTSTART") or ""), ics_dt(field("DTEND") or "")
        if not s or not e or not (lo <= s <= hi):
            continue
        summary = (field("SUMMARY") or "").replace("\\,", ",").replace("\\n", " ")
        loc = field("LOCATION") or ""
        link = loc if loc.startswith("http") else None
        if not link:
            m = re.search(r"https://meet\.google\.com/[a-z-]+", body)
            link = m.group(0) if m else None
        out.append({
            "date":  s.strftime("%Y-%m-%d"),
            "start": s.strftime("%H:%M"),
            "end":   e.strftime("%H:%M"),
            "mins":  int((e - s).total_seconds() // 60),
            "title": clean_title(summary),
            "type":  classify(summary, "ATTENDEE" in body, bool(link)),
            "link":  link,
        })
    return out

def conf_ics_url():
    if not os.path.exists(CONF):
        return None
    for line in open(CONF):
        if line.strip().startswith("ICS_URL="):
            return line.split("=", 1)[1].strip()
    return None

# ---------------------------------------------------------------- write
def write(events):
    days = {}
    for ev in sorted(events, key=lambda x: (x["date"], x["start"])):
        days.setdefault(ev.pop("date"), []).append(ev)
    payload = {
        "updated":  datetime.now(TZ).isoformat(timespec="seconds"),
        "timezone": "Australia/Adelaide",
        "days":     days,
    }
    json.dump(payload, open(OUT, "w"), indent=1, ensure_ascii=False)
    n = sum(len(v) for v in days.values())
    print(f"wrote {OUT}: {n} events across {len(days)} days")
    for d in sorted(days):
        kinds = ", ".join(f"{e['start']} {e['type']}" for e in days[d])
        print(f"  {d}  {kinds}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", help="Google Calendar API events payload (JSON file)")
    ap.add_argument("--ics",    help="Secret iCal feed URL (overrides the config file)")
    a = ap.parse_args()

    if a.events:
        write(from_events_payload(a.events))
    else:
        url = a.ics or conf_ics_url()
        if not url:
            sys.exit(f"No source. Pass --events FILE, or put ICS_URL=... in {CONF}")
        write(from_ics(url))
