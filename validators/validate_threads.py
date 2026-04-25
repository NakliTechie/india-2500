#!/usr/bin/env python3
"""
validate_threads.py — schema conformance for threads_*.json files.

Threads reference event IDs from the events corpus. This validator loads the
events corpus first (every events_*.json), then validates each thread against
both the schema and the resolved event IDs.

Usage
-----
    python3 validate_threads.py [path/to/dir]

Exit code
---------
    0 if all hard rules pass
    1 if any hard rule fails
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from collections import defaultdict

ERAS = {
    "vedic", "mahajanapada", "maurya", "post-maurya", "gupta",
    "early-medieval", "sultanate", "mughal", "maratha",
    "colonial", "independence", "republic",
}
KINDS = {"narrative", "causal-chain", "thematic", "counterfactual"}
SOURCE_TYPES = {"scholarly", "primary", "secondary", "reference"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

errors: list[str] = []
warnings: list[str] = []


def err(loc, msg):
    errors.append(f"  ERROR  {loc}: {msg}")


def warn(loc, msg):
    warnings.append(f"  warn   {loc}: {msg}")


def parse_year(s):
    if isinstance(s, int):
        return s
    if not isinstance(s, str) or not s:
        return None
    parts = s.split("-")
    if s.startswith("-"):
        if len(parts) == 1:
            try:
                return int(s)
            except ValueError:
                return None
        try:
            return -int(parts[1])
        except (ValueError, IndexError):
            return None
    try:
        return int(parts[0])
    except ValueError:
        return None


REQUIRED_THREAD_FIELDS = [
    "id", "title", "summary", "kind", "era_span", "date_span",
    "steps", "coda", "verified",
]


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_corpus(root: Path):
    """Return dict id -> event for every events_*.json file. Looks in
    <repo>/data/events by default; falls back to `root` if the caller
    passed a flat directory."""
    corpus = {}
    events_dir = REPO_ROOT / "data" / "events"
    if not events_dir.is_dir():
        events_dir = root
    event_files = sorted(events_dir.glob("events_*.json"))
    for p in event_files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for ev in data.get("events", []):
            if ev.get("id"):
                corpus[ev["id"]] = ev
    return corpus, event_files


def validate_thread(t, path, corpus_ids):
    loc = f"{path.name}#{t.get('id', '<missing-id>')}"

    for f in REQUIRED_THREAD_FIELDS:
        if f not in t:
            err(loc, f"missing required field '{f}'")

    tid = t.get("id")
    if tid and not ID_RE.match(tid):
        err(loc, f"id '{tid}' must be kebab-case")

    # kind
    if t.get("kind") not in KINDS:
        err(loc, f"kind '{t.get('kind')}' not in {sorted(KINDS)}")

    # era_span
    es = t.get("era_span") or []
    if not isinstance(es, list) or not es:
        err(loc, "era_span must be a non-empty list")
    else:
        for e in es:
            if e not in ERAS:
                err(loc, f"era_span value '{e}' not in {sorted(ERAS)}")

    # date_span
    ds = t.get("date_span") or {}
    if not isinstance(ds, dict):
        err(loc, "date_span must be an object")
    else:
        if "start" not in ds or "end" not in ds:
            err(loc, "date_span must have start and end")
        ys = parse_year(ds.get("start"))
        ye = parse_year(ds.get("end"))
        if ys is not None and ye is not None and ys > ye:
            err(loc, f"date_span.start ({ys}) > date_span.end ({ye})")

    # steps
    steps = t.get("steps") or []
    if not isinstance(steps, list):
        err(loc, "steps must be a list")
    else:
        if len(steps) < 3:
            err(loc, f"thread has only {len(steps)} steps; minimum is 3")
        if len(steps) > 12:
            warn(loc, f"thread has {len(steps)} steps; consider splitting (>10 is heavy)")

        prev_event = None
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                err(loc, f"steps[{i}] must be an object")
                continue
            ev_id = step.get("event_id")
            if not ev_id:
                err(loc, f"steps[{i}].event_id required")
            elif ev_id not in corpus_ids:
                err(loc, f"steps[{i}].event_id '{ev_id}' does not resolve to any event")
            if prev_event and ev_id == prev_event:
                err(loc, f"steps[{i}] repeats the previous step's event_id ('{ev_id}')")
            prev_event = ev_id

            if not step.get("note"):
                err(loc, f"steps[{i}].note required (cannot be empty)")

            transition = step.get("transition")
            is_last = i == len(steps) - 1
            if is_last:
                if transition is not None:
                    err(loc, f"final step's transition must be null (got: {transition!r})")
            else:
                if not transition:
                    err(loc, f"steps[{i}].transition required for non-final steps")

        # date_span vs actual events
        if isinstance(ds, dict) and steps:
            event_years = []
            for step in steps:
                ev = next((e for e in corpus.values() if e.get("id") == step.get("event_id")), None)
                if ev:
                    y = parse_year(ev.get("date", {}).get("start"))
                    if y is not None:
                        event_years.append(y)
            if event_years:
                actual_min, actual_max = min(event_years), max(event_years)
                ys = parse_year(ds.get("start"))
                ye = parse_year(ds.get("end"))
                if ys is not None and ys > actual_min:
                    warn(loc, f"date_span.start ({ys}) > earliest event ({actual_min})")
                if ye is not None and ye < actual_max:
                    warn(loc, f"date_span.end ({ye}) < latest event ({actual_max})")

    # coda
    coda = t.get("coda") or ""
    word_count = len(coda.split())
    if word_count < 20:
        warn(loc, f"coda is {word_count} words (<20 — feels truncated)")
    elif word_count > 150:
        warn(loc, f"coda is {word_count} words (>150 — consider trimming)")

    # sources
    srcs = t.get("sources") or []
    for i, s in enumerate(srcs):
        if not isinstance(s, dict):
            err(loc, f"sources[{i}] must be an object")
            continue
        if not s.get("label"):
            err(loc, f"sources[{i}].label required")
        ty = s.get("type")
        if ty and ty not in SOURCE_TYPES:
            err(loc, f"sources[{i}].type '{ty}' not in {sorted(SOURCE_TYPES)}")

    # verified
    if "verified" in t and not isinstance(t["verified"], bool):
        err(loc, "verified must be true or false")
    if t.get("verified") is False:
        warn(loc, "verified=false (FYI)")


# Module-level so validate_thread can read events
corpus = {}


def main():
    global corpus
    # Default to <repo>/data/threads; allow CLI override
    default = REPO_ROOT / "data" / "threads"
    root = Path(sys.argv[1] if len(sys.argv) > 1 else default).resolve()
    corpus, event_files = load_corpus(root)
    if not event_files:
        print(f"No events_*.json files found; cannot resolve thread references.")
        return 1
    corpus_ids = set(corpus.keys())

    thread_files = sorted(root.glob("threads_*.json"))
    if not thread_files:
        print(f"No threads_*.json files found in {root}")
        return 0

    print(f"Loaded {len(corpus_ids)} events from {len(event_files)} file(s).")
    print(f"Validating {len(thread_files)} threads file(s) in {root}\n")

    # Collect threads + check uniqueness
    all_threads = []
    id_counts = defaultdict(list)
    for p in thread_files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            err(p.name, f"invalid JSON: {e}")
            continue
        for t in data.get("threads", []):
            all_threads.append((p, t))
            if t.get("id"):
                id_counts[t["id"]].append(p.name)

    for tid, where in id_counts.items():
        if len(where) > 1:
            err("corpus", f"duplicate thread id '{tid}' in {where}")

    for p, t in all_threads:
        validate_thread(t, p, corpus_ids)

    print(f"Found {len(all_threads)} thread(s).\n")
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(w)
        print()
    if errors:
        print(f"{len(errors)} error(s):")
        for e in errors:
            print(e)
        print("\nFAIL")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
