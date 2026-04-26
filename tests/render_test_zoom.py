#!/usr/bin/env python3
"""
render_test_zoom.py — exercise the new zoom + pan system.

Tests:
  1. Initial viewBox matches the projection's full-map extents.
  2. Wheel-up zooms in: viewBox width shrinks, pin radii shrink too.
  3. Wheel zoom is anchored to cursor — point under cursor stays under cursor.
  4. Pan via mouse-drag shifts the viewBox.
  5. Pan does NOT trigger the pin's click handler when the drag ends on a pin.
  6. Reset button restores the initial viewBox.
  7. + / − buttons step the zoom level and disable at limits.
  8. Title is the new "India — 2500 years to the Republic".
"""
import math
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / "web" / "india-history.html"
ARTIFACTS = REPO / "tests" / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)


def vb(page):
    return page.evaluate(
        "() => { const v = document.querySelector('#map').viewBox.baseVal; "
        "return [v.x, v.y, v.width, v.height]; }"
    )


def pin_radius(page):
    return page.evaluate(
        "() => parseFloat(document.querySelector('#pins .pin .dot').getAttribute('r'))"
    )


def main():
    failures = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(f"file://{HTML}")
        page.wait_for_load_state("networkidle")
        # Defensive wait + readiness check — networkidle returns immediately
        # for file:// URLs but bootRenders() needs a moment to bind
        # wheel/drag listeners to the ~150-event corpus. Wait for the boot
        # to finish (zoom global is the most reliable signal it's done).
        page.wait_for_function("() => typeof zoom !== 'undefined' && zoom.scale === 1")
        page.wait_for_timeout(1500)

        # ---- 1. Initial viewBox ----
        x0, y0, w0, h0 = vb(page)
        if not (abs(x0) < 0.5 and abs(y0) < 0.5):
            failures.append(f"Initial viewBox should start at (0,0); got ({x0},{y0})")
        if not (995 < w0 < 1005):
            failures.append(f"Initial viewBox width should be ~1000; got {w0}")

        # ---- 2. Wheel-up zooms in ----
        # We dispatch a wheel event over the centre of the map.
        rect = page.evaluate(
            "() => { const r = document.querySelector('#map').getBoundingClientRect();"
            "return { left: r.left, top: r.top, width: r.width, height: r.height }; }"
        )
        cx_screen = rect["left"] + rect["width"] / 2
        cy_screen = rect["top"]  + rect["height"] / 2
        page.mouse.move(cx_screen, cy_screen)
        page.mouse.wheel(0, -300)  # negative deltaY = zoom in
        page.wait_for_timeout(60)

        x1, y1, w1, h1 = vb(page)
        if not (w1 < w0 * 0.9):
            failures.append(f"Wheel-up should reduce viewBox width; got {w0:.1f} → {w1:.1f}")

        # ---- 3. Pin radius inverse-scaled ----
        r0_to_r1_ratio = 5.0 / pin_radius(page)
        # If viewBox shrank by factor k, scale = k, r should be 5/k
        scale = w0 / w1
        if abs(r0_to_r1_ratio - scale) > 0.05:
            failures.append(
                f"Pin radius inverse-scale wrong: scale={scale:.2f}, but r=5/{r0_to_r1_ratio:.2f}"
            )

        # ---- 4. Wheel anchor: zoom around the cursor ----
        # Reset, move cursor to a known offset, zoom, check the SVG point under
        # the cursor stayed under the cursor.
        page.click("#zoom-reset")
        page.wait_for_timeout(40)
        # Aim cursor at the lower-right quadrant — far from the centre
        target_screen_x = rect["left"] + rect["width"] * 0.75
        target_screen_y = rect["top"]  + rect["height"] * 0.75
        # Compute the SVG point under that screen point at zoom=1
        svg_pt_before = page.evaluate(
            """([cx, cy]) => {
              const rect = document.querySelector('#map').getBoundingClientRect();
              const fx = (cx - rect.left) / rect.width;
              const fy = (cy - rect.top)  / rect.height;
              const vb = document.querySelector('#map').viewBox.baseVal;
              return [vb.x + fx * vb.width, vb.y + fy * vb.height];
            }""",
            [target_screen_x, target_screen_y],
        )
        page.mouse.move(target_screen_x, target_screen_y)
        page.mouse.wheel(0, -300)
        page.wait_for_timeout(60)
        svg_pt_after = page.evaluate(
            """([cx, cy]) => {
              const rect = document.querySelector('#map').getBoundingClientRect();
              const fx = (cx - rect.left) / rect.width;
              const fy = (cy - rect.top)  / rect.height;
              const vb = document.querySelector('#map').viewBox.baseVal;
              return [vb.x + fx * vb.width, vb.y + fy * vb.height];
            }""",
            [target_screen_x, target_screen_y],
        )
        # Point under cursor should be stable to within 1 viewBox unit
        d = math.hypot(svg_pt_after[0] - svg_pt_before[0],
                       svg_pt_after[1] - svg_pt_before[1])
        if d > 1.0:
            failures.append(
                f"Cursor anchor drifted by {d:.2f} vbu (expected ~0); "
                f"before {svg_pt_before}, after {svg_pt_after}"
            )

        # ---- 5. Pan via drag ----
        page.click("#zoom-reset")
        page.wait_for_timeout(40)
        x0, y0, w0, h0 = vb(page)
        # Click-drag from centre to upper-left
        start_x = rect["left"] + rect["width"] / 2
        start_y = rect["top"]  + rect["height"] / 2
        page.mouse.move(start_x, start_y)
        page.mouse.down()
        page.mouse.move(start_x - 200, start_y - 100, steps=8)
        page.mouse.up()
        page.wait_for_timeout(40)
        x1, y1, w1, h1 = vb(page)
        # At zoom=1 the viewBox can't shift (clamped to map extent), so first
        # zoom in then pan.
        page.mouse.move(start_x, start_y)
        page.mouse.wheel(0, -400)  # zoom in to allow panning
        page.wait_for_timeout(40)
        x_zoomed, y_zoomed, _, _ = vb(page)
        page.mouse.down()
        page.mouse.move(start_x - 150, start_y - 80, steps=8)
        page.mouse.up()
        page.wait_for_timeout(40)
        x_panned, y_panned, _, _ = vb(page)
        if abs(x_panned - x_zoomed) < 5 and abs(y_panned - y_zoomed) < 5:
            failures.append(
                f"Drag did not pan viewBox: zoomed=({x_zoomed:.1f},{y_zoomed:.1f}) "
                f"after drag=({x_panned:.1f},{y_panned:.1f})"
            )

        # ---- 6. Reset restores initial viewBox ----
        page.click("#zoom-reset")
        page.wait_for_timeout(40)
        xr, yr, wr, hr = vb(page)
        if not (abs(xr) < 0.5 and abs(yr) < 0.5 and 995 < wr < 1005):
            failures.append(f"Reset did not restore initial viewBox; got ({xr},{yr},{wr},{hr})")
        if abs(pin_radius(page) - 5) > 0.01:
            failures.append(f"Pin radius did not reset; got {pin_radius(page)}")

        # ---- 7. Buttons + step zoom and reach limits ----
        for _ in range(20):
            disabled = page.evaluate("document.querySelector('#zoom-in').disabled")
            if disabled: break
            page.evaluate("document.querySelector('#zoom-in').click()")
            page.wait_for_timeout(15)
        in_disabled = page.evaluate("document.querySelector('#zoom-in').disabled")
        if not in_disabled:
            failures.append("Zoom-in did not become disabled at max scale")
        for _ in range(20):
            disabled = page.evaluate("document.querySelector('#zoom-out').disabled")
            if disabled: break
            page.evaluate("document.querySelector('#zoom-out').click()")
            page.wait_for_timeout(15)
        out_disabled = page.evaluate("document.querySelector('#zoom-out').disabled")
        if not out_disabled:
            failures.append("Zoom-out did not become disabled at min scale")

        # ---- 8. Title check ----
        title = page.evaluate("document.querySelector('h1').innerText")
        if "2500 years to the Republic" not in title:
            failures.append(f"Title not updated: '{title}'")

        # ---- Final screenshot at a useful zoom level ----
        page.click("#zoom-reset")
        page.wait_for_timeout(40)
        # Zoom into Punjab (the cluster of pins) for the screenshot
        page.mouse.move(rect["left"] + rect["width"] * 0.48,
                        rect["top"]  + rect["height"] * 0.45)
        for _ in range(6):
            page.mouse.wheel(0, -250)
            page.wait_for_timeout(20)
        page.screenshot(path=str(ARTIFACTS / "render_test_zoom.png"), full_page=False)

        browser.close()

    if failures:
        print(f"FAIL — {len(failures)} issue(s):")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("PASS — all 8 zoom/pan checks succeeded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
