# India history explorer — runbook

The asset at `india-history.html` is built from data files plus a template plus a
build script. This document covers how to extend it without breaking anything.

## Before you start

Read `SCHEMA.md` and `THREADS_SCHEMA.md` first. The validators enforce them.

The boundary rule for any India map: **Datameet, never Natural Earth for the
India outline.** Natural Earth and world-atlas show PoK, Aksai Chin, and parts
of Arunachal Pradesh as outside India. Datameet's `india-soi.geojson` shows
them inside, which is the official representation. The map pipeline already
handles this: surrounding states use world-atlas, India uses Datameet, India is
drawn last so it sits on top.

## File map

```
india-history/
├── SCHEMA.md                       events schema (the contract)
├── THREADS_SCHEMA.md               threads schema (the contract)
├── PEOPLE_SCHEMA.md                people schema (drafted, no UI yet)
│
├── events_independence.json        seed corpus (12 events, 1885–1947)
├── threads_independence.json       seed thread (Chauri Chaura chain)
│
├── validate_events.py              schema + cross-reference + PIP validator
├── validate_threads.py             schema + corpus-resolution validator
│
├── build_map.py                    Datameet + world-atlas → SVG paths + validator boundaries
├── build_html.py                   template + data → india-history.html
├── template.html                   HTML + CSS + JS, with __PLACEHOLDER__s
│
├── render_test_v2.py               clicks pins, panel opens
├── render_test_popover.py          popover system + relation-card-shows-popover
├── render_test_zoom.py             zoom + pan, cursor anchor, button limits
│
├── map_paths.json                  output of build_map.py (basemap, cached)
├── validator_boundaries.json       output of build_map.py (PIP polygons, ~672 KB)
├── india-history.html              output of build_html.py (the asset)
│
└── datameet/                       cloned from github.com/datameet/maps
    └── Country/india-soi.geojson   the authoritative India boundary
```

## Adding new events

1. **Create or extend a campaign file.** Each era / campaign goes in its own
   `events_<campaign>.json`. The validator merges all of them at load time.
   Examples planned: `events_mughal.json`, `events_maurya.json`,
   `events_central_asia.json` (for Babur's pre-1526 events outside the
   subcontinent).

2. **Required fields per event.** Beyond the obvious (id, title, date, era,
   category, links, verified) every event needs:

   - `tooltip` (string, ≤80 chars hard cap, validator-enforced) — the line
     shown on native pin hover. Should read like a museum-label caption,
     e.g. `"Jallianwala Bagh massacre, Amritsar, 1919"`.
   - `summary` (string, ≤160 chars hard cap) — one sentence shown in the
     popover card body and in popover-internal relation cards.
   - `detail` (string, 80–150 words) — full prose for the right panel.
   - `location.country` (ISO alpha-2 from the controlled vocab; or `"OFF"`
     for events outside the asset's bounding box like London Round Tables).
     The validator does a point-in-polygon check confirming `points[0]`
     actually falls inside the polygon for the declared country. This
     catches typos (lat/lon swap, decimal off) before they ship.

   The full controlled vocab for `location.country` is in `SCHEMA.md`. Don't
   invent codes — if you need one that isn't there, add it both there and
   to the `COUNTRIES` set in `validate_events.py`.

3. **Wire causal links.** Use `caused_by` for direct causal/responsive edges,
   `part_of` for hierarchical containment. `caused_by` requires a `gloss` —
   the editorial sentence that says *what* about the prior event led to this
   one. A bare ID without a gloss is a validator error. Multiple parents
   and multiple children are both supported natively (the schema is a DAG,
   not a tree); `led_to` is derived as the inverse of `caused_by` at runtime
   and never authored by hand.

4. **Validate.** `python3 validate_events.py .` — must PASS before rebuilding.
   The PIP check requires `validator_boundaries.json` to exist; if you
   regenerate the basemap, that file gets regenerated alongside.

5. **Rebuild.** `python3 build_html.py` re-splices everything into the HTML.

6. **Render-test.** `python3 render_test_popover.py` exercises the popover
   system, the dodge math, and the relation-card-shows-popover behavior;
   `python3 render_test_v2.py` covers the older click-opens-panel path.

## Adding new threads

Same workflow with `threads_<campaign>.json` and `validate_threads.py`. The
threads validator runs after the events validator so it can resolve
`event_id` references across the entire corpus. A thread in
`threads_independence.json` can reference an event from
`events_mughal.json` — they don't need to be co-located.

## Editorial discipline (not enforced by validator)

- **Verified figures only.** Cross-check dates, locations, and key claims
  against at least two independent sources before setting `verified: true`.
  When in doubt, set `verified: false` — the UI surfaces it as a small tag,
  better than dropping interesting events with contested details.
- **Wikipedia is the rabbit-hole link, not the source.** The summary should
  read like the start of the editorial, not an extract of the Wikipedia
  lead.
- **A thread must have a thesis.** If you can't write the `coda` in one
  paragraph, the thread isn't ready.

## Click model (popover vs panel)

The asset has two surfaces for showing event content. Future edits must
preserve the split — they're meaningfully different affordances.

- **Popover** = scan. Anchored card next to a pin on desktop, bottom sheet
  on mobile. Shows tooltip-headline + date + location + tags + summary +
  Wikipedia link + a "Read full entry →" button. Dismissed via X, Esc, or
  click-outside (with `.pin`, `.relation-card`, `.thread-step` excluded
  from the click-outside check — clicks on those are deliberate
  navigations).
- **Panel** = read. The right column. Shows full detail, figures, sources,
  caused-by / led-to / part-of relation cards. Stays open until explicitly
  closed.

Click handlers (in `template.html`):

| Action | Popover | Panel |
|---|---|---|
| Single click pin | open / toggle | unchanged |
| Shift-click pin | hide | open with that event |
| Double-click pin | hide | open with that event |
| "Read full entry →" in popover | stays (locator) | open with same event |
| Relation card click in panel | open for new event | switch to new event |
| Thread step click | open for step's event | switch to step's event |

The relation-card and thread-step cases call `navigateToEvent(id)` which
does both `selectEvent(id)` and `showPopover(id)`. The user requested
this so the map keeps a visual locator while they walk through chains
in the panel.

When pins re-render (filter / year-range change), `renderPins()` checks
whether the popover's event is still in the rendered set. If not, the
popover auto-closes. If yes, the popover repositions to the new pin
location.

## Zoom + pan

The map is a viewBox-manipulation surface, not a CSS-transform surface — so paths stay sharp at any zoom level. Single source of truth is the `zoom` object: `{ scale, cx, cy, min: 1, max: 8 }`.

- **Wheel** zooms around the cursor, anchored so the SVG point under the cursor stays under the cursor through the zoom. `wheel` is `{ passive: false }` because we `preventDefault()` to stop the page from scrolling when the cursor is over the map.
- **Drag** pans (left mouse button only). Pan is initiated only when the mousedown does NOT land on a pin — pin clicks would otherwise be eaten. A 4-pixel dead zone before pan engages so a click that wobbles still registers as a click.
- **After a real drag**, the next click event is suppressed via `_suppressNextMapClick`. Without this, a pan that ends over a pin opens the popover unintentionally.
- **Touch**: one finger = pan, two fingers = pinch zoom anchored to the pinch centroid. Pin click on touch still works because `touchstart` checks `target.closest('.pin')` before initiating pan.
- **Buttons**: `+ / − / ↺` at top-right of the map. `+` and `−` zoom centred on the *current* viewBox centre, not the original map centre — so successive presses zoom into wherever the user has panned to. Auto-disabled at the limits.
- **Reset** restores the initial viewBox and resets `scale=1`.

### Pin and stroke scaling

Pin radii are inverse-scaled with zoom (`r = 5 / zoom.scale`) so they keep a constant CSS-pixel size at any zoom level. This is recomputed in `applyZoom()`. Routes (e.g., Salt March's polyline) rely on `vector-effect="non-scaling-stroke"` for the same reason. **Don't** use `transform: scale()` on the SVG — use viewBox manipulation, otherwise paths blur.

### Popover positioning under zoom

`positionPopover` reads `elMap.viewBox.baseVal` at call time (not the initial viewBox) so popovers stay anchored to their pin through any zoom or pan. If the pin's viewBox coords fall outside the *current* visible viewBox (panned off screen), the popover hides itself rather than pinning to a stale screen position. `applyZoom()` calls `positionPopover` on every frame the viewBox changes, so popover follows the pin in real time during a pan or zoom.

### Don't raise zoom.max past 8 lightly

At scale=8 the visible viewBox is 125 vbu wide, ~925 km — about the width of Punjab. Pin radius becomes 0.625 vbu (still ~3.5 CSS pixels at typical display widths). Going past 8 means pin radii fall below the click-target minimum, and the dodge starts looking like noise.


## Constraints

- **Single-file portability.** No external fetches, no CDNs at runtime, no
  build step on the user's end. The HTML must work from `file://`,
  `assets.chiragpatnaik.com`, and iOS Quick Look.
- **iOS Quick Look strips JavaScript.** The build script pre-renders a
  static fallback for the threads bar and the map pins inside the SVG, so
  the asset previews correctly without JS. JS replaces them on page load.
- **DATA:BEGIN / DATA:END markers** in the script block are the splice
  points for Claude Code or manual paste. Don't move them. Don't put
  human-edited content between them — they get overwritten on rebuild.
- **Naklitechie design system.** See `STYLE-GUIDE.md` in the project root.
  Cream surfaces, two type weights, no shadows, no gradients, country
  palette is canonical.

## Known issues / open work

- **Pin overlap dodge** is tuned in geographic terms, not screen terms. At
  our viewBox scale, 1 vbu ≈ 7.4 km on the ground. Constants in
  `template.html`:
  - `MERGE_DIST = 3` (~22 km — only true co-location clusters)
  - `DODGE_RADIUS = 5` (~37 km — caps displacement at city scale)

  These were 14 and 12 in an earlier version; that produced ~88 km of
  geographic displacement, which was enough to push pins across borders
  near Wagah (Lahore appearing in India, Amritsar in Pakistan). Don't
  raise them without checking what happens to the Punjab cluster.

- **Pin density at scale.** With 30+ events in one region the radial dodge
  starts to look weird — pins fan out in directions that don't match
  geography. When that happens, replace the radial dodge with a cluster
  badge (count + expand-on-click).

- **Active-range tint on the slider** is `rgba(83, 74, 183, 0.18)` — visible
  but subtle when the user has narrowed the range. If feedback comes in
  that it's too faint, bump alpha to 0.28 and add a 1px border on the
  active range div.

- **Off-map events** are now handled: set `location.country = "OFF"` to
  opt out of the point-in-polygon check. Pin still renders at its
  projected position, which may fall outside the visible viewBox — when
  we have actual off-map events (London Round Tables, Babur in Samarkand)
  we'll need to either widen the projection bounds or add an
  "elsewhere" indicator at the map edge.

- **PNG companion** for the explorer is not yet built. When done, follow the
  `make_<slug>.py` matplotlib pattern from STYLE-GUIDE.md §9 — 16:9, 200
  DPI, cream background, country palette canonical.

## Next planned work

1. **People slice (`people_freedom-fighters.json` + UI).** Schema is
   drafted in `PEOPLE_SCHEMA.md`. Build order: validator first, then
   author Gandhi + Nehru + Bhagat Singh + Ambedkar + Jinnah as a seed
   corpus, then add the People selector pill alongside Threads in the
   top bar, then track rendering on the map (numbered pins + connecting
   line, like the Salt March route) and the vertical timeline reader.
2. **`events_mughal.json`** — Mughal campaign, Babur (1526) through
   Aurangzeb (1707). Roughly 25 events.
3. **`events_central_asia.json`** — pre-Mughal Timurid events from
   Ferghana to Kabul, so the Babur thread can be wired without
   geographic gaps.
4. **Babur thread** — `narrative` kind, ~6 steps from inheritance of
   Ferghana to Panipat. Stress-tests trans-regional map handling.
5. **Cluster badge for high-density regions.** When ≥3 pins fall within
   MERGE_DIST after the dodge pass, replace the dodged pins with one
   numbered "+N" badge. Click → chooser popover listing each pin's
   tooltip → click a row → regular popover for that event. Touch-
   friendly, replaces the need for hover-zoom UX. Defer until a region
   actually breaks visually (probably Mughal-era Delhi).
6. **Sultanate events** — Ghurids through Lodis, ~20 events.
7. **Maurya / post-Maurya events** — Buddha's lifetime, Mahajanapadas,
   Chandragupta to Ashoka, ~15 events. This is also when the time slider
   gets stress-tested at the BCE end.
8. **Off-map handling** for events outside the asset's bounding box
   (London Round Tables, etc.) — the schema already supports
   `country: "OFF"`; UI needs an indicator when the user is on an
   active thread/track step that points off-map.
9. **PNG companion** for social sharing.

## Updating the map

If the map projection or extent needs to change, edit `build_map.py` and
re-run it. The output `map_paths.json` is then re-spliced via
`build_html.py`. Pin coordinates in events files don't change — they're
stored as lat/lon and projected at runtime by the matching JS LCC.

The Python and JS LCC formulae are spherical (R=6371000) and have been
verified to agree to integer-meter precision. If you change the projection
parameters, change them in **both** places: `build_map.py` (the proj4
string and the LCC math in `build_html.py`'s `lcc()`) **and** the
`lcc()` function in `template.html`.
