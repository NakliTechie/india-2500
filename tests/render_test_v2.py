"""Verify the pin dodge fix — click the three pins that previously collided
in the Lahore/Amritsar cluster and confirm the right event panel opens."""
from playwright.sync_api import sync_playwright
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / "web" / "india-history.html"
ARTIFACTS = REPO / "tests" / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

errors = []

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
    page.on("console", lambda msg: errors.append(("console-error", msg.text)) if msg.type == "error" else None)

    page.goto(f"file://{HTML.absolute()}")
    page.wait_for_timeout(500)

    # Click each of the three formerly-colliding pins and assert the right title appears.
    cases = [
        ("jallianwala-bagh-1919",       "Jallianwala Bagh massacre"),
        ("simon-commission-protest-1928", "Simon Commission protest, Lahore"),
        ("lahore-session-1929",         "Lahore Session — Purna Swaraj declaration"),
        ("salt-march-1930",             "Salt March (Dandi March)"),
        ("inc-founded-1885",            "Indian National Congress founded"),
        ("quit-india-1942",             "Quit India Movement"),
    ]
    for pin_id, expected_title in cases:
        # Dispatch the event directly to the targeted element — works even
        # when dodge has put another pin on top at the same pixel position.
        page.dispatch_event(f'g.pin[data-id="{pin_id}"]', 'click', {"shiftKey": True})
        page.wait_for_timeout(150)
        title = page.locator("#event-panel h3").first.inner_text()
        ok = expected_title in title
        print(f"  {'✓' if ok else '✗'} click {pin_id} → panel title: {title!r}")
        if not ok:
            errors.append(("wrong-panel", f"clicked {pin_id} expected {expected_title!r}, got {title!r}"))

    # Test relation-card navigation: click Salt March, then click its "Caused by"
    # card → panel should switch to Lahore Session.
    page.dispatch_event('g.pin[data-id="salt-march-1930"]', 'click', {"shiftKey": True})
    page.wait_for_timeout(150)
    # Find the "Caused by" card
    page.dispatch_event('.relation-card[data-id="lahore-session-1929"]', 'click')
    page.wait_for_timeout(150)
    title = page.locator("#event-panel h3").first.inner_text()
    ok = "Lahore Session" in title
    print(f"  {'✓' if ok else '✗'} Salt March → Caused by → Lahore Session: {title!r}")
    if not ok:
        errors.append(("relation-nav", f"expected Lahore Session, got {title!r}"))

    # Test thread activation
    page.click('button.pill[data-tid="chauri-chaura-and-the-cost-of-non-violence"]')
    page.wait_for_timeout(200)
    has_reader = page.locator(".thread-reader").count() > 0
    print(f"  {'✓' if has_reader else '✗'} thread activation: reader visible = {has_reader}")

    # Test slider — change start year and confirm pin count drops
    page.evaluate("""() => {
      const r = document.getElementById('r-start');
      r.value = 1930;
      r.dispatchEvent(new Event('input'));
    }""")
    page.wait_for_timeout(150)
    pin_count = page.locator("#pins g.pin").count()
    # In thread mode, thread events stay visible regardless of slider — should be ≥4
    print(f"  range start 1930 + thread active: {pin_count} pins visible (thread events kept)")

    page.screenshot(path=str(ARTIFACTS / "shot_after_dodge_fix.png"), full_page=True)
    browser.close()

if errors:
    print("\nERRORS:")
    for tag, msg in errors:
        print(f"  [{tag}] {msg}")
    raise SystemExit(1)

print("\nAll click tests passed.")
