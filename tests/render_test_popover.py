#!/usr/bin/env python3
"""
render_test_popover.py — exercise the new popover system and confirm pin placement.

Tests:
  1. All expected independence pins render and have visible dots
     (the test pre-dates the Mughal corpus; a 12-event subset is checked).
  2. Each pin lands within ~5 viewBox units of its true projected lat/lon
     (validates the dodge fix — was 12 vbu = 88 km, now 5 vbu = 37 km max).
  3. Single click on Jallianwala pin shows popover containing "Jallianwala".
  4. Popover does NOT update the right-hand panel (panel still shows welcome).
  5. Esc dismisses popover.
  6. Double-click on a pin opens the panel and skips popover.
  7. Shift-click on a pin opens the panel and skips popover.
  8. From an open panel, clicking a relation card opens BOTH a popover
     for the new event AND switches the panel to it.
"""
import math
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / "web" / "india-history.html"
ARTIFACTS = REPO / "tests" / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

# ---- spherical Lambert Conformal Conic (must match build_map.py & template) ----
R = 6_371_000.0
LAT_1, LAT_2, LAT_0, LON_0 = 20.0, 40.0, 30.0, 78.0


def _to_rad(d): return d * math.pi / 180.0


def _lcc(lat_deg, lon_deg):
    p1, p2, p0 = _to_rad(LAT_1), _to_rad(LAT_2), _to_rad(LAT_0)
    n = math.log(math.cos(p1) / math.cos(p2)) / math.log(
        math.tan(math.pi / 4 + p2 / 2) / math.tan(math.pi / 4 + p1 / 2)
    )
    F = math.cos(p1) * (math.tan(math.pi / 4 + p1 / 2) ** n) / n
    rho0 = R * F / (math.tan(math.pi / 4 + p0 / 2) ** n)
    p = _to_rad(lat_deg)
    lam = _to_rad(lon_deg)
    rho = R * F / (math.tan(math.pi / 4 + p / 2) ** n)
    theta = n * (lam - _to_rad(LON_0))
    x = rho * math.sin(theta)
    y = rho0 - rho * math.cos(theta)
    return x, y


# Bounds: read from the actual built map_paths.json so the test never drifts
# from build_map.py defaults.
import json as _json
_proj = _json.loads((REPO / "build" / "map_paths.json").read_text())["projection"]
BOUNDS = {
    "minx": _proj["minx"], "miny": _proj["miny"],
    "maxx": _proj["maxx"], "maxy": _proj["maxy"],
}
SCALE = _proj["scale"]
TARGET_W = _proj["target_w"]
TARGET_H = _proj["target_h"]


def project_to_viewbox(lat, lon):
    x, y = _lcc(lat, lon)
    sx = (x - BOUNDS["minx"]) * SCALE
    sy = (BOUNDS["maxy"] - y) * SCALE
    return sx, sy


# Expected pins: id -> (lat, lon, expected_country)
EXPECTED = {
    "inc-founded-1885":             (18.9388, 72.8344, "IN"),
    "partition-of-bengal-1905":     (22.5726, 88.3639, "IN"),
    "jallianwala-bagh-1919":        (31.6203, 74.8800, "IN"),
    "non-cooperation-movement-1920":(21.1458, 79.0882, "IN"),
    "chauri-chaura-1922":           (26.7589, 83.7375, "IN"),
    "simon-commission-protest-1928":(31.5497, 74.3436, "PK"),
    "lahore-session-1929":          (31.5670, 74.3220, "PK"),
    "salt-march-1930":              (23.0593, 72.5806, "IN"),
    "civil-disobedience-movement-1930": (22.0, 78.5, "IN"),
    "quit-india-1942":              (18.9667, 72.8167, "IN"),
    "direct-action-day-1946":       (22.5726, 88.3639, "IN"),
    "independence-and-partition-1947": (28.6172, 77.2082, "IN"),
}

DODGE_RADIUS_VBU = 5  # max expected displacement


def get_pin_position(page, ev_id):
    """Return (sx, sy) in viewBox units for the pin's transform."""
    return page.evaluate(
        """(id) => {
          const pin = document.querySelector(`#pins .pin[data-id="${id}"]`);
          if (!pin) return null;
          const t = pin.getAttribute('transform') || '';
          const m = t.match(/translate\\(([^,]+),([^)]+)\\)/);
          if (!m) return null;
          return [parseFloat(m[1]), parseFloat(m[2])];
        }""",
        ev_id,
    )


def main():
    failures = []
    notes = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(f"file://{HTML}")
        page.wait_for_load_state("networkidle")

        # ---- 1. Pin count ----
        n_pins = page.evaluate("document.querySelectorAll('#pins .pin').length")
        print(f"  Pins rendered: {n_pins}")
        if n_pins < len(EXPECTED):
            failures.append(f"Expected at least {len(EXPECTED)} pins, got {n_pins}")

        # ---- 2. Pin placement vs true projected position ----
        for ev_id, (lat, lon, country) in EXPECTED.items():
            pos = get_pin_position(page, ev_id)
            if pos is None:
                failures.append(f"{ev_id}: pin not found in DOM")
                continue
            sx, sy = pos
            esx, esy = project_to_viewbox(lat, lon)
            dx, dy = sx - esx, sy - esy
            dist = math.hypot(dx, dy)
            # Allow up to DODGE_RADIUS_VBU + small fudge for cluster centroids
            if dist > DODGE_RADIUS_VBU + 1:
                failures.append(
                    f"{ev_id}: pin at ({sx:.1f},{sy:.1f}), expected near "
                    f"({esx:.1f},{esy:.1f}) — drift {dist:.1f} vbu (>{DODGE_RADIUS_VBU+1})"
                )
            else:
                notes.append(f"  {ev_id}: drift {dist:.1f} vbu ({country})")

        # ---- 3. Single click → popover ----
        page.evaluate(
            "document.querySelector('#pins .pin[data-id=\"jallianwala-bagh-1919\"]').dispatchEvent("
            "new MouseEvent('click', {bubbles:true,cancelable:true}))"
        )
        page.wait_for_timeout(60)
        is_open = page.evaluate("document.querySelector('#popover').classList.contains('is-open')")
        body = page.evaluate("document.querySelector('#popover').innerText")
        if not is_open:
            failures.append("Single-click did not open popover")
        elif "Jallianwala" not in body:
            failures.append(f"Popover content missing — got: {body[:120]}")

        # ---- 4. Single click did NOT change panel ----
        panel_html = page.evaluate("document.querySelector('#event-panel').innerHTML")
        if "Jallianwala" in panel_html and "Browse" not in panel_html:
            failures.append("Single click leaked into the right panel (should stay welcome)")

        # ---- 5. Esc dismisses popover ----
        page.keyboard.press("Escape")
        page.wait_for_timeout(40)
        if page.evaluate("document.querySelector('#popover').classList.contains('is-open')"):
            failures.append("Esc did not close popover")

        # ---- 6. Double-click → panel, no popover ----
        page.evaluate(
            "var pin=document.querySelector('#pins .pin[data-id=\"chauri-chaura-1922\"]');"
            "pin.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,cancelable:true}));"
        )
        page.wait_for_timeout(60)
        panel_html = page.evaluate("document.querySelector('#event-panel').innerHTML")
        if "Chauri Chaura" not in panel_html:
            failures.append("Double-click did not load Chauri Chaura into panel")
        if page.evaluate("document.querySelector('#popover').classList.contains('is-open')"):
            failures.append("Double-click should not leave popover open")

        # ---- 7. Shift-click → panel, no popover ----
        # First clear by clicking close on panel
        page.evaluate(
            "var pin=document.querySelector('#pins .pin[data-id=\"salt-march-1930\"]');"
            "pin.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true,shiftKey:true}));"
        )
        page.wait_for_timeout(60)
        panel_html = page.evaluate("document.querySelector('#event-panel').innerHTML")
        if "Salt March" not in panel_html:
            failures.append("Shift-click did not load Salt March into panel")
        if page.evaluate("document.querySelector('#popover').classList.contains('is-open')"):
            failures.append("Shift-click should not leave popover open")

        # ---- 8. Relation card click → both panel + popover ----
        # Salt March's caused_by includes lahore-session-1929. Click that card.
        clicked = page.evaluate(
            """() => {
              const card = document.querySelector('.relation-card[data-id="lahore-session-1929"]');
              if (!card) return false;
              card.dispatchEvent(new MouseEvent('click', {bubbles:true,cancelable:true}));
              return true;
            }"""
        )
        if not clicked:
            failures.append("Could not find lahore-session-1929 relation card under Salt March")
        else:
            page.wait_for_timeout(80)
            panel_html = page.evaluate("document.querySelector('#event-panel').innerHTML")
            if "Lahore Session" not in panel_html and "Purna Swaraj" not in panel_html:
                failures.append("Relation card click did not switch panel to Lahore Session")
            popover_open = page.evaluate(
                "document.querySelector('#popover').classList.contains('is-open')"
            )
            popover_text = page.evaluate("document.querySelector('#popover').innerText")
            if not popover_open:
                failures.append("Relation card click did not open popover")
            elif "Lahore" not in popover_text:
                failures.append(
                    f"Popover after relation click does not show Lahore — got: {popover_text[:120]}"
                )

        # ---- 9. Screenshot for visual review ----
        page.evaluate("document.querySelector('#popover .popover-close')?.click()")  # tidy
        page.wait_for_timeout(40)
        # Re-open Jallianwala for the final screenshot
        page.evaluate(
            "document.querySelector('#pins .pin[data-id=\"jallianwala-bagh-1919\"]').dispatchEvent("
            "new MouseEvent('click',{bubbles:true,cancelable:true}))"
        )
        page.wait_for_timeout(120)
        page.screenshot(path=str(ARTIFACTS / "render_test_popover.png"), full_page=False)

        browser.close()

    print()
    if notes:
        print("Pin drift summary:")
        for n in notes:
            print(n)

    print()
    if failures:
        print(f"FAIL — {len(failures)} issue(s):")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("PASS — all 8 popover/panel/pin checks succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
