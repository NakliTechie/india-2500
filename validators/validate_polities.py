#!/usr/bin/env python3
"""
validate_polities.py — schema conformance for polities_*.json files.

Polities have an explicit events[] list of constitutive event ids; this
validator resolves each id against the events corpus, validates the
date_span and era vocab, and soft-warns when a capital's place reference
doesn't resolve to a place record.
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

CATEGORIES = {
    "empire", "sultanate", "dynasty", "princely-state",
    "confederacy", "colonial-state", "republic", "trading-company",
}

LINK_TYPES = {"wikipedia", "primary", "archive", "related", "secondary"}
SOURCE_TYPES = {"scholarly", "primary", "secondary", "reference"}
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

REPO_ROOT = Path(__file__).resolve().parent.parent

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


def load_event_ids():
    out = set()
    events_dir = REPO_ROOT / "data" / "events"
    if not events_dir.is_dir():
        return out
    for p in sorted(events_dir.glob("events_*.json")):
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for ev in data.get("events", []):
            if ev.get("id"):
                out.add(ev["id"])
    return out


def load_place_ids():
    out = set()
    places_dir = REPO_ROOT / "data" / "places"
    if not places_dir.is_dir():
        return out
    for p in sorted(places_dir.glob("places_*.json")):
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for pl in data.get("places", []):
            if pl.get("id"):
                out.add(pl["id"])
    return out


REQUIRED = ["id", "name", "tooltip", "summary", "date_span", "era_span",
            "category", "capitals", "rulers", "events", "links", "verified"]


def validate_polity(p, path, event_ids, place_ids):
    loc = f"{path.name}#{p.get('id', '<missing-id>')}"

    for f in REQUIRED:
        if f not in p:
            err(loc, f"missing required field '{f}'")

    pid = p.get("id")
    if pid and not ID_RE.match(pid):
        err(loc, f"id '{pid}' must be kebab-case")

    name = p.get("name", "")
    if not name:
        err(loc, "name is required")

    tooltip = p.get("tooltip", "")
    if isinstance(tooltip, str):
        if len(tooltip) > 80:
            err(loc, f"tooltip is {len(tooltip)} chars (>80 is the hard cap)")
        elif len(tooltip) == 0:
            err(loc, "tooltip cannot be empty")

    summary = p.get("summary", "")
    if isinstance(summary, str):
        if len(summary) > 160:
            err(loc, f"summary is {len(summary)} chars (>160 is the hard cap)")

    framing = p.get("framing")
    if framing:
        wc = len(framing.split())
        if wc > 300:
            warn(loc, f"framing is {wc} words (>300 — consider tightening)")

    ds = p.get("date_span") or {}
    if not isinstance(ds, dict):
        err(loc, "date_span must be an object")
    else:
        for f in ("start", "end", "display"):
            if f not in ds:
                err(loc, f"date_span.{f} missing")
        ys = parse_year(ds.get("start"))
        ye = parse_year(ds.get("end"))
        if ys is None and ds.get("start"):
            err(loc, f"date_span.start '{ds.get('start')}' is unparseable")
        if ye is None and ds.get("end"):
            err(loc, f"date_span.end '{ds.get('end')}' is unparseable")
        if ys is not None and ye is not None and ys > ye:
            err(loc, f"date_span.start ({ys}) > date_span.end ({ye})")

    es = p.get("era_span") or []
    if not isinstance(es, list) or not es:
        err(loc, "era_span must be a non-empty list")
    else:
        for e in es:
            if e not in ERAS:
                err(loc, f"era_span value '{e}' not in {sorted(ERAS)}")

    cat = p.get("category")
    if cat not in CATEGORIES:
        err(loc, f"category '{cat}' not in {sorted(CATEGORIES)}")

    caps = p.get("capitals") or []
    if not isinstance(caps, list) or not caps:
        err(loc, "capitals must be a non-empty list")
    else:
        for i, c in enumerate(caps):
            if not isinstance(c, dict):
                err(loc, f"capitals[{i}] must be an object")
                continue
            if not c.get("place"):
                err(loc, f"capitals[{i}].place is required")
            elif place_ids and c["place"] not in place_ids:
                warn(loc, f"capitals[{i}].place '{c['place']}' does not resolve to a place record (will render as plain text)")
            for f in ("from_year", "to_year"):
                if f not in c:
                    err(loc, f"capitals[{i}].{f} is required")
                elif not isinstance(c[f], int):
                    err(loc, f"capitals[{i}].{f} must be an integer")
            if isinstance(c.get("from_year"), int) and isinstance(c.get("to_year"), int) and c["from_year"] > c["to_year"]:
                err(loc, f"capitals[{i}] from_year ({c['from_year']}) > to_year ({c['to_year']})")

    rulers = p.get("rulers") or []
    if not isinstance(rulers, list) or not rulers:
        err(loc, "rulers must be a non-empty list")
    else:
        for i, r in enumerate(rulers):
            if not isinstance(r, str) or not r.strip():
                err(loc, f"rulers[{i}] must be a non-empty string")

    evs = p.get("events") or []
    if not isinstance(evs, list) or not evs:
        err(loc, "events must be a non-empty list")
    else:
        if event_ids:
            for i, eid in enumerate(evs):
                if not isinstance(eid, str):
                    err(loc, f"events[{i}] must be a string event id")
                elif eid not in event_ids:
                    err(loc, f"events[{i}] '{eid}' does not resolve to any event")
        if len(evs) < 3:
            warn(loc, f"only {len(evs)} event(s) — probably needs more to earn a polity record")

    links = p.get("links") or []
    if not isinstance(links, list):
        err(loc, "links must be a list")
    else:
        types_present = set()
        for i, lk in enumerate(links):
            if not isinstance(lk, dict):
                err(loc, f"links[{i}] must be an object")
                continue
            if not lk.get("url"):
                err(loc, f"links[{i}].url required")
            t = lk.get("type")
            if t not in LINK_TYPES:
                err(loc, f"links[{i}].type '{t}' not in {sorted(LINK_TYPES)}")
            types_present.add(t)
        if "wikipedia" not in types_present:
            err(loc, "every polity must have a link with type='wikipedia'")

    srcs = p.get("sources") or []
    if not isinstance(srcs, list):
        err(loc, "sources must be a list")
    else:
        for i, s in enumerate(srcs):
            if not isinstance(s, dict):
                err(loc, f"sources[{i}] must be an object")
                continue
            if not s.get("label"):
                err(loc, f"sources[{i}].label required")
            t = s.get("type")
            if t and t not in SOURCE_TYPES:
                err(loc, f"sources[{i}].type '{t}' not in {sorted(SOURCE_TYPES)}")

    if "verified" in p and not isinstance(p["verified"], bool):
        err(loc, "verified must be true or false")
    if p.get("verified") is False:
        warn(loc, "verified=false (FYI)")


def main():
    default = REPO_ROOT / "data" / "polities"
    root = Path(sys.argv[1] if len(sys.argv) > 1 else default).resolve()

    if not root.is_dir():
        print(f"No polities directory at {root} — nothing to validate.")
        print("PASS")
        return 0

    files = sorted(root.glob("polities_*.json"))
    if not files:
        print(f"No polities_*.json files found in {root} — nothing to validate.")
        print("PASS")
        return 0

    event_ids = load_event_ids()
    place_ids = load_place_ids()
    print(f"Loaded {len(event_ids)} events and {len(place_ids)} places for cross-reference.")
    print(f"Validating {len(files)} polities file(s) in {root}\n")

    all_records = []
    id_counts = defaultdict(list)
    for p in files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            err(p.name, f"invalid JSON: {e}")
            continue
        for rec in data.get("polities", []):
            all_records.append((p, rec))
            if rec.get("id"):
                id_counts[rec["id"]].append(p.name)

    for pid, where in id_counts.items():
        if len(where) > 1:
            err("corpus", f"duplicate polity id '{pid}' in {where}")

    for p, rec in all_records:
        validate_polity(rec, p, event_ids, place_ids)

    print(f"Found {len(all_records)} polit{'y' if len(all_records) == 1 else 'ies'}.\n")
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
