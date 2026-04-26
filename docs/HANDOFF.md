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
│   ├── events/events_*.json       99 events across 13 campaign files
│   ├── threads/threads_*.json     2 threads: Chauri Chaura, Babur road-to-Panipat
│   ├── people/people_*.json       6 people (5 freedom fighters + Babur)
│   ├── collections/collections_*.json   5 collections (Babur's road, Founding moments, First-person works, Women shapers, Rebellions)
│   ├── places/places_*.json       12 places (Delhi, Agra, Lahore, Calcutta, Bombay, Pune, Hyderabad, Murshidabad, Sabarmati, Srirangapatna, Vellore, Puri)
│   └── polities/polities_*.json   9 polities (Delhi Sultanate, Bahmani, Sur, Mughal, Mysore, EIC, British Raj, Hyderabad State, Republic of India)
│
├── validators/                    schema enforcement, run on every PR via CI
│   ├── validate_events.py         schema + cross-reference + PIP + tag format
│   ├── validate_threads.py        schema + corpus event_id resolution
│   ├── validate_people.py         schema + two-kind step + PIP
│   ├── validate_collections.py    schema + member resolution (event id OR tag selector)
│   ├── validate_places.py         schema + PIP + auto-derived gather count check
│   └── validate_polities.py       schema + events[] resolution + capitals place-id resolution
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
│   ├── render_test_collections.py collections UI (22 checks)
│   ├── render_test_places.py      places UI (23 checks)
│   ├── render_test_polities.py    polities UI (23 checks; capital-place link cross-nav)
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
│   ├── COLLECTIONS_SCHEMA.md      collections schema
│   ├── PLACES_SCHEMA.md           places schema (coordinate-anchored event gathers)
│   └── POLITIES_SCHEMA.md         polities schema (regime-shaped institutional spines)
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
- **Corpus today:** 99 events spanning 1192–1958 CE.
  - `events_sultanate.json` — 20 events, 1192–1517 (Tarain through Ibrahim Lodi; 5 dynasties + Barani memoir)
  - `events_central_asia.json` — 6 events, 1494–1524 (Babur's Timurid arc, all tagged `babur-arc`)
  - `events_mughal.json` — 26 events, 1526–1707 (Babur → Aurangzeb; + Mughal court chronicle memoirs)
  - `events_sur.json` — 2 events, 1539–1556 (Suri interregnum)
  - `events_bengal.json` — 3 events (Sannyasi-Fakir, Faraizi, Indigo; Tebhaga / Renaissance / partition aftermath to come)
  - `events_chotanagpur.json` — 3 events (Kol, Santhal Hool, Birsa Munda Ulgulan)
  - `events_northeast.json` — 2 events (Khasi Rebellion, Heraka/Gaidinliu; Ahom / Naga nationalism to come)
  - `events_odisha.json` — 3 events (Madala Panji + Paika + Khond)
  - `events_south_india.json` — 5 events (Tipu Khwabnama + Vellore + Moplah + Rampa + Vaikom)
  - `events_reform.json` — 6 events (Rammohan Roy, Phule, Pandita Ramabai, Vivekananda, Tagore, Mahad)
  - `events_1857.json` — 1 event (Lakshmibai; major 1857 events still to author)
  - `events_princely_states.json` — 2 events (Sultan Jahan Begum + Telangana Rebellion)
  - `events_independence.json` — 20 events, 1885–1958 (+ Lajpat Rai / Champaran / Gandhi Experiments / Sarojini / Ambedkar / Bose / Azad)

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
- **Corpus today:** 5 collections —
  - `collections_central_asia.json#baburs-road-from-andijan-to-lahore` — `tag:babur-arc` → 6 members.
  - `collections_subcontinent.json#founding-moments-of-modern-india` — explicit list of 6 events spanning 1540–1885.
  - `collections_memoirs.json#first-person-works-of-the-subcontinent` — `tag:memoir` → 20 members spanning 1357–1958.
  - `collections_women.json#women-shapers-of-the-freedom-struggle` — `tag:women-leaders` → 4 members.
  - `collections_rebellions.json#rebellions-before-and-beyond-1857` — `tag:rebellion` → 18 members spanning 1763–1951. Argues "1857 was not the first"; 8 of the 18 are also tagged `tribal`, 5 also `peasant`, 2 also `caste-rights` for future sub-collections.

### Places (NEW — coordinate-anchored event gathers)
- **Schema:** `docs/PLACES_SCHEMA.md`. A place has `id`, `name`, `tooltip`, `summary`, optional `framing` (≤250 words), `location` (lat/lon + `radius_km` + optional `alt_names`), `era_span`, `category` (controlled vocab: capital / city / fort / sacred-site / port / university / sangam-confluence / massacre-site / trade-hub / ashram / prison / princely-state-capital / military-cantonment), `links`, `sources`, `verified`.
- **Auto-derived membership:** every event whose `location.points[0]` falls within `radius_km` of the place's anchor is automatically a member — no event-side change needed. Default radius 5 km; tightly-bounded sites (Sabarmati, Vellore Fort) use 3–5; wide-spread historical territories raise it (Delhi 12 km).
- **Validator:** `validators/validate_places.py`. Schema + PIP on the anchor + soft warning when fewer than 3 events fall within the gather radius (signals deliberate seed places that need their corpus to grow).
- **UI:** Fourth pill row beneath Collections. Click a pill → place reader (title, tooltip subtitle, summary, optional framing block, era+category+radius+alt-names meta lines, member count, chronologically-sorted event cards). Map enters `.in-place` mode highlighting member pins / clusters in `--amber` (distinct from collection blue and thread purple). Mutually exclusive with Threads + People + Collections.
- **Corpus today:** 12 places — Delhi (18 events, 12 km), Agra (7), Lahore (5), Calcutta (5), Bombay (3), Pune (2), Murshidabad (2), Sabarmati Ashram (2), Hyderabad (1), Srirangapatna (1), Vellore (1), Puri (1). The seven small-gather places are deliberate seeds — their corpus presence will grow as more events are authored.

### Polities (NEW — regime-shaped institutional spines)
- **Schema:** `docs/POLITIES_SCHEMA.md`. A polity has `id`, `name`, `tooltip`, `summary`, optional `framing` (≤300 words), `date_span` (start / end / display), `era_span`, `category` (controlled vocab: empire / sultanate / dynasty / princely-state / confederacy / colonial-state / republic / trading-company), `capitals[]` (chronological list of `{place, from_year, to_year}` — `place` references a place id; soft-warns when unresolved, renders as plain text), `rulers[]` (freeform strings), `events[]` (explicit list of constitutive event ids), `links`, `sources`, `verified`.
- **Explicit membership:** unlike places (which auto-derive members by proximity), polities use a hand-curated `events[]` list. The same event can belong to multiple polities (e.g. Telangana Rebellion is in both `hyderabad-state` and `republic-of-india`). No event-side backfill — the polity record is self-contained.
- **Validator:** `validators/validate_polities.py`. Schema + every event id resolves + capitals' `place` ids cross-checked against the places corpus (soft warning on unresolved).
- **UI:** Fifth pill row beneath Places. Click a pill → polity reader (title, tooltip subtitle, summary, optional framing, date_span / eras / category meta, capitals list with clickable place-links to the place reader, rulers list, member count, chronologically-sorted event cards). Map enters `.in-polity` mode highlighting member pins / clusters in `--rose` (distinct from the four other modes' colours). Mutually exclusive with Threads + People + Collections + Places.
- **Cross-navigation:** capital place-links jump to the place's reader (regime → geography). Future: place reader could surface "polities that ruled here" as a back-link, but that's deferred.
- **Corpus today:** 9 polities — Delhi Sultanate (19 events), Bahmani Sultanate (1), Sur Empire (2), Mughal Empire (26), Mysore Sultanate (1), East India Company (11), British Raj (31), Hyderabad State (1), Republic of India (3). The four single-event polities (Bahmani, Mysore, Hyderabad, Sur with 2) are deliberate seeds awaiting their corpus to grow.

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

### Tests passing today (13/13)
- `validators/validate_events.py` — PASS (~20 soft warnings on summaries 140–160 chars)
- `validators/validate_threads.py` — PASS
- `validators/validate_people.py` — PASS (5 soft warnings)
- `validators/validate_collections.py` — PASS
- `validators/validate_places.py` — PASS (7 soft warnings on places with <3 auto-derived members; deliberate seeds awaiting more events)
- `validators/validate_polities.py` — PASS (warnings on capitals referencing places not yet authored: daulatabad, gulbarga, bidar, fatehpur-sikri, madras; rendered as plain text)
- `tests/render_test_v2.py` — PASS
- `tests/render_test_popover.py` — PASS (9 checks)
- `tests/render_test_zoom.py` — PASS (8 checks)
- `tests/render_test_people.py` — PASS (10 checks)
- `tests/render_test_collections.py` — PASS (22 checks)
- `tests/render_test_places.py` — PASS (23 checks)
- `tests/render_test_polities.py` — PASS (23 checks)

---

## What's NOT built yet

In rough priority order:

**Architectural status (2026-04-26 evening):** All five content types now first-class — events, threads, people, collections, places, polities. The framework is feature-complete for content authoring at the 100-event scale. Future expansion is content, not infrastructure (modulo polish).

1. **Round out the still-thin seeded campaign files.** Sultanate is full (20 events). Still want: Paika rebellion + Konark for `events_odisha.json`, Vijayanagara + Anglo-Mysore + Wodeyars for `events_south_india.json`, Delhi / Lucknow / Kanpur / Awadh for `events_1857.json`, Hyderabad / Travancore / Kashmir for `events_princely_states.json`, more reformers for `events_reform.json`.
2. **Maurya / post-Maurya events** — stress-tests the BCE end of the year slider.
3. **More memoirs** to round out the first-person-works collection (currently 20 members; deferred queue below).
4. **Incident-shaped collections** — political show trials, negotiation moments, etc. (catalogued below).
5. **More polities** as the corpus grows — Maratha Confederacy (when Maratha events land), Vijayanagara Empire (when South India expands), Sikh Empire (when Punjab events land), Bhopal princely state (Sultan Jahan's event already in corpus), Travancore princely state (Vaikom + Sethu Lakshmi Bayi already authored).
6. **More places** to fill the gaps that polities surfaced — Daulatabad, Gulbarga, Bidar, Fatehpur Sikri, Madras (each is a polity capital but not yet a place record).
5. **More cross-cutting collections** — incident-shaped sets logged for future:
   - **Political show trials** — Tilak 1897/1908/1916, Alipore Bombing 1908, Kakori 1925, Meerut Conspiracy 1929–33, Lahore Conspiracy / Bhagat Singh 1929–31, INA trials 1945–46, Naval Mutiny court-martials 1946. Tag `show-trial`. Highly recommended next.
   - **Negotiation moments** — Cripps 1942, Cabinet Mission 1946, Wavell Plan 1945, Mountbatten Plan, Round Tables 1930–32, Treaty of Allahabad 1765, Treaty of Salbai 1782, Lahore Treaty 1846, McMahon Line 1914. Tag `negotiation`.
   - **Massacres of civilians** — Jallianwala 1919, Qissa Khwani 1930, Hijli 1931, Sholapur 1930, Bengal famine 1943. Tag `massacre`.
   - **Off-subcontinent India / diaspora** — Vivekananda Chicago, Bose Vienna/Berlin/Singapore, Gandhi South Africa, Babur Hindu Kush, Krishna Menon UN, Madame Cama Stuttgart 1907. Tag `diaspora`.
   - **Sites of confinement** — Yerwada, Ahmednagar Fort, Alipore, Mandalay, Cellular Jail Andamans, Aga Khan Palace. Tag `prison-site`.
   - **Naval & sepoy mutinies** — Vellore 1806, 1857 itself, RIN Mutiny 1946. Tag `mutiny` (subset of `rebellion`).
   - **Communal incidents that altered politics** — Direct Action Day 1946, Noakhali, Bihar 1946, Punjab 1947. Tag `communal-incident`. Politically loaded; needs careful framing.
   - **Famines** — Bengal 1770, Madras 1877, Bengal 1943. Frame as state-failure, not "natural disaster". Tag `famine`.
   - **Tribal resistance** (subset of rebellion) — Khasi, Kol, Khond, Santhal, Birsa Munda, Heraka, Telangana, plus future Bhil / Bhumij / Naikda / Tana Bhagat / Warli. Tag `tribal`.
   - **Caste-led satyagrahas** — Mahad 1927, Vaikom 1924, Kalaram 1930, Ezhava agitations. Tag `caste-rights`.
   - **Prison-writing** — Lajpat Rai + Nehru already tagged `prison-writing`; Aurobindo, Bhagat Singh notebook, Gandhi Yerwada writings to come.
   - **Court chronicles** — Tarikh-i Firuz Shahi already tagged `memoir`; would also fit `court-chronicle` alongside Akbarnama, Tuzuk, Padshahnama.
6. **More Mughal biographical tracks** — Akbar, Shah Jahan, Aurangzeb.
7. **GitHub publishing** — push to `naklitechie/india-2500`, enable Pages, optional CNAME for `assets.chiragpatnaik.com`.

### Deferred memoirs (queue for first-person-works expansion)
Padshahnama (Shah Jahan court chronicle); Ibn Battuta's *Rihla*; Isami's *Futuh-us-Salatin* (Bahmani perspective); Aurobindo's *Karakahini / Tales of Prison Life* (1909); Cornelia Sorabji's *India Calling* (1934); Kamaladevi Chattopadhyay's *Inner Recesses, Outer Spaces* (1986); Verrier Elwin's *Tribal World* (1964); Bhagat Singh prison notebook + jail letters; Naoroji's *Poverty and Un-British Rule*; Ahilyabai Holkar's administrative correspondence; Vamshavalis (Nepali royal genealogies); Periyar first-person works; Iqbal correspondence and lectures.

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
