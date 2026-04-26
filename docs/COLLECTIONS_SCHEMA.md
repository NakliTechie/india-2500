# Collections schema (`collections_*.json`)

The events corpus answers *what happened where and when*. Threads answer *here is a story you can tell with these events*. Collections answer *here is a kinship — these events belong together because of a shared property*.

Collections are sets, not sequences. They have no per-member notes and no transitions. If you want to write an argument with editorial connective tissue, write a thread. If you want to gather every event that shares a property and frame the gathering, write a collection.

This document is the contract. The validator (`validate_collections.py`) enforces it.

---

## When to use a collection vs. a thread

| | Collection | Thread |
|---|---|---|
| Shape | Set | Ordered sequence |
| Per-member text | None — the events speak for themselves | `note` + `transition` per step |
| Membership | `members[]` — explicit ids OR tag selectors | `steps[]` — explicit event_ids only |
| Editorial weight | A summary + optional framing paragraph at the top | Notes between every pair of steps + a coda |
| Argument | "These belong together" | "This sequence proves something" |
| Author cost | Cheap — list the members, ship | Expensive — every step needs prose |
| Best for | Cross-cutting catalogues (women in independence, rebellions, memoirs, founding moments) | Causal chains, narrative arcs, counterfactual readings |

Rule of thumb: a thread can always be demoted to a collection by dropping its notes and transitions. A collection is harder to promote to a thread — promotion requires writing the editorial connective tissue from scratch. Default to collections for cataloguing; reserve threads for arguments.

---

## File shape

```jsonc
{
  "campaign": "independence",
  "scope": "Cross-cutting collections through the independence movement",
  "updated": "2026-04-26",
  "collections": [
    { /* collection record */ }
  ]
}
```

The validator merges all `collections_*.json` files in the directory into one corpus, then resolves each member against the events corpus.

---

## Collection record

```jsonc
{
  "id": "women-in-the-independence-movement",
  "title": "Women in the independence movement",
  "subtitle": "Leaders, organisers, and instigators whose work the textbook telling tends to flatten.",
  "summary": "From Sarojini Naidu in the salt campaigns to Aruna Asaf Ali at Quit India, women shaped the independence movement at every scale — and were repeatedly written out of its memory.",

  "framing": "Optional editorial paragraph (≤200 words) shown above the member list. Use this when the framing matters more than the gathering itself — e.g., to argue why this grouping is worth surfacing, what gets erased without it, or what reading the collection asks the visitor to bring.",

  "members": [
    { "kind": "tag", "tag": "women-leaders" },
    { "kind": "event", "id": "specific-event-not-otherwise-tagged" }
  ],

  "sources": [
    { "label": "Geraldine Forbes, Women in Modern India (1996)", "type": "scholarly" }
  ],
  "verified": true
}
```

---

## Field reference

### `id` — required, string, unique

Kebab-case, globally unique across all collection files. Convention: descriptive phrase, not just a noun. `women-in-the-independence-movement`, not `women-collection`.

### `title` — required, string

Display title. Sentence case. Shown on the collection pill in the bar and at the head of the collection reader.

### `subtitle` — optional, string

Second line under the title. The "what's interesting about this gathering" framing in one sentence.

### `summary` — required, string

The collection's elevator pitch. One paragraph, 30–80 words. Shown in the collections picker before the reader opens the collection itself.

### `framing` — optional, string

Editorial paragraph that goes above the member list. ≤200 words. Use when the *frame* of the collection is the point — e.g. arguing why this grouping deserves surfacing. If the title and summary already say it, skip framing.

### `members` — required, list of `{kind, ...}`

At least one member entry. Heterogeneous list — each entry is one of:

- `{ "kind": "event", "id": "salt-march-1930" }` — single event by id. Validator fails if id doesn't resolve to an event.
- `{ "kind": "tag", "tag": "women-leaders" }` — all events whose `tags[]` contains the named tag. Expanded at runtime. Validator fails if no event in the corpus has the tag (use sparingly — empty tag selectors silently produce empty collections).

Mixing kinds in one `members[]` is fine and common — a tag selector pulls in the regulars, explicit event entries patch in the events that don't fit any tag cleanly.

The renderer deduplicates: if an event matches both a tag selector and an explicit entry, it appears once.

The renderer sorts members chronologically (by `date.start`) regardless of authoring order. Authoring order is not load-bearing.

### `sources` — recommended, list of `{label, url?, type}`

Same shape as the events `sources` array. Where the editorial framing came from.

### `verified` — required, bool

Same meaning as on events and threads. `false` is allowed and surfaces in the UI.

---

## Hard validator rules

A collection fails validation if any of the following:

1. Missing any required field (`id`, `title`, `summary`, `members`, `verified`)
2. `id` is not unique across the collections corpus
3. `id` is not kebab-case
4. `members` is empty or not a list
5. Any member entry is not an object
6. Any member entry's `kind` is not in `{event, tag}`
7. `kind: "event"` member with missing `id` or `id` doesn't resolve to any event
8. `kind: "tag"` member with missing `tag` or `tag` is not kebab-case
9. `kind: "tag"` member where no event in the corpus has that tag (empty selector)
10. `verified` is not a bool

## Soft warnings (build still passes)

- `summary` shorter than 30 words or longer than 80
- `framing` longer than 200 words
- Effective member count (after expansion + dedup) is fewer than 3 (a collection of 1–2 events is usually better as either a thread or just two separately authored events)
- `verified: false`

---

## Curation discipline (not validator-enforced)

1. **A collection should answer "why these together?"** If the answer is "because they happened" or "because they're famous", it's not a collection — it's a list. Collections argue for kinship. Threads argue for sequence. Lists belong in the events corpus itself.

2. **Tags follow collections, not the other way.** The intended workflow is: when authoring a collection, invent a tag for it, apply the tag to every event that fits, then use the tag selector. Tags created independently of collections often languish unused.

3. **Cross-collection events are fine and good.** The same event can belong to many collections — Salt March can sit in "women in independence" (Sarojini led day 24), "rebellions", and "founding moments of mass civil disobedience" simultaneously. Collections aren't a partition.

4. **Collections that span the whole subcontinent across centuries are usually too broad.** "Major battles" is too broad; "Battles that altered dynastic succession" earns the framing. Specificity is the editorial value.
