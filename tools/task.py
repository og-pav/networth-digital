#!/usr/bin/env python3
"""Drive the NetWorth Routine app from the command line (or from Claude).

Talks to the sync Worker, so every device picks the change up at its next
sync — nothing here touches a browser.

  task.py list                              what every client has open
  task.py add "Client" "task text"          add a task under a client
  task.py done "Client" "task text"         clear a task (matches like the
                                            webhook: exact title, then contains)
  task.py day YYYY-MM-DD "activity"         add a one-off activity to a day's plan

Credentials come from ~/.config/networth-routine/calendar.conf (WORKER_URL,
SYNC_KEY) — the same file the calendar sync uses. Nothing is stored in the repo.
"""
import json, os, random, string, sys, time, urllib.request

CONF = os.path.expanduser("~/.config/networth-routine/calendar.conf")
uid  = lambda: ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))

def conf(name):
    for line in open(CONF):
        if line.strip().startswith(name + "="):
            return line.split("=", 1)[1].strip()
    sys.exit(f"{name} missing from {CONF}")

W   = conf("WORKER_URL").rstrip("/")
HDR = {"X-Sync-Key": conf("SYNC_KEY"), "Content-Type": "application/json",
       "User-Agent": "networth-routine-sync/1.0"}

def call(path, data=None, method=None):
    req = urllib.request.Request(W + path, data=data, headers=HDR,
                                 method=method or ("PUT" if data else "GET"))
    return json.load(urllib.request.urlopen(req, timeout=30))

def post_task(action, client, task):
    body = json.dumps({"action": action, "client": client, "task": task}).encode()
    r = call("/task", body, "POST")
    print(f"queued {action} · \"{task}\" · {client} — every device applies it at its next sync ({r.get('queued')} in queue)")

def list_clients():
    st = call("/state")
    clients = [c for c in st.get("clients", {}).values() if not c.get("deleted")]
    if not clients:
        print("no clients in the synced state yet"); return
    for c in sorted(clients, key=lambda x: x.get("name", "")):
        open_t = [t for t in c.get("tasks", []) if not t.get("done")]
        flag = " (paused)" if c.get("status") == "paused" else ""
        print(f"{c.get('name')}{flag} — {len(open_t)} open")
        for t in open_t:
            print(f"   · {t.get('title')}")

def add_day(date, title):
    st = call("/state")
    if not st.get("template"):
        sys.exit("synced state has no template yet — open the app once with sync on first")
    day = st.setdefault("days", {}).get(date)
    import datetime as dt
    wd = dt.date(*map(int, date.split("-"))).weekday()
    prof = "weekend" if wd >= 5 else "weekday"
    if not day:
        # A minimal day; the app fills in the template's routine when it first
        # opens this date, and repairs the slot if ids have changed.
        day = st["days"][date] = {"date": date, "profile": prof, "items": [],
                                  "generated": "template"}
        day["items"] = [
            {"id": uid(), "src": a.get("id"), "slotId": a.get("slotId"),
             "title": a.get("title"), "cat": a.get("cat"), "min": a.get("min"),
             "rec": "always", "status": "pending", "carried": 0}
            for a in st["template"][prof].get("acts", []) if a.get("rec") == "always"]
    slot = st["template"][day.get("profile", prof)]["slots"][0]["id"]
    cat  = st.get("cats", [{}])[0].get("id")
    day["items"].append({"id": uid(), "src": None, "slotId": slot, "title": title,
                         "cat": cat, "min": None, "rec": "manual",
                         "status": "pending", "carried": 0})
    day["updated"] = int(time.time() * 1000)
    st.setdefault("log", []).append({"id": uid(), "at": day["updated"],
        "type": "day.add", "by": "claude", "text": f'Added "{title}" to {date}'})
    call("/state", json.dumps(st).encode())
    print(f'added "{title}" to {date} (first slot — drag it where it belongs)')

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] not in ("list", "add", "done", "day"):
        sys.exit(__doc__)
    if a[0] == "list":                list_clients()
    elif a[0] == "add"  and len(a) == 3: post_task("add", a[1], a[2])
    elif a[0] == "done" and len(a) == 3: post_task("complete", a[1], a[2])
    elif a[0] == "day"  and len(a) == 3: add_day(a[1], a[2])
    else: sys.exit(__doc__)
