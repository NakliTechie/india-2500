# India — 2500 years to the Republic — handoff

This document captures the entire state of the project. Read it cold and you should be able to keep building, reviewing PRs, or onboarding a contributor.

---

## What the project is

A validator-enforced, browser-renderable atlas of subcontinental history. Three slices:

- **Events** — first-class historical events (battles, treaties, foundings, deaths) with editorial summaries, causal links, and pin-on-map placements.
- **Threads** — curated walks through sequences of events. Each thread makes an argument; each step has author-written prose.
- **People** — biographical tracks. Each step is either an existing event (event-ref) or a private moment (location not in the events corpus).

**Brand:** Naklitechie / Chirag Patnaik
**Target:** `assets.chiragpatnaik.com/india-history.html` (and `/shell.html` for runtime-fetch)
**Editorial stance:** neutral, data-grounded, named entities and numbers over adjectives, no textbook flattening
**Audience:** Indian readers, but the design system and the Datameet boundary are correct globally

---

## Repository layout

```
2500/                              the repo (will be pushed as naklitechie/india-2500)
├── README.md                      project overview, quick start, contributing pointer
├── .gitignore                     datameet/, package/, .claude/, tests/artifacts/
│
├── data/                          editorial content — what contributors PR
│   ├── events/events_*.json       37 events: independence, mughal, sur
│   ├── threads/threads_*.json     1 thread: Chauri Chaura
│   └── people/people_*.json       5 people, 45 track steps
│
├── validators/                    schema enforcement, run on every PR via CI
│   ├── validate_events.py         schema + cross-reference + PIP
│   ├── validate_threads.py        schema + corpus event_id resolution
│   └── validate_people.py         schema + two-kind step + PIP
│
├── build/                         pipeline + cached basemap
│   ├── build_map.py               Datameet + world-atlas → SVG basemap (slow, rare)
│   ├── build_html.py              template + data → web/india-history.html AND web/shell.html
│   ├── map_paths.json             cached basemap (committed)
│   └── validator_boundaries.json  cached PIP polygons (committed, ~700 KB)
│
├── web/                           the asset itself
│   ├── template.html              source HTML/CSS/JS with __PLACEHOLDER__ tokens
│   ├── india-history.html         BUILT single-file asset, deployable as-is
│   └── shell.html                 BUILT runtime-fetch version (loads /data and /build)
│
├── tests/                         Playwright regression tests
│   ├── render_test_v2.py          click pins → panel content
│   ├── render_test_popover.py     popover system (8 checks)
│   ├── render_test_zoom.py        zoom + pan (8 checks)
│   ├── render_test_people.py      people UI (10 checks)
│   └── artifacts/                 (gitignored — screenshots from test runs)
│
├── contribute/                    GUIDED FORMS for non-technical contributors
│   ├── index.html                 landing + editorial guidance
│   ├── event.html                 event form with Leaflet map picker
│   ├── thread.html                thread builder with searchable event picker
│   ├── person.html                person form with track-step builder
│   └── lib/
│       ├── validators.js          JS port of validators (UX layer; Python is authoritative)
│       ├── submit.js              Download / open-PR / open-issue helpers (no OAuth)
│       └── styles.css             shared Naklitechie shell
│
├── docs/                          this document, schemas, runbook, contributing
│   ├── HANDOFF.md                 you are here
│   ├── CLAUDE.md                  AI-assisted development runbook
│   ├── CONTRIBUTING.md            for human contributors
│   ├── SCHEMA.md                  events schema (the contract)
│   ├── THREADS_SCHEMA.md          threads schema
│   └── PEOPLE_SCHEMA.md           people schema
│
├── .github/
│   ├── workflows/validate.yml     CI: validators + render tests on every PR
│   ├── ISSUE_TEMPLATE/            correction, new-event, editorial
│   └── PULL_REQUEST_TEMPLATE.md
│
├── datameet/                      EXTERNAL — `git clone github.com/datameet/maps`
└── package/                       EXTERNAL — `curl unpkg.com/world-atlas@2/countries-50m.json`
```

---

## What's built and shipping

### Events
- **Schema:** `docs/SCHEMA.md`. Hard caps enforced by validator: tooltip ≤80, summary ≤160, detail 80–150 words.
- **Causal layer:** `caused_by` + `gloss` per edge. `led_to` derived as inverse at runtime, never authored. `part_of` for hierarchical containment without gloss. Multi-parent / multi-child both supported. Cross-file references work — `events_mughal.json` can have a `caused_by` referencing `events_independence.json`.
- **Validator:** `validators/validate_events.py`. Schema enforcement + cross-reference + point-in-polygon (PIP) check confirming each pin's lat/lon falls inside its declared country.
- **Corpus today:** 37 events spanning 1526–1947 CE.
  - `events_independence.json` — 12 events, 1885–1947
  - `events_mughal.json` — 23 events, 1526–1707 (Babur → Aurangzeb)
  - `events_sur.json` — 2 events, 1539–1556 (Suri interregnum, separate file per the granular-dynasties principle)

### Threads
- **Schema:** `docs/THREADS_SCHEMA.md`. Each step references an event by id, carries a `note` (per-step framing) and a `transition` (prose bridge to next step; `null` on last). Coda required (the closing argument; ≤150 words).
- **Validator:** `validators/validate_threads.py`. Resolves event_ids across the entire events corpus.
- **Corpus today:** `threads_independence.json`, one thread on Chauri Chaura.

### People (UI shipped)
- **Schema:** `docs/PEOPLE_SCHEMA.md`. Person has lifespan + a `track[]`. Each track step is `kind: "event-ref"` (with `role`) or `kind: "moment"` (own date, location, summary, note). Moments are intentionally lighter than events.
- **Validator:** `validators/validate_people.py`. Schema + cross-corpus event_id resolution + PIP on every moment + birth/deathplace + chronological order check.
- **Corpus today:** `people_freedom-fighters.json`, 5 people with 45 track steps — Gandhi (13), Nehru (9), Bhagat Singh (6), Ambedkar (10), Jinnah (9).
- **UI:** Multi-select people pills bar (mutually exclusive with threads). Each person gets a Rangrez accent colour assigned by load order (KHADI/AAKASH/KUMKUM/NEEL/MOR for the 5 seed people). Tracks render as numbered pins + dashed connecting line in the person's colour. Vertical timeline reader in the right panel. Off-map steps appear in a single table below the map (one row per step, grouped by person), with click-through to the popover.

### Map
- **Pipeline:** `build/build_map.py` reads Datameet `india-soi.geojson` (PoK/Aksai Chin/J&K correctly inside India) plus world-atlas `countries-50m.json` for surrounding states. Spherical Lambert Conformal Conic (`lat_1=20, lat_2=40, lat_0=30, lon_0=78, R=6_371_000`).
- **Outputs:** `build/map_paths.json` (basemap, committed) and `build/validator_boundaries.json` (PIP polygons, committed).

### Build pipeline
`build/build_html.py` reads template + data + cached basemap, writes **two** files:
- `web/india-history.html` — single-file, all data inlined, iOS Quick Look-friendly. The deployable asset.
- `web/shell.html` — runtime-fetch version. Empty data placeholders + a boot script that fetches `/data/*` and `/build/*` over HTTP, then calls `bootRenders()`. For hosted deployment where data updates daily.

The shared `template.html` uses `let` (not `const`) for the four data globals and a single `__BOOT_INVOCATION__` placeholder that controls how `bootRenders()` is called.

### Interactivity
- **Click model:** Single-click pin → popover. Shift-click or double-click → panel direct (skip popover). "Read full entry →" in popover → opens panel. Relation card click → both panel update AND popover swaps to the new pin. Thread / track step click → same.
- **Popover:** Anchored card on desktop, bottom sheet on mobile (<920px). Auto-hides when its pin gets filtered out or panned off-screen.
- **Zoom + pan:** Wheel zooms anchored to cursor. Drag pans. Pinch + two-finger drag on touch. `+/−/↺` controls top-right of map. Pin radii inverse-scale with zoom. Routes use `non-scaling-stroke`. Popover stays anchored to its pin through any zoom/pan.

### Contribute forms (NEW)
- Static HTML pages under `contribute/` for non-technical contributors.
- Each form embeds JS validators (length caps, ID format, vocab) so errors surface as the contributor types.
- Three submit paths: Download JSON (primary, no GitHub account needed), Open as Pull Request (uses GitHub create-file URL — auto-forks if needed), Open as Issue.
- Forms fetch the live events corpus over HTTP for cross-reference (thread step picker, event-ref autocomplete).

### Tests passing today (7/7)
- `validators/validate_events.py` — PASS (20 soft warnings on summaries 140–160 chars)
- `validators/validate_threads.py` — PASS
- `validators/validate_people.py` — PASS (5 soft warnings)
- `tests/render_test_v2.py` — PASS
- `tests/render_test_popover.py` — PASS (8 checks)
- `tests/render_test_zoom.py` — PASS (8 checks)
- `tests/render_test_people.py` — PASS (10 checks)

---

## What's NOT built yet

In rough priority order:

1. **`events_central_asia.json`** — Pre-Mughal Timurid events for Babur's biographical track to be wired without geographic gaps.
2. **Babur biographical track** in `people_*.json` — once Central Asia is in.
3. **Babur thread** — `narrative` kind, ~6 steps from Ferghana to Panipat. Depends on #1.
4. **Sultanate events** — Ghurids through Lodis, ~20 events.
5. **Maurya / post-Maurya events** — stress-tests the BCE end of the year slider.
6. **GitHub publishing** — push to `naklitechie/india-2500`, enable Pages, optional CNAME for `assets.chiragpatnaik.com`. Tooling is ready; needs decision + execution.

---

## The five summary fields and when to use which

| Field | Length | Where it shows | Job |
|---|---|---|---|
| `title` | ≤60 chars | Pin's native browser tooltip headline; right panel header | Display name. Sentence case. No date in the title — the date goes in `tooltip`. |
| `tooltip` | ≤80 chars hard | Native pin hover, popover-internal relation cards | One-line caption with a date or place anchor. Reads like a museum label. |
| `summary` | ≤160 chars hard | Popover card body, popover-internal relation cards | One sentence. Stands alone. |
| `detail` | 80–150 words | Right panel body | Editorial paragraph. Direct, calibrated. |
| `gloss` (on `caused_by`) | ≤200 chars (soft) | Relation card body in panel | Editorial sentence about *what* about the prior event led to this one. From the descendant's perspective. |
| `note` (thread step) | ≤200 chars (soft) | Thread reader step | Per-step framing for the thread's argument. |
| `transition` (thread step) | ≤300 chars (soft) | Between thread steps | Bridge to the next step. `null` on last step. |
| `note` (people moment) | ≤300 chars (soft) | People reader step | Biographical context, written from the person's life arc. |
| `role` (people event-ref) | ≤200 chars (soft) | People reader step | Person's specific part in the referenced event. |

**Most error:** stuffing `summary` with what should be in `detail`. Summary is one sentence; detail is the paragraph. If you can't stop at one sentence, the text belongs in detail.

---

## Vocabularies (validator-enforced)

```
era       = vedic | mahajanapada | maurya | post-maurya | gupta | early-medieval
          | sultanate | mughal | maratha | colonial | independence | republic

category  = political | military | religious | cultural | scientific | economic
          | dynastic | colonial-administration | resistance | reform

precision = day | month | year | decade | century

location.type = point | city | region | route

country   = IN PK BD NP BT LK AF UZ TJ TM KZ KG MM CN IR RU MN AE OM SA YE
            TH LA VN KH OFF
            (ISO alpha-2; OFF = outside the asset's bbox)

link.type   = wikipedia | primary | archive | related | secondary
source.type = scholarly | primary | secondary | reference

thread.kind = narrative | causal-chain | thematic | counterfactual

people track step.kind = event-ref | moment
```

To add a new value: edit the schema doc + the validator's set + the contribute/lib/validators.js port. **All three or none** — the validator is the contract.

---

## Click model (what the user expects)

```
Pin click (no modifier)        → popover (light scan; panel unchanged)
Pin shift-click                → panel opens (popover hidden)
Pin double-click               → panel opens (popover hidden)
Pin click again on same pin    → toggle popover off

"Read full entry →" in popover → panel opens (popover stays as locator)
Wikipedia ↗ in popover         → external tab

Relation card in panel         → panel switches AND popover opens for new pin
Thread step click              → panel switches AND popover opens for step's pin

People pill click              → toggle person in active set (multi-select)
                                 (clears any active thread)
Threads pill click             → set active thread, clears active people
Track-pin click (event-ref)    → event popover with role + Read-full
Track-pin click (moment)       → moment popover (own content, no event)
Off-map row click              → popover anchored to the row

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

Click handlers in `template.html` exclude `.pin`, `.track-pin`, `.relation-card`, `.thread-step`, `.people-reader .track-step`, `.offmap-panel li` from the document-level click-outside dismiss. If you add a new popover-triggering surface, add it to that exclusion list.

---

## Constraints (do not violate)

- **Single-file portability of `india-history.html`.** No CDNs at runtime, no build step on the user's end. Works from `file://`, `assets.chiragpatnaik.com`, and iOS Quick Look. All data inlined as JSON. `shell.html` is the runtime-fetch alternative for hosted use; it does NOT have these constraints.
- **iOS Quick Look strips JavaScript.** `build_html.py` pre-renders static fallbacks for the threads bar, the people bar, and the map pins inside the SVG, so `india-history.html` previews correctly without JS.
- **Datameet boundary rule.** For any India map, use Datameet, not Natural Earth or world-atlas. NE/world-atlas show PoK, Aksai Chin, and parts of Arunachal as outside India. Datameet shows them inside, which is the official representation. The build pipeline already enforces this — surrounds use world-atlas, India uses Datameet, India is drawn last so it sits on top.
- **Naklitechie design system.** Cream surfaces, two type weights (400 / 500), no shadows, no gradients, country palette canonical. Accent colours: `--purple #534AB7, --amber #BA7517, --rose #72243E, --blue #185FA5, --pink #D4537E`. Near-black `--cream-text #2C2A24`. Per-person accents from Rangrez India · NORTH palette.
- **Verified figures only.** Cross-check ≥2 sources before `verified: true`. When in doubt, `false` and let the UI tag it.
- **Pin dodge tuned in geography, not pixels.** `MERGE_DIST=3` (~22 km), `DODGE_RADIUS=5` (~37 km). Don't raise without re-checking the Punjab cluster (Wagah border).
- **Zoom max=8.** Past 8, pin radii fall below click-target minimum.
- **Granular dynasties.** Don't fold smaller / shorter dynasties into bigger neighbours for narrative convenience. Sur dynasty = own file. Asaf Jah = own file when added. See `feedback_granular_history.md` in auto-memory.

---

## Pickup checklist for the next session

1. **Run the suite to confirm baseline:**
   ```bash
   for v in validators/validate_*.py; do python3 "$v"; done
   for t in tests/render_test_*.py; do python3 "$t"; done
   ```
   All 7 should PASS.

2. **Skim the auto-memory `MEMORY.md` index** for project-level context that's not in the repo (granular-dynasties principle, etc.).

3. **Pick from `What's NOT built yet` above.** Cluster badge + PNG companion are the next infra items; Central Asia / Babur / Sultanate / Maurya are the next content batches; GitHub publishing is the path to actually being live.

4. **For content additions:** the contribute forms (`contribute/event.html` etc.) are the easiest way to author new entries — they validate as you type and download a JSON file you drop into `data/`.

---

## Bhai's working preferences

- Brisk communication. Short imperative inputs, expects judgment calls.
- Wants verified figures, not flags. Wikipedia is the rabbit-hole link, not the source.
- Editorial voice: direct, calibrated, slightly opinionated. Numbers and named entities over adjectives. No mid-sentence bolding in body copy. No emoji.
- iOS Quick Look fallback matters because he previews assets on phone before publishing.
- "% change in seats" type framing is a known anti-pattern — share-of-house is the right metric. Apply the same scepticism elsewhere.
- Public-repo, community-contribution oriented. The contribute forms exist for a reason — non-technical contributors are a real audience.

---

End of handoff.
