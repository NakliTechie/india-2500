# India history explorer — handoff to Claude Code

This is a single-file interactive HTML asset for `assets.chiragpatnaik.com`, built across multiple sessions in the Claude.ai web interface. The project has now grown past the point where multi-file editing in this interface is reliable — too many tool-calling errors on `str_replace`. Moving to Claude Code so file state persists between turns and tests can run in a tighter loop.

This document captures the entire state. Read it cold and you should be able to keep building.

---

## What the project is

A standalone HTML asset that renders a map of the Indian subcontinent with pins for historical events, threads of curated walks through those events, and (newly drafted but not yet built into the UI) biographical tracks for major figures. Designed for editorial publication on the Naklitechie/`chiragpatnaik.com` brand, single-file portable, opens from `file://` and from hosted paths alike.

**Title:** *India — 2500 years to the Republic*
**Brand:** Naklitechie / Chirag Patnaik
**Target:** `assets.chiragpatnaik.com/india-history.html`
**Editorial stance:** neutral, data-grounded, named entities and numbers over adjectives
**Audience:** Indian readers, but the design system and the boundaries are correct globally

---

## What's built and shipping

### Atlas of events
- **Schema:** `SCHEMA.md`. Every event has `id`, `title`, `tooltip` (≤80 char hard cap), `summary` (≤160 char hard cap), `detail` (80–150 words), `date`, `location` (with `country` ISO alpha-2 + `points`), `era`, `category`, `figures`, `links`, optional `caused_by` and `part_of`.
- **Causal layer:** `caused_by` carries an editorial `gloss` per edge; `led_to` derived as inverse at runtime — never authored. `part_of` for hierarchical containment without gloss. Multi-parent and multi-child both supported natively.
- **Validator:** `validate_events.py` with full schema enforcement plus a point-in-polygon check that confirms each pin's lat/lon falls inside its declared country's polygon. Pure-Python ray casting against `validator_boundaries.json`.
- **Seed corpus:** `events_independence.json`, 12 events from INC founding (1885) through Independence and Partition (1947).

### Threads (curated walks)
- **Schema:** `THREADS_SCHEMA.md`. A thread has `id`, `kind` (`narrative | causal-chain | thematic | counterfactual`), `title`, `subtitle`, `coda`, `steps[]`. Each step is `event_id` + per-step `note` + `transition` (the prose bridge to the next step, null on the last).
- **Validator:** `validate_threads.py`. Resolves `event_id` references against the entire events corpus.
- **Seed corpus:** `threads_independence.json`, one thread on Chauri Chaura and the cost of non-violence.

### People (drafted, schema + seed authored, UI not yet built)
- **Schema:** `PEOPLE_SCHEMA.md`. A person has lifespan + a `track[]` of ordered moments. Each track step is either an `event-ref` (with `role`) or a standalone `moment` (with date, location, summary, note). Moments are intentionally lighter than events.
- **Validator:** *not yet written.* High priority. Should mirror `validate_events.py` with the two-kinds-of-step distinction.
- **Seed corpus:** `people_freedom-fighters.json`, **5 people** with a total of **45 track steps** — Gandhi (13), Nehru (9), Bhagat Singh (6), Ambedkar (10), Jinnah (9). Mix of event-refs and moments. Tests off-map handling (London, Brussels, NYC, Pretoria), event-ref roles, and standalone biographical moments. Editorial framing already polished — read once before building UI.

### Map
- **Pipeline:** `build_map.py` reads Datameet `india-soi.geojson` (the authoritative India boundary, includes PoK / Aksai Chin / full J&K) plus world-atlas `countries-50m.json` for surrounding states. Spherical Lambert Conformal Conic projection (`lat_1=20, lat_2=40, lat_0=30, lon_0=78, R=6_371_000`). Outputs `map_paths.json` (basemap, ~101 KB inlined into HTML) and `validator_boundaries.json` (PIP polygons, ~672 KB, separate file).
- **Rendering:** SVG with `viewBox=__VIEWBOX__` placeholder filled at build time. India drawn last so PoK is correctly inside India.

### Interactivity
- **Click model.** Single-click pin → popover. Shift-click or double-click pin → panel direct (skip popover). "Read full entry →" in popover → opens panel; popover stays as map locator. Relation card click in panel → both panel updates AND popover swaps to the new event's pin. Thread step click → same as relation card. Click outside popover or Esc → dismiss popover.
- **Popover.** Anchored card on desktop (centred horizontally on pin, above or below depending on viewport room). Bottom sheet on mobile (<920px). Auto-hides if pin filtered out or panned off-screen.
- **Zoom + pan.** Wheel zooms anchored to cursor. Drag to pan (4-px dead zone, suppressed click after a real drag so pan-into-pin doesn't open popover). Pinch + two-finger drag on touch. `+ / − / ↺` controls top-right of map. Pin radii inverse-scale with zoom so they stay constant CSS pixels. Routes use `vector-effect="non-scaling-stroke"`. Popover stays anchored to its pin through any zoom/pan via re-reading `viewBox.baseVal` at call time.

### Filters that work today
| Filter | Where it lives | Notes |
|---|---|---|
| Search | `#search` input | Live filter on input event, no debounce. Searches title, tooltip, summary, location.name, location.region, figures. Hits are highlighted via `<mark>`. |
| Year range slider | `#r-start` and `#r-end` | Two range inputs at `#timeline`. Hides pins outside the active range. Reset restores `[-500, 2025]`. |
| Threads bar | `#threads-bar` | Pills for each thread. Selecting a thread enters thread-mode: the right panel becomes the thread reader, pins highlighted in-thread, dim others. |
| Reset | `#reset` button | Clears search, restores year range, exits thread mode. Does NOT reset zoom (zoom has its own reset button). |

### Tests passing today
- `validate_events.py .` — schema + cross-reference + PIP. PASS with 6 soft warnings about summaries between 140–160 chars (hard cap is 160).
- `validate_threads.py .` — schema + cross-corpus event_id resolution. PASS.
- `render_test_v2.py` — clicks every pin, panel opens with right content. PASS.
- `render_test_popover.py` — 8 checks: popover opens, panel doesn't leak, Esc closes, double-click skips popover, shift-click skips, relation card opens both panel + popover, pin drift bounded by DODGE_RADIUS. PASS.
- `render_test_zoom.py` — 8 checks: viewBox starts correct, wheel zooms in, cursor anchor stable to within 1 vbu, drag pans, reset restores, +/− buttons disable at limits, title check. PASS.

---

## What's NOT built yet

In rough priority order:

1. **`validate_people.py`** — port `validate_events.py` with the two-kinds-of-step distinction. Required before authoring more people content.
2. **People UI.** Top-bar selector pill alongside Threads (mutually exclusive). Track rendering on map as numbered pins connected by a thin line, each person in a different accent colour from the Naklitechie palette. Vertical timeline reader in right panel. Click step → centre+zoom map on that pin, scroll reader. *Sized:* one full session.
3. **`events_mughal.json`** — Babur (1526) through Aurangzeb (1707). ~25 events. Stress-tests trans-regional layout (Babur's track will need to extend through Central Asia).
4. **`events_central_asia.json`** — Pre-Mughal Timurid events for Babur's biographical track to be wired without geographic gaps.
5. **Cluster badge for high-density regions.** Replace dodge with a numbered "+N" badge when ≥3 pins fall within MERGE_DIST. Click → chooser popover listing each pin's tooltip → click → regular popover. Touch-friendly. Defer until a region actually breaks visually.
6. **Sultanate events** — Ghurids through Lodis, ~20 events.
7. **Maurya / post-Maurya events** — stress-tests the BCE end of the year slider.
8. **Off-map handling for active threads/tracks.** The schema already supports `country: "OFF"`; UI needs an indicator when a thread or track step points off-map (e.g., Round Table Conferences in London). For now, off-map events render outside the visible viewport and clip — fine for atlases, broken when walking a thread.
9. **PNG companion** for social sharing per `STYLE-GUIDE.md` §9 — 16:8 or 16:9, 200 DPI, cream background.

---

## File inventory

```
india-history/
├── HANDOFF.md                      this document
├── SCHEMA.md                       events schema
├── THREADS_SCHEMA.md               threads schema
├── PEOPLE_SCHEMA.md                people schema (UI not built)
├── CLAUDE.md                       runbook for extending the asset
│
├── events_independence.json        12 events, 1885–1947
├── threads_independence.json       1 thread (Chauri Chaura chain)
├── people_freedom-fighters.json    5 people, 45 track steps  ← NEW
│
├── validate_events.py              schema + PIP validator (working)
├── validate_threads.py             schema + cross-corpus validator (working)
│   (validate_people.py)            NOT YET WRITTEN
│
├── build_map.py                    Datameet + world-atlas → SVG basemap + PIP polygons
├── build_html.py                   template + data → india-history.html
├── template.html                   HTML + CSS + JS, with __PLACEHOLDER__ tokens
│
├── render_test_v2.py               click-pin → panel-opens regression test
├── render_test_popover.py          popover system test (8 checks)
├── render_test_zoom.py             zoom + pan test (8 checks)
│
├── map_paths.json                  build_map.py output (basemap, inlined)
├── validator_boundaries.json       build_map.py output (PIP polygons, ~672 KB)
├── india-history.html              build_html.py output (the asset, ~187 KB)
│
└── datameet/                       cloned from github.com/datameet/maps (read-only here, populated locally)
    └── Country/india-soi.geojson   the authoritative India boundary
```

**Datameet boundary rule (non-negotiable):** for any India map, use Datameet, not Natural Earth or world-atlas. NE/world-atlas show PoK, Aksai Chin, and parts of Arunachal as outside India. Datameet shows them inside, which is the official Indian government representation. The build pipeline already enforces this — surrounds use world-atlas, India uses Datameet, India is drawn last so it sits on top.

---

## The five summary fields and when to use which

This is the most error-prone part of authoring. Each field has a specific job.

| Field | Length | Where it shows | Job |
|---|---|---|---|
| `title` | ≤60 chars | Pin's native browser tooltip headline; right panel header | Display name. Sentence case. No date in the title — the date goes in `tooltip`. |
| `tooltip` | ≤80 chars hard | Native pin hover (browser tooltip), popover-internal relation cards | One-line caption that *includes* a date or place anchor. Reads like a museum label. e.g. `"Jallianwala Bagh massacre, Amritsar, 1919"`. |
| `summary` | ≤160 chars hard | Popover card body, popover-internal relation cards | One sentence. The reader's first taste. Must stand alone. |
| `detail` | 80–150 words | Right panel body | Editorial paragraph. Direct, calibrated, named entities and numbers. Voice matters — this is where the prose carries weight. |
| `gloss` (on `caused_by` edges) | ≤200 chars (soft) | Relation card body in panel | The editorial sentence about *what* about the prior event led to this one. Written from the descendant's perspective. |
| `note` (on thread steps) | ≤200 chars (soft) | Thread reader step body | The thread author's per-step framing. Different from `gloss` because it's written for the thread's argument, not the underlying event. |
| `transition` (on thread steps) | ≤300 chars (soft) | Between thread steps | The prose bridge to the next step. `null` on the last step. |
| `note` (on people moments) | ≤300 chars (soft) | People reader step body | Biographical context, written from the person's life arc, not the event's logic. |
| `role` (on people event-refs) | ≤200 chars (soft) | People reader step body | The person's specific part in the referenced event. |

**Mistake to avoid:** stuffing `summary` with what should be in `detail`. Summary is one sentence, detail is the paragraph. If you can't stop at one sentence, that text belongs in detail.

---

## Vocabularies (validator-enforced)

```
era       = vedic | mahajanapada | maurya | post-maurya | gupta | early-medieval
          | sultanate | mughal | maratha | colonial | independence | republic

category  = political | military | religious | cultural | scientific | economic
          | dynastic | colonial-administration | resistance | reform

precision = day | month | year | decade | century

location  = point | city | region | route        (event location.type)

country   = IN PK BD NP BT LK AF UZ TJ TM KZ KG MM CN IR RU MN AE OM SA YE TH LA VN KH OFF
            (location.country, ISO alpha-2; OFF = outside the asset's bbox)

link.type   = wikipedia | primary | archive | related | secondary
source.type = scholarly | primary | secondary | reference

thread.kind = narrative | causal-chain | thematic | counterfactual

people track step.kind = event-ref | moment
```

To add a new value to any vocab: edit the schema doc + the validator's set + (if it affects validation) the relevant build script. All three or none — the validator is the contract.

---

## Click model summary (what the user expects)

```
Pin click (no modifier)        → popover (light scan; panel unchanged)
Pin shift-click                → panel opens (popover hidden)
Pin double-click               → panel opens (popover hidden)
Pin click again on same pin    → toggle popover off

"Read full entry →" in popover → panel opens (popover stays as locator)
Wikipedia ↗ in popover         → external tab

Relation card in panel         → panel switches AND popover opens for new pin
Thread step click              → panel switches AND popover opens for step's pin

Click outside popover          → popover closes
Esc                            → popover closes
Filter hides popover's pin     → popover auto-closes

Wheel on map                   → zoom anchored to cursor
Drag on map (not on pin)       → pan
Pinch on map (touch)           → zoom anchored to pinch centroid
Two-finger drag (touch)        → pan
+/−/↺ buttons (top-right)      → zoom in / out / reset

Drag ending over a pin         → suppressed; not treated as pin click
```

The pin / relation-card / thread-step click handlers all explicitly stop their click events from triggering the document-level click-outside handler. If you wire a new popover-triggering surface, add it to that exclusion list in `template.html`.

---

## Constraints (do not violate)

- **Single-file portability.** No CDNs at runtime, no build step on the user's end. The HTML must work from `file://`, `assets.chiragpatnaik.com`, and iOS Quick Look. All data inlined as JSON inside `<script>` between `DATA:BEGIN` and `DATA:END` markers — those markers are splice points for `build_html.py`; don't move them.
- **iOS Quick Look strips JavaScript.** `build_html.py` pre-renders static fallbacks for the threads bar and the map pins inside the SVG, so the asset previews correctly without JS. JS replaces the static content on page load.
- **Datameet boundary rule.** See above.
- **Naklitechie design system.** See `STYLE-GUIDE.md` in the project root. Cream surfaces, two type weights (400 / 500), no shadows, no gradients, country palette is canonical. Accent colours: `--purple #534AB7, --amber #BA7517, --rose #72243E, --blue #185FA5, --pink #D4537E`. Near-black `--cream-text #2C2A24`. Use these tokens.
- **Verified figures only.** Cross-check before setting `verified: true`. When in doubt, set `false` and let the UI tag it.
- **Pin dodge tuned in geography, not pixels.** `MERGE_DIST=3` (~22 km), `DODGE_RADIUS=5` (~37 km). Earlier values of 14 and 12 produced 88 km of displacement, enough to push pins across the Wagah border. Don't raise these without re-checking the Punjab cluster.
- **Zoom max=8.** Past 8, pin radii fall below click-target minimum.

---

## Open architectural questions

These are decisions I made under time pressure that I want you to revisit before they ossify.

1. **People moments — embedded vs extracted.** Currently moments live inline within each person's `track`. If two people share a private moment (Patel and Gandhi at Bardoli, say), the moment is duplicated. A `moments_*.json` extraction layer would dedup but adds a fourth file class. PEOPLE_SCHEMA.md recommends embed-for-v1; revisit when you hit a real shared-moment case.
2. **People accent colours.** Each person should render their track in a distinct colour for visual separation when multiple are loaded. The Naklitechie palette has 5 accent colours, which neatly matches the seed batch of 5. As the corpus grows past 5 people, either we colour-code by *role* (revolutionary, statesman, theorist) or generate per-person hashes from the id. Punt on this until UI build.
3. **Cluster badge vs hover-zoom.** Bhai asked for hover-zoom on clusters; I pushed back and proposed cluster badges instead. Bhai said "continue" rather than picking, which I read as "defer". When you build people UI, the cluster question will come up again because Gandhi alone has 13 track steps, several within ~50 km of each other. Cluster badge is the right answer — touch-friendly, simpler to implement. Don't build hover-zoom unless explicitly asked.
4. **Off-map UI when on a thread or track step.** Currently a step that points off-map renders the pin outside the visible viewport and clips. For Round Table Conferences in London or Ambedkar at Columbia, this is wrong — the user is told *here* the next step happened, but sees nothing on the map. Need an "elsewhere" indicator at the map edge. Build before authoring more off-map content.
5. **Title attribute on pins.** Currently each `<g class="pin">` has a `<title>` element with `title · date`. Native browser hover. The popover system replaces the click affordance but native hover is still the only quick-scan tool. Should the native `<title>` use the new `tooltip` field instead of `title + date`? Probably yes — they're more carefully written. Trivial change, do it on the next pass.
6. **Search across people and threads.** Search currently only matches event fields. With people and threads added, the search probably should index both — typing "Gandhi" should surface his person card and his event roles. Schema is in place (every person has tooltip, summary, etc.) but search code isn't wired.

---

## Pickup checklist for Claude Code

When you start the next session, in this order:

1. **Read this document.** Then `SCHEMA.md`, `THREADS_SCHEMA.md`, `PEOPLE_SCHEMA.md`, `CLAUDE.md`. The schemas are the contract; CLAUDE.md is the runbook.
2. **Reproduce the working state.** `python3 build_map.py && python3 build_html.py && python3 render_test_popover.py && python3 render_test_zoom.py`. All four should succeed. If any fail, fix before adding features — the existing tests are the safety net.
3. **Write `validate_people.py`.** Use `validate_events.py` as the template. Two-kinds-of-step branch: for `event-ref`, resolve `event_id` against the corpus and require `role`; for `moment`, require `id` (unique within the track), `tooltip`, `summary`, `date`, `location`, and run the same PIP check used for events. Then run it against `people_freedom-fighters.json` and fix any seed issues that surface.
4. **Build the People UI.** PEOPLE_SCHEMA.md has the rendering sketch under "What the UI renders". The infrastructure already exists — Salt March's route demonstrates the connecting-line treatment, the threads reader demonstrates the vertical-timeline pattern. The new code is a top-bar selector, a track renderer that combines route + numbered pins, and a reader pattern that shows `note` and `role` per step.
5. **Add `events_mughal.json`** when you're ready for content rather than infrastructure work. Probably its own session.

---

## What I'd do differently if starting over

- **Scope split earlier.** I should have moved to Claude Code after the popover work, not three sessions later. The error rate on `str_replace` calls climbs sharply once a single file passes ~40 KB.
- **Schema first, content second, UI last.** I followed this for events and threads. For people I drafted schema and seed in the same session, which mostly worked but compressed the editorial pass — re-read the seed in Claude Code with fresh eyes before authoring more.
- **Render tests as you build.** Every time a new interaction lands (popover, zoom, eventually People), write the render test in the same session. The test catches regressions faster than human inspection.
- **Don't conflate `summary` with `detail`.** Several events still have summaries between 140–160 chars (validator passes but warns) because the line between "one sentence" and "two sentences" is fuzzy. The hard cap is doing real work; respect it as a forcing function.

---

## Bhai's working preferences (relevant to the asset)

- Brisk communication. Short imperative inputs, expects judgment calls.
- Wants verified figures, not flags. Wikipedia is the rabbit-hole link, not the source.
- Editorial voice: direct, calibrated, slightly opinionated. Numbers and named entities over adjectives. No mid-sentence bolding in body copy. No emoji.
- Files batched at session end with `present_files`. He doesn't read intermediate state.
- "% change in seats" type framing is a known anti-pattern — share-of-house is the right metric. Apply the same scepticism elsewhere.
- iOS Quick Look fallback matters because he previews assets on phone before publishing.

---

End of handoff.
