"""
build_png.py — render a static PNG companion for social sharing.

Reads:
  - build/map_paths.json   (cached basemap from build_map.py)
  - data/events/events_*.json
  - data/people/people_*.json   (for accent palette only)

Writes:
  - web/india-history.png       (1200×675, 16:9 — Open Graph standard)
  - web/india-history-square.png (1080×1080, square — Instagram/X)

Uses matplotlib with the Naklitechie cream tokens. Pin dots replay the same
projection the asset uses, so positions match the live site exactly.

Why a static PNG:
  Social previews (Twitter card, Open Graph, link-unfurl previews in
  Slack/iMessage) need an image, not an interactive HTML. The PNG is also
  a useful "frozen snapshot" for newsletter inserts and PDF print.

Run:
  python3 build/build_png.py
"""
import json
import re
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # no GUI; we render straight to file
import matplotlib.pyplot as plt
from matplotlib.path import Path as MplPath
from matplotlib.patches import PathPatch

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
BUILD = REPO / "build"
WEB = REPO / "web"

# Naklitechie tokens — must match web/template.html :root.
CREAM        = "#F7F2E7"
CREAM_CARD   = "#FFFDF7"
CREAM_TEXT   = "#2C2A24"
CREAM_MUTED  = "#6B665A"
CREAM_FAINT  = "#938D7E"
SURROUNDS_FILL   = "#EFE7D4"
SURROUNDS_STROKE = "#C0B59C"
PIN_FILL = CREAM_TEXT


# ---------- Load corpus ----------
map_data = json.loads((BUILD / "map_paths.json").read_text())
events = []
for p in sorted((DATA / "events").glob("events_*.json")):
    events.extend(json.loads(p.read_text())["events"])

print(f"PNG companion: {len(events)} events")


# ---------- Spherical LCC matching the JS / Python pipeline ----------
def lcc(lat, lon):
    R = 6_371_000
    lat1 = math.radians(20); lat2 = math.radians(40)
    lat0 = math.radians(30); lon0 = math.radians(78)
    phi = math.radians(lat); lam = math.radians(lon)
    n = math.log(math.cos(lat1) / math.cos(lat2)) / \
        math.log(math.tan(math.pi / 4 + lat2 / 2) / math.tan(math.pi / 4 + lat1 / 2))
    F = math.cos(lat1) * math.tan(math.pi / 4 + lat1 / 2) ** n / n
    rho = R * F / math.tan(math.pi / 4 + phi / 2) ** n
    rho0 = R * F / math.tan(math.pi / 4 + lat0 / 2) ** n
    x = rho * math.sin(n * (lam - lon0))
    y = rho0 - rho * math.cos(n * (lam - lon0))
    return x, y


PROJ = map_data["projection"]
def to_svg(lat, lon):
    x, y = lcc(lat, lon)
    sx = (x - PROJ["minx"]) * PROJ["scale"]
    sy = (PROJ["maxy"] - y) * PROJ["scale"]
    return sx, sy


# ---------- SVG path → matplotlib Path ----------
# Only M, L, Z appear in build_map.py output (verified). The renderer is
# intentionally minimal — adding other commands would require expanding the
# regex AND threading curve tessellation through matplotlib's Path codes.
PATH_TOKEN = re.compile(r'([MLZ])([^MLZ]*)')

def svg_path_to_mpl(d):
    verts = []
    codes = []
    for cmd, rest in PATH_TOKEN.findall(d):
        if cmd in ("M", "L"):
            for pair in rest.strip().split("L"):
                # First token after M may be space-or-comma separated
                pair = pair.strip()
                if not pair:
                    continue
                # Tokens look like "402.4,458.9" — possibly multiple separated
                # by L (already split above). Each pair is x,y.
                parts = pair.replace(",", " ").split()
                if len(parts) >= 2:
                    x, y = float(parts[0]), float(parts[1])
                    verts.append((x, y))
                    codes.append(MplPath.MOVETO if cmd == "M" else MplPath.LINETO)
                    cmd = "L"  # subsequent pairs after an M are implicit L
        elif cmd == "Z":
            verts.append((0, 0))  # Path requires a vertex even for CLOSEPOLY
            codes.append(MplPath.CLOSEPOLY)
    return MplPath(verts, codes)


# ---------- Render ----------
def render(outfile, *, width_px, height_px, dpi=200, title=None, subtitle=None):
    """Render the basemap + event pins into a PNG.

    width_px / height_px set the final pixel dimensions; figsize derives
    from those at the chosen dpi. The viewport (xlim/ylim) is set so the
    map fills the canvas with cream margins, leaving room for title text.
    """
    fig_w = width_px / dpi
    fig_h = height_px / dpi
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=dpi)
    fig.patch.set_facecolor(CREAM)
    ax.set_facecolor(CREAM)

    # The viewport from build_map.py: width × height in viewBox units.
    vb_w = map_data["viewport"]["width"]
    vb_h = map_data["viewport"]["height"]

    # Surrounds first (drawn behind India)
    for s in map_data["surrounds"]:
        path = svg_path_to_mpl(s["path"])
        patch = PathPatch(path, facecolor=SURROUNDS_FILL, edgecolor=SURROUNDS_STROKE,
                          linewidth=0.6, antialiased=True)
        ax.add_patch(patch)

    # India (Datameet — drawn last so PoK / Aksai Chin / J&K sit on top)
    india_path = svg_path_to_mpl(map_data["india_path"])
    india_patch = PathPatch(india_path, facecolor=CREAM_CARD, edgecolor=CREAM_TEXT,
                            linewidth=0.9, antialiased=True)
    ax.add_patch(india_patch)

    # Pins — same lat/lon → SVG projection the live asset uses.
    pin_xs, pin_ys = [], []
    for ev in events:
        pts = ev.get("location", {}).get("points") or []
        if not pts:
            continue
        sx, sy = to_svg(pts[0]["lat"], pts[0]["lon"])
        pin_xs.append(sx)
        pin_ys.append(sy)
    ax.scatter(pin_xs, pin_ys, s=18, c=PIN_FILL, edgecolors=CREAM_CARD, linewidths=0.8, zorder=10)

    # Frame the map. Add ~6% top padding for the title.
    title_pad = vb_h * 0.18 if title else 0
    ax.set_xlim(0, vb_w)
    ax.set_ylim(vb_h, -title_pad)  # invert y so SVG-style coords map correctly
    ax.set_aspect("equal")
    ax.axis("off")

    # Title and subtitle, top-left
    if title:
        ax.text(vb_w * 0.04, -title_pad * 0.55, title,
                color=CREAM_TEXT, fontsize=20, fontweight=500,
                ha="left", va="center", family="sans-serif")
    if subtitle:
        ax.text(vb_w * 0.04, -title_pad * 0.18, subtitle,
                color=CREAM_MUTED, fontsize=11, fontstyle="italic",
                ha="left", va="center", family="sans-serif")

    # Footer: count + URL, bottom-right
    footer_y = vb_h * 1.02
    ax.text(vb_w * 0.98, footer_y,
            f"{len(events)} events · assets.chiragpatnaik.com/india-history.html",
            color=CREAM_FAINT, fontsize=9, ha="right", va="top",
            family="sans-serif")

    fig.tight_layout(pad=0)
    fig.savefig(outfile, dpi=dpi, facecolor=CREAM, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)
    print(f"  Wrote {outfile.relative_to(REPO)}: {outfile.stat().st_size/1024:.1f} KB ({width_px}×{height_px})")


# Title/subtitle — pulled from corpus span.
years = sorted(int(re.match(r'-?\d+', str(ev.get("date", {}).get("start", "")))[0])
               for ev in events if ev.get("date", {}).get("start"))
year_span = f"{abs(years[0])} {'BCE' if years[0] < 0 else 'CE'} – {years[-1]} CE" if years else ""
TITLE = "India — 2500 years to the Republic"
SUBTITLE = f"An interactive atlas of subcontinental history · {year_span}" if year_span else ""

render(WEB / "india-history.png", width_px=1200, height_px=675,
       title=TITLE, subtitle=SUBTITLE)
render(WEB / "india-history-square.png", width_px=1080, height_px=1080,
       title=TITLE, subtitle=SUBTITLE)
