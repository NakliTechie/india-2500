"""
build_html.py — splice JSON data into template.html and emit india-history.html.

Reads:
  - template.html
  - map_paths.json
  - events_*.json
  - threads_*.json
  - people_*.json
  - collections_*.json
  - places_*.json
  - polities_*.json

Writes:
  - india-history.html

The template uses these placeholders:
  __VIEWBOX__                   viewBox attribute for the SVG
  __INDIA_PATH__                single SVG path for the India outline (Datameet)
  __SURROUNDS_PATHS__           SVG <path> elements for surrounding countries
  __MAP_DATA__                  JS object literal (projection params + paths)
  __EVENTS_DATA__               JS array literal of event records
  __THREADS_DATA__              JS array literal of thread records
  __PEOPLE_DATA__               JS array literal of person records (with colour assigned)
  __COLLECTIONS_DATA__          JS array literal of collection records
  __PLACES_DATA__               JS array literal of place records
  __POLITIES_DATA__             JS array literal of polity records
  __STATIC_PINS__               pre-rendered SVG pins (iOS Quick Look fallback)
  __STATIC_THREADS_BAR__        pre-rendered threads bar HTML (fallback)
  __STATIC_PEOPLE_BAR__         pre-rendered people bar HTML (fallback)
  __STATIC_COLLECTIONS_BAR__    pre-rendered collections bar HTML (fallback)
  __STATIC_PLACES_BAR__         pre-rendered places bar HTML (fallback)
  __STATIC_POLITIES_BAR__       pre-rendered polities bar HTML (fallback)

The DATA:BEGIN / DATA:END markers in the template are preserved so that
later updates can be spliced in mechanically (Claude Code, manual paste).

iOS Quick Look strips JavaScript. The static fallbacks are baked into the
HTML so the file previews correctly even without JS — JS replaces them on
page load in a real browser.
"""
import json
import math
from pathlib import Path
from html import escape as h

REPO   = Path(__file__).resolve().parent.parent
DATA   = REPO / "data"
BUILD  = REPO / "build"
WEB    = REPO / "web"

# Per-person accent colours from the Rangrez India · NORTH (india1) collection.
# Assigned in load order, cycles when more than 5 people. Each was picked for
# thematic resonance with the figure (KHADI for Gandhi's hand-spun symbolism,
# AAKASH for Nehru's Ashoka-chakra blue, KUMKUM vermillion for Bhagat Singh's
# revolutionary intensity, NEEL indigo for Ambedkar, MOR peacock teal for Jinnah).
PEOPLE_PALETTE = [
    "#b03018",  # KHADI    — Gandhi
    "#1a4870",  # AAKASH   — Nehru
    "#c8281a",  # KUMKUM   — Bhagat Singh
    "#1a3a90",  # NEEL     — Ambedkar
    "#1f7a8a",  # MOR      — Jinnah
]

map_data = json.loads((BUILD / "map_paths.json").read_text())
events = []
for p in sorted((DATA / "events").glob("events_*.json")):
    events.extend(json.loads(p.read_text())["events"])
threads = []
for p in sorted((DATA / "threads").glob("threads_*.json")):
    threads.extend(json.loads(p.read_text())["threads"])
people = []
for p in sorted((DATA / "people").glob("people_*.json")):
    people.extend(json.loads(p.read_text())["people"])
collections = []
collections_dir = DATA / "collections"
if collections_dir.is_dir():
    for p in sorted(collections_dir.glob("collections_*.json")):
        collections.extend(json.loads(p.read_text())["collections"])
places = []
places_dir = DATA / "places"
if places_dir.is_dir():
    for p in sorted(places_dir.glob("places_*.json")):
        places.extend(json.loads(p.read_text())["places"])
polities = []
polities_dir = DATA / "polities"
if polities_dir.is_dir():
    for p in sorted(polities_dir.glob("polities_*.json")):
        polities.extend(json.loads(p.read_text())["polities"])

# Per-person accent: prefer explicit `colour` field on the person object;
# fall back to cycling PEOPLE_PALETTE in load order. Authors should set
# `colour` explicitly once the corpus passes 5 people to avoid collisions.
for i, person in enumerate(people):
    if not person.get("colour"):
        person["colour"] = PEOPLE_PALETTE[i % len(PEOPLE_PALETTE)]

print(f"Splicing: {len(events)} events, {len(threads)} threads, {len(people)} people, {len(collections)} collections, {len(places)} places, {len(polities)} polities")


# --- Spherical LCC (matches the JS formula in the template) ---
def lcc(lat, lon):
    R = 6371000
    lat1 = math.radians(20); lat2 = math.radians(40)
    lat0 = math.radians(30); lon0 = math.radians(78)
    phi = math.radians(lat); lam = math.radians(lon)
    n = math.log(math.cos(lat1)/math.cos(lat2)) / math.log(math.tan(math.pi/4 + lat2/2)/math.tan(math.pi/4 + lat1/2))
    F = math.cos(lat1) * math.tan(math.pi/4 + lat1/2)**n / n
    rho = R * F / math.tan(math.pi/4 + phi/2)**n
    rho0 = R * F / math.tan(math.pi/4 + lat0/2)**n
    x = rho * math.sin(n * (lam - lon0))
    y = rho0 - rho * math.cos(n * (lam - lon0))
    return x, y

PROJ = map_data["projection"]
def to_svg(lat, lon):
    x, y = lcc(lat, lon)
    sx = (x - PROJ["minx"]) * PROJ["scale"]
    sy = (PROJ["maxy"] - y) * PROJ["scale"]
    return sx, sy


# --- Static pin pre-render (no dodge — fine for preview) ---
static_pins = []
for ev in events:
    pts = ev.get("location", {}).get("points") or []
    if not pts: continue
    sx, sy = to_svg(pts[0]["lat"], pts[0]["lon"])
    static_pins.append(
        f'<g class="pin" data-id="{h(ev["id"])}" transform="translate({sx:.1f},{sy:.1f})">'
        f'<circle class="dot" r="5"></circle>'
        f'<title>{h(ev["title"])} · {h(ev["date"]["display"])}</title>'
        f'</g>'
    )
static_pins_html = "\n      ".join(static_pins)


# --- Static threads bar pre-render ---
thread_pills = "\n    ".join(
    f'<button class="pill" data-tid="{h(t["id"])}">{h(t["title"])}</button>'
    for t in threads
)
static_threads_bar = f'<span class="label">Threads</span>\n    {thread_pills}'

# --- Static people bar pre-render (no JS — for iOS Quick Look) ---
people_pills = "\n    ".join(
    f'<button class="pill is-person" data-pid="{h(person["id"])}" '
    f'style="--accent:{h(person["colour"])};">'
    f'<span class="pill-swatch" style="background:{h(person["colour"])};"></span>'
    f'{h(person["name"].split()[-1] if person.get("name") else person["id"])}'
    f'</button>'
    for person in people
)
static_people_bar = f'<span class="label">People</span>\n    {people_pills}'

# --- Static collections bar pre-render ---
collection_pills = "\n    ".join(
    f'<button class="pill" data-cid="{h(c["id"])}">{h(c["title"])}</button>'
    for c in collections
)
static_collections_bar = f'<span class="label">Collections</span>\n    {collection_pills}'

# --- Static places bar pre-render ---
place_pills = "\n    ".join(
    f'<button class="pill" data-plid="{h(p["id"])}">{h(p["name"])}</button>'
    for p in places
)
static_places_bar = f'<span class="label">Places</span>\n    {place_pills}'

# --- Static polities bar pre-render ---
polity_pills = "\n    ".join(
    f'<button class="pill" data-poid="{h(p["id"])}">{h(p["name"])}</button>'
    for p in polities
)
static_polities_bar = f'<span class="label">Polities</span>\n    {polity_pills}'


# --- Map + viewport ---
vb = map_data["viewport"]
viewbox = f"0 0 {vb['width']} {vb['height']}"
surrounds_paths = "\n".join(
    f'<path class="surrounds-fill" d="{s["path"]}" data-name="{h(s["name"])}"/>'
    for s in map_data["surrounds"]
)

# Map data passed to JS — only projection params (paths are inline as SVG)
map_js = json.dumps({
    "projection": map_data["projection"],
    "viewport": vb,
}, separators=(",", ":"))

events_js      = json.dumps(events,      ensure_ascii=False, separators=(",", ":"))
threads_js     = json.dumps(threads,     ensure_ascii=False, separators=(",", ":"))
people_js      = json.dumps(people,      ensure_ascii=False, separators=(",", ":"))
collections_js = json.dumps(collections, ensure_ascii=False, separators=(",", ":"))
places_js      = json.dumps(places,      ensure_ascii=False, separators=(",", ":"))
polities_js    = json.dumps(polities,    ensure_ascii=False, separators=(",", ":"))

template = (WEB / "template.html").read_text()


# ---- Single-file build: india-history.html ------------------------------
# All data inlined; bootRenders() called immediately. iOS Quick Look-friendly
# (no network fetches at runtime, JS optional).
single = (template
       .replace("__VIEWBOX__", viewbox)
       .replace("__INDIA_PATH__", map_data["india_path"])
       .replace("__SURROUNDS_PATHS__", surrounds_paths)
       .replace("__MAP_DATA__", map_js)
       .replace("__EVENTS_DATA__", events_js)
       .replace("__THREADS_DATA__", threads_js)
       .replace("__PEOPLE_DATA__", people_js)
       .replace("__COLLECTIONS_DATA__", collections_js)
       .replace("__PLACES_DATA__", places_js)
       .replace("__POLITIES_DATA__", polities_js)
       .replace("__STATIC_PINS__", static_pins_html)
       .replace("__STATIC_THREADS_BAR__", static_threads_bar)
       .replace("__STATIC_PEOPLE_BAR__", static_people_bar)
       .replace("__STATIC_COLLECTIONS_BAR__", static_collections_bar)
       .replace("__STATIC_PLACES_BAR__", static_places_bar)
       .replace("__STATIC_POLITIES_BAR__", static_polities_bar)
       .replace("__BOOT_INVOCATION__", "bootRenders();"))

(WEB / "india-history.html").write_text(single)
print(f"  Wrote india-history.html: {len(single)/1024:.1f} KB (single-file, deployable as-is)")


# ---- Runtime-fetch build: shell.html ------------------------------------
# Data placeholders stubbed with empty literals; real data fetched at boot.
# Also enumerates the actual data files so new ones added later don't need
# a shell.html change — just re-run build_html.py to regenerate the manifest.
events_files      = sorted(p.name for p in (DATA / "events").glob("events_*.json"))
threads_files     = sorted(p.name for p in (DATA / "threads").glob("threads_*.json"))
people_files      = sorted(p.name for p in (DATA / "people").glob("people_*.json"))
collections_files = (
    sorted(p.name for p in (DATA / "collections").glob("collections_*.json"))
    if (DATA / "collections").is_dir() else []
)
places_files = (
    sorted(p.name for p in (DATA / "places").glob("places_*.json"))
    if (DATA / "places").is_dir() else []
)
polities_files = (
    sorted(p.name for p in (DATA / "polities").glob("polities_*.json"))
    if (DATA / "polities").is_dir() else []
)

# Manifest consumed by the contribute forms (thread.html, collection.html) so
# they pick up new slice files without a code edit.
manifest = {
    "events_files":      events_files,
    "threads_files":     threads_files,
    "people_files":      people_files,
    "collections_files": collections_files,
    "places_files":      places_files,
    "polities_files":    polities_files,
}
(DATA / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"  Wrote data/manifest.json: {len(events_files)} events, {len(threads_files)} threads, {len(people_files)} people, {len(collections_files)} collections, {len(places_files)} places, {len(polities_files)} polities slice files")

# Inline the same colour palette used at build time so shell.html assigns
# accents identically to the single-file build.
shell_palette = json.dumps(PEOPLE_PALETTE)

shell_boot = f"""(async function() {{
  // Hosted runtime fetch — data lives at /data/* and /build/* relative to
  // wherever shell.html is served from. Adjust BASE if you mount this asset
  // under a sub-path other than the default.
  const BASE = (function() {{
    const here = new URL(window.location.href);
    return here.pathname.replace(/[^/]*$/, '').replace(/\\/web\\/?$/, '/');
  }})();
  const PALETTE = {shell_palette};

  async function fetchJson(path) {{
    const r = await fetch(BASE + path, {{cache: 'force-cache'}});
    if (!r.ok) throw new Error(`fetch ${{path}} → ${{r.status}}`);
    return r.json();
  }}

  try {{
    const [mapDoc, eventsDocs, threadsDocs, peopleDocs, collectionsDocs, placesDocs, politiesDocs] = await Promise.all([
      fetchJson('build/map_paths.json'),
      Promise.all({json.dumps(events_files)}.map(f => fetchJson('data/events/' + f))),
      Promise.all({json.dumps(threads_files)}.map(f => fetchJson('data/threads/' + f))),
      Promise.all({json.dumps(people_files)}.map(f => fetchJson('data/people/' + f))),
      Promise.all({json.dumps(collections_files)}.map(f => fetchJson('data/collections/' + f))),
      Promise.all({json.dumps(places_files)}.map(f => fetchJson('data/places/' + f))),
      Promise.all({json.dumps(polities_files)}.map(f => fetchJson('data/polities/' + f))),
    ]);

    // Populate the data globals declared by the template.
    MAP         = {{ projection: mapDoc.projection, viewport: mapDoc.viewport }};
    EVENTS      = eventsDocs.flatMap(d => d.events || []);
    THREADS     = threadsDocs.flatMap(d => d.threads || []);
    PEOPLE      = peopleDocs.flatMap(d => d.people || []);
    COLLECTIONS = collectionsDocs.flatMap(d => d.collections || []);
    PLACES      = placesDocs.flatMap(d => d.places || []);
    POLITIES    = politiesDocs.flatMap(d => d.polities || []);
    PEOPLE.forEach((p, i) => {{ p.colour = PALETTE[i % PALETTE.length]; }});

    // Render the static SVG basemap from the fetched paths.
    const svg = document.getElementById('map');
    svg.setAttribute('viewBox', `0 0 ${{mapDoc.viewport.width}} ${{mapDoc.viewport.height}}`);
    document.getElementById('surrounds').innerHTML = (mapDoc.surrounds || [])
      .map(s => `<path class="surrounds-fill" d="${{s.path}}" data-name="${{s.name}}"/>`)
      .join('');
    document.querySelector('.india-fill').setAttribute('d', mapDoc.india_path);

    // Now hand off to the same boot path the single-file build uses.
    bootRenders();
  }} catch (err) {{
    console.error('shell.html boot failed:', err);
    document.getElementById('event-panel').innerHTML =
      '<div class="panel-head"><h3>Failed to load data</h3></div>'
      + '<p class="summary">' + (err.message || err) + '</p>';
  }}
}})();"""

shell = (template
       .replace("__VIEWBOX__", "0 0 1000 736")
       .replace("__INDIA_PATH__", "")
       .replace("__SURROUNDS_PATHS__", "")
       .replace("__MAP_DATA__", "null")
       .replace("__EVENTS_DATA__", "[]")
       .replace("__THREADS_DATA__", "[]")
       .replace("__PEOPLE_DATA__", "[]")
       .replace("__COLLECTIONS_DATA__", "[]")
       .replace("__PLACES_DATA__", "[]")
       .replace("__POLITIES_DATA__", "[]")
       .replace("__STATIC_PINS__", "")
       .replace("__STATIC_THREADS_BAR__", '<span class="label">Threads</span>')
       .replace("__STATIC_PEOPLE_BAR__", '<span class="label">People</span>')
       .replace("__STATIC_COLLECTIONS_BAR__", '<span class="label">Collections</span>')
       .replace("__STATIC_PLACES_BAR__", '<span class="label">Places</span>')
       .replace("__STATIC_POLITIES_BAR__", '<span class="label">Polities</span>')
       .replace("__BOOT_INVOCATION__", shell_boot))

(WEB / "shell.html").write_text(shell)
print(f"  Wrote shell.html:        {len(shell)/1024:.1f} KB (runtime-fetch, hosted from assets.chiragpatnaik.com)")
