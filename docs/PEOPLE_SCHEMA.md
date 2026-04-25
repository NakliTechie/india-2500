# People schema (`people_*.json`)

A **person** is a first-class entity with biographical metadata and an ordered **track** — a sequence of significant locations across their life. Tracks render on the map as a connected line through numbered pins, the way `salt-march-1930` already renders as a route. The right panel shows the track as a vertical timeline, with editorial notes tying each step to the next.

People are **not** threads. Threads make an argument by walking through events. A track shows a life. They run on parallel infrastructure but are separate slices.

---

## Why a separate file class

The existing `figures` array on each event lists who was present, but it doesn't tell you where Gandhi was *between* events, or capture the moments that don't merit a full event entry — the train at Pietermaritzburg, the cell at Yerwada, the broadcasts from Sevagram. A full life is dozens of consequential locations, most of which won't ever be standalone events.

So: events stay as the atlas of *what happened in history*. Threads stay as curated *arguments* through events. People become the third slice — the *biographical paths* of major figures, with locations both inside and outside the events corpus.

---

## File structure

One file per coherent biographical group:

```
people_freedom-fighters.json    # Gandhi, Nehru, Patel, Bose, Ambedkar, Jinnah…
people_mughals.json             # Babur, Akbar, Aurangzeb…
people_writers.json             # Tagore, Premchand, Iqbal…
```

Top-level shape mirrors `events_*.json`:

```jsonc
{
  "campaign": "freedom-fighters",
  "scope":    "Major figures of the Indian independence movement, 1885–1947.",
  "updated":  "2026-04-25",
  "people":   [ /* … */ ]
}
```

---

## Person object

```jsonc
{
  "id":       "gandhi",                         // kebab-case, globally unique across ALL people files
  "name":     "Mohandas Karamchand Gandhi",
  "tooltip":  "Mohandas Gandhi (1869–1948)",    // ≤80 chars, shown on track pin hover
  "summary":  "Lawyer, activist, architect of mass non-violent resistance.",  // ≤160 chars
  "era":      "colonial",                        // matches events vocab; used for time-axis grouping
  "lifespan": {
    "born":       "1869-10-02",
    "died":       "1948-01-30",
    "birthplace": { "name": "Porbandar",                 "country": "IN", "lat": 21.6417, "lon": 69.6293 },
    "deathplace": { "name": "Birla House, New Delhi",    "country": "IN", "lat": 28.6105, "lon": 77.2128 }
  },
  "links": [
    { "url": "https://en.wikipedia.org/wiki/Mahatma_Gandhi", "label": "Wikipedia",  "type": "wikipedia" }
  ],
  "track": [ /* see below */ ],
  "verified": true
}
```

`birthplace` and `deathplace` anchor the start and end of the track automatically — the validator inserts implicit "born" and "died" pins so authors don't have to.

---

## Track step — two kinds

Each track step is either an **event reference** (the person was at an existing first-class event) or a **moment** (a person-specific location not in the events corpus). Distinguish via `kind`.

### Event reference

```jsonc
{
  "kind":     "event-ref",
  "event_id": "salt-march-1930",
  "role":     "Led the march; reached Dandi on 6 April 1930.",   // person's specific part — required
  "note":     "Hand-picked 78 satyagrahis; deliberately walked 12 miles a day to maximise press coverage."
}
```

The validator resolves `event_id` against the entire events corpus. If the event's `location.type === 'route'`, the track pin uses the route's first point unless `role_at` overrides it.

### Standalone moment

```jsonc
{
  "kind":    "moment",
  "id":      "gandhi-pietermaritzburg",                 // kebab-case, unique within this person's track
  "tooltip": "Thrown off the train at Pietermaritzburg, 1893",
  "summary": "First-class ticket holder removed for being non-white — the radicalising incident.",
  "date": {
    "start":      "1893-06-07",
    "end":        "1893-06-07",
    "precision":  "day",
    "approximate": false,
    "display":    "7 June 1893"
  },
  "location": {
    "name":    "Pietermaritzburg railway station, South Africa",
    "region":  "Natal Colony",
    "country": "OFF",
    "points":  [ { "lat": -29.6035, "lon": 30.3787, "name": "Pietermaritzburg" } ]
  },
  "note":    "The night Gandhi later cited as the moment he committed to political action."
}
```

A moment carries the same fields as a slim event (`tooltip`, `summary`, `date`, `location`) plus the biographical `note`. It's intentionally lighter than a full event — no `figures`, no causal links, no `detail`. If a moment outgrows that and accrues consequences, promote it to a real event in `events_*.json` and convert the track step to `event-ref`.

---

## Track ordering

Steps in `track` are stored in chronological order — the validator enforces it. The renderer draws the connecting line in array order. Don't rely on date sorting at runtime; if you re-order, re-order the array.

---

## Vocabulary

| Field                    | Vocab |
|--------------------------|-------|
| `era`                    | same as events: `vedic` `mahajanapada` `maurya` `post-maurya` `gupta` `early-medieval` `sultanate` `mughal` `maratha` `colonial` `independence` `republic` |
| `location.country`       | same as events: ISO alpha-2 from the asset's allowed set, or `OFF` for off-map (validator skips PIP) |
| `links[].type`           | `wikipedia` `archive` `primary` `related` `secondary` |

---

## Validation rules (enforced by `validate_people.py`)

1. `id` must be kebab-case and globally unique across all `people_*.json` files. Once published, never changed.
2. `tooltip` ≤ 80 chars. `summary` ≤ 160 chars. Both required.
3. `lifespan.born`, `lifespan.died` must parse as valid dates. If `died` is null the person is presumed living (not modelled in the seed corpus).
4. `track` must contain at least 1 step. Steps must be in non-decreasing date order.
5. For `event-ref` steps: `event_id` must resolve against the events corpus. `role` is required.
6. For `moment` steps: `id` must be kebab-case and unique within the track. `tooltip`, `summary`, `date`, `location` all required. PIP check on `location.points[0]` against `country`.
7. At least one `links` entry with `type: "wikipedia"`.

The validator runs after the events validator so `event_id` resolution sees the full corpus.

---

## What the UI renders (sketch — not implemented yet)

- A **People** selector pill in the top bar, alongside Threads. Mutually exclusive — selecting a person clears any active thread, and vice versa.
- The selected person's track renders on the map as numbered pins (1, 2, 3, …) connected by a thin line. Birthplace = pin 0, deathplace = last pin. Pins use the person's accent colour (one of the Naklitechie palette per person, declared on the person object — TBD).
- Right panel shows the track as a vertical reader, similar to the threads reader: number, tooltip, dates, location, note. Click a step to scroll the reader and centre/zoom the map on that pin.
- The chronology slider continues to apply — narrowing the year range hides track pins outside it but keeps the connecting line so the user sees gaps in coverage.

---

## Open architectural question

The above models a person's track as **embedded** in the person object. Alternative: extract moments into a separate `moments_*.json` file and have track steps reference moments by id, the same way `event-ref` steps reference events. This deduplicates moments shared by multiple people (e.g., "the 1928 Bardoli Satyagraha" might be a moment for both Patel and Gandhi).

Recommendation: **embed for v1.** Shared moments are rare in practice, and the embedded form is much simpler for authoring. Revisit if and when we hit a real case where two people's track steps describe the exact same private event.

---

## Seed corpus, when we build it

Start with **5 people** to validate the schema and UI before scaling:

1. **Gandhi** — most events, longest track, tests both `event-ref` and `moment` density
2. **Nehru** — overlaps Gandhi heavily, tests parallel tracks
3. **Bhagat Singh** — short, intense, tests the time-narrow case
4. **Ambedkar** — different geography (Mhow → London → Columbia → Mumbai → Delhi), tests off-map handling
5. **Jinnah** — partition perspective, tests political opposition

After those five, the schema is either solid or we know what's broken.
