## What this PR adds / changes

<!-- One or two sentences. -->

## Type

<!-- Tick all that apply. -->
- [ ] New event(s) — `data/events/`
- [ ] New thread(s) — `data/threads/`
- [ ] New person / track step(s) — `data/people/`
- [ ] Correction to existing entry
- [ ] Schema / validator change
- [ ] Build / template / UI change
- [ ] Docs

## Sources for new / changed editorial content

<!-- Two independent sources for any new or changed `verified: true` entries. Scholarly preferred. Skip if this is purely code/infra. -->

1.
2.

## Validators + tests

<!-- CI runs all of these. Confirm you've also run them locally. -->
- [ ] `python3 validators/validate_events.py` — PASS
- [ ] `python3 validators/validate_threads.py` — PASS
- [ ] `python3 validators/validate_people.py` — PASS
- [ ] `python3 build/build_html.py` — succeeded
- [ ] `python3 tests/render_test_*.py` — all PASS

## Editorial checklist

- [ ] Verified figures (cross-checked against ≥2 sources, or `verified: false`)
- [ ] Tooltip ≤ 80 chars; summary ≤ 160 chars; detail 80–150 words
- [ ] Wikipedia link present (`type: "wikipedia"`)
- [ ] No mid-sentence bolding, no emoji
- [ ] No flattening of small dynasties into larger neighbours

## Notes for reviewer

<!--  -->
