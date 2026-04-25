#!/usr/bin/env python3
"""
render_test_people.py — exercise the People UI: pills, tracks, off-map table,
moment + event-ref popovers, mutual exclusion with Threads, multi-select.

Tests (10 checks):
  1. Five People pills render with the Rangrez accent colours assigned by
     load order (Gandhi=KHADI, Nehru=AAKASH, Singh=KUMKUM, Ambedkar=NEEL,
     Jinnah=MOR).
  2. Activating Gandhi paints 13 numbered track pins + 1 connecting line +
     2 off-map rows (Inner Temple, Pietermaritzburg).
  3. Multi-select: adding Ambedkar yields 23 track pins + 5 off-map rows.
  4. Track pin click on a 'moment' step opens a moment popover with the
     `is-moment` class set and the moment's tooltip as the heading.
  5. Track pin click on an 'event-ref' step opens an event popover with
     the resolved event's title and a working "Read full event →" button.
  6. Off-map table row click opens the popover for that step (anchored to
     the row, since the pin is outside the visible viewBox).
  7. Activating a Thread with People active clears the People (mutual
     exclusion). Re-activating a Person clears the Thread.
  8. Reset button clears all active people, popover, and search.
  9. Pin radius scales inversely with zoom — the SVG `r` attribute on a
     track pin shrinks when zoom.scale increases.
 10. People reader (right panel) renders one block per active person with
     numbered timeline steps and OFF-MAP tags on off-map moments.
"""
from playwright.sync_api import sync_playwright
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / "web" / "india-history.html"
ARTIFACTS = REPO / "tests" / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

errors: list[tuple[str, str]] = []


def check(name: str, ok: bool, detail: str = ""):
    mark = "✓" if ok else "✗"
    print(f"  {mark} {name}{(': ' + detail) if detail else ''}")
    if not ok:
        errors.append((name, detail))


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 1000})
    page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
    page.on("console",
            lambda msg: errors.append(("console-error", msg.text))
            if msg.type == "error" else None)

    page.goto(f"file://{HTML}")
    page.wait_for_timeout(500)

    # ----- 1. Pills render with accent colours -----
    pill_data = page.evaluate("""() => {
      return Array.from(document.querySelectorAll('.pill.is-person')).map(b => ({
        pid: b.dataset.pid,
        accent: b.style.getPropertyValue('--accent').trim()
      }));
    }""")
    expected = {
        "gandhi": "#b03018",
        "nehru": "#1a4870",
        "bhagat-singh": "#c8281a",
        "ambedkar": "#1a3a90",
        "jinnah": "#1f7a8a",
    }
    pids_seen = {p["pid"]: p["accent"] for p in pill_data}
    ok = all(pids_seen.get(k, "").lower() == v.lower() for k, v in expected.items())
    check("5 people pills with Rangrez accents", ok,
          f"got {pids_seen}" if not ok else "")

    # ----- 2. Activate Gandhi -----
    page.evaluate("""() => document.querySelector('.pill.is-person[data-pid="gandhi"]').click()""")
    page.wait_for_timeout(150)
    state_after = page.evaluate("""() => ({
      activePeople: Array.from(state.activePeople),
      trackPins: document.querySelectorAll('#tracks .track-pin').length,
      trackLines: document.querySelectorAll('#tracks .track-line').length,
      offmapRows: document.querySelectorAll('.offmap-panel li').length
    })""")
    ok = (state_after["activePeople"] == ["gandhi"]
          and state_after["trackPins"] == 13
          and state_after["trackLines"] == 1
          and state_after["offmapRows"] == 2)
    check("Gandhi activates: 13 pins + 1 line + 2 off-map rows",
          ok, f"got {state_after}" if not ok else "")

    # ----- 3. Multi-select Ambedkar -----
    page.evaluate("""() => document.querySelector('.pill.is-person[data-pid="ambedkar"]').click()""")
    page.wait_for_timeout(150)
    state_multi = page.evaluate("""() => ({
      activePeople: Array.from(state.activePeople).sort(),
      trackPins: document.querySelectorAll('#tracks .track-pin').length,
      offmapRows: document.querySelectorAll('.offmap-panel li').length
    })""")
    ok = (state_multi["activePeople"] == ["ambedkar", "gandhi"]
          and state_multi["trackPins"] == 23
          and state_multi["offmapRows"] == 5)
    check("Multi-select Gandhi+Ambedkar: 23 pins + 5 off-map rows",
          ok, f"got {state_multi}" if not ok else "")

    # ----- 4. Click a moment-kind track pin → moment popover -----
    moment_state = page.evaluate("""() => {
      // Gandhi step 3 is gandhi-champaran-1917 (a 'moment' kind)
      const pin = document.querySelector(
        '#tracks .track-pin[data-person-id="gandhi"][data-step-idx="3"]');
      pin.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
      return {
        popoverOpen: document.querySelector('#popover').classList.contains('is-open'),
        isMoment: document.querySelector('#popover').classList.contains('is-moment'),
        popoverMoment: state.popoverMoment,
        headerText: document.querySelector('#popover h4')?.innerText
      };
    }""")
    ok = (moment_state["popoverOpen"]
          and moment_state["isMoment"]
          and moment_state["popoverMoment"] == "gandhi::gandhi-champaran-1917"
          and "Champaran" in (moment_state.get("headerText") or ""))
    check("Track-pin click on moment → moment popover",
          ok, f"got {moment_state}" if not ok else "")

    # ----- 5. Click an event-ref track pin → event popover -----
    eventref_state = page.evaluate("""() => {
      // Find the salt-march-1930 event-ref step in Gandhi's track
      const track = peopleById.get('gandhi').track;
      const idx = track.findIndex(s => s.kind === 'event-ref' && s.event_id === 'salt-march-1930');
      const pin = document.querySelector(
        `#tracks .track-pin[data-person-id="gandhi"][data-step-idx="${idx}"]`);
      pin.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
      return {
        popoverEvent: state.popoverEvent,
        popoverMoment: state.popoverMoment,
        isMoment: document.querySelector('#popover').classList.contains('is-moment'),
        headerText: document.querySelector('#popover h4')?.innerText,
        hasReadFull: !!document.querySelector('#popover .btn-read-full:not([disabled])')
      };
    }""")
    ok = (eventref_state["popoverEvent"] == "salt-march-1930"
          and eventref_state["popoverMoment"] is None
          and not eventref_state["isMoment"]
          and "Salt March" in (eventref_state.get("headerText") or "")
          and eventref_state["hasReadFull"])
    check("Track-pin click on event-ref → event popover with role + Read-full",
          ok, f"got {eventref_state}" if not ok else "")

    # ----- 6. Off-map row click opens popover anchored to row -----
    offmap_state = page.evaluate("""() => {
      const row = document.querySelector('.offmap-panel li[data-person-id="ambedkar"]');
      row.click();
      return {
        popoverOpen: document.querySelector('#popover').classList.contains('is-open'),
        popoverMoment: state.popoverMoment,
        headerText: document.querySelector('#popover h4')?.innerText
      };
    }""")
    ok = (offmap_state["popoverOpen"]
          and offmap_state["popoverMoment"]
          and offmap_state["popoverMoment"].startswith("ambedkar::"))
    check("Off-map row click → popover for off-map step",
          ok, f"got {offmap_state}" if not ok else "")

    # ----- 7. Mutual exclusion with Threads -----
    excl_state = page.evaluate("""() => {
      // Click a thread pill — should clear active people
      document.querySelector('.threads-bar .pill[data-tid="chauri-chaura-and-the-cost-of-non-violence"]').click();
      const afterThread = {
        activeThread: state.activeThread,
        activePeople: Array.from(state.activePeople),
        trackPins: document.querySelectorAll('#tracks .track-pin').length
      };
      // Now click a person pill — should clear active thread
      document.querySelector('.pill.is-person[data-pid="nehru"]').click();
      const afterPerson = {
        activeThread: state.activeThread,
        activePeople: Array.from(state.activePeople)
      };
      return { afterThread, afterPerson };
    }""")
    ok = (excl_state["afterThread"]["activePeople"] == []
          and excl_state["afterThread"]["activeThread"] is not None
          and excl_state["afterThread"]["trackPins"] == 0
          and excl_state["afterPerson"]["activeThread"] is None
          and excl_state["afterPerson"]["activePeople"] == ["nehru"])
    check("Threads + People mutually exclusive", ok,
          f"got {excl_state}" if not ok else "")

    # ----- 8. Reset clears everything -----
    reset_state = page.evaluate("""() => {
      document.querySelector('#reset').click();
      return {
        activePeople: Array.from(state.activePeople),
        activeThread: state.activeThread,
        trackPins: document.querySelectorAll('#tracks .track-pin').length,
        offmapRows: document.querySelectorAll('.offmap-panel li').length,
        popoverOpen: document.querySelector('#popover').classList.contains('is-open')
      };
    }""")
    ok = (reset_state["activePeople"] == []
          and reset_state["activeThread"] is None
          and reset_state["trackPins"] == 0
          and reset_state["offmapRows"] == 0
          and not reset_state["popoverOpen"])
    check("Reset clears people, thread, popover, off-map", ok,
          f"got {reset_state}" if not ok else "")

    # ----- 9. Track pin radius scales inversely with zoom -----
    scale_state = page.evaluate("""() => {
      // Activate Gandhi to get track pins
      document.querySelector('.pill.is-person[data-pid="gandhi"]').click();
      const r1 = document.querySelector('#tracks .track-pin .dot').getAttribute('r');
      // Zoom in 2× via the button
      document.querySelector('#zoom-in').click();
      document.querySelector('#zoom-in').click();
      const r2 = document.querySelector('#tracks .track-pin .dot').getAttribute('r');
      return { r1: parseFloat(r1), r2: parseFloat(r2), scale: zoom.scale };
    }""")
    ok = scale_state["r2"] < scale_state["r1"] and scale_state["scale"] > 1.0
    check("Track pin radius shrinks on zoom-in", ok,
          f"got r1={scale_state['r1']}, r2={scale_state['r2']}, scale={scale_state['scale']}"
          if not ok else "")

    # Reset zoom for next check
    page.evaluate("() => document.querySelector('#zoom-reset').click()")
    page.wait_for_timeout(150)

    # ----- 10. People reader: numbered steps + OFF-MAP tag -----
    reader_state = page.evaluate("""() => {
      // Gandhi already active from check 9
      const reader = document.querySelector('.people-reader');
      if (!reader) return { rendered: false };
      const stepCount = reader.querySelectorAll('.track-step').length;
      const offmapTags = reader.querySelectorAll('.offmap-tag').length;
      const personName = reader.querySelector('.person-name')?.innerText;
      const firstStepNum = reader.querySelector('.track-step')?.dataset.num;
      return { rendered: true, stepCount, offmapTags, personName, firstStepNum };
    }""")
    ok = (reader_state["rendered"]
          and reader_state["stepCount"] == 13
          and reader_state["offmapTags"] >= 2  # Inner Temple, Pietermaritzburg
          and "Gandhi" in (reader_state.get("personName") or "")
          and reader_state["firstStepNum"] == "1")
    check("People reader: 13 numbered steps + ≥2 OFF-MAP tags",
          ok, f"got {reader_state}" if not ok else "")

    page.screenshot(path=str(ARTIFACTS / "render_test_people.png"), full_page=False)
    browser.close()

if errors:
    print("\nERRORS:")
    for tag, msg in errors:
        print(f"  [{tag}] {msg}")
    raise SystemExit(1)

print("\nPASS — all 10 People UI checks succeeded.")
