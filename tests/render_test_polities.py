"""Verify the Polities UI: pill bar, reader panel, explicit events[]
membership (no auto-derivation), capital-place link cross-navigation,
.in-polity mode highlighting, mutual exclusion with all four other modes."""
from playwright.sync_api import sync_playwright
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HTML = REPO / "web" / "india-history.html"
ARTIFACTS = REPO / "tests" / "artifacts"
ARTIFACTS.mkdir(exist_ok=True)

errors = []


def check(name, condition, detail=""):
    mark = "✓" if condition else "✗"
    print(f"  {mark} {name}{(': ' + detail) if detail else ''}")
    if not condition:
        errors.append((name, detail))


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
    page.on("console", lambda msg: errors.append(("console-error", msg.text)) if msg.type == "error" else None)

    page.goto(f"file://{HTML.absolute()}")
    page.wait_for_timeout(500)

    # 1. Bar present, pills rendered for every POLITIES record.
    pill_count = page.evaluate("() => document.querySelectorAll('#polities-bar .pill[data-poid]').length")
    polities_count = page.evaluate("() => POLITIES.length")
    check("Polities bar pill count matches POLITIES corpus",
          pill_count == polities_count and pill_count >= 1,
          f"pills={pill_count} corpus={polities_count}")

    # 2. Indexes built.
    indexes = page.evaluate("() => ({ pbi: politiesById.size, pm: polityMembers.size })")
    check("Polity indexes built",
          indexes["pbi"] == polities_count and indexes["pm"] == polities_count,
          f"politiesById={indexes['pbi']} polityMembers={indexes['pm']}")

    # 3. Activate Mughal Empire (largest member-count polity).
    page.evaluate("activatePolity('mughal-empire')")
    page.wait_for_timeout(150)
    mughal_state = page.evaluate("""() => ({
      readerVisible: !!document.querySelector('.polity-reader'),
      readerTitle: document.querySelector('.polity-reader h3')?.textContent,
      eventCount: document.querySelectorAll('.polity-event').length,
      capitalsCount: document.querySelectorAll('.capitals-list li').length,
      rulersCount: document.querySelectorAll('.rulers-list li').length,
      mapInPolity: document.querySelector('#map').classList.contains('in-polity'),
      memberIds: polityMembers.get('mughal-empire').length,
    })""")
    check("Mughal polity: reader renders + members + capitals + rulers",
          mughal_state["readerVisible"]
            and mughal_state["readerTitle"] == "Mughal Empire"
            and mughal_state["eventCount"] == mughal_state["memberIds"]
            and mughal_state["memberIds"] >= 20
            and mughal_state["capitalsCount"] >= 3
            and mughal_state["rulersCount"] >= 5,
          f"state={mughal_state}")
    check("Mughal polity: map enters .in-polity mode", mughal_state["mapInPolity"])

    # 4. Every member event id from the polity's events[] resolves to a real
    #    event. (Validator already enforces this on the source side; the test
    #    confirms the UI doesn't drop members silently.)
    resolution = page.evaluate("""() => {
      const memberIds = polityMembers.get('mughal-empire');
      const allResolve = memberIds.every(id => eventById.has(id));
      const sourceList = politiesById.get('mughal-empire').events;
      return { memberCount: memberIds.length, sourceCount: sourceList.length, allResolve };
    }""")
    check("Every Mughal source event resolves and is rendered",
          resolution["memberCount"] == resolution["sourceCount"] and resolution["allResolve"],
          f"members={resolution['memberCount']} source={resolution['sourceCount']}")

    # 5. Map coverage — every member event has a visible single pin OR is
    #    inside an .in-polity cluster pin.
    map_coverage = page.evaluate("""() => {
      const memberIds = polityMembers.get('mughal-empire');
      const singlePinIds = new Set(Array.from(document.querySelectorAll('#pins .pin.in-polity:not(.pin-cluster-group)')).map(g => g.dataset.id));
      const clusterMemberIds = new Set(Array.from(document.querySelectorAll('#pins .pin-cluster-group.in-polity'))
        .flatMap(g => (g.dataset.clusterIds || '').split('|')));
      const covered = memberIds.filter(id => singlePinIds.has(id) || clusterMemberIds.has(id));
      return { covered: covered.length, total: memberIds.length };
    }""")
    check("Every Mughal member has a visible pin or cluster",
          map_coverage["covered"] == map_coverage["total"],
          f"covered {map_coverage['covered']}/{map_coverage['total']}")

    # 6. Capital-place link cross-navigation: clicking a place-resolved capital
    #    in the polity reader switches to that place's reader.
    cap_click = page.evaluate("""() => {
      const link = document.querySelector('.capital-place-link[data-place-id="agra"]');
      if (!link) return { error: 'no agra link found' };
      link.click();
      return {
        afterPolity: state.activePolity,
        afterPlace: state.activePlace,
        readerTitle: document.querySelector('.place-reader h3')?.textContent,
      };
    }""")
    check("Clicking a capital place-link switches to that place reader",
          cap_click.get("afterPolity") is None
            and cap_click.get("afterPlace") == "agra"
            and cap_click.get("readerTitle") == "Agra",
          f"state={cap_click}")

    # 7–10. Mutual-exclusion tests across all four other modes.
    page.evaluate("activatePolity('british-raj')")
    page.evaluate("activateThread('chauri-chaura-and-the-cost-of-non-violence')")
    page.wait_for_timeout(80)
    after_thread = page.evaluate("() => ({ pol: state.activePolity, th: state.activeThread })")
    check("Activating thread clears active polity",
          after_thread["pol"] is None and after_thread["th"] is not None,
          f"state={after_thread}")

    page.evaluate("activatePolity('british-raj')")
    page.evaluate("activateCollection('rebellions-before-and-beyond-1857')")
    page.wait_for_timeout(80)
    after_collection = page.evaluate("() => ({ pol: state.activePolity, c: state.activeCollection })")
    check("Activating collection clears active polity",
          after_collection["pol"] is None and after_collection["c"] is not None,
          f"state={after_collection}")

    page.evaluate("activatePolity('british-raj')")
    page.evaluate("activatePlace('delhi')")
    page.wait_for_timeout(80)
    after_place = page.evaluate("() => ({ pol: state.activePolity, pl: state.activePlace })")
    check("Activating place clears active polity",
          after_place["pol"] is None and after_place["pl"] == "delhi",
          f"state={after_place}")

    page.evaluate("activatePolity('british-raj')")
    page.evaluate("togglePerson('mohandas-gandhi')")
    page.wait_for_timeout(80)
    after_person = page.evaluate("() => ({ pol: state.activePolity, ap: state.activePeople.size })")
    check("Activating person clears active polity",
          after_person["pol"] is None and after_person["ap"] == 1,
          f"state={after_person}")

    # 11. Activating a polity clears all other modes.
    page.evaluate("activatePolity('mughal-empire')")
    page.wait_for_timeout(80)
    after_all_clear = page.evaluate(
        "() => ({ pol: state.activePolity, ap: state.activePeople.size, c: state.activeCollection, pl: state.activePlace, th: state.activeThread })"
    )
    check("Activating a polity clears all four other modes",
          after_all_clear["pol"] == "mughal-empire"
            and after_all_clear["ap"] == 0
            and after_all_clear["c"] is None
            and after_all_clear["pl"] is None
            and after_all_clear["th"] is None,
          f"state={after_all_clear}")

    # 12. Member-row click navigates to event.
    page.evaluate("""() => {
      const id = polityMembers.get('mughal-empire')[0];
      document.querySelector(`.polity-event[data-event-id="${id}"]`).click();
    }""")
    page.wait_for_timeout(150)
    after_event_click = page.evaluate("() => state.activeEvent")
    check("Clicking a polity-event row navigates to that event",
          after_event_click in (page.evaluate("() => polityMembers.get('mughal-empire')") or []),
          f"activeEvent={after_event_click}")

    # 13. clearPolity() resets state and map class.
    page.evaluate("clearPolity()")
    page.wait_for_timeout(100)
    after_clear = page.evaluate(
        "() => ({ pol: state.activePolity, in: document.querySelector('#map').classList.contains('in-polity') })"
    )
    check("clearPolity() resets state and map class",
          after_clear["pol"] is None and after_clear["in"] is False,
          f"state={after_clear}")

    # 14. Per-polity smoke loop — every named polity opens, has at least 1
    #     resolved member event, and reader title matches the record's name.
    smoke = page.evaluate("""() => {
      const out = [];
      for (const po of POLITIES) {
        activatePolity(po.id);
        const titleEl = document.querySelector('.polity-reader h3');
        out.push({
          id: po.id,
          name: po.name,
          renderedTitle: titleEl ? titleEl.textContent : null,
          memberCount: (polityMembers.get(po.id) || []).length,
        });
      }
      clearPolity();
      return out;
    }""")
    for po in smoke:
        check(f"Polity '{po['id']}' renders + has ≥1 member",
              po["renderedTitle"] == po["name"] and po["memberCount"] >= 1,
              f"renderedTitle={po['renderedTitle']!r} members={po['memberCount']}")

    page.screenshot(path=str(ARTIFACTS / "render_test_polities.png"), full_page=True)
    browser.close()

if errors:
    print("\nERRORS:")
    for tag, msg in errors:
        print(f"  [{tag}] {msg}")
    raise SystemExit(1)

print("\nPASS — all polity UI checks succeeded.")
