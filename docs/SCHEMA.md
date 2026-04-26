# Events schema (`events_*.json`)

The events corpus is the atlas. Every pin on the map, every entry in search, every step in a thread resolves to an event record. Threads, the editorial overlay, never duplicate event content — they reference event IDs.

This document is the contract. The validator (`validate_events.py`) enforces it.

---

## File shape

Each campaign lives in its own file: `events_independence.json`, `events_mughal.json`, `events_maurya.json`, etc.

```jsonc
{
  "campaign": "independence",
  "scope": "Indian independence movement, 1857–1947",
  "updated": "2026-04-25",
  "events": [
    { /* event record */ },
    { /* event record */ }
  ]
}
```

The validator merges all `events_*.json` files in the directory into one corpus before resolving cross-references. A thread in `threads_independence.json` can reference an event from `events_mughal.json`; the validator will resolve it.

---

## Event record

```jsonc
{
  "id": "salt-march-1930",
  "title": "Salt March",
  "summary": "Gandhi's 24-day march from Sabarmati to Dandi to break the British salt monopoly — opening act of the Civil Disobedience Movement.",
  "detail": "Optional longer paragraph in editorial voice. 80–150 words. Skip if summary suffices. The detail is shown only when the user opens the side panel; the summary is shown in tooltips and thread step cards.",
  "date": {
    "start": "1930-03-12",
    "end":   "1930-04-06",
    "precision": "day",
    "approximate": false,
    "display": "12 March – 6 April 1930"
  },
  "location": {
    "type": "route",
    "name": "Sabarmati to Dandi",
    "region": "Gujarat",
    "points": [
      { "lat": 23.0395, "lon": 72.5662, "name": "Sabarmati Ashram" },
      { "lat": 20.8467, "lon": 72.7150, "name": "Dandi" }
    ]
  },
  "era":      "colonial",
  "category": ["resistance", "political"],
  "figures":  ["Mohandas Gandhi", "Sarojini Naidu", "Abbas Tyabji"],

  "caused_by": [
    { "id": "lahore-session-1929", "gloss": "The Purna Swaraj declaration committed Congress to mass action; the Salt March was the first concrete campaign." }
  ],
  "part_of": [
    { "id": "civil-disobedience-movement-1930" }
  ],

  "links": [
    { "url": "https://en.wikipedia.org/wiki/Salt_March", "label": "Wikipedia", "type": "wikipedia" }
  ],
  "sources": [
    { "label": "Guha, India After Gandhi (2007), pp. 28–32", "type": "scholarly" }
  ],
  "verified": true
}
```

---

## Field reference

### `id` — required, string

Stable, kebab-case, globally unique across all event files. Convention: `subject-year` or `subject-keyword-year`. Example: `chauri-chaura-1922`, `babur-takes-kabul-1504`.

The ID is the public anchor — threads reference it, the URL fragment uses it (`#event=salt-march-1930`). Don't rename once published.

### `title` — required, string

Display title. Sentence case. Avoid "The…". 60 characters or under is comfortable; the validator soft-warns above that.

### `tooltip` — required, string

One-line label, ≤80 characters (hard cap, validator-enforced). Shown on native pin hover and as the visual label on relation cards in popovers. Should stand alone — read like a museum-label caption. Examples: `"Jallianwala Bagh massacre, 1919"`, `"Salt March to Dandi, 1930"`.

Distinct from `title`: `title` is the display name (sentence case, no date), `tooltip` is the at-a-glance line that includes a date or place anchor.

### `summary` — required, string

One sentence, ≤160 characters (hard cap). Shown in the click-popover card and in popover-internal relation cards. Should describe what happened in plain language — when in doubt, lead with the verb.

### `detail` — optional, string

The longer editorial paragraph shown when the side panel is open. Voice: direct, calibrated, named entities and numbers over adjectives. 80–150 words. Skip if `summary` already says everything worth saying.

### `date` — required, object

```jsonc
{
  "start":     "1930-03-12",       // required
  "end":       "1930-04-06",       // required (= start for single-day events)
  "precision": "day",              // required: day | month | year | decade | century
  "approximate": false,            // required: bool
  "display":   "12 March – 6 April 1930"  // required: human-readable
}
```

Date strings are ISO-8601 for `precision: day` (`YYYY-MM-DD`). For `month`, drop the day (`YYYY-MM`). For `year`, just the year (`1930` or `-322` for 322 BCE). For `decade`, the start year (`-320` means 320s BCE). For `century`, `-300` means the 4th century BCE.

`start <= end` always. For an instantaneous event, set them equal.

`approximate: true` flags dates that are scholarly best-guesses, not firm — typical for pre-Common-Era events. The UI may render an approximate date with a `c.` prefix.

`display` is the canonical string the UI uses. It overrides any rendering the slider might do. It can include era ("c. 600 BCE"), ranges ("12 March – 6 April 1930"), or qualifiers ("died 1530, exact date contested").

### `location` — required, object

```jsonc
{
  "type":    "point",                       // point | city | region | route
  "name":    "Jallianwala Bagh, Amritsar",  // human-readable
  "region":  "Punjab",                      // optional, broader region
  "country": "IN",                          // ISO alpha-2, see vocab below
  "points": [
    { "lat": 31.6203, "lon": 74.8800, "name": "Jallianwala Bagh" }
  ]
}
```

Always provide at least one point with `lat` and `lon`. The map pin uses the first point. For `region`, the lat/lon is a representative centroid (notional is fine — Bengal Presidency centred near 24°N, 88°E).

`country` is required and uses ISO 3166-1 alpha-2 codes. Validator-enforced vocab:

`IN, PK, BD, NP, BT, LK, AF, UZ, TJ, TM, KZ, KG, MM, CN, IR, RU, MN, AE, OM, SA, YE, TH, LA, VN, KH, OFF`

`OFF` is reserved for events whose centroid falls outside the asset's bounding box (e.g., Round Table Conferences in London, Babur in Samarkand if you're using a tighter map). The validator does a point-in-polygon check confirming `points[0]` actually falls inside the polygon for the declared `country` — this catches typos like swapping lat and lon, or pinning Lahore at a Delhi coordinate.

For `type: route`, `points` is an ordered list — the line is drawn in order. Two or more points required.

For multi-location events that are *not* a route (e.g., simultaneous outbreaks across cities in 1857), prefer to model each location as a **separate event** rather than one event with many points. Cleaner data, each location surfaces independently in search and in the date filter.

### `era` — required, enum

Single value. The slider may render era bands behind the track using these.

Controlled vocab:

`vedic | mahajanapada | maurya | post-maurya | gupta | early-medieval | sultanate | mughal | maratha | colonial | independence | republic`

Boundaries are conventional, not absolute — pick the era that best fits the event's centre of gravity, not the regime that nominally held power at the location.

### `category` — required, list of strings

One or more of: `political | military | religious | cultural | scientific | economic | dynastic | colonial-administration | resistance | reform`.

Used for pin colour and category filters. Pick the dominant one or two; resist the urge to tag everything.

### `figures` — optional, list of strings

Named individuals primarily associated with the event. Plain strings, not linked entities. Searchable.

### `tags` — optional, list of strings

Free-form, kebab-case lowercase. Unlike `category` (controlled vocab, drives pin colour), tags are open-ended thematic markers that drive *filtering* and *collection membership* — see `COLLECTIONS_SCHEMA.md`. Examples: `women-leaders`, `rebellion`, `memoir`, `institution-founding`, `babur-arc`.

Use sparingly. A tag earns its place when at least two events share it — single-use tags are a soft warning (likely typos). The intended pattern is: a tag is invented when a collection is being authored, and applied to all events that the collection wants to gather.

Tags are not a controlled vocab. The validator only checks format (kebab-case) and surfaces the single-use warning. Coordinate with other authors before introducing a new tag — there's no central registry, just the corpus.

### `caused_by` — optional, list of `{id, gloss}`

Direct causal or responsive links. Each entry must include a `gloss`: a one-sentence editorial statement of *what* about the prior event led to this one. Bare ID without gloss is a validator error — the gloss is the editorial layer that makes the chain readable.

`led_to` is the inverse, **derived at load time**. Don't author it. This keeps the data normalized: adding a new event that was caused by Chauri Chaura doesn't require editing the Chauri Chaura record.

Use `caused_by` sparingly. If you can't write the gloss with a straight face, the link probably doesn't earn the word "caused" — it might belong in `part_of` (hierarchy) instead, or nowhere.

### `part_of` — optional, list of `{id}`

Hierarchical containment. The Salt March is `part_of` the Civil Disobedience Movement. The movement itself is also an event — model it with `location.type: region` and a date range.

No gloss on `part_of` — the hierarchy is self-evident.

### `links` — required, list of `{url, label, type}`

Reader-facing links. Wikipedia is **required** — every event must have a Wikipedia link with `type: wikipedia`. Optional secondary links: `primary` (primary source), `archive` (archived source), `related` (further reading).

### `sources` — recommended, list of `{label, url?, type}`

Editorial provenance. Where the facts came from. Less prominent in UI, but strongly recommended for any event pre-1857 or where a non-trivial claim is made. `type` is one of `scholarly | primary | secondary | reference`.

### `verified` — required, bool

`true` means a Naklitechie editor has cross-checked the dates, location, and key claims against at least two independent sources. `false` is allowed and is *not* an error — it surfaces a small "unverified" tag in the UI. Better to publish honestly-flagged uncertainty than to drop interesting events with contested details.

---

## Hard validator rules

A record fails validation if any of the following:

1. Missing any required field above
2. `id` is not unique across the corpus
3. `id` is not kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`)
4. `date.start > date.end`
5. `date.precision` not in vocab
6. `era` not in vocab
7. Any item in `category` not in vocab
8. Any `location.points[*].lat` outside [-90, 90] or `lon` outside [-180, 180]
9. Any `caused_by` or `part_of` `id` does not resolve to a real event
10. Any `caused_by` entry missing or empty `gloss`
11. An event lists itself in `caused_by` or `part_of` (no self-reference)
12. No `links` entry with `type: wikipedia`

## Soft warnings (build still passes)

- `title` longer than 60 characters
- `summary` longer than 240 characters
- `detail` over 200 words
- `verified: false` (just an FYI)
- An event has `caused_by` but no event in the corpus lists it as their cause (orphan in the graph — possibly fine, possibly a missing link)
