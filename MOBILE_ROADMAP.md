# Phone layout

The app has no responsive styling. This is what is wrong, in what order to fix
it, and how to tell when it is done.

Measured on an iPhone 13 viewport (390px) against the live site, 2026-11-20.
Items 1 to 5 were done on 2026-11-24; the check below passes on all four pages.

---

## The one cause

**There are no media queries. Not one, in any of the seven stylesheets.**

`<meta name="viewport">` is correct, so the browser tries to honour 390px. The
fixed grids refuse, and the layout viewport inflates to 523-526px on Browse,
Explore and Title. Everything is then scaled down to fit — which is why it
reads as "too big and cut off" rather than "too small".

So this is one problem wearing five hats. Fixing the grids fixes the zoom as a
side effect; there is no separate "make the text smaller" task.

One breakpoint is enough. **640px**, phones only — inventing a tablet design
here would be work nobody asked for. Overrides go in each stylesheet next to
the rule they override, not in a new global file.

---

## The work

### 1. Chat is unusable — `Chat.css:3`

`grid-template-columns: 240px 1fr`. On 390px the Recent sidebar takes 240 and
the conversation gets the rest, so the messages and the input are a vertical
sliver at the screen edge. This is the one that makes the app look broken
rather than cramped.

- [x] one column below 640px
- [x] Recent becomes a horizontal strip above the thread (a drawer was more machinery than the problem needed)
- [x] `height: 700px` on the same rule → viewport-relative, so the input is reachable
- [x] the chat input and send button already overflow their container at 390px, before any grid fight

### 2. Explore's filter bar overflows — `Explore.css`, `Explore.jsx:192,222,248,276`

Four tabs in a row: Studio is off-screen, Year is clipped. The popups are
positioned with pixel offsets hardcoded into the JSX — `left: '0px'`,
`'110px'`, `'220px'`, `'330px'` — which are wrong at every width except the one
they were eyeballed at.

- [x] bar wraps or scrolls horizontally
- [x] the four hardcoded offsets are gone; popups now sit under the bar, which holds at every width
- [x] on a phone the popups probably want to be full-width sheets, not floating boxes

### 3. Result cards clip the title mid-word — `Explore.css:257`

`grid-template-columns: 200px 1fr`. A 200px poster leaves ~190px, so "Frieren:
Beyond Journey's End" renders as `Friere / Beyo / Journ / End`.

- [x] stack poster above content below the breakpoint

### 4. Four-across grids — `Browse.css:72`, `Title.css:140`

Both `repeat(4, 1fr)`.

- [x] two columns on a phone, or `repeat(auto-fill, minmax(150px, 1fr))` and let it decide

### 5. The title page is two columns — `Title.css:19`

`300px 1fr`.

- [x] stack it

### 6. Things that only bite on a phone

- [x] **Touch targets** on the filter tabs and the `+`.
- [x] Pagination controls are still cursor-sized. (The pager went with the Explore list.)
- [x] **499 pages of 5.** Gone with the Explore list: Browse shows 24 results and a Show more button.

---

## Done when

Checkable, not a matter of taste:

> `window.innerWidth` stays **390** and `document.scrollWidth` equals it, on
> Chat, Browse, Explore and Title.

`scripts/mobile-check.mjs` drives Playwright's `devices['iPhone 13']`, reports
both numbers, names any element extending past the viewport, and screenshots
each page. Keep it as a check rather than re-eyeballing screenshots.

```bash
node scripts/mobile-check.mjs                     # against the live site
node scripts/mobile-check.mjs http://localhost:5173
```

---

## Sizing

Chat is the bulk — maybe half a day if the sidebar becomes a drawer. Items 3
to 5 are an hour or two together, since they are all "stack below 640px".


---

## Done on 2026-11-24

All four pages now hold 390px. Two things only showed up once the fixes were
in, and both are the same mistake in different clothes:

**A grid child defaults to `min-width: auto`.** Stacking Chat to one column and
making Recent a scroll strip pushed the layout viewport to **1021px** — worse
than before the fix. The strip's content width was propagating up through the
grid. `min-width: 0` on the sidebar, the thread and the strip.

**`overflow-x` creates a clipping context.** Making the filter bar scroll
hid the popups entirely, because they are absolutely positioned against it and
now sat outside its painted box. The tabs moved into their own
`.filter-tabs` wrapper so the bar itself no longer scrolls.

Desktop was checked after, since removing the popup offsets changes it too:
the popups open under the bar rather than under their tab, left-aligned and
280px wide. The open tab is highlighted, so nothing is ambiguous.

Both remaining items — pagination touch targets and 499 pages of 5 — closed
on 2026-11-25 when the Explore result list was retired and its filters moved
to Browse, which shows 24 cards and a Show more button.
