# Places schema (`places_*.json`)

The events corpus answers *what happened where and when*. Threads answer *here is a story you can tell*. Collections answer *here is a kinship*. **Places** answer *here is a continuous geographical protagonist — what this location means across centuries.*

A place is a city, fort, sacred site, port, ashram, or other location that has editorial weight in itself, not just as the backdrop for events. Delhi is a place; the field outside Delhi where Babur fought Ibrahim Lodi is just an event-location.

This document is the contract. The validator (`validate_places.py`) enforces it.

---

## When to use a place vs. just an event location

Most events name a location in `location.name` and that's it — the location is just a string. A place record adds editorial framing *on top of* that — it argues for the location's significance as a continuous historical actor.

| | Event location | Place |
|---|---|---|
| Schema | Field on event record | Standalone record |
| Membership | One event has one location | One place gathers many events automatically (proximity-based) |
| Editorial weight | None — just a label | Optional framing paragraph |
| Cost to author | Free (already required on every event) | Modest (coordinates + framing + sources) |
| When | Always | When the place is a historical protagonist worth its own reader |

Rule of thumb: a place earns its own record when the corpus has at least 3 events anchored within ~5 km of it AND those events span at least two eras OR two distinct narrative threads. Five events at Delhi across Sultanate / Mughal / Colonial / Independence is a place. Three events at the Battle of Tarain spanning 1191–1192 is just three event-locations in the same neighbourhood.

---

## File shape

```jsonc
{
  "campaign": "subcontinent",
  "scope": "Cities and sites that act as continuous protagonists across the corpus.",
  "updated": "2026-04-26",
  "places": [
    { /* place record */ }
  ]
}
```

The validator merges all `places_*.json` files into one corpus.

---

## Place record

```jsonc
{
  "id": "delhi",
  "name": "Delhi",
  "tooltip": "Delhi — capital across eight regimes, 1206–present",
  "summary": "From Qutb-ud-din Aibak's coronation (1206) to the Republic's seat — eight regimes, two destructions, and the longest continuous capital in the subcontinent.",
  "framing": "Optional editorial paragraph (≤250 words) arguing what this place means across time. The place reader shows this above the chronological list of events anchored here. Use this when the place is doing genuinely cross-era work — Delhi's continuity through Sultanate / Mughal / Colonial / Republic, or Banaras's continuity as a sacred centre across two and a half millennia. Skip framing when the events themselves carry the meaning.",
  "location": {
    "country": "IN",
    "lat": 28.6139,
    "lon": 77.2090,
    "radius_km": 8,
    "alt_names": ["Dilli", "Shahjahanabad", "New Delhi", "Indraprastha"]
  },
  "era_span": ["sultanate", "mughal", "colonial", "independence", "republic"],
  "category": ["capital", "city"],

  "links": [
    { "url": "https://en.wikipedia.org/wiki/Delhi", "label": "Wikipedia: Delhi", "type": "wikipedia" }
  ],
  "sources": [
    { "label": "Percival Spear, Delhi: Its Monuments and History (1937; rev. 1994)", "type": "scholarly" }
  ],
  "verified": true
}
```

---

## Field reference

### `id` — required, string, unique
Kebab-case, globally unique across all places files. Convention: a single noun (`delhi`, `agra`, `sabarmati-ashram`). Don't use the city's modern political-administrative qualifier (`new-delhi`, `mumbai`) unless that's specifically what you mean — places are historical protagonists, modern names rename them.

### `name` — required, string
Display name. The name as the corpus refers to the place in events.

### `tooltip` — required, string, ≤80 chars
One-line caption shown on the place pill and on hover. Should include date span or essential function.

### `summary` — required, string, ≤160 chars hard
One-sentence pitch. Stands alone; appears in the place picker before the reader opens.

### `framing` — optional, string, ≤250 words soft
The editorial paragraph above the gathered-events list in the reader. Use when the place's continuity *is* the argument. Skip when the events speak for themselves.

### `location` — required, object
```jsonc
{
  "country": "IN",                  // ISO alpha-2 from the events country vocab
  "lat": 28.6139,                   // place's anchor point
  "lon": 77.2090,
  "radius_km": 8,                   // optional; defaults to 5; events within this distance auto-associate
  "alt_names": ["Dilli", "..."]     // optional; surfaced in search
}
```

**Auto-association.** Every event whose `location.points[0]` falls within `radius_km` of the place's `(lat, lon)` is automatically considered a member of the place — no event-side change needed. The radius defaults to 5 km, can be raised for spread-out historical territories (Khasi Hills, Damin-i-Koh) or lowered for tightly-bounded sites (Sabarmati Ashram, Jallianwala Bagh).

**PIP check.** The validator confirms `(lat, lon)` falls inside the polygon for `country` (or skips if `country: "OFF"`).

### `era_span` — required, list of `era` values
Which eras the place is active across. Validator-checked against the events `ERAS` vocab. Used for the time-range filter — when the slider is set to a range that excludes all of a place's eras, its pill greys out.

### `category` — required, list of strings
Controlled vocab — what kind of place this is. One or more of:

`capital | city | fort | sacred-site | port | university | sangam-confluence | massacre-site | trade-hub | ashram | prison | princely-state-capital | military-cantonment`

Drives pill icon and list-view filter. Pick the dominant one or two.

### `links` — required, list of `{url, label, type}`
Wikipedia required (`type: "wikipedia"`). Optional: `primary`, `archive`, `related`, `secondary`.

### `sources` — recommended
Same shape as event sources. Strongly recommended for any place where the framing makes a contestable historical claim.

### `verified` — required, bool
Same meaning as on events / threads / collections.

---

## Hard validator rules

A place fails validation if any of:

1. Missing required field (`id`, `name`, `tooltip`, `summary`, `location`, `era_span`, `category`, `links`, `verified`)
2. `id` not unique across all places files
3. `id` not kebab-case
4. `tooltip` > 80 chars
5. `summary` > 160 chars
6. `location.country` not in events `COUNTRIES` vocab
7. `location.lat`/`lon` invalid or outside polygon for `country` (PIP check)
8. `location.radius_km` not a positive number when present
9. `era_span` empty or contains a value not in events `ERAS` vocab
10. `category` empty or contains a value not in places `CATEGORIES` vocab
11. No link with `type: "wikipedia"`
12. `verified` not a bool

## Soft warnings (build still passes)

- Effective member count (events auto-associated by proximity) is < 3 (probably doesn't earn its own place record)
- `framing` > 250 words (consider tightening)
- `verified: false`

---

## Curation discipline (not validator-enforced)

1. **A place must be a continuous protagonist.** A pin where one event happened is just an event-location. A pin where five events across three eras happened is potentially a place. Frame the question: would a reader benefit from seeing this geography's full editorial arc, or is each individual event enough?

2. **Place radius controls the gather.** Small (Jallianwala Bagh — 1 km) gathers only the precise site. Medium (Delhi — 8 km) gathers all of historical Delhi, including separate Mughal fort, modern New Delhi, and the Mehrauli archaeology zone. Large (Damin-i-Koh — 30 km) gathers a region. Pick the radius that matches the editorial scope.

3. **Don't use places to argue what threads should argue.** A place that exists primarily to organise a narrative is a thread, not a place. Places are *where things converge*, not *what things mean*.

4. **Cross-corpus events join automatically.** Authoring a place record does not require touching any event file. Tag application is geographic, not editorial — if your place includes events you didn't intend, either narrow `radius_km` or accept that geography brought them in.
