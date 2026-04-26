"""Verify the Places UI: pill bar, reader panel, auto-derived gather by
haversine proximity, .in-place mode highlighting (single + cluster pins),
mutual exclusion with thread / people / collection modes."""
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

    # 1. Bar present, pills rendered for every PLACES record.
    pill_count = page.evaluate("() => document.querySelectorAll('#places-bar .pill[data-plid]').length")
    places_count = page.evaluate("() => PLACES.length")
    check("Places bar pill count matches PLACES corpus",
          pill_count == places_count and pill_count >= 1,
          f"pills={pill_count} corpus={places_count}")

    # 2. Indexes built — placesById and placeMembers populated.
    indexes = page.evaluate("() => ({ pbi: placesById.size, pm: placeMembers.size })")
    check("Place indexes built",
          indexes["pbi"] == places_count and indexes["pm"] == places_count,
          f"placesById={indexes['pbi']} placeMembers={indexes['pm']}")

    # 3. Activate the densest place (Delhi). Reader renders, member events
    #    populate via auto-derivation, map enters in-place mode.
    page.evaluate("activatePlace('delhi')")
    page.wait_for_timeout(150)
    delhi_state = page.evaluate("""() => ({
      readerVisible: !!document.querySelector('.place-reader'),
      readerTitle: document.querySelector('.place-reader h3')?.textContent,
      eventCount: document.querySelectorAll('.place-event').length,
      mapInPlace: document.querySelector('#map').classList.contains('in-place'),
      memberIds: placeMembers.get('delhi').length,
    })""")
    check("Delhi place: reader renders + auto-derived gather populated",
          delhi_state["readerVisible"] and delhi_state["readerTitle"] == "Delhi"
            and delhi_state["eventCount"] == delhi_state["memberIds"]
            and delhi_state["memberIds"] >= 5,
          f"state={delhi_state}")

    check("Delhi place: map enters .in-place mode", delhi_state["mapInPlace"])

    # 4. Auto-derived gather is correct — every member event's coordinates
    #    are within the place's radius. This is the core invariant of the
    #    proximity-based membership model.
    coverage = page.evaluate("""() => {
      const pl = placesById.get('delhi');
      const r = (pl.location.radius_km) || 5;
      const lat0 = pl.location.lat;
      const lon0 = pl.location.lon;
      const memberIds = placeMembers.get('delhi');
      const distances = memberIds.map(id => {
        const ev = eventById.get(id);
        const pt = ev.location.points[0];
        return haversineKm(lat0, lon0, pt.lat, pt.lon);
      });
      return { allWithinRadius: distances.every(d => d <= r), maxDistance: Math.max(...distances), radius: r };
    }""")
    check("Every Delhi member is within radius (auto-derivation invariant)",
          coverage["allWithinRadius"],
          f"max distance {coverage['maxDistance']:.2f} km / radius {coverage['radius']} km")

    # 5. Member coverage on the map — every member should be visible either
    #    as a single .in-place pin OR as a member of an .in-place cluster.
    map_coverage = page.evaluate("""() => {
      const memberIds = placeMembers.get('delhi');
      const singlePinIds = new Set(Array.from(document.querySelectorAll('#pins .pin.in-place:not(.pin-cluster-group)')).map(g => g.dataset.id));
      const clusterMemberIds = new Set(Array.from(document.querySelectorAll('#pins .pin-cluster-group.in-place'))
        .flatMap(g => (g.dataset.clusterIds || '').split('|')));
      const covered = memberIds.filter(id => singlePinIds.has(id) || clusterMemberIds.has(id));
      return { covered: covered.length, total: memberIds.length };
    }""")
    check("Every Delhi member has a visible pin or cluster",
          map_coverage["covered"] == map_coverage["total"],
          f"covered {map_coverage['covered']}/{map_coverage['total']}")

    # 6. Mutual exclusion: activating a thread clears the active place.
    page.evaluate("activateThread('chauri-chaura-and-the-cost-of-non-violence')")
    page.wait_for_timeout(100)
    after_thread = page.evaluate("() => ({ pl: state.activePlace, th: state.activeThread })")
    check("Activating thread clears active place",
          after_thread["pl"] is None and after_thread["th"] == "chauri-chaura-and-the-cost-of-non-violence",
          f"state={after_thread}")

    # 7. Mutual exclusion: activating a collection clears active place.
    page.evaluate("activatePlace('agra')")
    page.wait_for_timeout(80)
    page.evaluate("activateCollection('rebellions-before-and-beyond-1857')")
    page.wait_for_timeout(100)
    after_collection = page.evaluate("() => ({ pl: state.activePlace, c: state.activeCollection })")
    check("Activating a collection clears active place",
          after_collection["pl"] is None and after_collection["c"] == "rebellions-before-and-beyond-1857",
          f"state={after_collection}")

    # 8. Mutual exclusion: activating a person clears active place.
    page.evaluate("activatePlace('agra')")
    page.wait_for_timeout(80)
    page.evaluate("togglePerson('mohandas-gandhi')")
    page.wait_for_timeout(100)
    after_person = page.evaluate(
        "() => ({ pl: state.activePlace, ap: state.activePeople.size })"
    )
    check("Activating a person clears active place",
          after_person["pl"] is None and after_person["ap"] == 1,
          f"state={after_person}")

    # 9. Re-activating a place clears active person.
    page.evaluate("activatePlace('delhi')")
    page.wait_for_timeout(100)
    after_replace = page.evaluate(
        "() => ({ pl: state.activePlace, ap: state.activePeople.size, c: state.activeCollection, th: state.activeThread })"
    )
    check("Activating a place clears all other modes",
          after_replace["pl"] == "delhi"
            and after_replace["ap"] == 0
            and after_replace["c"] is None
            and after_replace["th"] is None,
          f"state={after_replace}")

    # 10. Member-row click opens the event's popover (navigateToEvent path).
    page.evaluate("""() => {
      const memberIds = placeMembers.get('delhi');
      const id = memberIds[0];
      document.querySelector(`.place-event[data-event-id="${id}"]`).click();
    }""")
    page.wait_for_timeout(150)
    after_member_click = page.evaluate("() => state.activeEvent")
    check("Clicking a place-event row navigates to that event",
          after_member_click in (page.evaluate("() => placeMembers.get('delhi')") or []),
          f"activeEvent={after_member_click}")

    # 11. clearPlace() resets state and map class.
    page.evaluate("clearPlace()")
    page.wait_for_timeout(100)
    after_clear = page.evaluate(
        "() => ({ pl: state.activePlace, in: document.querySelector('#map').classList.contains('in-place') })"
    )
    check("clearPlace() resets state and map class",
          after_clear["pl"] is None and after_clear["in"] is False,
          f"state={after_clear}")

    # 12. Per-place smoke tests — every named place opens, has at least one
    #     auto-derived member (warning at <3 in validator but allowed), and
    #     reader title matches the place's name.
    smoke = page.evaluate("""() => {
      const out = [];
      for (const pl of PLACES) {
        activatePlace(pl.id);
        const titleEl = document.querySelector('.place-reader h3');
        out.push({
          id: pl.id,
          name: pl.name,
          renderedTitle: titleEl ? titleEl.textContent : null,
          memberCount: (placeMembers.get(pl.id) || []).length,
        });
      }
      clearPlace();
      return out;
    }""")
    # Note: 0-member places are valid — they exist as polity-capital records
    # so the polity reader's capital cross-nav has a target. The validator's
    # <3 soft-warning is the editorial check; the UI handles 0 fine (reader
    # renders framing + meta + empty member list).
    for pl in smoke:
        check(f"Place '{pl['id']}' renders with correct title",
              pl["renderedTitle"] == pl["name"],
              f"renderedTitle={pl['renderedTitle']!r} members={pl['memberCount']}")

    page.screenshot(path=str(ARTIFACTS / "render_test_places.png"), full_page=True)
    browser.close()

if errors:
    print("\nERRORS:")
    for tag, msg in errors:
        print(f"  [{tag}] {msg}")
    raise SystemExit(1)

print("\nPASS — all place UI checks succeeded.")
