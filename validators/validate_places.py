#!/usr/bin/env python3
"""
validate_places.py — schema conformance for places_*.json files.

Places auto-gather events by coordinate proximity. This validator:
- Enforces the place schema (id format, length caps, controlled vocab).
- Runs PIP (point-in-polygon) on each place's anchor against its country.
- Surfaces a soft warning when the effective gather (events within
  radius_km of the place's anchor) has fewer than 3 members.

Usage
-----
    python3 validate_places.py [path/to/dir]
"""
from __future__ import annotations

import json
import math
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
    "capital", "city", "fort", "sacred-site", "port", "university",
    "sangam-confluence", "massacre-site", "trade-hub", "ashram",
    "prison", "princely-state-capital", "military-cantonment",
}

COUNTRIES = {
    "IN", "PK", "BD", "NP", "BT", "LK", "AF",
    "UZ", "TJ", "TM", "KZ", "KG",
    "MM", "CN", "IR", "RU", "MN",
    "AE", "OM", "SA", "YE",
    "TH", "LA", "VN", "KH",
    "OFF",
}

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

REPO_ROOT = Path(__file__).resolve().parent.parent

errors: list[str] = []
warnings: list[str] = []


def err(loc, msg):
    errors.append(f"  ERROR  {loc}: {msg}")


def warn(loc, msg):
    warnings.append(f"  warn   {loc}: {msg}")


# --- PIP (copied from validate_events.py) ---
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
    if not polygon or not polygon[0]:
        return False
    if not _point_in_ring(x, y, polygon[0]):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(x, y, hole):
            return False
    return True


def point_in_geometry(lon, lat, geom):
    if geom["type"] == "Polygon":
        return _point_in_polygon(lon, lat, geom["coordinates"])
    if geom["type"] == "MultiPolygon":
        return any(_point_in_polygon(lon, lat, poly) for poly in geom["coordinates"])
    return False


_boundaries = None
def get_boundaries(root):
    global _boundaries
    if _boundaries is not None:
        return _boundaries
    for f in (root / "validator_boundaries.json", REPO_ROOT / "build" / "validator_boundaries.json"):
        if f.exists():
            _boundaries = json.loads(f.read_text())
            return _boundaries
    return None


# --- Spherical haversine for proximity check ---
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dlam/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def load_event_corpus():
    """Returns list of (event_id, lat, lon) for proximity-gathering."""
    out = []
    events_dir = REPO_ROOT / "data" / "events"
    if not events_dir.is_dir():
        return out
    for p in sorted(events_dir.glob("events_*.json")):
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for ev in data.get("events", []):
            pts = (ev.get("location") or {}).get("points") or []
            if pts and ev.get("id"):
                lat = pts[0].get("lat")
                lon = pts[0].get("lon")
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                    out.append((ev["id"], lat, lon))
    return out


REQUIRED = ["id", "name", "tooltip", "summary", "location", "era_span", "category", "links", "verified"]


def validate_place(p, path, all_ids, boundaries, event_corpus):
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
        if wc > 250:
            warn(loc, f"framing is {wc} words (>250 — consider tightening)")

    locn = p.get("location") or {}
    if not isinstance(locn, dict):
        err(loc, "location must be an object")
    else:
        country = locn.get("country")
        if not country:
            err(loc, "location.country is required")
        elif country not in COUNTRIES:
            err(loc, f"location.country '{country}' not in {sorted(COUNTRIES)}")

        lat = locn.get("lat")
        lon = locn.get("lon")
        if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
            err(loc, f"location.lat invalid: {lat}")
        if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
            err(loc, f"location.lon invalid: {lon}")

        radius = locn.get("radius_km", 5)
        if not isinstance(radius, (int, float)) or radius <= 0:
            err(loc, f"location.radius_km must be a positive number, got {radius}")

        # PIP
        if (country and country != "OFF" and isinstance(lat, (int, float))
                and isinstance(lon, (int, float)) and boundaries):
            geom = None
            if country == "IN":
                geom = boundaries.get("IN")
            else:
                cn = COUNTRY_NAMES.get(country)
                if cn:
                    geom = boundaries.get("by_country_name", {}).get(cn)
            if geom is None:
                warn(loc, f"no boundary polygon for country='{country}' — PIP skipped")
            elif not point_in_geometry(lon, lat, geom):
                err(loc, f"location ({lat:.4f}, {lon:.4f}) does not fall inside {country}'s polygon")

        # Effective member count via proximity
        if (isinstance(lat, (int, float)) and isinstance(lon, (int, float))
                and isinstance(radius, (int, float)) and radius > 0 and event_corpus):
            members = sum(1 for (_, elat, elon) in event_corpus
                          if haversine_km(lat, lon, elat, elon) <= radius)
            if members < 3:
                warn(loc, f"only {members} event(s) within {radius} km of anchor (<3 — consider whether this earns its own place record)")

    es = p.get("era_span") or []
    if not isinstance(es, list) or not es:
        err(loc, "era_span must be a non-empty list")
    else:
        for e in es:
            if e not in ERAS:
                err(loc, f"era_span value '{e}' not in {sorted(ERAS)}")

    cats = p.get("category") or []
    if not isinstance(cats, list) or not cats:
        err(loc, "category must be a non-empty list")
    else:
        for c in cats:
            if c not in CATEGORIES:
                err(loc, f"category '{c}' not in {sorted(CATEGORIES)}")

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
            err(loc, "every place must have a link with type='wikipedia'")

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
    default = REPO_ROOT / "data" / "places"
    root = Path(sys.argv[1] if len(sys.argv) > 1 else default).resolve()

    if not root.is_dir():
        print(f"No places directory at {root} — nothing to validate.")
        print("PASS")
        return 0

    files = sorted(root.glob("places_*.json"))
    if not files:
        print(f"No places_*.json files found in {root} — nothing to validate.")
        print("PASS")
        return 0

    boundaries = get_boundaries(root)
    if boundaries is None:
        print("  (no validator_boundaries.json — point-in-polygon checks skipped)")

    event_corpus = load_event_corpus()
    print(f"Loaded {len(event_corpus)} events for proximity-membership checks.")
    print(f"Validating {len(files)} places file(s) in {root}\n")

    all_records = []
    id_counts = defaultdict(list)
    for p in files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            err(p.name, f"invalid JSON: {e}")
            continue
        for rec in data.get("places", []):
            all_records.append((p, rec))
            if rec.get("id"):
                id_counts[rec["id"]].append(p.name)

    for pid, where in id_counts.items():
        if len(where) > 1:
            err("corpus", f"duplicate place id '{pid}' in {where}")

    all_ids = set(id_counts.keys())
    for p, rec in all_records:
        validate_place(rec, p, all_ids, boundaries, event_corpus)

    print(f"Found {len(all_records)} place(s).\n")
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
