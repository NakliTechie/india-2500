"""
Build the inline map data for the India history explorer.

Inputs
------
- Datameet India boundary (Survey of India)  — authoritative for India outline
- world-atlas countries-110m.json (Natural Earth via TopoJSON) — surrounding states only

Output
------
- map_paths.json: { india: <svgpath>, surrounds: [{name, path}, ...], bbox: [w,h], project: {fn descriptor} }

Projection
----------
Lambert Conformal Conic, centered ~30N 75E. Standard parallels 20 and 40.
This handles the latitude band from Sri Lanka (5N) to Samarkand (40N) without
ugly distortion at the extremes.

Important
---------
Datameet's India polygon is drawn LAST so it sits on top of any neighbouring
country outline that has the wrong PoK / Aksai Chin / Arunachal representation.
This is the boundary rule for any India map.
"""

import json
import sys
from pathlib import Path

from shapely.geometry import shape, MultiPolygon, Polygon, mapping
from shapely.ops import transform as shapely_transform
from shapely.validation import make_valid
import pyproj

REPO = Path(__file__).resolve().parent.parent
# datameet/ and package/ are external dependencies kept at REPO root and
# gitignored (datameet is a 200+ MB clone; package/ is fetched separately).
DATAMEET = REPO / "datameet"
PACKAGE  = REPO / "package"
# Build outputs land here, alongside this script.
OUT      = REPO / "build"

# ---------- Projection ----------
# Lambert Conformal Conic, lat_1=20, lat_2=40, lat_0=30, lon_0=78
# SPHERE (R=6371000), not WGS84 ellipsoid — so the JS pin projection (which
# uses simple spherical math) lines up exactly with the basemap.
LCC = pyproj.CRS.from_proj4(
    "+proj=lcc +lat_1=20 +lat_2=40 +lat_0=30 +lon_0=78 "
    "+x_0=0 +y_0=0 +ellps=sphere +R=6371000 +units=m +no_defs"
)
# Use spherical lon/lat as the source CRS too, for consistency.
SPHERE_LL = pyproj.CRS.from_proj4(
    "+proj=longlat +ellps=sphere +R=6371000 +no_defs"
)
TX = pyproj.Transformer.from_crs(SPHERE_LL, LCC, always_xy=True).transform


def project(geom):
    return shapely_transform(TX, geom)


# ---------- Load Datameet India ----------
print("Loading Datameet India (SOI)…")
with open(DATAMEET / "Country" / "india-soi.geojson") as f:
    india_gj = json.load(f)

india_geoms = []
for feat in india_gj["features"]:
    g = shape(feat["geometry"])
    if not g.is_valid:
        g = make_valid(g)
    india_geoms.append(g)

# Union all features into one boundary geometry
from shapely.ops import unary_union
india_union = unary_union(india_geoms)
print(f"  India geometry: {india_union.geom_type}, {len(india_geoms)} input features")

# Simplify aggressively — this is a context layer, not a precision map.
# 0.015° ≈ 1.7 km at our scale. The earlier 0.04° was visually fine but
# moved the Wagah border far enough that pin placement near the line
# looked inconsistent. 0.015° doubles the file size; worth it.
india_simple = india_union.simplify(0.015, preserve_topology=True)
india_proj = project(india_simple)
print(f"  Simplified, projected.")


# ---------- Load surrounding countries ----------
print("Loading world-atlas surrounds…")
with open(PACKAGE / "countries-50m.json") as f:
    topo = json.load(f)

# Convert TopoJSON to GeoJSON manually (no topojson python lib for this direction)
# Actually the Python topojson lib is for the other direction. Let me parse manually.

def topo_to_geojson(topo, layer):
    """Decode TopoJSON to GeoJSON FeatureCollection."""
    arcs = topo["arcs"]
    transform_ = topo.get("transform")
    if transform_:
        scale = transform_["scale"]
        translate = transform_["translate"]

        def decode_arc(arc):
            x = y = 0
            out = []
            for dx, dy in arc:
                x += dx
                y += dy
                out.append([x * scale[0] + translate[0], y * scale[1] + translate[1]])
            return out
    else:
        def decode_arc(arc):
            return arc

    decoded = [decode_arc(a) for a in arcs]

    def stitch(arc_indexes):
        # arc_indexes is a list of arc indices; negative means reverse and ~i
        coords = []
        for idx in arc_indexes:
            if idx < 0:
                a = list(reversed(decoded[~idx]))
            else:
                a = decoded[idx]
            if coords and coords[-1] == a[0]:
                coords.extend(a[1:])
            else:
                coords.extend(a)
        return coords

    def geom_to_geojson(g):
        t = g["type"]
        if t == "Polygon":
            return {"type": "Polygon", "coordinates": [stitch(ring) for ring in g["arcs"]]}
        if t == "MultiPolygon":
            return {
                "type": "MultiPolygon",
                "coordinates": [[stitch(ring) for ring in poly] for poly in g["arcs"]],
            }
        return None

    feats = []
    for g in topo["objects"][layer]["geometries"]:
        geom = geom_to_geojson(g)
        if geom:
            feats.append({"type": "Feature", "properties": g.get("properties", {}), "id": g.get("id"), "geometry": geom})
    return {"type": "FeatureCollection", "features": feats}


countries_gj = topo_to_geojson(topo, "countries")
print(f"  Decoded {len(countries_gj['features'])} countries.")

# Map of country names we want as surrounds
SURROUND_NAMES = {
    "Pakistan", "Afghanistan", "Nepal", "Bhutan", "Bangladesh",
    "Myanmar", "Sri Lanka", "China", "Iran",
    "Uzbekistan", "Tajikistan", "Turkmenistan", "Kyrgyzstan",
    "Kazakhstan", "Oman", "United Arab Emirates", "Saudi Arabia", "Yemen",
    "Thailand", "Laos", "Vietnam", "Cambodia",
    "Mongolia", "Russia",
}

surrounds = []
for feat in countries_gj["features"]:
    name = feat["properties"].get("name") or ""
    if name not in SURROUND_NAMES:
        continue
    g = shape(feat["geometry"])
    if not g.is_valid:
        g = make_valid(g)
    # Clip to a generous bbox covering the subcontinent + Central Asia
    from shapely.geometry import box
    clip = box(40, -5, 110, 50)
    g = g.intersection(clip)
    if g.is_empty:
        continue
    g = g.simplify(0.06, preserve_topology=True)
    g = project(g)
    surrounds.append((name, g))

print(f"  {len(surrounds)} surrounds kept after clipping.")


# ---------- Compute viewport ----------
# Bounding box: union of all rendered geometries in projected coords.
all_geoms = [india_proj] + [g for _, g in surrounds]
ux = []
uy = []
for g in all_geoms:
    minx, miny, maxx, maxy = g.bounds
    ux += [minx, maxx]
    uy += [miny, maxy]

minx, maxx = min(ux), max(ux)
miny, maxy = min(uy), max(uy)
print(f"  Projected bounds: x [{minx:.0f}, {maxx:.0f}]  y [{miny:.0f}, {maxy:.0f}]")

# Add 2% padding
pad_x = (maxx - minx) * 0.02
pad_y = (maxy - miny) * 0.02
minx -= pad_x; maxx += pad_x
miny -= pad_y; maxy += pad_y

# Convert to SVG coords. SVG y is flipped.
TARGET_W = 1000
scale = TARGET_W / (maxx - minx)
TARGET_H = (maxy - miny) * scale


def proj_to_svg_xy(x, y):
    sx = (x - minx) * scale
    sy = (maxy - y) * scale  # flip
    return sx, sy


# ---------- Geometry to SVG path ----------
def geom_to_svg(geom):
    parts = []

    def ring_to_path(ring):
        coords = list(ring.coords)
        if len(coords) < 3:
            return ""
        sx, sy = proj_to_svg_xy(*coords[0])
        s = [f"M{sx:.1f},{sy:.1f}"]
        for x, y in coords[1:]:
            sx, sy = proj_to_svg_xy(x, y)
            s.append(f"L{sx:.1f},{sy:.1f}")
        s.append("Z")
        return "".join(s)

    polygons = []
    if geom.geom_type == "Polygon":
        polygons = [geom]
    elif geom.geom_type == "MultiPolygon":
        polygons = list(geom.geoms)
    elif geom.geom_type in ("GeometryCollection",):
        polygons = [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]

    for poly in polygons:
        if poly.geom_type == "MultiPolygon":
            for p in poly.geoms:
                parts.append(ring_to_path(p.exterior))
                for hole in p.interiors:
                    parts.append(ring_to_path(hole))
        else:
            parts.append(ring_to_path(poly.exterior))
            for hole in poly.interiors:
                parts.append(ring_to_path(hole))
    return "".join(parts)


india_path = geom_to_svg(india_proj)
surrounds_paths = [{"name": name, "path": geom_to_svg(g)} for name, g in surrounds]


# ---------- Lon/lat to SVG helper (for pinning events) ----------
# Encode the projection params so the JS can reproduce them.
# But projection in JS is annoying. Easier: pre-project a coarse lookup grid.
# Actually: since we only have a handful of pins, we can just embed the
# python-projected positions directly when we generate the events file —
# OR have the HTML compute them from lon/lat using a JS LCC.
#
# Decision: emit a JS function snippet that does LCC → SVG, parameterized.
# The math is short (~30 lines).

projection_params = {
    "lat_1": 20.0,
    "lat_2": 40.0,
    "lat_0": 30.0,
    "lon_0": 78.0,
    "minx": minx,
    "maxx": maxx,
    "miny": miny,
    "maxy": maxy,
    "scale": scale,
    "target_w": TARGET_W,
    "target_h": TARGET_H,
}

out = {
    "india_path": india_path,
    "surrounds": surrounds_paths,
    "viewport": {"width": round(TARGET_W, 1), "height": round(TARGET_H, 1)},
    "projection": projection_params,
}

with open(OUT / "map_paths.json", "w") as f:
    json.dump(out, f, separators=(",", ":"))

# Sanity: byte sizes
import os
size = os.path.getsize(OUT / "map_paths.json")
print(f"\nmap_paths.json: {size/1024:.1f} KB")
print(f"  india path: {len(india_path)} chars")
print(f"  surrounds: {sum(len(s['path']) for s in surrounds_paths)} chars")
print(f"  viewport: {TARGET_W:.0f} x {TARGET_H:.0f}")


# ---------- Validator boundaries (separate file) ----------
# The validator does point-in-polygon checks against these. Simplification is
# tighter (~1 km) than the basemap because the validator must catch placement
# errors that are smaller than the basemap's visual tolerance.
print("\nBuilding validator_boundaries.json…")

# India: simplify slightly less aggressively than basemap
india_for_validator = india_union.simplify(0.01, preserve_topology=True)

# Surrounds: re-load from world-atlas at full resolution
surrounds_for_validator = {}
for feat in countries_gj["features"]:
    name = feat["properties"].get("name") or ""
    if name not in SURROUND_NAMES:
        continue
    g = shape(feat["geometry"])
    if not g.is_valid:
        g = make_valid(g)
    g = g.simplify(0.02, preserve_topology=True)
    # Use mapping() to serialise back to GeoJSON
    surrounds_for_validator[name] = mapping(g)

validator_data = {
    "IN": mapping(india_for_validator),
    "by_country_name": surrounds_for_validator,
}

with open(OUT / "validator_boundaries.json", "w") as f:
    json.dump(validator_data, f, separators=(",", ":"))

vsize = os.path.getsize(OUT / "validator_boundaries.json")
print(f"  validator_boundaries.json: {vsize/1024:.1f} KB ({len(surrounds_for_validator)} countries + India)")
