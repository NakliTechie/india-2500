#!/usr/bin/env python3
"""
validate_collections.py — schema conformance for collections_*.json files.

Collections reference events by id (kind="event") or by tag (kind="tag"). This
validator loads the events corpus first (every events_*.json), then validates
each collection against both the schema and the resolved event ids / tag uses.

Usage
-----
    python3 validate_collections.py [path/to/dir]

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

SOURCE_TYPES = {"scholarly", "primary", "secondary", "reference"}
MEMBER_KINDS = {"event", "tag"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

errors: list[str] = []
warnings: list[str] = []


def err(loc, msg):
    errors.append(f"  ERROR  {loc}: {msg}")


def warn(loc, msg):
    warnings.append(f"  warn   {loc}: {msg}")


REQUIRED_COLLECTION_FIELDS = ["id", "title", "summary", "members", "verified"]


REPO_ROOT = Path(__file__).resolve().parent.parent


def load_corpus(root: Path):
    """Return (event_by_id, tag_to_events) for every events_*.json file.

    Looks in <repo>/data/events by default; falls back to `root` if the
    caller passed a flat directory."""
    events_by_id = {}
    tag_to_events = defaultdict(list)
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
            eid = ev.get("id")
            if not eid:
                continue
            events_by_id[eid] = ev
            for tag in ev.get("tags") or []:
                if isinstance(tag, str):
                    tag_to_events[tag].append(eid)
    return events_by_id, tag_to_events, event_files


def validate_collection(c, path, events_by_id, tag_to_events):
    loc = f"{path.name}#{c.get('id', '<missing-id>')}"

    for f in REQUIRED_COLLECTION_FIELDS:
        if f not in c:
            err(loc, f"missing required field '{f}'")

    cid = c.get("id")
    if cid and not ID_RE.match(cid):
        err(loc, f"id '{cid}' must be kebab-case")

    title = c.get("title", "")
    if isinstance(title, str) and len(title) > 80:
        warn(loc, f"title is {len(title)} chars (>80 may not display well)")

    # summary word count (30-80 expected)
    summary = c.get("summary") or ""
    if summary:
        wc = len(summary.split())
        if wc < 30:
            warn(loc, f"summary is {wc} words (<30 — feels truncated)")
        elif wc > 80:
            warn(loc, f"summary is {wc} words (>80 — consider trimming)")

    # framing (optional, ≤200 words)
    framing = c.get("framing")
    if framing:
        wc = len(framing.split())
        if wc > 200:
            warn(loc, f"framing is {wc} words (>200 — consider tightening)")

    # members
    members = c.get("members")
    if not isinstance(members, list):
        err(loc, "members must be a list")
    elif not members:
        err(loc, "members cannot be empty")
    else:
        # Track resolved event ids for the effective-count warning.
        resolved_ids: set[str] = set()
        for i, m in enumerate(members):
            if not isinstance(m, dict):
                err(loc, f"members[{i}] must be an object with kind + id|tag")
                continue
            kind = m.get("kind")
            if kind not in MEMBER_KINDS:
                err(loc, f"members[{i}].kind '{kind}' not in {sorted(MEMBER_KINDS)}")
                continue
            if kind == "event":
                eid = m.get("id")
                if not eid:
                    err(loc, f"members[{i}] kind=event requires 'id'")
                elif eid not in events_by_id:
                    err(loc, f"members[{i}].id '{eid}' does not resolve to any event")
                else:
                    resolved_ids.add(eid)
            elif kind == "tag":
                tag = m.get("tag")
                if not tag:
                    err(loc, f"members[{i}] kind=tag requires 'tag'")
                elif not isinstance(tag, str) or not ID_RE.match(tag):
                    err(loc, f"members[{i}].tag '{tag}' must be kebab-case")
                elif tag not in tag_to_events:
                    err(loc, f"members[{i}].tag '{tag}' does not match any event in the corpus (empty selector)")
                else:
                    resolved_ids.update(tag_to_events[tag])

        if len(resolved_ids) < 3 and members:
            warn(loc, f"effective member count is {len(resolved_ids)} (<3 — consider whether this earns its own collection)")

    # sources
    srcs = c.get("sources") or []
    if not isinstance(srcs, list):
        err(loc, "sources must be a list")
    else:
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
    if "verified" in c and not isinstance(c["verified"], bool):
        err(loc, "verified must be true or false")
    if c.get("verified") is False:
        warn(loc, "verified=false (FYI)")


def main():
    # Default to <repo>/data/collections; allow CLI override
    default = REPO_ROOT / "data" / "collections"
    root = Path(sys.argv[1] if len(sys.argv) > 1 else default).resolve()

    events_by_id, tag_to_events, event_files = load_corpus(root)
    if not event_files:
        print("No events_*.json files found; cannot resolve collection references.")
        return 1

    if not root.is_dir():
        print(f"No collections directory at {root} — nothing to validate.")
        print("PASS")
        return 0

    collection_files = sorted(root.glob("collections_*.json"))
    if not collection_files:
        print(f"No collections_*.json files found in {root} — nothing to validate.")
        print("PASS")
        return 0

    print(f"Loaded {len(events_by_id)} events ({len(tag_to_events)} distinct tags) from {len(event_files)} file(s).")
    print(f"Validating {len(collection_files)} collections file(s) in {root}\n")

    all_collections = []
    id_counts = defaultdict(list)
    for p in collection_files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            err(p.name, f"invalid JSON: {e}")
            continue
        for c in data.get("collections", []):
            all_collections.append((p, c))
            if c.get("id"):
                id_counts[c["id"]].append(p.name)

    for cid, where in id_counts.items():
        if len(where) > 1:
            err("corpus", f"duplicate collection id '{cid}' in {where}")

    for p, c in all_collections:
        validate_collection(c, p, events_by_id, tag_to_events)

    print(f"Found {len(all_collections)} collection(s).\n")
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
