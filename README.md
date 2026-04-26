# India — 2500 years to the Republic

An interactive HTML atlas of subcontinental history. Tap a pin, read the editorial summary, follow the chain of cause and effect, walk a thread, or trace a life.

Hosted at **[assets.chiragpatnaik.com/india-history.html](https://assets.chiragpatnaik.com/india-history.html)**.

## What's here

A growing, validator-enforced corpus of historical events, threads (curated walks through events), people (biographical tracks across the map), and collections (set-shaped thematic groupings). Editorial stance: neutral, data-grounded, named entities and numbers over adjectives.

Current corpus:
- **61 events** spanning 1357–1958 CE across 10 campaign files (Sultanate, Central Asia, Mughal, Sur, Odisha, South India, Reform-era, 1857, Princely States, Independence)
- **2 threads** (Chauri Chaura and the cost of non-violence; Babur's road to Panipat)
- **6 people** (Gandhi, Nehru, Bhagat Singh, Ambedkar, Jinnah, Babur)
- **3 collections** (Babur's road from Andijan to Lahore; Founding moments of modern India; First-person works of the subcontinent — 18 memoirs from Barani 1357 to Azad 1958)

Upcoming: Maurya / post-Maurya, more events to round out the seeded campaign files (Ghurids→Lodis, Vijayanagara, more 1857 / princely states / reformers), more memoirs (Padshahnama, Aurobindo, Bose, Phule, Sorabji), more cross-cutting collections (women in independence, rebellions reframe, prison-writing).

## Repository layout

```
data/                  Editorial content. Add new events, threads, people, collections here.
  events/events_*.json
  threads/threads_*.json
  people/people_*.json
  collections/collections_*.json

validators/            Schema enforcement. Run on every PR via CI.
  validate_events.py
  validate_threads.py
  validate_people.py
  validate_collections.py

build/                 Pipeline that turns data + template into the asset.
  build_map.py         Datameet + world-atlas → SVG basemap (slow, rare)
  build_html.py        template + data → web/india-history.html (fast, frequent)
  map_paths.json       Cached basemap (committed; rebuilds rarely)
  validator_boundaries.json   Cached PIP polygons (committed)

web/                   The asset itself.
  template.html        Source HTML/CSS/JS with __PLACEHOLDER__ tokens
  india-history.html   Built single-file asset (committed; deployable to assets.chiragpatnaik.com)
  shell.html           Runtime-fetch version for hosted use (loads data/ over HTTP)

tests/                 Browser regression tests (Playwright).
  render_test_v2.py
  render_test_popover.py
  render_test_zoom.py
  render_test_people.py
  render_test_collections.py

docs/                  Editorial + technical docs.
  SCHEMA.md                Events schema (the contract; includes optional tags[])
  THREADS_SCHEMA.md
  PEOPLE_SCHEMA.md
  COLLECTIONS_SCHEMA.md
  CLAUDE.md                Runbook for AI-assisted development
  HANDOFF.md               Full project context for new contributors
  CONTRIBUTING.md          How to add events, threads, people, collections

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

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md). Short version:

- New event / thread / person → open a PR with a JSON edit. CI runs all three validators and the render tests.
- Found an error in an existing entry → open an issue with the [correction template](.github/ISSUE_TEMPLATE/correction.md).
- Want to discuss editorial framing → open an issue, tag `editorial`.

The validators are the contract. If your PR passes them and the editorial review, it can merge.

## Editorial stance

- Verified figures only. Cross-check dates against ≥2 independent sources before setting `verified: true`.
- Wikipedia is the rabbit-hole link, not the source.
- Direct, calibrated voice. Numbers and named entities over adjectives.
- We are not limited by textbooks. Indian history is discrete; small dynasties (Sur, Asaf Jah) get their own files, not folded into the bigger neighbour.

## License

Editorial content (`data/`) is CC BY-SA 4.0. Code is MIT.

External dependencies retain their original licenses: [Datameet](https://github.com/datameet/maps) (CC BY 4.0), [world-atlas](https://github.com/topojson/world-atlas) (ISC).
