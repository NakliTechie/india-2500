# Contributing to India — 2500 years to the Republic

This is an editorial corpus first, code project second. The validators ensure shape; humans ensure substance. Both are gates.

## Three things to know before you start

1. **Validators are the contract.** Schema in `docs/SCHEMA.md`, `docs/THREADS_SCHEMA.md`, `docs/PEOPLE_SCHEMA.md`, `docs/COLLECTIONS_SCHEMA.md`, `docs/PLACES_SCHEMA.md`, `docs/POLITIES_SCHEMA.md`. If your PR doesn't pass `validators/validate_*.py`, CI will block it.
2. **Verified figures only.** Cross-check dates, locations, and key claims against at least two independent sources before setting `verified: true`. When in doubt, set `false` and let the UI tag it.
3. **Wikipedia is the rabbit-hole link, not the source.** The summary should read like the start of an editorial, not an extract of the Wikipedia lead.

## Adding a new event

1. **Pick a campaign file**, or create one. Each era / campaign goes in its own `data/events/events_<campaign>.json`. Examples: `events_mughal.json`, `events_independence.json`. The validator merges all of them; you don't need to co-locate causally-linked events.

2. **Use the schema.** Required fields: `id`, `title`, `tooltip` (≤80 chars), `summary` (≤160 chars hard, ≤140 soft), `detail` (80–150 words), `date`, `location`, `era`, `category`, `links` (must include `type: "wikipedia"`), `verified`. See `docs/SCHEMA.md` for the full list.

3. **Wire causal links.** Use `caused_by` for direct causal/responsive edges (each requires a `gloss` — the editorial sentence). `part_of` for hierarchical containment. `led_to` is derived as the inverse at runtime — never authored. Multi-parent and multi-child are both supported (the schema is a DAG, not a tree). Cross-file references work (validator merges the corpus).

4. **Validate locally.**
   ```bash
   python3 validators/validate_events.py
   python3 validators/validate_threads.py        # checks any threads referencing your event
   python3 validators/validate_people.py         # checks any people event-refs
   python3 validators/validate_collections.py    # checks any collection members
   python3 validators/validate_places.py         # checks place anchors + auto-derived gathers
   python3 validators/validate_polities.py       # checks polity events[] + capitals
   ```
   The point-in-polygon (PIP) check confirms each pin's lat/lon falls inside its declared `country` polygon. If you set `country: "OFF"`, the check is skipped.

5. **Rebuild and run tests.**
   ```bash
   python3 build/build_html.py
   for t in tests/render_test_*.py; do python3 "$t"; done
   ```

6. **Open a PR.** CI re-runs all of the above.

## Adding a thread

1. Create or extend `data/threads/threads_<campaign>.json`.
2. Each step references an existing event by `event_id`. Cross-corpus refs work.
3. Each step needs a `note` (the per-step framing) and a `transition` (the prose bridge to the next step; `null` on the last step).
4. The thread needs a `coda` — your closing argument, ≤150 words. If you can't write the coda in one paragraph, the thread isn't ready.
5. Validate: `python3 validators/validate_threads.py`.

## Adding a person

1. Create or extend `data/people/people_<group>.json`.
2. Each track step is either `kind: "event-ref"` (references an event_id, requires `role`) or `kind: "moment"` (a standalone biographical pin with its own location, requires `tooltip`, `summary`, `date`, `location`).
3. Track steps must be in chronological order.
4. The first 5 people in load order get distinct accent colours from the Rangrez India · NORTH palette. Beyond 5, colours cycle.
5. Validate: `python3 validators/validate_people.py`.

## Adding a collection

1. Create or extend `data/collections/collections_<campaign>.json`.
2. Each collection has `id`, `title`, `summary` (30–80 words), `members[]`, `verified`. Optional `subtitle`, `framing` (≤200 words), `sources`.
3. Members are heterogeneous: `{kind: "event", id}` or `{kind: "tag", tag}`. Mixing kinds in one `members[]` is fine. Renderer dedupes and sorts chronologically.
4. **Tag selectors require existing tags.** If your collection wants a tag that doesn't exist yet, add it to relevant events via `tags[]` first (or invent it inside the contribute form). The validator rejects tag selectors that match zero events.
5. Validate: `python3 validators/validate_collections.py`.

## Adding a place

Places are coordinate-anchored gathers — a single record (Delhi, Sabarmati Ashram, Hampi) groups all events whose `location.points[0]` falls within `radius_km` of the place's anchor. Membership is auto-derived at boot — no event-side change needed.

1. Create or extend `data/places/places_<campaign>.json`.
2. Required: `id`, `name`, `tooltip` (≤80c), `summary` (≤160c), `location` (`country`, `lat`, `lon`, optional `radius_km` default 5, optional `alt_names[]`), `era_span`, `category` (controlled vocab — see PLACES_SCHEMA), `links` (Wikipedia required), `verified`. Optional: `framing` (≤250 words), `sources`.
3. Radius tuning: 3–5 km for tightly-bounded sites (Sabarmati Ashram, Vellore Fort); 5–10 km for standard cities; 10–15 km for spread-out historical territories (Delhi 12 km).
4. A place earns its own record when at least 3 events from at least 2 eras anchor at it, OR when it serves as a polity capital and needs to back the cross-navigation link. The validator soft-warns at <3 auto-gathered members; this is acceptable for deliberate seeds.
5. Validate: `python3 validators/validate_places.py`.

## Adding a polity

Polities are regime-shaped institutional spines — Delhi Sultanate, Mughal Empire, EIC, British Raj, the Republic. Each polity has structured metadata (date span, capitals, rulers) plus an explicit `events[]` list of constitutive event ids — no auto-derivation, no event-side backfill.

1. Create or extend `data/polities/polities_<campaign>.json`.
2. Required: `id`, `name`, `tooltip` (≤80c), `summary` (≤160c), `date_span` (`start`, `end`, `display`), `era_span`, `category` (controlled vocab — see POLITIES_SCHEMA), `capitals[]` (each `{place, from_year, to_year}` — `place` references a place id), `rulers[]` (freeform strings), `events[]` (explicit event ids; non-empty), `links` (Wikipedia required), `verified`. Optional: `framing` (≤300 words), `sources`.
3. **Cross-listing is normal.** The same event can belong to multiple polities (Telangana Rebellion is in both `hyderabad-state` and `republic-of-india`). Author the polity's events list independently of other polities' lists.
4. **Capitals reference place ids.** Author the corresponding place record first (see "Adding a place" above) — if the place doesn't exist, the capital renders as plain text and the cross-navigation link is dead.
5. Validate: `python3 validators/validate_polities.py`.

## Editorial discipline

These aren't validator-enforced; they're how the corpus reads as a whole.

- **Verified figures only.** Two-source rule.
- **Wikipedia is the rabbit hole, not the source.** Don't paraphrase the lead.
- **A thread must have a thesis.** If you can't write the coda in one paragraph, it's not ready.
- **Numbers and named entities over adjectives.** "32 million rupees, 5–8% of annual revenue" beats "vast wealth."
- **No mid-sentence bolding in body copy. No emoji.**
- **Don't flatten dynasties for narrative convenience.** Indian history is discrete. Smaller dynasties (Sur, Asaf Jah, regional Sultanates) get their own files, even when only a few years long.
- **Religious / political framings need calibration.** Particularly for Mughal-era and modern events: write policies, not essences. Mention parallel realities (e.g., "Muslims paid the parallel zakat tithe" alongside jizya).

## Schema changes

The era / category / country / link-type / location-type vocabularies are in the schema docs and re-asserted in the validator's set literals. To add a value: edit the schema doc + the validator's set + the relevant build script. **All three or none** — the validator is the contract.

## Rebuilding the basemap

You almost certainly don't need to do this. The basemap (`build/map_paths.json` + `build/validator_boundaries.json`) is committed. Rebuild only if you change the projection parameters or the boundary sources. See the README for the external-dependency setup.

## Reporting issues without a fix

Use the issue templates:
- **Correction** — a date / fact / name in an existing entry is wrong.
- **New event request** — you think an event belongs here but you can't author it yourself.
- **Editorial** — a framing question that needs discussion before any change.

## What we don't accept

- PRs that fail the validators (CI blocks them).
- PRs that change the schema without updating all three: schema doc + validator + build script.
- Entries based on a single contested source.
- Sectarian or polemical framings. Calibrated voice only.
- Wikipedia-lead paraphrases.
