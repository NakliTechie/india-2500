# India — 2500 years to the Republic

An interactive HTML atlas of subcontinental history. Tap a pin, read the editorial summary, follow the chain of cause and effect, walk a thread, or trace a life.

Hosted at **[assets.chiragpatnaik.com/india-history.html](https://assets.chiragpatnaik.com/india-history.html)**.

## What's here

A growing, validator-enforced corpus of historical events, threads (curated walks through events), people (biographical tracks across the map), and collections (set-shaped thematic groupings). Editorial stance: neutral, data-grounded, named entities and numbers over adjectives.

Current corpus:
- **203 events** spanning 518 BCE → 1992 CE across 28 campaign files
- **5 threads** — Chauri Chaura · Babur's road to Panipat · Mandir-Mandal nexus 1990–92 · Road to Pakistan · Unfinished business of partition
- **32 people** — freedom-fighters (Gandhi, Nehru, Bhagat Singh, Ambedkar, Jinnah, Bose); Mughals (Babur, Akbar, Aurangzeb); regional resistance (Shivaji, Tipu Sultan, Ranjit Singh, Birsa Munda, Krishnadevaraya, Guru Gobind Singh, Tarabai, Rani Gaidinliu); reformers and thinkers (Phule pair, Pandita Ramabai, Periyar, Tagore); Bengal Renaissance (Rammohan Roy, Vidyasagar, Vivekananda); Bhakti-Sufi poets (Kabir, Mirabai, Tukaram); scientists (J.C. Bose, Ramanujan, C.V. Raman, Meghnad Saha)
- **14 collections** — Babur's road · Founding moments of modern India (1857 → Constitution) · First-person works · Women shapers · Rebellions · European arrival · EIC ascent · Wars of empire · Famines on the subcontinent (1335–1943) · Land settlements · Bhakti and Sufi currents · Bengal Renaissance · Indian scientific renaissance · Princely states question
- **40 places** across the subcontinent
- **27 polities** spanning Maurya through Republic

All six first-class content types — events, threads, people, collections, places, polities — ship. Every polity-capital cross-navigation link clicks through to a real place record.

## Deployment

The built `web/india-history.html` is a single-file artifact you can host anywhere — it has no runtime dependencies. Production copy lives at [assets.chiragpatnaik.com/india-history.html](https://assets.chiragpatnaik.com/india-history.html).

A helper script stages the build into any directory of your choosing:
```bash
./build/deploy.sh /path/to/your/hosting/directory
```
It validates the corpus, rebuilds, and copies the artifacts. It does not touch git or push — review and publish from the destination yourself.

## Repository layout

```
data/                  Editorial content. Six first-class types.
  events/events_*.json
  threads/threads_*.json
  people/people_*.json
  collections/collections_*.json
  places/places_*.json
  polities/polities_*.json

validators/            Schema enforcement. Run on every PR via CI.
  validate_events.py
  validate_threads.py
  validate_people.py
  validate_collections.py
  validate_places.py
  validate_polities.py

build/                 Pipeline that turns data + template into the asset.
  build_map.py         Datameet + world-atlas → SVG basemap (slow, rare)
  build_html.py        template + data → web/india-history.html (fast, frequent)
  map_paths.json       Cached basemap (committed; rebuilds rarely)
  validator_boundaries.json   Cached PIP polygons (committed)

web/                   The asset itself.
  template.html        Source HTML/CSS/JS with __PLACEHOLDER__ tokens
  india-history.html   Built single-file asset (committed; deploy anywhere)
  shell.html           Runtime-fetch version for hosted use (loads data/ over HTTP)

tests/                 Browser regression tests (Playwright).
  render_test_v2.py
  render_test_popover.py
  render_test_zoom.py
  render_test_people.py
  render_test_collections.py
  render_test_places.py
  render_test_polities.py

docs/                  Editorial + technical docs.
  SCHEMA.md                Events schema (the contract; includes optional tags[])
  THREADS_SCHEMA.md
  PEOPLE_SCHEMA.md
  COLLECTIONS_SCHEMA.md
  PLACES_SCHEMA.md
  POLITIES_SCHEMA.md
  CLAUDE.md                Runbook for AI-assisted development
  HANDOFF.md               Full project context for new contributors
  CONTRIBUTING.md          How to add events, threads, people, collections, places, polities

datameet/              External — clone separately (gitignored, ~200 MB)
package/               External — fetch world-atlas separately (gitignored)
```

## Quick start

### Run locally
```bash
# Open the built single-file asset directly
open web/india-history.html
```

### Add a new event
```bash
# 1. Edit (or create) a campaign file under data/events/
$EDITOR data/events/events_<your-campaign>.json

# 2. Validate
python3 validators/validate_events.py
python3 validators/validate_threads.py        # cross-reference check
python3 validators/validate_people.py         # cross-reference check
python3 validators/validate_collections.py    # cross-reference check
python3 validators/validate_places.py         # PIP + auto-derived gather check
python3 validators/validate_polities.py       # events + capitals cross-reference

# 3. Rebuild the asset
python3 build/build_html.py

# 4. Run the regression tests
for t in tests/render_test_*.py; do python3 "$t"; done
```

### Rebuild the basemap (rare)
The basemap (`build/map_paths.json` + `build/validator_boundaries.json`) is committed, so you only need to rebuild if you change the projection or simplification. It needs two external dependencies:
```bash
# Datameet — official India boundary (PoK/Aksai Chin/Arunachal correctly inside India)
git clone --depth 1 https://github.com/datameet/maps.git datameet

# world-atlas — surrounding countries (Natural Earth at 50M scale)
mkdir -p package
curl -sL https://unpkg.com/world-atlas@2/countries-50m.json -o package/countries-50m.json

# Build
python3 build/build_map.py
```

## Contributing

The easiest path for everyone — including non-technical contributors — is the **[contribute form](https://naklitechie.github.io/india-2500/contribute/)**. It guides you through adding a new event, thread, person, or collection, validates as you type, and gives you a downloadable JSON or a one-click PR.

Other paths:

- **Direct PR (if you prefer)** — edit a JSON file under `data/` and open a PR. CI runs all six validators and the render tests.
- **Found an error in an existing entry?** Open an [issue using the correction template](https://github.com/naklitechie/india-2500/issues/new?template=correction.md).
- **Want to discuss editorial framing?** Open an [editorial issue](https://github.com/naklitechie/india-2500/issues/new?template=editorial.md).

Full guide: [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). The validators are the contract — if your PR passes them and the editorial review, it can merge.

## Editorial stance

- Verified figures only. Cross-check dates against ≥2 independent sources before setting `verified: true`.
- Wikipedia is the rabbit-hole link, not the source.
- Direct, calibrated voice. Numbers and named entities over adjectives.
- We are not limited by textbooks. Indian history is discrete; small dynasties (Sur, Asaf Jah) get their own files, not folded into the bigger neighbour.

## License

- **Editorial content** (`data/`, `docs/*_SCHEMA.md`, `docs/CONTRIBUTING.md`, and the derived HTML/PNG artifacts) is licensed under **[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)**. See `LICENSE`. Attribution to **Chirag Patnaik** required; derivatives must use the same license.
- **Code** (`validators/`, `build/`, `web/template.html`, `tests/`, `contribute/lib/`) is licensed under **MIT**. See `LICENSE-CODE`.

External dependencies retain their original licenses: [Datameet](https://github.com/datameet/maps) (CC BY 4.0), [world-atlas](https://github.com/topojson/world-atlas) (ISC).
