# NetWorth Routine

A base daily template that adapts itself each evening. One HTML file, no backend,
no accounts, no AI calls — your routine data stays in your own browser.

## The mark

The NetWorth NN mark and growth arrow, with a flame as the Routine symbol — the
streak you don't break. Colours are the NetWorth pair: navy `#223870`, gold
`#B1870F`, gold lifted to `#E3B33F` on dark.

Two things were corrected against the supplied `NW Routine - Standard.svg`
(kept untouched as `assets/logo-original-supplied.svg`):

- **The flame was clipped.** Content ran to `y=269.3`; the viewBox stopped at
  `260.12`, cutting the bottom off.
- **It hung below the baseline.** Both NN strokes end exactly at `y=253.1`; the
  flame sagged 16 units past it.

The integration was then tightened: the flame's axis went from 18° to 27° so it
leans with the diagonal strokes rather than standing upright against them.

Every asset is generated — run `python3 tools/make_brand.py` after changing the
placement, colours or icon padding, and all the SVGs and PNGs rebuild. It uses
macOS `qlmanage` and `sips`, so there's nothing to install.

| File | Use |
|---|---|
| `logo-lockup.svg` | Full logo, colour, for light backgrounds |
| `logo-lockup-reverse.svg` | White NN, flame centre knocked out — any dark background |
| `logo-lockup-2048.png` | Transparent raster for decks, emails, GHL |
| `flame.svg` / `flame-gold.svg` | Symbol alone |
| `icon-*.png` | App icons — gold flame knocked out of a navy tile |

## Running it locally

```bash
python3 -m http.server 8765 --directory ~/daily-routine
```

Open http://localhost:8765, or the Mac's LAN address from your phone on the same
wi-fi. Opening `index.html` by double-clicking won't save anything — browsers
block storage on `file://` addresses.

## Publishing to GitHub Pages

The repo is ready to push. On github.com:

1. **New repository** → name it `networth-routine` → **Public** → *don't* add a
   README → **Create**.
2. Back in Terminal:
   ```bash
   cd ~/daily-routine
   git remote add origin https://github.com/<your-username>/networth-routine.git
   git push -u origin main
   ```
3. In the repo: **Settings → Pages → Source: Deploy from a branch → `main` / `root` → Save.**

A minute later it's live at `https://<your-username>.github.io/networth-routine/`.

On the free plan Pages only works from a **public** repo. That publishes the app
code, not your data — your routine never leaves your phone. If you'd rather it
weren't public at all, Cloudflare Pages does private hosting for free.

To update later: edit, then `git commit -am "..."` and `git push`. Bump `CACHE`
in `sw.js` when you change `index.html`, or phones keep serving the old copy.

## Installing on your phone

Open the Pages URL in Safari → **Share → Add to Home Screen**. It gets the gold
ring icon, opens full screen with no browser chrome, and works offline.

## Clients

The **Clients** tab keeps a to-do list per client, separate from the daily
routine. Ticking a task clears it into "cleared recently" (kept 30 days, with an
↩ to put it back). Client names and task titles edit in place — click them.
Client lists sync between devices the same way days do: per client, last edit
wins.

### Clearing tasks from outside

Any system that can send a webhook — a GHL workflow, a Zap, a script — can clear
or add a client task. It needs the sync Worker (below) deployed. Send a POST to
`https://<your-worker>/task` with the sync key in the `X-Sync-Key` header (or as
`"key"` in the body if the sender can't set headers):

```json
{"action":"complete","client":"Acme Pty Ltd","task":"send proposal"}
{"action":"add","client":"Acme Pty Ltd","task":"chase signed agreement"}
```

`complete` matches the open task by title — exact first, then contains — so a
workflow can send `"task":"proposal"` and clear "Send proposal". `add` creates
the client too if it doesn't exist yet. Events queue on the Worker for a week;
every device applies them at its next sync and remembers which it has applied,
so two devices pulling the same queue don't double up.

## How a day gets built

Every day starts from the base template, then adapts:

| What it is | What happens tomorrow |
|---|---|
| Daily / weekday / weekend activity | Comes back on its normal schedule |
| One-off task, ticked done | Gone |
| One-off task, not done | Carried over, tagged `carried ×n` so you see it chasing you |
| Missed habit (recurring) | Not carried — it just returns on schedule |
| Added in the review as "just tomorrow" | Appears tomorrow only |
| Added in the review as daily/weekdays/weekends | Added to the base template permanently |

Override any of it with the tick boxes in the review before hitting
**Generate tomorrow's plan**.

## Things worth knowing

- Moving an activity to a different slot on a given day changes **that day
  only**. To move it permanently, edit it on the **Template** tab.
- Data lives in one browser's local storage. It does **not** sync between your
  Mac and your phone — pick one as the main one.
- **Template → Export backup** writes a `.json` you can re-import later or on the
  other device. Clearing browser data wipes everything, so do this occasionally.
- Categories and their colours are edited on the Template tab and apply
  everywhere.

## The Mac app

`dist/NetWorth Routine.app` — a real macOS app: own dock icon, own window, no
browser, works with no internet and no server running.

```bash
./desktop/build.sh
cp -R "dist/NetWorth Routine.app" ~/Applications/
```

Re-run both lines after editing `index.html` or `assets/` — the bundle carries
its own copy of the web files.

It's a WKWebView wrapper (`desktop/main.m`, ~200 lines, no dependencies). Two
things worth knowing about how it's built:

- The page is served over a custom `nwroutine://` scheme, **not** `file://`.
  WebKit gives `file://` pages an opaque origin and denies them localStorage,
  which would throw the whole routine away on every launch. The custom scheme
  gets a real origin, so data persists in
  `~/Library/WebKit/com.networthdigital.routine/`.
- It's Objective-C, not Swift, because this Mac's Command Line Tools ship a
  Swift compiler that disagrees with its own SDK and can't build `import WebKit`.
  Clang is unaffected. If the toolchain is ever repaired, nothing here needs to
  change.

The Mac app and the phone keep **separate** data. Use Export/Import backup on the
Template tab to move a snapshot between them.

## Sync between devices

Without this, the Mac app and the phone each keep their own separate copy —
browser storage is per-origin and per-device. The sync is a small Cloudflare
Worker with a KV namespace, on the free tier.

### Deploy it

```bash
cd ~/daily-routine/sync
npx wrangler login                      # opens a browser, approve once
npx wrangler kv namespace create ROUTINE
```

Paste the printed `id` into `wrangler.toml`, then:

```bash
npx wrangler deploy
```

It prints a URL like `https://networth-routine-sync.<you>.workers.dev`.

### Turn it on

Template tab → **Sync between devices** → paste the Worker address, hit
**Generate key**, **Save**. Then put the *same address and key* into the app on
the other device. That key is the only thing protecting your data — treat it
like a password.

### How merging works

Each device pulls, merges locally, and pushes back; the Worker never merges.
Merging is **per day and per template**, decided by whichever side was edited
last. Ticking things off on the phone at lunch and editing the template on the
Mac that evening both survive — whole-state last-write-wins would silently throw
one of them away.

Days are stamped by diffing their content on save rather than by trusting each
mutation site to mark itself dirty, because one missed call there loses a day's
work in a merge with no error.

### The calendar on your phone

`calendar.json` never leaves the Mac — client names and live Meet links. Add
your Worker details to `~/.config/networth-routine/calendar.conf`:

```
ICS_URL=https://calendar.google.com/calendar/ical/.../basic.ics
WORKER_URL=https://networth-routine-sync.<you>.workers.dev
SYNC_KEY=<the same key>
```

`tools/sync_calendar.py` then writes the local file *and* pushes a private copy
to the Worker. The Mac reads the file; the phone falls back to the Worker copy.
Nothing about your calendar is ever published.
