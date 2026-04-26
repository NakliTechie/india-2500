# Polities schema (`polities_*.json`)

A polity is a state, empire, sultanate, dynasty, confederacy, princely state, colonial regime, or republic — a continuous political-institutional actor with a definable date range, rulers, capitals, and constitutive events. The Mughal Empire is a polity; so is the East India Company; so is the Republic of India.

Polities are first-class records because the corpus's events are too thin a substrate by themselves — a coronation, a battle, a treaty — to carry the political-institutional continuity readers want to see. The polity record adds the spine that holds the events together: date range, succession of rulers, succession of capitals.

This document is the contract. The validator (`validate_polities.py`) enforces it.

---

## When to use a polity vs. a thread or a collection

| | Polity | Thread | Collection |
|---|---|---|---|
| Spine | Date range + rulers + capitals | An argument | Shared property |
| Membership | Explicit `events[]` list (curated) | Ordered `steps[]` with notes | Set via id list OR tag selector |
| Per-member text | None — events stand alone | Note + transition per step | None |
| Order | Chronological at render | Author-controlled | Chronological at render |
| Asks reader to | "See the regime as a continuous institution" | "Walk this argument with me" | "Notice these belong together" |
| When | Regime-shaped continuity | Argued sequence | Cross-cutting catalogue |

A polity is *not* a thread because it has no single argument — Mughal Empire is the institution, not the case for it. A polity is *not* a collection because it has structured metadata (capitals, rulers, date span) that collections deliberately don't carry.

---

## File shape

```jsonc
{
  "campaign": "subcontinent",
  "scope": "Subcontinental polities — empires, sultanates, princely states, colonial regimes, the Republic.",
  "updated": "2026-04-26",
  "polities": [
    { /* polity record */ }
  ]
}
```

The validator merges all `polities_*.json` files into one corpus.

---

## Polity record

```jsonc
{
  "id": "mughal-empire",
  "name": "Mughal Empire",
  "tooltip": "Mughal Empire — 1526–1857",
  "summary": "Babur's victory at Panipat to the formal dissolution of the empire after 1857 — the longest unified subcontinental imperial regime since the Mauryas.",
  "framing": "Optional editorial paragraph (≤300 words) that argues what this polity was as an institution. Use when the institutional continuity is the editorial point — e.g. arguing the Mughal Empire's tax system, court culture, and succession politics as a coherent regime distinct from its ruler-by-ruler narrative.",

  "date_span": {
    "start": "1526",
    "end":   "1857",
    "display": "1526–1857 (formal dissolution after 1857)"
  },
  "era_span":  ["mughal", "maratha", "colonial"],
  "category":  "empire",

  "capitals": [
    { "place": "agra",            "from_year": 1526, "to_year": 1571 },
    { "place": "fatehpur-sikri",  "from_year": 1571, "to_year": 1585 },
    { "place": "agra",            "from_year": 1585, "to_year": 1638 },
    { "place": "delhi",           "from_year": 1638, "to_year": 1857 }
  ],

  "rulers": [
    "Babur (1526–1530)",
    "Humayun (1530–1540, 1555–1556)",
    "Akbar (1556–1605)",
    "Jahangir (1605–1627)"
  ],

  "events": [
    "first-battle-of-panipat-1526",
    "battle-of-khanwa-1527",
    "battle-of-ghaghra-1529"
  ],

  "links": [
    { "url": "https://en.wikipedia.org/wiki/Mughal_Empire", "label": "Wikipedia: Mughal Empire", "type": "wikipedia" }
  ],
  "sources": [
    { "label": "Satish Chandra, Medieval India: From Sultanate to the Mughals — Part Two (1999)", "type": "scholarly" }
  ],
  "verified": true
}
```

---

## Field reference

### `id` — required, string, unique
Kebab-case, globally unique across all polities files. Convention: institution-name (`mughal-empire`, `delhi-sultanate`, `east-india-company`, `republic-of-india`).

### `name` — required, string
Display name. The institution's standard English name.

### `tooltip` — required, string, ≤80 chars
One-line caption shown on the pill and on hover. Should include date span.

### `summary` — required, string, ≤160 chars hard
One-sentence pitch. Stands alone in the polity picker.

### `framing` — optional, string, ≤300 words soft
Editorial paragraph above the rulers/capitals/events list. Use when arguing the institution's character, not just listing its events.

### `date_span` — required, object
```jsonc
{
  "start":    "1526",   // year as string or integer; negative for BCE
  "end":      "1857",   // same; for ongoing polities use the current year
  "display":  "1526–1857 (formal dissolution after 1857)"   // canonical UI string
}
```
The `display` field is the human-readable form shown in the reader. The `start`/`end` years drive era-span checks and chronological filtering.

### `era_span` — required, list of `era` values
Which eras the polity is active across. Validator-checked against the events `ERAS` vocab.

### `category` — required, string
Single value from the controlled vocab:

`empire | sultanate | dynasty | princely-state | confederacy | colonial-state | republic | trading-company`

Drives pill icon and reader colour band.

### `capitals` — required, list of `{place, from_year, to_year}`
Chronological list of capital cities. Each entry references a place by id (must resolve to a place in the places corpus, OR be a freeform string for capitals not yet authored as places). `from_year`/`to_year` are integers; both required. `to_year` may equal `from_year` for one-year capitals.

The validator soft-warns when a referenced `place` does not resolve to a place record (the place is then displayed as plain text).

### `rulers` — required, list of strings
Freeform strings — one per ruler. Convention: `"Name (start–end)"` or `"Name (only year)"`. Future schema may upgrade these to people-id references.

### `events` — required, list of event ids
Explicit list of constitutive events for this polity. Each id must resolve to an event in the events corpus. Validator fails on unresolved ids.

The renderer sorts events chronologically by `date.start` regardless of authoring order.

### `links` — required, list of `{url, label, type}`
Wikipedia required (`type: "wikipedia"`).

### `sources` — recommended
Same shape as event sources.

### `verified` — required, bool
Same meaning as on other types.

---

## Hard validator rules

A polity fails validation if any of:

1. Missing required field (`id`, `name`, `tooltip`, `summary`, `date_span`, `era_span`, `category`, `capitals`, `rulers`, `events`, `links`, `verified`)
2. `id` not unique across polities corpus
3. `id` not kebab-case
4. `tooltip` > 80 chars
5. `summary` > 160 chars
6. `date_span.start` or `.end` unparseable
7. `date_span.start` > `date_span.end`
8. `era_span` empty or contains a value not in events `ERAS` vocab
9. `category` not in polities `CATEGORIES` vocab
10. `capitals` empty OR any entry missing `place` / `from_year` / `to_year`
11. `rulers` empty
12. `events` empty
13. Any `events[i]` does not resolve to an event in the corpus
14. No `links` entry with `type: "wikipedia"`
15. `verified` not a bool

## Soft warnings

- Any `capitals[i].place` does not resolve to a place record (rendered as plain text)
- `framing` > 300 words
- `events` count < 3 (probably needs more events to earn a polity record)
- `verified: false`

---

## Curation discipline (not validator-enforced)

1. **A polity is an institution, not a moment.** The Khalsa is a religious order (could be a polity if and when the Khalsa Misls / Sikh Empire material lands); a single battle is not.

2. **Multi-polity events are normal.** A 19th-century event in princely Hyderabad belongs to BOTH `hyderabad-state` and `british-raj` (paramountcy). Both polities should list the event in their `events[]`.

3. **Polities and places intersect but don't overlap.** A polity is *who governed*; a place is *where*. The Mughal Empire (polity) used Delhi (place) as one of several capitals across centuries.

4. **Don't overload a polity with optional metadata.** The schema is intentionally tight — date span, era span, category, capitals, rulers, events. Anything else belongs in `framing` prose, not in new structured fields.
