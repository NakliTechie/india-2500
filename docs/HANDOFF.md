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
│   ├── events/events_*.json       61 events across 10 campaign files
│   ├── threads/threads_*.json     2 threads: Chauri Chaura, Babur road-to-Panipat
│   ├── people/people_*.json       6 people (5 freedom fighters + Babur)
│   └── collections/collections_*.json   3 collections: Babur's road, Founding moments, First-person works
│
├── validators/                    schema enforcement, run on every PR via CI
│   ├── validate_events.py         schema + cross-reference + PIP + tag format
│   ├── validate_threads.py        schema + corpus event_id resolution
│   ├── validate_people.py         schema + two-kind step + PIP
│   └── validate_collections.py    schema + member resolution (event id OR tag selector)
│
├── build/                         pipeline + cached basemap
│   ├── build_map.py               Datameet + world-atlas → SVG basemap (slow, rare)
│   ├── build_html.py              template + data → web/india-history.html AND web/shell.html
│   ├── build_png.py               matplotlib → web/india-history.png + .square.png
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
│   ├── render_test_popover.py     popover system (9 checks)
│   ├── render_test_zoom.py        zoom + pan (8 checks)
│   ├── render_test_people.py      people UI (10 checks)
│   ├── render_test_collections.py collections UI (13 checks)
│   └── artifacts/                 (gitignored — screenshots from test runs)
│
├── contribute/                    GUIDED FORMS for non-technical contributors
│   ├── index.html                 landing + editorial guidance
│   ├── event.html                 event form with Leaflet map picker (now incl. tags)
│   ├── thread.html                thread builder with searchable event picker
│   ├── person.html                person form with track-step builder
│   ├── collection.html            collection builder (event search + tag selector)
│   └── lib/
│       ├── validators.js          JS port of validators (UX layer; Python is authoritative)
│       ├── submit.js              Download / open-PR / open-issue helpers (no OAuth)
│       └── styles.css             shared Naklitechie shell
│
├── docs/                          this document, schemas, runbook, contributing
│   ├── HANDOFF.md                 you are here
│   ├── CLAUDE.md                  AI-assisted development runbook
│   ├── CONTRIBUTING.md            for human contributors
│   ├── SCHEMA.md                  events schema (the contract; now includes tags)
│   ├── THREADS_SCHEMA.md          threads schema
│   ├── PEOPLE_SCHEMA.md           people schema
│   └── COLLECTIONS_SCHEMA.md      collections schema
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
- **Tags:** optional `tags[]` field, free-form kebab-case. Drives filtering and **collection membership** (see Collections below). Distinct from `category` — categories are controlled vocab + pin colour; tags are open-ended thematic markers.
- **Validator:** `validators/validate_events.py`. Schema enforcement + cross-reference + point-in-polygon (PIP) check confirming each pin's lat/lon falls inside its declared country + tag format check + corpus-level warning on single-use tags.
- **Corpus today:** 61 events spanning 1357–1958 CE.
  - `events_sultanate.json` — 1 event (Barani 1357; ~20 Ghurids→Lodis to come)
  - `events_central_asia.json` — 6 events, 1494–1524 (Babur's Timurid arc, all tagged `babur-arc`)
  - `events_mughal.json` — 26 events, 1526–1707 (Babur → Aurangzeb; +Baburnama / Akbarnama / Tuzuk-i-Jahangiri memoirs)
  - `events_sur.json` — 2 events, 1539–1556 (Suri interregnum)
  - `events_odisha.json` — 1 event (Madala Panji; Paika rebellion, Konark, etc. to come)
  - `events_south_india.json` — 1 event (Tipu Khwabnama; Vijayanagara / Wodeyars / Anglo-Mysore to come)
  - `events_reform.json` — 4 events (Rammohan Roy, Pandita Ramabai, Vivekananda, Tagore — 19th-c reform-era cluster)
  - `events_1857.json` — 1 event (Lakshmibai letters; Doctrine of Lapse / Delhi / Lucknow / Kanpur to come)
  - `events_princely_states.json` — 1 event (Sultan Jahan Begum; Hyderabad / Travancore / Kashmir to come)
  - `events_independence.json` — 18 events, 1885–1958 (+Lajpat Rai / Gandhi Experiments / Sarojini / Ambedkar Annihilation / Azad)

### Threads
- **Schema:** `docs/THREADS_SCHEMA.md`. Each step references an event by id, carries a `note` (per-step framing) and a `transition` (prose bridge to next step; `null` on last). Coda required (the closing argument; ≤150 words).
- **Validator:** `validators/validate_threads.py`. Resolves event_ids across the entire events corpus.
- **Corpus today:** 2 threads — Chauri Chaura (independence) and Babur's road (Central Asia).

### Collections (NEW — set-shaped groupings)
- **Schema:** `docs/COLLECTIONS_SCHEMA.md`. A collection has `id`, `title`, `summary`, optional `subtitle` + `framing` (≤200 words), and `members[]`.
- **Members are heterogeneous:** each entry is either `{kind: "event", id}` (explicit) or `{kind: "tag", tag}` (selector — pulls every event whose `tags[]` contains the named tag). Mixing kinds in one `members[]` is fine; the renderer dedups and sorts chronologically.
- **Sets vs sequences:** collections are sets (no per-member notes, no transitions). Threads are sequences (notes + transitions per step). The cheap-to-author bit is deliberate — collections are how we cover cross-cutting catalogues without paying a thread's editorial overhead.
- **Validator:** `validators/validate_collections.py`. Hard rules include: every event id resolves; every tag selector matches ≥1 event in the corpus (no empty selectors); soft warning when the effective member count after expansion + dedup is <3.
- **UI:** Third pill row beneath People (`Collections — [pill] [pill] Exit collection`). Click a pill → reader panel renders title, subtitle, summary, optional framing block, member count + cards (tooltip + date for each), sources. Member pins on the map highlight in `--accent-blue` via the `.in-collection` mode class on `#map`. Cluster pins inherit the highlight if any member sits inside them. Mutually exclusive with Threads + People.
- **Corpus today:** 3 collections —
  - `collections_central_asia.json#baburs-road-from-andijan-to-lahore` — single tag selector `babur-arc` → 6 members.
  - `collections_subcontinent.json#founding-moments-of-modern-india` — explicit list of 6 events spanning 1540–1885.
  - `collections_memoirs.json#first-person-works-of-the-subcontinent` — single tag selector `memoir` → 18 members spanning 1357–1958. The seeded memoir batch (commit reference: this batch) gives the collection real range across Sultanate, Mughal, regional/institutional (Madala Panji, Tipu Khwabnama), 19th-c reform, 1857, princely states, and Big-Three independence.

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

### Tests passing today (9/9)
- `validators/validate_events.py` — PASS (~20 soft warnings on summaries 140–160 chars; 2 single-use-tag warnings on `prison-writing`)
- `validators/validate_threads.py` — PASS
- `validators/validate_people.py` — PASS (5 soft warnings)
- `validators/validate_collections.py` — PASS
- `tests/render_test_v2.py` — PASS
- `tests/render_test_popover.py` — PASS (9 checks)
- `tests/render_test_zoom.py` — PASS (8 checks)
- `tests/render_test_people.py` — PASS (10 checks)
- `tests/render_test_collections.py` — PASS (13 checks)

---

## What's NOT built yet

In rough priority order:

1. **Round out the seeded campaign files.** The memoirs batch seeded six new files with 1–4 events each — they want their full content: Ghurids→Lodis for `events_sultanate.json`, Paika rebellion + Konark for `events_odisha.json`, Vijayanagara + Anglo-Mysore for `events_south_india.json`, Delhi / Lucknow / Kanpur / Awadh for `events_1857.json`, Hyderabad / Travancore / Kashmir for `events_princely_states.json`, more reformers for `events_reform.json`.
2. **Maurya / post-Maurya events** — stress-tests the BCE end of the year slider.
3. **More memoirs** to round out the first-person-works collection (currently 18 members; deferred queue below).
4. **More cross-cutting collections.** Infra shipped; highest-leverage next ones: **women in independence** (Sarojini, Lakshmibai, Pandita Ramabai, Sultan Jahan are already in the corpus and would seed it cleanly), **rebellions reframe** (1857 file plus Birsa Munda, Paika, Santhal etc.), **prison-writing** (Lajpat Rai + Nehru already tagged `prison-writing`).
5. **More Mughal biographical tracks** — Akbar, Shah Jahan, Aurangzeb.
6. **GitHub publishing** — push to `naklitechie/india-2500`, enable Pages, optional CNAME for `assets.chiragpatnaik.com`.

### Deferred memoirs (queue for first-person-works expansion)
Padshahnama (Shah Jahan court chronicle); Ibn Battuta's *Rihla*; Isami's *Futuh-us-Salatin* (Bahmani perspective); Aurobindo's *Karakahini / Tales of Prison Life* (1909); Phule's *Gulamgiri* (1873); Cornelia Sorabji's *India Calling* (1934); Bose's *The Indian Struggle* (1935/1948); Kamaladevi Chattopadhyay's *Inner Recesses, Outer Spaces* (1986); Verrier Elwin's *Tribal World* (1964); Bhagat Singh prison notebook + jail letters; Naoroji's *Poverty and Un-British Rule*; Ahilyabai Holkar's administrative correspondence; Vamshavalis (Nepali royal genealogies); Periyar / Iqbal / Sri Aurobindo first-person works.

**Deliberately excluded:** Savarkar's *Maazi Janmathep / My Transportation for Life*.

### Known follow-ups (small, parked)
- `contribute/thread.html` and `contribute/collection.html` hardcode the events corpus file list. The forms now miss events from the 6 new files in their search-as-you-type and tag-suggest. `data/manifest.json` is already written by `build_html.py`; the forms just need to fetch it instead of their hardcoded array.
- `data/people/people_mughal-emperors.json#babur.track[11]` has a step year (1539) that postdates Babur's death (1530). Validator surfaces this as a warning.

### Content slices to explore (candidates for collections + dedicated event/people files)

These surfaced from the Babur work and earlier discussions. Each is either a **collection** (cross-cutting, would benefit from the tags+collections hybrid in #1), an **event campaign file** (chronological, like the existing events_mughal.json), or a **people group** (like people_freedom-fighters.json).

**Cross-cutting collections (best served by collections slice once #1 lands):**
- **Women in the independence movement** — Sarojini Naidu, Aruna Asaf Ali, Bhikaji Cama, Rani Lakshmibai, Begum Hazrat Mahal. Tag: `women-leaders`.
- **Rebellions, pre-1857 included** — Sannyasi-Fakir 1770s, Vellore 1806, Paika 1817, Indigo 1859, Santhal 1855, 1857 itself, Birsa Munda 1899, Moplah 1921, Chittagong 1930. Tag: `rebellion`. Important corrective to the "1857 was the first" textbook framing.
- **INC conventions** — annual sessions 1885 onwards. Probably too granular for individual events; better as a single "INC sessions catalogue" entry with a list, OR as a collection with each major session (Lahore 1929, Tripuri 1939, Karachi 1931) as separate events.
- **First-person memoirs** — primary-source autobiographical works. Baburnama, Akbarnama, Tuzuk-i-Jahangiri, Ambedkar's *Annihilation of Caste*, Nehru's *Discovery of India*, Gandhi's *Story of My Experiments with Truth*. Tag: `memoir`.
- **Indian history beyond the subcontinent** — Babur (Hindu Kush), Gandhi (South Africa), Ambedkar (NYC, London), Bose (Berlin, Tokyo, Singapore), Krishna Menon at the UN. Tag: `diaspora` or `off-map-significant`.
- **Founding moments of major institutions** — INC 1885, Khalsa 1699, Sabarmati 1917, Aligarh 1875, Banaras Hindu University 1916, Visva-Bharati 1921, IIT Kharagpur 1951. Tag: `institution-founding`.
- **Place-as-biographical-locus** — Bagh-e-Babur, Fatehpur Sikri, Sabarmati Ashram, Sevagram, Wardha. Buildings/cities that bound a person's arc.

**Dedicated event campaign files (chronological additions):**
- **`events_maratha.json`** — Shivaji 1674 → Panipat III 1761 → Maratha confederacy through 1818. Stress-tests Deccan density.
- **`events_sikh.json`** — Banda Singh Bahadur, Ranjit Singh, Anglo-Sikh wars 1845–49. Punjab campaign.
- **`events_bengal.json`** — Plassey 1757, Buxar 1764, Permanent Settlement 1793, Bengal Renaissance, partition aftermath. Long arc.
- **`events_south_india.json`** — Vijayanagara, Tipu Sultan, Anglo-Mysore wars, Travancore, Madras Presidency.
- **`events_northeast.json`** — Ahom kingdom, British annexations, Naga rebellion, AFSPA. Historically under-represented.
- **`events_post_independence.json`** — 1947 onwards: states' reorganisation 1956, 1962/1965/1971 wars, emergency 1975–77, Mandal 1990, liberalisation 1991, etc.
- **`events_economic.json`** — currency reforms (Sher Shah → modern rupee), zamindari, Permanent Settlement, Swadeshi, planning era, 1991. Maybe better as tag than file — most economic events overlap with political ones.

**Dedicated people files:**
- **`people_mughal-emperors.json`** (started, has Babur) — Akbar, Shah Jahan, Aurangzeb queued.
- **`people_marathas.json`** — Shivaji, Sambhaji, Bajirao I, Nana Saheb, Mahadji Scindia.
- **`people_sikh-gurus-and-rulers.json`** — Guru Nanak through Gobind Singh, then Banda Bahadur and Ranjit Singh.
- **`people_political-leaders-post-1947.json`** — Patel, Maulana Azad, Indira, Vajpayee, Manmohan Singh.
- **`people_thinkers-and-reformers.json`** — Rammohan Roy, Vidyasagar, Phule, Periyar, Tagore, Iqbal, Sri Aurobindo.
- **`people_scientists.json`** — CV Raman, Ramanujan, Bose (J.C.), Saha, Homi Bhabha, Vikram Sarabhai.
- **`people_artists-and-writers.json`** — Tagore (overlaps with thinkers), Premchand, Manto, MF Husain, Ravi Shankar, Bismillah Khan.

**Latent thread ideas:**
- Akbar's religious experiment (Ibadat Khana → Din-i-Ilahi → Aurangzeb's reversal)
- The arc of the Sikh community (Arjan execution → Hargobind militarises → Tegh Bahadur execution → Khalsa → Banda Bahadur → Ranjit Singh's empire)
- The economic logic of partition (Bengal 1905 → Direct Action Day → 1947 — already partly covered by Chauri Chaura thread)
- Three battles of Panipat as a political compass (1526 founds Mughals, 1556 restores Mughals, 1761 ends Maratha hegemony)

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
