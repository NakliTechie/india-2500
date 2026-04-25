# Threads schema (`threads_*.json`)

The events corpus answers *what happened where and when*. Threads answer *here is a story you can tell with these events*.

A thread is a curated, ordered walk through events that already exist in the events corpus. It never duplicates event content — it only adds the editorial connective tissue that makes a sequence read as prose.

This document is the contract. The validator (`validate_threads.py`) enforces it.

---

## File shape

```jsonc
{
  "campaign": "independence",
  "scope": "Editorial threads through the independence movement",
  "updated": "2026-04-25",
  "threads": [
    { /* thread record */ }
  ]
}
```

A thread can reference event IDs from any campaign file in the events corpus. The validator fails if any referenced event ID doesn't resolve.

---

## Thread record

```jsonc
{
  "id": "chauri-chaura-and-the-cost-of-non-violence",
  "title": "Chauri Chaura and the cost of non-violence",
  "subtitle": "Why Gandhi suspended a movement at its peak — and what it cost the freedom struggle.",
  "summary": "In February 1922, with the Non-Cooperation Movement at its high tide, a single incident at a small police station in eastern UP made Gandhi call the whole thing off. It would be eight years before he led another mass campaign.",

  "kind": "causal-chain",
  "era_span":  ["colonial"],
  "date_span": { "start": "1919", "end": "1930" },
  "tags":      ["resistance", "gandhi"],

  "steps": [
    {
      "event_id": "jallianwala-bagh-1919",
      "note": "The wound that radicalized a generation of moderates. Constitutional politics no longer felt like the answer.",
      "transition": "Within a year, Gandhi had a programme: not constitutional, not violent, mass and organized."
    },
    {
      "event_id": "non-cooperation-movement-1920",
      "note": "Gandhi's response to Jallianwala — a coordinated boycott of British institutions. By late 1921 it was the largest mass movement India had ever seen.",
      "transition": "Then a single afternoon in February 1922 changed Gandhi's calculation."
    },
    {
      "event_id": "chauri-chaura-1922",
      "note": "A demonstration turned on the police; 22 policemen were killed and the station burned. Gandhi suspended the entire movement within a week — over the objections of nearly every other Congress leader.",
      "transition": "The pause stretched. It would be eight years before he led another mass campaign."
    },
    {
      "event_id": "salt-march-1930",
      "note": "When Gandhi returned to mass action, the staging was meticulous — 24 days, 240 miles, no improvisation. He had learned from Chauri Chaura that the optics of discipline mattered more than the speed of escalation.",
      "transition": null
    }
  ],

  "coda": "It took eight years for Gandhi to lead another mass movement after Chauri Chaura. The pause was the price of insisting non-violence wasn't a tactic but a precondition. Generations have argued whether the price was worth paying.",

  "sources": [
    { "label": "Shahid Amin, Event, Metaphor, Memory: Chauri Chaura 1922–1992 (1995)", "type": "scholarly" },
    { "label": "Guha, India After Gandhi (2007)", "type": "scholarly" }
  ],
  "verified": true
}
```

---

## Field reference

### `id` — required, string, unique

Kebab-case, globally unique across all thread files. Convention: descriptive phrase, not just a year. `chauri-chaura-and-the-cost-of-non-violence`, not `chauri-chaura-thread`.

### `title` — required, string

The display title in the threads picker and at the head of the thread reader.

### `subtitle` — optional, string

A second line under the title. The "what's interesting about this" framing, in one sentence.

### `summary` — required, string

The thread's elevator pitch. One paragraph, 30–80 words. Shown in the threads picker before the reader opens the thread itself.

### `kind` — required, enum

How the thread is organized. The renderer uses this for slight differences in presentation.

- **`narrative`** — a story arc (Babur's road to Panipat). Steps move forward in time, transitions emphasize cause and consequence.
- **`causal-chain`** — a tight chain following `caused_by` edges in the events graph (Jallianwala → Non-Cooperation → Chauri Chaura → Salt March). Steps are usually contiguous in the graph.
- **`thematic`** — non-causal grouping around an idea ("Capitals that didn't last," "Major Indian famines under colonial rule"). Steps may span centuries with no causal link between adjacent ones.
- **`counterfactual`** — same events, alternative reading. Used sparingly. The coda usually carries the editorial weight.

### `era_span` — required, list of `era` values

Which eras the thread touches. Used for filtering ("show me threads that cross into the colonial era"). At least one value.

### `date_span` — required, `{start, end}`

Outer envelope of the thread's events. Years as integers (negative for BCE) or ISO date strings. Validator checks consistency with the actual events referenced.

### `tags` — optional, list of strings

Free-form tags used in the threads picker. Common tags: `gandhi`, `dynastic`, `military`, `resistance`, `economic`, `religious`, `central-asia`. Lowercase, kebab-case.

### `steps` — required, list of step objects

Minimum 3 steps. Maximum 12 (soft warning above 10).

Each step:

```jsonc
{
  "event_id": "chauri-chaura-1922",
  "note": "Editorial gloss for why this event matters in this thread. 1–4 sentences. The same event in a different thread gets a different note.",
  "transition": "Connective sentence that bridges this step to the next. Last step's transition is null."
}
```

- `event_id` must resolve to a real event in the corpus.
- `note` is the *thread-specific* editorial framing of the event. Salt March in "Gandhi's tactics" reads about method; Salt March in "Economic grievances of the freedom struggle" reads about salt as a tax instrument. Same pin, different story.
- `transition` is the prose bridge to the next step. Last step's transition must be `null`. Every other step's transition must be a non-empty string.

### `coda` — required, string

The takeaway. One paragraph in your voice. The thing the reader walks away with. 30–120 words.

### `sources` — recommended, list of `{label, url?, type}`

Same shape as the events `sources` array. Where the editorial framing came from — typically scholarly works that argue for the reading the thread proposes.

### `verified` — required, bool

Same meaning as on events. `false` means the thread has been published with at least one event whose facts haven't been double-checked.

---

## Hard validator rules

1. Missing any required field
2. `id` not unique
3. `kind` not in vocab
4. Any `era_span` value not in the events era vocab
5. Fewer than 3 `steps`
6. Any `event_id` doesn't resolve to a real event
7. Two adjacent `steps` reference the same `event_id`
8. Any non-final `step.transition` is null or empty
9. Final `step.transition` is not `null`
10. `note` empty on any step

## Soft warnings

- More than 10 steps (consider splitting)
- `coda` shorter than 20 words or longer than 150 words
- `date_span` doesn't match the actual range of referenced events
- Thread spans events from more than three campaign files (consider whether the scope is too broad)
- `verified: false`

---

## Curation discipline

Three rules that aren't enforced by the validator but matter editorially:

1. **A thread must have a thesis.** If you can't write the `coda` in one paragraph, the thread isn't ready. "Events around Akbar" is not a thread; "How Akbar's religious policy created a backlash that defined Aurangzeb" is.
2. **Threads accumulate slow.** Aim for roughly 1 thread per 15–25 events long-term. Don't force them.
3. **Threads can disagree.** Two threads can frame the same events differently. The asset shouldn't pretend history has one reading.
