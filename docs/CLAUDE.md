# India — 2500 years to the Republic — runbook

How to extend the asset without breaking anything. Read this alongside `HANDOFF.md` (project state) and the three schema docs (`SCHEMA.md`, `THREADS_SCHEMA.md`, `PEOPLE_SCHEMA.md`).

## Before you start

The validators are the contract. If a change breaks them, CI blocks the PR. Run them locally before any build:

```bash
python3 validators/validate_events.py
python3 validators/validate_threads.py
python3 validators/validate_people.py
python3 validators/validate_collections.py
```

The boundary rule for any India map: **Datameet, never Natural Earth or world-atlas for the India outline.** NE/world-atlas show PoK, Aksai Chin, and parts of Arunachal as outside India. Datameet's `india-soi.geojson` shows them inside, which is the official representation. The build pipeline already enforces this — surrounding states use world-atlas, India uses Datameet, India is drawn last so it sits on top.

## File map

```
2500/
├── README.md                     project overview, quick start
├── .gitignore                    datameet/, package/, .claude/, tests/artifacts/
│
├── data/
│   ├── events/events_*.json           99 events across 13 campaign files
│   ├── threads/threads_*.json         2 threads
│   ├── people/people_*.json           6 people
│   ├── collections/collections_*.json 5 collections
│   └── places/places_*.json           12 places
│
├── validators/
│   ├── validate_events.py        schema + cross-reference + PIP + tag format
│   ├── validate_threads.py       schema + corpus event_id resolution
│   ├── validate_people.py        schema + two-kind step + PIP
│   ├── validate_collections.py   schema + member resolution (event id OR tag selector)
│   └── validate_places.py        schema + PIP + auto-derived gather count
│
├── build/
│   ├── build_map.py              Datameet + world-atlas → SVG basemap (slow, rare)
│   ├── build_html.py             template + data → web/india-history.html AND shell.html
│   ├── build_png.py              matplotlib → web/india-history.png + .square.png
│   ├── map_paths.json            cached basemap (committed)
│   └── validator_boundaries.json cached PIP polygons (committed)
│
├── web/
│   ├── template.html             source HTML/CSS/JS with __PLACEHOLDER__ tokens
│   ├── india-history.html        BUILT single-file asset (deployable as-is)
│   └── shell.html                BUILT runtime-fetch version (loads /data and /build)
│
├── tests/
│   ├── render_test_v2.py            click pins → panel content
│   ├── render_test_popover.py       popover system (9 checks)
│   ├── render_test_zoom.py          zoom + pan (8 checks)
│   ├── render_test_people.py        people UI (10 checks)
│   ├── render_test_collections.py   collections UI (22 checks)
│   ├── render_test_places.py        places UI (23 checks)
│   └── artifacts/                   (gitignored — screenshots from test runs)
│
├── contribute/                   GUIDED FORMS for non-technical contributors
│   ├── index.html                landing + editorial guidance
│   ├── event.html                event form with Leaflet map picker
│   ├── thread.html               thread builder
│   ├── person.html               person form
│   └── lib/                      validators.js, submit.js, styles.css
│
├── docs/
│   ├── HANDOFF.md                project state for new contributors
│   ├── CLAUDE.md                 you are here
│   ├── CONTRIBUTING.md           for human contributors
│   ├── SCHEMA.md                 events schema (the contract)
│   ├── THREADS_SCHEMA.md
│   └── PEOPLE_SCHEMA.md
│
├── .github/
│   ├── workflows/validate.yml    CI: validators + render tests
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── datameet/                     EXTERNAL — `git clone github.com/datameet/maps`
└── package/                      EXTERNAL — fetch world-atlas separately
```

## Adding new events

1. **Pick a campaign file** under `data/events/`, or create a new one. Each era / campaign goes in its own `events_<campaign>.json`. The validator merges all of them at load time.

2. **Required fields per event** (full list in `SCHEMA.md`):
   - `id` — kebab-case, globally unique across the entire events corpus.
   - `tooltip` — ≤80 chars, validator-enforced. Includes a date or place anchor.
   - `summary` — ≤160 chars hard, ≤140 soft. One sentence.
   - `detail` — 80–150 words.
   - `location.country` — ISO alpha-2 from the controlled vocab (or `"OFF"` for events outside the asset's bounding box). PIP-checked against `validator_boundaries.json` to catch lat/lon typos.
   - `links` — must include one with `type: "wikipedia"`.
   - `verified` — `true` only if cross-checked against ≥2 sources.

3. **Wire causal links.** `caused_by` requires a `gloss` (the editorial sentence about *what* about the prior event led to this one). `part_of` for hierarchical containment without gloss. `led_to` is derived as inverse of `caused_by` at runtime — never authored. Cross-file references work; an event in `events_independence.json` can be `caused_by` something in `events_mughal.json`.

4. **Validate.**
   ```bash
   python3 validators/validate_events.py
   ```

5. **Rebuild.**
   ```bash
   python3 build/build_html.py
   ```
   This emits both `web/india-history.html` (single-file) and `web/shell.html` (runtime-fetch).

6. **Render-test.**
   ```bash
   for t in tests/render_test_*.py; do python3 "$t"; done
   ```

**Faster path for non-technical contributors:** the `contribute/event.html` form has the same workflow with inline validation and a Leaflet map picker. It generates the JSON; reviewer drops it into `data/events/`.

## Adding new threads

Same workflow with `data/threads/threads_<campaign>.json` and `validators/validate_threads.py`. Each step references an event by id; cross-corpus references work. Every step needs a `note`; non-final steps need a `transition`. Coda required (≤150 words; the closing argument).

`contribute/thread.html` form has a search-as-you-type event picker that loads the live corpus.

## Adding new people

Same workflow with `data/people/people_<group>.json` and `validators/validate_people.py`. Each track step is `kind: "event-ref"` (with `role`) or `kind: "moment"` (own date, location, summary, optional note). Track must be in chronological order.

The first 5 people in load order get distinct accents from the Rangrez India · NORTH palette (KHADI, AAKASH, KUMKUM, NEEL, MOR). Beyond 5, colours cycle.

`contribute/person.html` form has a track-step builder that toggles between event-ref (autocomplete from corpus) and moment (full sub-form with map picker).

## Adding new collections

Collections gather events into a *set* — unlike threads, no per-member notes or transitions. Use them for cross-cutting catalogues (women in independence, rebellions, founding moments, memoirs).

Workflow: file at `data/collections/collections_<campaign>.json`, validator `validators/validate_collections.py`. Required fields: `id`, `title`, `summary` (30–80 words), `members[]`, `verified`. Optional: `subtitle`, `framing` (≤200 words editorial paragraph), `sources`.

Members are heterogeneous — each entry is either:
- `{"kind": "event", "id": "salt-march-1930"}` — explicit, validator fails if id doesn't resolve.
- `{"kind": "tag", "tag": "women-leaders"}` — selector, validator fails if no event in the corpus has the tag (no empty selectors).

Mixing kinds in one `members[]` is fine. Renderer dedupes and sorts chronologically by `date.start`.

If your collection wants a tag that doesn't exist yet, **invent the tag, apply it to every event that fits via `tags[]`, then use the tag selector**. Tags are open-ended and free-form (kebab-case only); coordinate informally before introducing one.

`contribute/collection.html` form has both an event search-picker and a tag selector with autocomplete from existing tags.

## Adding tags to existing events

Tags are an optional `tags[]` field on event records — free-form, kebab-case, no controlled vocab. Validator only checks format. Single-use tags surface as a soft warning (typo signal). Keep `category` (controlled vocab, drives pin colour) separate from `tags` (open-ended, drives filtering / collection membership).

## Adding new places

Places are coordinate-anchored gathers — a single record (Delhi, Sabarmati Ashram, Vellore Fort) groups all events that happened within `radius_km` of its anchor. Membership is auto-derived at boot (haversine ≤ radius), so authoring a place does NOT require touching event files.

Workflow: file at `data/places/places_<campaign>.json`, validator `validators/validate_places.py`. Required: `id`, `name`, `tooltip` (≤80c), `summary` (≤160c), `location` (`country`, `lat`, `lon`, `radius_km` optional + defaults to 5, `alt_names` optional), `era_span`, `category` (controlled vocab — see PLACES_SCHEMA), `links` (Wikipedia required), `verified`. Optional: `subtitle`, `framing` (≤250 words editorial paragraph), `sources`.

Radius tuning:
- 3–5 km: tightly-bounded sites (Sabarmati Ashram, Jallianwala Bagh, Vellore Fort)
- 5–10 km: standard cities (Murshidabad, Pune, Lahore)
- 10–15 km: spread-out historical territories (Delhi 12 km — covers Mehrauli through New Delhi)
- 15+ km: regional gathers (use sparingly; consider whether the events belong in a polity record instead)

Validator soft-warns when fewer than 3 events are auto-gathered — usually a sign that either the place is a stub awaiting more events (acceptable, intentional seed) or the radius is too tight. The seven small-gather seeds in the current corpus are deliberate.

A place earns its own record when at least 3 events from at least 2 eras anchor at it, OR when the place's continuity-as-protagonist is the editorial point. Places are *where* things happen across time; they are not threads (which argue an interpretation) or collections (which gather by tag).

## Editorial discipline (not validator-enforced)

- **Verified figures only.** Cross-check dates, locations, and key claims against ≥2 independent sources before `verified: true`. When in doubt, `false`.
- **Wikipedia is the rabbit-hole link, not the source.** Summary should read like the start of an editorial, not an extract of the lead.
- **A thread must have a thesis.** If you can't write the coda in one paragraph, the thread isn't ready.
- **Numbers and named entities over adjectives.** "32 million rupees, 5–8% of annual revenue" beats "vast wealth".
- **Granular dynasties.** Don't fold smaller / shorter dynasties into bigger neighbours. Sur (1540–1556) gets its own file; same logic for Asaf Jah and other regional polities. The era vocab is a coarse time bucket, not a dynastic taxonomy — multiple files can share an era token (`era: "mughal"` for both Mughal and Suri events).

## The build pipeline (single-source two outputs)

`build/build_html.py` reads the same `web/template.html` and emits two files:

- **`web/india-history.html`** — all data inlined. Single-file portable. Works from `file://`, `assets.chiragpatnaik.com`, iOS Quick Look. The deployable asset.
- **`web/shell.html`** — data placeholders stubbed with empty literals; a boot script fetches `/data/*` and `/build/*` over HTTP, then calls `bootRenders()`. For hosted use where data updates daily.

The shared template uses `let` (not `const`) for the four data globals (`MAP`, `EVENTS`, `THREADS`, `PEOPLE`) so the shell can reassign them after fetch. Indexes (`eventById`, `ledTo`, `peopleById`, `momentByKey`) are populated by `buildIndexes()` which `bootRenders()` calls first. A single `__BOOT_INVOCATION__` placeholder in the template controls how the boot fires per build target.

## Click model (popover vs panel)

Two surfaces for showing event content. Future edits must preserve the split — they're meaningfully different affordances.

- **Popover** = scan. Anchored card next to a pin on desktop, bottom sheet on mobile. Shows tooltip / date / location / tags / summary / Wikipedia link / "Read full entry →" button. Dismissed via X, Esc, or click-outside (with `.pin`, `.track-pin`, `.relation-card`, `.thread-step`, `.people-reader .track-step`, and `.offmap-panel li` excluded — clicks on those are deliberate navigations).
- **Panel** = read. The right column. Full detail, figures, sources, caused-by / led-to / part-of relation cards, OR the thread reader, OR the people reader.

| Action | Popover | Panel |
|---|---|---|
| Single click pin | open / toggle | unchanged |
| Shift-click pin | hide | open with that event |
| Double-click pin | hide | open with that event |
| "Read full entry →" in popover | stays (locator) | open with same event |
| Relation card click in panel | open for new event | switch to new event |
| Thread step click | open for step's event | switch to step's event |
| People pill click | (no popover change) | toggle person in active set; render people reader |
| Track-pin click (event-ref) | open event popover with role | unchanged |
| Track-pin click (moment) | open moment popover | unchanged |
| Off-map row click | open popover anchored to the row | unchanged |

Relation-card and thread-step cases call `navigateToEvent(id)` which does both `selectEvent(id)` and `showPopover(id)`. The user wants the map to keep a visual locator while they walk through chains in the panel.

When pins re-render (filter / year-range change), `renderPins()` checks whether the popover's event is still in the rendered set. If not, the popover auto-closes. If yes, it repositions to the new pin location.

## Zoom + pan

The map is a viewBox-manipulation surface, not a CSS-transform surface — paths stay sharp at any zoom level. Single source of truth: `zoom = { scale, cx, cy, min: 1, max: 8 }`.

- **Wheel** zooms around the cursor, anchored so the SVG point under the cursor stays under the cursor through the zoom. `wheel` is `{ passive: false }` because we `preventDefault()` to stop page scroll.
- **Drag** pans (left mouse button only). Pan only initiates if mousedown does NOT land on a pin. 4-pixel dead zone before pan engages.
- **After a real drag**, the next click is suppressed via `_suppressNextMapClick` so a pan ending over a pin doesn't open the popover unintentionally.
- **Touch:** one finger = pan, two fingers = pinch zoom anchored to centroid.
- **Buttons:** `+ / − / ↺` zoom centred on the *current* viewBox centre.

### Pin and stroke scaling

Pin radii are inverse-scaled with zoom (`r = 5 / zoom.scale` for event pins, `4 / zoom.scale` for track pins) so they keep constant CSS-pixel size at any zoom. Recomputed in `applyZoom()`. Routes (Salt March polyline) and track lines rely on `vector-effect="non-scaling-stroke"`. **Don't** use `transform: scale()` on the SVG.

### Popover positioning under zoom

`positionPopover` reads `elMap.viewBox.baseVal` at call time (not the initial viewBox), so popovers stay anchored to their pin through any zoom or pan. If the pin's viewBox coords fall outside the *current* visible viewBox (panned off screen), the popover hides itself. `applyZoom()` calls `positionPopover` on every frame the viewBox changes.

For track-step popovers, `positionPopoverForStep` falls back to anchoring at the off-map table row when the underlying pin is outside the viewport.

### Don't raise zoom.max past 8 lightly

At scale=8 the visible viewBox is 125 vbu wide (~925 km — about Punjab width). Pin radius is 0.625 vbu (~3.5 CSS pixels). Going past 8 means pin radii fall below click-target minimum.

## Constraints

- **Single-file portability of `india-history.html`.** No external fetches at runtime. Works from `file://`, `assets.chiragpatnaik.com`, iOS Quick Look. (Constraint does NOT apply to `shell.html` or `contribute/*.html` — those are hosted-only and may use CDNs.)
- **iOS Quick Look strips JavaScript.** The build pre-renders static fallbacks for the threads bar, the people bar, and the map pins inside the SVG.
- **DATA:BEGIN / DATA:END markers** in `template.html` are the splice points for data injection. Don't move them.
- **`__BOOT_INVOCATION__` placeholder** in `template.html` controls boot — the single-file build replaces it with `bootRenders();`, the shell build replaces it with an async fetch + boot block.
- **Naklitechie design system.** Cream surfaces, two type weights, no shadows, no gradients. Country palette canonical. Accents per design tokens.

## Known issues / open work

- **Pin overlap dodge** is tuned in geographic terms, not screen terms. At our viewBox scale, 1 vbu ≈ 7.4 km. Constants in `template.html`:
  - `MERGE_DIST = 3` (~22 km — only true co-location)
  - `DODGE_RADIUS = 5` (~37 km — caps displacement at city scale)
  Earlier values of 14 and 12 produced ~88 km of displacement, enough to push pins across the Wagah border. Don't raise without re-checking the Punjab cluster.

- **Pin density at scale.** With 30+ events in one region the radial dodge starts looking weird. Mughal-era Delhi already approaches this. The fix is the cluster badge (count + expand-on-click) — see `HANDOFF.md` "What's NOT built yet" #1.

- **PNG companion** is built. `python3 build/build_png.py` writes `web/india-history.png` (1200×675, OG/Twitter card) and `web/india-history-square.png` (1080×1080). Re-run after content changes if you want the social preview to reflect the latest event count.

## Updating the map

If the projection or extent needs to change, edit `build/build_map.py` and re-run it. Outputs `build/map_paths.json` and `build/validator_boundaries.json` (both committed). Pin coordinates in event/people files don't change — they're stored as lat/lon and projected at runtime by the matching JS LCC.

The Python and JS LCC formulae are spherical (R=6371000) and have been verified to agree to integer-meter precision. If you change the projection parameters, change them in **all three places**:
- `build/build_map.py` (the proj4 string)
- `build/build_html.py` (the Python `lcc()` used for static pin pre-render)
- `web/template.html` (the JS `lcc()`)

## Updating the auto-memory

Project-specific principles that should outlive any single conversation (like the granular-dynasties rule) should go in the auto-memory feedback files at `~/.claude/projects/-Users-chiragpatnaik-Code-Sites/memory/`. They get loaded into every session via `MEMORY.md`.

## Test suite map

| Test | Checks |
|---|---|
| `validate_events.py` | schema + cross-reference + PIP for events |
| `validate_threads.py` | schema + event_id resolution for threads |
| `validate_people.py` | schema + event_id resolution + PIP for people |
| `validate_collections.py` | schema + member resolution (event id OR tag selector) |
| `render_test_v2.py` | shift-click pins → right panel content |
| `render_test_popover.py` | popover system, dodge math, relation cards (8 checks) |
| `render_test_zoom.py` | viewBox manipulation, cursor anchor, button limits (8 checks) |
| `render_test_people.py` | full People UI: pills, tracks, off-map table, popovers, mutual exclusion (10 checks) |
| `render_test_collections.py` | full Collections UI: pills, member resolution, tag selectors (13 checks) |

Total: 4 validators + 5 render tests = 9. CI runs all of them on every PR.
