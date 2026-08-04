# NetWorth Routine

A base daily template that adapts itself each evening. One HTML file, no backend,
no accounts, no AI calls — your routine data stays in your own browser.

## The mark

An unbroken ring of 16 segments — the day divided into slots, closed into a loop
that doesn't break. The bright gold arc is the streak so far. Inside sits a
rising two-peak zigzag, echoing the NetWorth NN mark: a repeating rhythm that
climbs. Consistency in the ring, discipline in the climb.

Colours are the NetWorth Digital pair — navy `#223870` and gold `#B1870F`, with
gold lifted to `#E3B33F` on dark backgrounds.

Assets are generated, not hand-drawn — see `tools/make_brand.py` to change the
segment count, streak length or colours and rebuild every icon in one go.

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
