#!/usr/bin/env python3
"""
validate_people.py — schema conformance for people_*.json files.

People reference events from the events corpus (kind='event-ref') and carry
standalone biographical moments (kind='moment'). This validator loads the
events corpus first, then validates each person against both the schema and
the resolved event IDs, plus a point-in-polygon check on every moment's
location and on each person's birthplace/deathplace.

Usage
-----
    python3 validate_people.py [path/to/dir]

Exit code
---------
    0 if all hard rules pass (warnings allowed)
    1 if any hard rule fails
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from collections import defaultdict


# ---------- vocabularies (must match PEOPLE_SCHEMA.md) ----------
ERAS = {
    "vedic", "mahajanapada", "maurya", "post-maurya", "gupta",
    "early-medieval", "sultanate", "mughal", "maratha",
    "colonial", "independence", "republic",
}

PRECISIONS = {"day", "month", "year", "decade", "century"}

LOCATION_TYPES = {"point", "city", "region", "route"}

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

STEP_KINDS = {"event-ref", "moment"}

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

BBOX = (5.0, 55.0, 55.0, 105.0)  # min_lat, max_lat, min_lon, max_lon

# ---------- result accumulators ----------
errors: list[str] = []
warnings: list[str] = []


def err(loc, msg):
    errors.append(f"  ERROR  {loc}: {msg}")


def warn(loc, msg):
    warnings.append(f"  warn   {loc}: {msg}")


# ---------- point-in-polygon helper (same as validate_events.py) ----------
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


REPO_ROOT = Path(__file__).resolve().parent.parent

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


def pip_check(loc, lon, lat, country, boundaries):
    """Run point-in-polygon. Emits err if the point is not inside the country."""
    if country == "OFF" or not boundaries:
        return
    if not isinstance(lon, (int, float)) or not isinstance(lat, (int, float)):
        return
    geom = None
    if country == "IN":
        geom = boundaries.get("IN")
    else:
        name = COUNTRY_NAMES.get(country)
        if name:
            geom = boundaries.get("by_country_name", {}).get(name)
    if geom is None:
        warn(loc, f"no boundary polygon available for country='{country}' — PIP check skipped")
    elif not point_in_geometry(lon, lat, geom):
        err(loc, f"point ({lat:.4f}, {lon:.4f}) does not fall inside {country}'s polygon")


# ---------- date parsing ----------
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


_DATE_RE = re.compile(r"^-?\d{1,4}(-\d{2}(-\d{2})?)?$")
def is_valid_date_string(s):
    return isinstance(s, str) and bool(_DATE_RE.match(s))


# ---------- events corpus loader ----------
def load_event_corpus(root: Path):
    """Return dict id -> event for every events_*.json file. Looks in
    <repo>/data/events first; falls back to `root` for flat layouts."""
    corpus = {}
    events_dir = REPO_ROOT / "data" / "events"
    if not events_dir.is_dir():
        events_dir = root
    for p in sorted(events_dir.glob("events_*.json")):
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError:
            continue
        for ev in data.get("events", []):
            if ev.get("id"):
                corpus[ev["id"]] = ev
    return corpus


# ---------- per-place validation ----------
def validate_place(loc, place, boundaries, *, label):
    """birthplace / deathplace shape check + PIP."""
    if not isinstance(place, dict):
        err(loc, f"lifespan.{label} must be an object")
        return
    if not place.get("name"):
        err(loc, f"lifespan.{label}.name required")
    country = place.get("country")
    if not country:
        err(loc, f"lifespan.{label}.country required (ISO alpha-2 or 'OFF')")
    elif country not in COUNTRIES:
        err(loc, f"lifespan.{label}.country '{country}' not in {sorted(COUNTRIES)}")
    lat = place.get("lat")
    lon = place.get("lon")
    if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
        err(loc, f"lifespan.{label}.lat invalid: {lat}")
    if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
        err(loc, f"lifespan.{label}.lon invalid: {lon}")
    if (
        isinstance(lat, (int, float)) and isinstance(lon, (int, float))
        and country and country in COUNTRIES
    ):
        pip_check(f"{loc}.{label}", lon, lat, country, boundaries)


# ---------- per-step validation ----------
def validate_step(loc, step, idx, person_track_moment_ids, event_corpus, boundaries):
    """Returns the step's chronological anchor year (or None) so caller can enforce ordering."""
    sloc = f"{loc}.track[{idx}]"
    if not isinstance(step, dict):
        err(sloc, "must be an object")
        return None

    kind = step.get("kind")
    if kind not in STEP_KINDS:
        err(sloc, f"kind '{kind}' not in {sorted(STEP_KINDS)}")
        return None

    if kind == "event-ref":
        ev_id = step.get("event_id")
        if not ev_id:
            err(sloc, "event_id required")
            return None
        if ev_id not in event_corpus:
            err(sloc, f"event_id '{ev_id}' does not resolve to any event")
            return None
        if not step.get("role"):
            err(sloc, "role required (the person's specific part in this event)")
        # Anchor year comes from the resolved event's date.start.
        ev = event_corpus[ev_id]
        return parse_year(((ev.get("date") or {}).get("start")))

    # kind == "moment"
    mid = step.get("id")
    if not mid:
        err(sloc, "id required for moment step")
    elif not ID_RE.match(mid):
        err(sloc, f"id '{mid}' must be kebab-case")
    elif mid in person_track_moment_ids:
        err(sloc, f"moment id '{mid}' duplicated within this person's track")
    else:
        person_track_moment_ids.add(mid)

    tooltip = step.get("tooltip", "")
    if not tooltip:
        err(sloc, "tooltip required for moment")
    elif not isinstance(tooltip, str):
        err(sloc, "tooltip must be a string")
    elif len(tooltip) > 80:
        err(sloc, f"tooltip is {len(tooltip)} chars (>80 is the hard cap)")

    summ = step.get("summary", "")
    if not summ:
        err(sloc, "summary required for moment")
    elif not isinstance(summ, str):
        err(sloc, "summary must be a string")
    elif len(summ) > 160:
        err(sloc, f"summary is {len(summ)} chars (>160 is the hard cap)")
    elif len(summ) > 140:
        warn(sloc, f"summary is {len(summ)} chars (>140 — consider trimming)")

    # date
    date = step.get("date") or {}
    anchor_year = None
    if not isinstance(date, dict):
        err(sloc, "date must be an object")
    else:
        for f in ("start", "end", "precision", "approximate", "display"):
            if f not in date:
                err(sloc, f"date.{f} missing")
        prec = date.get("precision")
        if prec is not None and prec not in PRECISIONS:
            err(sloc, f"date.precision '{prec}' not in {sorted(PRECISIONS)}")
        ys = parse_year(date.get("start"))
        ye = parse_year(date.get("end"))
        if ys is None and date.get("start"):
            err(sloc, f"date.start '{date.get('start')}' is unparseable")
        if ye is None and date.get("end"):
            err(sloc, f"date.end '{date.get('end')}' is unparseable")
        if ys is not None and ye is not None and ys > ye:
            err(sloc, f"date.start ({ys}) > date.end ({ye})")
        anchor_year = ys

    # location
    locn = step.get("location") or {}
    if not isinstance(locn, dict):
        err(sloc, "location must be an object")
    else:
        # location.type is optional on moments per schema (moments are slim);
        # if present, validate. SCHEMA.md says moment carries the same shape
        # as a slim event but doesn't require type. Accept either way.
        ltype = locn.get("type")
        if ltype is not None and ltype not in LOCATION_TYPES:
            err(sloc, f"location.type '{ltype}' not in {sorted(LOCATION_TYPES)}")
        if not locn.get("name"):
            err(sloc, "location.name required")
        country = locn.get("country")
        if not country:
            err(sloc, "location.country required (ISO alpha-2 or 'OFF')")
        elif country not in COUNTRIES:
            err(sloc, f"location.country '{country}' not in {sorted(COUNTRIES)}")
        pts = locn.get("points") or []
        if not pts:
            err(sloc, "location.points must contain at least one {lat, lon}")
        for i, p in enumerate(pts):
            lat, lon = p.get("lat"), p.get("lon")
            if not isinstance(lat, (int, float)) or lat < -90 or lat > 90:
                err(sloc, f"location.points[{i}].lat invalid: {lat}")
            if not isinstance(lon, (int, float)) or lon < -180 or lon > 180:
                err(sloc, f"location.points[{i}].lon invalid: {lon}")
            if i == 0 and isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                if not (BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lon <= BBOX[3]):
                    if country != "OFF":
                        err(sloc, f"location.points[0] ({lat}, {lon}) is outside the asset bbox; set country='OFF' if intentional")
        # PIP check on point 0
        if country and country != "OFF" and pts:
            lat0 = pts[0].get("lat")
            lon0 = pts[0].get("lon")
            pip_check(sloc, lon0, lat0, country, boundaries)

    return anchor_year


# ---------- per-person validation ----------
REQUIRED_PERSON = ["id", "name", "tooltip", "summary", "era", "lifespan", "links", "track", "verified"]


def validate_person(person, path, all_person_ids, event_corpus, boundaries):
    loc = f"{path.name}#{person.get('id', '<missing-id>')}"

    for f in REQUIRED_PERSON:
        if f not in person:
            err(loc, f"missing required field '{f}'")

    pid = person.get("id")
    if pid is not None:
        if not isinstance(pid, str) or not ID_RE.match(pid):
            err(loc, f"id '{pid}' must be kebab-case")

    name = person.get("name", "")
    if not name or not isinstance(name, str):
        err(loc, "name required (non-empty string)")

    tooltip = person.get("tooltip", "")
    if isinstance(tooltip, str):
        if len(tooltip) > 80:
            err(loc, f"tooltip is {len(tooltip)} chars (>80 is the hard cap)")
        elif len(tooltip) == 0:
            err(loc, "tooltip cannot be empty")
    summ = person.get("summary", "")
    if isinstance(summ, str):
        if len(summ) > 160:
            err(loc, f"summary is {len(summ)} chars (>160 is the hard cap)")
        elif len(summ) > 140:
            warn(loc, f"summary is {len(summ)} chars (>140 — consider trimming)")
        elif len(summ) == 0:
            err(loc, "summary cannot be empty")

    era = person.get("era")
    if era and era not in ERAS:
        err(loc, f"era '{era}' not in {sorted(ERAS)}")

    # lifespan
    ls = person.get("lifespan") or {}
    born_year = died_year = None
    if not isinstance(ls, dict):
        err(loc, "lifespan must be an object")
    else:
        born = ls.get("born")
        died = ls.get("died")
        if not born:
            err(loc, "lifespan.born required")
        elif not is_valid_date_string(born):
            err(loc, f"lifespan.born '{born}' is not a valid date string")
        else:
            born_year = parse_year(born)
        if died is not None:
            if not is_valid_date_string(died):
                err(loc, f"lifespan.died '{died}' is not a valid date string")
            else:
                died_year = parse_year(died)
                if born_year is not None and died_year < born_year:
                    err(loc, f"lifespan.died year ({died_year}) < lifespan.born year ({born_year})")
        if "birthplace" in ls:
            validate_place(loc, ls["birthplace"], boundaries, label="birthplace")
        else:
            err(loc, "lifespan.birthplace required")
        if died is not None:
            if "deathplace" in ls:
                validate_place(loc, ls["deathplace"], boundaries, label="deathplace")
            else:
                err(loc, "lifespan.deathplace required (died is non-null)")

    # links — wikipedia required
    links = person.get("links") or []
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
            err(loc, "every person must have a link with type='wikipedia'")

    # track
    track = person.get("track") or []
    if not isinstance(track, list):
        err(loc, "track must be a list")
    elif len(track) == 0:
        err(loc, "track must contain at least 1 step")
    else:
        moment_ids: set[str] = set()
        prev_year = None
        for idx, step in enumerate(track):
            anchor = validate_step(loc, step, idx, moment_ids, event_corpus, boundaries)
            # Non-decreasing chronological order (skip pairs where either side is unknown)
            if anchor is not None and prev_year is not None and anchor < prev_year:
                err(f"{loc}.track[{idx}]", f"step year {anchor} is before previous step's year {prev_year} — track must be chronological")
            if anchor is not None:
                prev_year = anchor
            # Soft check: step sits inside lifespan
            if anchor is not None and born_year is not None and anchor < born_year:
                warn(f"{loc}.track[{idx}]", f"step year {anchor} predates lifespan.born ({born_year})")
            if anchor is not None and died_year is not None and anchor > died_year:
                warn(f"{loc}.track[{idx}]", f"step year {anchor} postdates lifespan.died ({died_year})")

    # verified
    if "verified" in person and not isinstance(person["verified"], bool):
        err(loc, "verified must be true or false")
    if person.get("verified") is False:
        warn(loc, "verified=false (FYI — UI will surface this)")


# ---------- main ----------
def main():
    default = REPO_ROOT / "data" / "people"
    root = Path(sys.argv[1] if len(sys.argv) > 1 else default).resolve()
    files = sorted(root.glob("people_*.json"))
    if not files:
        print(f"No people_*.json files found in {root}")
        return 0

    boundaries = get_boundaries(root)
    event_corpus = load_event_corpus(root)
    print(f"Loaded {len(event_corpus)} events for cross-reference.")
    print(f"Validating {len(files)} people file(s) in {root}")
    if boundaries is None:
        print("  (no validator_boundaries.json — point-in-polygon checks skipped)")
    else:
        n_surrounds = len(boundaries.get("by_country_name", {}))
        print(f"  point-in-polygon: India + {n_surrounds} surrounding countries")
    print()

    # Pass 1: load + collect IDs
    all_persons = []
    id_counts = defaultdict(list)
    for p in files:
        try:
            data = json.loads(p.read_text())
        except json.JSONDecodeError as e:
            err(p.name, f"invalid JSON: {e}")
            continue
        ppl = data.get("people") or []
        if not isinstance(ppl, list):
            err(p.name, "top-level 'people' must be a list")
            continue
        for person in ppl:
            all_persons.append((p, person))
            if person.get("id"):
                id_counts[person["id"]].append(p.name)

    for pid, where in id_counts.items():
        if len(where) > 1:
            err("corpus", f"duplicate person id '{pid}' in {where}")

    all_ids = set(id_counts.keys())

    for p, person in all_persons:
        validate_person(person, p, all_ids, event_corpus, boundaries)

    print(f"Found {len(all_persons)} person(s) across {len(files)} file(s).\n")
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
