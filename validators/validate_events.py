#!/usr/bin/env python3
"""
validate_events.py — schema conformance for events_*.json files.

Usage
-----
    python3 validate_events.py [path/to/events_dir]

If no path is given, defaults to the current directory.

Exit code
---------
    0 if all hard rules pass (warnings allowed)
    1 if any hard rule fails

Behaviour
---------
- Loads every events_*.json file in the directory.
- Builds a single corpus by concatenating events arrays.
- Runs hard rules (failures) and soft rules (warnings).
- Resolves caused_by / part_of references across the entire corpus.
- If validator_boundaries.json is present, runs point-in-polygon checks
  to confirm each event's lat/lon falls inside the polygon for its
  declared location.country.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from collections import defaultdict


# ---------- vocabularies (must match SCHEMA.md) ----------
ERAS = {
    "vedic", "mahajanapada", "maurya", "post-maurya", "gupta",
    "early-medieval", "sultanate", "mughal", "maratha",
    "colonial", "independence", "republic",
}

CATEGORIES = {
    "political", "military", "religious", "cultural", "scientific",
    "economic", "dynastic", "colonial-administration", "resistance", "reform",
}

PRECISIONS = {"day", "month", "year", "decade", "century"}

LOCATION_TYPES = {"point", "city", "region", "route"}

# ISO 3166-1 alpha-2 codes for countries that are in the asset's geographic
# scope. "OFF" is reserved for events outside the map (e.g., London Round
# Table conferences) — these are excluded from the point-in-polygon check.
COUNTRIES = {
    "IN", "PK", "BD", "NP", "BT", "LK", "AF",
    "UZ", "TJ", "TM", "KZ", "KG",
    "MM", "CN", "IR", "RU", "MN",
    "AE", "OM", "SA", "YE",
    "TH", "LA", "VN", "KH",
    "OFF",
}

# Mapping: ISO code -> name as used in world-atlas (validator_boundaries.json)
COUNTRY_NAMES = {
    "PK": "Pakistan", "BD": "Bangladesh", "NP": "Nepal", "BT": "Bhutan",
    "LK": "Sri Lanka", "AF": "Afghanistan",
    "UZ": "Uzbekistan", "TJ": "Tajikistan", "TM": "Turkmenistan",
    "KZ": "Kazakhstan", "KG": "Kyrgyzstan",
    "MM": "Myanmar", "CN": "China", "IR": "Iran", "RU": "Russia",
    "MN": "Mongolia",
    "AE": "United Arab Emirates", "OM": "Oman",
    "SA": "Saudi Arabia", "YE": "Yemen",
    "TH": "Thailand", "LA": "Laos", "VN": "Vietnam", "KH": "Cambodia",
}

LINK_TYPES = {"wikipedia", "primary", "archive", "related", "secondary"}
SOURCE_TYPES = {"scholarly", "primary", "secondary", "reference"}

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# Asset bounding box — events outside this should set country="OFF" or be
# moved. Generous to allow Babur's Central Asia.
BBOX = (5.0, 55.0, 55.0, 105.0)  # min_lat, max_lat, min_lon, max_lon

# ---------- result accumulators ----------
errors: list[str] = []
warnings: list[str] = []


def err(loc, msg):
    errors.append(f"  ERROR  {loc}: {msg}")


def warn(loc, msg):
    warnings.append(f"  warn   {loc}: {msg}")


# ---------- point-in-polygon helper ----------
# Pure-Python ray casting; avoids a shapely dependency at validator time.
def _point_in_ring(x, y, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_polygon(x, y, polygon):
    # polygon is a list of rings; first is outer, rest are holes
    if not polygon or not polygon[0]:
        return False
    if not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True


def point_in_geometry(lon, lat, geom):
    """geom is a GeoJSON-shaped Polygon or MultiPolygon dict."""
    if geom["type"] == "Polygon":
        return _point_in_polygon(lon, lat, geom["coordinates"])
    if geom["type"] == "MultiPolygon":
        return any(_point_in_polygon(lon, lat, poly) for poly in geom["coordinates"])
    return False


REPO_ROOT = Path(__file__).resolve().parent.parent

_boundaries = None
def get_boundaries(root):
    """Lazy-load boundaries.json once per validator run. Returns None if absent.

    Looks first at <root>/validator_boundaries.json (legacy flat layout),
    then at <REPO>/build/validator_boundaries.json (current layout).
    """
    global _boundaries
    if _boundaries is not None:
        return _boundaries
    for f in (root / "validator_boundaries.json", REPO_ROOT / "build" / "validator_boundaries.json"):
        if f.exists():
            _boundaries = json.loads(f.read_text())
            return _boundaries
    return None


# ---------- date parsing ----------
def parse_year(s):
    """Return integer year from a date-like string, or None if unparseable."""
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
    else:
        try:
            return int(parts[0])
        except ValueError:
            return None


# ---------- per-event validation ----------
REQUIRED = ["id", "title", "tooltip", "summary", "date", "location", "era", "category", "links", "verified"]


def validate_event(ev, path, all_ids, boundaries):
    loc = f"{path.name}#{ev.get('id', '<missing-id>')}"

    # required fields
    for f in REQUIRED:
        if f not in ev:
            err(loc, f"missing required field '{f}'")

    # id format
    eid = ev.get("id")
    if eid is not None:
        if not isinstance(eid, str) or not ID_RE.match(eid):
            err(loc, f"id '{eid}' must be kebab-case")

    # title length
    title = ev.get("title", "")
    if isinstance(title, str) and len(title) > 60:
        warn(loc, f"title is {len(title)} chars (>60 is hard to display)")

    # tooltip length
    tooltip = ev.get("tooltip", "")
    if isinstance(tooltip, str):
        if len(tooltip) > 80:
            err(loc, f"tooltip is {len(tooltip)} chars (>80 is the hard cap)")
        elif len(tooltip) > 60:
            warn(loc, f"tooltip is {len(tooltip)} chars (>60 — consider trimming)")
        elif len(tooltip) == 0:
            err(loc, "tooltip cannot be empty")

    # summary length
    summ = ev.get("summary", "")
    if isinstance(summ, str):
        if len(summ) > 160:
            err(loc, f"summary is {len(summ)} chars (>160 is the hard cap)")
        elif len(summ) > 140:
            warn(loc, f"summary is {len(summ)} chars (>140 — consider trimming)")

    # detail word count
    detail = ev.get("detail")
    if detail and len(detail.split()) > 200:
        warn(loc, f"detail is {len(detail.split())} words (>200)")

    # date
    date = ev.get("date") or {}
    if not isinstance(date, dict):
        err(loc, "date must be an object")
    else:
        for f in ("start", "end", "precision", "approximate", "display"):
            if f not in date:
                err(loc, f"date.{f} missing")

        prec = date.get("precision")
        if prec is not None and prec not in PRECISIONS:
            err(loc, f"date.precision '{prec}' not in {sorted(PRECISIONS)}")

        ys = parse_year(date.get("start"))
        ye = parse_year(date.get("end"))
        if ys is None and date.get("start"):
            err(loc, f"date.start '{date.get('start')}' is unparseable")
        if ye is None and date.get("end"):
            err(loc, f"date.end '{date.get('end')}' is unparseable")
        if ys is not None and ye is not None and ys > ye:
            err(loc, f"date.start ({ys}) > date.end ({ye})")
        if ys is not None and (ys < -3000 or ys > 2100):
            warn(loc, f"date.start year {ys} is outside expected range [-3000, 2100]")

    # location
    locn = ev.get("location") or {}
    if not isinstance(locn, dict):
        err(loc, "location must be an object")
    else:
        if locn.get("type") not in LOCATION_TYPES:
            err(loc, f"location.type '{locn.get('type')}' not in {sorted(LOCATION_TYPES)}")
        if not locn.get("name"):
            err(loc, "location.name is required")
        country = locn.get("country")
        if not country:
            err(loc, "location.country is required (use ISO alpha-2 or 'OFF')")
        elif country not in COUNTRIES:
            err(loc, f"location.country '{country}' not in {sorted(COUNTRIES)}")
        pts = locn.get("points") or []
        if not pts:
            err(loc, "location.points must contain at least one {lat, lon}")
        for i, p in enumerate(pts):
            lat, lon = p.get("lat"), p.get("lon")
            if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
                err(loc, f"location.points[{i}].lat invalid: {lat}")
            if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
                err(loc, f"location.points[{i}].lon invalid: {lon}")
            # bbox check (only on point 0; routes can wander)
            if i == 0 and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                if not (BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lon <= BBOX[3]):
                    if country != "OFF":
                        err(loc, f"location.points[0] ({lat}, {lon}) is outside the asset bbox; set country='OFF' if intentional")
        if locn.get("type") == "route" and len(pts) < 2:
            err(loc, "location.type 'route' requires at least 2 points")

        # Point-in-polygon: pin must fall inside the country polygon.
        # Skipped if: country is OFF, boundaries file is absent, or no point.
        if country and country != "OFF" and pts and boundaries:
            lon0 = pts[0].get("lon")
            lat0 = pts[0].get("lat")
            if isinstance(lon0, (int, float)) and isinstance(lat0, (int, float)):
                geom = None
                if country == "IN":
                    geom = boundaries.get("IN")
                else:
                    name = COUNTRY_NAMES.get(country)
                    if name:
                        geom = boundaries.get("by_country_name", {}).get(name)
                if geom is None:
                    warn(loc, f"no boundary polygon available for country='{country}' — PIP check skipped")
                elif not point_in_geometry(lon0, lat0, geom):
                    err(loc, f"location.points[0] ({lat0:.4f}, {lon0:.4f}) does not fall inside {country}'s polygon")

    # era
    era = ev.get("era")
    if era and era not in ERAS:
        err(loc, f"era '{era}' not in {sorted(ERAS)}")

    # category
    cats = ev.get("category") or []
    if not isinstance(cats, list) or not cats:
        err(loc, "category must be a non-empty list")
    else:
        for c in cats:
            if c not in CATEGORIES:
                err(loc, f"category '{c}' not in {sorted(CATEGORIES)}")

    # links — wikipedia required
    links = ev.get("links") or []
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
            err(loc, "every event must have a link with type='wikipedia'")

    # sources (optional)
    srcs = ev.get("sources") or []
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

    # caused_by — needs gloss, no self-reference, ID must resolve
    cb = ev.get("caused_by") or []
    if not isinstance(cb, list):
        err(loc, "caused_by must be a list")
    else:
        for i, link in enumerate(cb):
            if not isinstance(link, dict):
                err(loc, f"caused_by[{i}] must be an object")
                continue
            cid = link.get("id")
            if not cid:
                err(loc, f"caused_by[{i}].id required")
            elif cid == eid:
                err(loc, f"caused_by[{i}] is a self-reference")
            elif cid not in all_ids:
                err(loc, f"caused_by[{i}].id '{cid}' does not resolve to any event")
            if not link.get("gloss"):
                err(loc, f"caused_by[{i}].gloss required (the editorial reason for the link)")

    # part_of — no self-reference, ID must resolve, gloss not required
    po = ev.get("part_of") or []
    if not isinstance(po, list):
        err(loc, "part_of must be a list")
    else:
        for i, link in enumerate(po):
            if not isinstance(link, dict):
                err(loc, f"part_of[{i}] must be an object")
                continue
            pid = link.get("id")
            if not pid:
                err(loc, f"part_of[{i}].id required")
            elif pid == eid:
                err(loc, f"part_of[{i}] is a self-reference")
            elif pid not in all_ids:
                err(loc, f"part_of[{i}].id '{pid}' does not resolve to any event")

    # verified
    if "verified" in ev and not isinstance(ev["verified"], bool):
        err(loc, "verified must be true or false")
    if ev.get("verified") is False:
        warn(loc, "verified=false (FYI — UI will surface this)")


# ---------- main ----------
def main():
    # Default to <repo>/data/events; allow CLI override for ad-hoc lints.
    default = REPO_ROOT / "data" / "events"
    root = Path(sys.argv[1] if len(sys.argv) > 1 else default).resolve()
    files = sorted(root.glob("events_*.json"))
    if not files:
        print(f"No events_*.json files found in {root}")
        return 1

    print(f"Validating {len(files)} events file(s) in {root}")
    boundaries = get_boundaries(root)
    if boundaries is None:
        print("  (no validator_boundaries.json — point-in-polygon checks skipped)")
    else:
        n_surrounds = len(boundaries.get("by_country_name", {}))
        print(f"  point-in-polygon: India + {n_surrounds} surrounding countries")
    print()

    # Pass 1: load + collect IDs
    corpus = []
    id_counts = defaultdict(list)
    for p in files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            err(p.name, f"invalid JSON: {e}")
            continue
        evs = data.get("events") or []
        if not isinstance(evs, list):
            err(p.name, "top-level 'events' must be a list")
            continue
        for ev in evs:
            corpus.append((p, ev))
            if ev.get("id"):
                id_counts[ev["id"]].append(p.name)

    for eid, where in id_counts.items():
        if len(where) > 1:
            err("corpus", f"duplicate id '{eid}' in {where}")

    all_ids = set(id_counts.keys())

    for p, ev in corpus:
        validate_event(ev, p, all_ids, boundaries)

    print(f"Found {len(corpus)} events across {len(files)} file(s).\n")
    if warnings:
        print(f"{len(warnings)} warning(s):")
        for w in warnings:
            print(w)
        print()
    if errors:
        print(f"{len(errors)} error(s):")
        for e in errors:
            print(e)
        print(f"\nFAIL")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
