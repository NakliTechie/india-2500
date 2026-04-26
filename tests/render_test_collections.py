"""Verify the Collections UI: pill bar, reader panel, member resolution
(both event-id and tag selectors), map highlighting (including cluster pins),
and mutual exclusion with Threads + People.

Asserts the shipped UI works without relying on the static SVG fallback —
all checks happen post-JS-boot.
"""
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

    # 1. Bar present, the two infra-test seed collections rendered as pills
    #    (other collections may exist alongside them — content authoring grows
    #    this set; the test pins only the two it depends on for downstream
    #    assertions).
    pill_cids = page.evaluate(
        "() => Array.from(document.querySelectorAll('#collections-bar .pill[data-cid]')).map(b => b.dataset.cid)"
    )
    seed_pills = {"baburs-road-from-andijan-to-lahore", "founding-moments-of-modern-india"}
    check("Collections bar contains both infra-seed pills",
          seed_pills.issubset(set(pill_cids)),
          f"got {pill_cids}")

    # 2. Indexes built — collectionsById has the seed pair, tag-to-events
    #    resolves babur-arc to 6 (Babur's Central Asian arc events).
    indexes = page.evaluate(
        "() => ({ cbi: collectionsById.size, baburArc: (tagToEvents.get('babur-arc') || []).length })"
    )
    check("Indexes built", indexes["cbi"] >= 2 and indexes["baburArc"] == 6,
          f"collectionsById={indexes['cbi']}, babur-arc tag → {indexes['baburArc']} events")

    # 3. Activate the tag-selector collection. Verify reader, member count,
    #    chronological order, map.in-collection class, and that ALL six
    #    members are highlighted (5 single pins + 1 in a cluster).
    page.evaluate("activateCollection('baburs-road-from-andijan-to-lahore')")
    page.wait_for_timeout(150)

    reader_visible = page.locator(".collection-reader").count() > 0
    check("Tag-selector collection: reader visible", reader_visible)

    member_titles = page.evaluate(
        "() => Array.from(document.querySelectorAll('.collection-member .member-title')).map(e => e.textContent)"
    )
    check("Tag-selector resolves to 6 members",
          len(member_titles) == 6, f"got {len(member_titles)}: {member_titles}")

    member_years = page.evaluate(
        "() => Array.from(document.querySelectorAll('.collection-member')).map(c => eventById.get(c.dataset.eventId)._yearStart)"
    )
    check("Members sorted chronologically",
          member_years == sorted(member_years), f"got {member_years}")

    map_in_collection = page.evaluate("() => document.querySelector('#map').classList.contains('in-collection')")
    check("Map enters in-collection mode", map_in_collection)

    # All 6 members must be visually accounted for via .in-collection — either
    # as a single pin OR via a cluster pin that contains the member.
    coverage = page.evaluate("""() => {
      const memberIds = resolveCollectionMembers(collectionsById.get('baburs-road-from-andijan-to-lahore'));
      const singlePinIds = new Set(Array.from(document.querySelectorAll('#pins .pin.in-collection:not(.pin-cluster-group)')).map(g => g.dataset.id));
      const clusterIds = new Set(Array.from(document.querySelectorAll('#pins .pin-cluster-group.in-collection'))
        .flatMap(g => (g.dataset.clusterIds || '').split('|')));
      const covered = memberIds.filter(id => singlePinIds.has(id) || clusterIds.has(id));
      return { memberIds, covered };
    }""")
    check("All members have a visible pin or cluster",
          len(coverage["covered"]) == len(coverage["memberIds"]),
          f"covered {len(coverage['covered'])}/{len(coverage['memberIds'])}: missing {set(coverage['memberIds']) - set(coverage['covered'])}")

    # 4. Switch to the explicit-event-id collection. Same structural checks.
    page.evaluate("activateCollection('founding-moments-of-modern-india')")
    page.wait_for_timeout(150)
    explicit_count = page.evaluate("() => document.querySelectorAll('.collection-member').length")
    check("Explicit-id collection resolves to 6 members", explicit_count == 6, f"got {explicit_count}")

    # 5. Mutual exclusion: activating a thread clears the active collection.
    page.evaluate("activateThread('chauri-chaura-and-the-cost-of-non-violence')")
    page.wait_for_timeout(100)
    after_thread = page.evaluate("() => ({ ac: state.activeCollection, at: state.activeThread })")
    check("Activating thread clears active collection",
          after_thread["ac"] is None and after_thread["at"] == "chauri-chaura-and-the-cost-of-non-violence",
          f"state={after_thread}")

    # 6. Mutual exclusion: activating a person also clears the collection (and the thread).
    page.evaluate("activateCollection('founding-moments-of-modern-india')")
    page.wait_for_timeout(80)
    page.evaluate("togglePerson('mohandas-gandhi')")
    page.wait_for_timeout(100)
    after_person = page.evaluate(
        "() => ({ ac: state.activeCollection, at: state.activeThread, ap: state.activePeople.size })"
    )
    check("Activating a person clears collection (and thread)",
          after_person["ac"] is None and after_person["at"] is None and after_person["ap"] == 1,
          f"state={after_person}")

    # 7. Re-activating a collection clears any active person.
    page.evaluate("activateCollection('baburs-road-from-andijan-to-lahore')")
    page.wait_for_timeout(100)
    after_collection = page.evaluate(
        "() => ({ ac: state.activeCollection, at: state.activeThread, ap: state.activePeople.size })"
    )
    check("Activating a collection clears active people",
          after_collection["ac"] == "baburs-road-from-andijan-to-lahore" and after_collection["ap"] == 0,
          f"state={after_collection}")

    # 8. Clicking a member row opens that event's popover (navigateToEvent path).
    page.evaluate("""() => document.querySelector('.collection-member[data-event-id="babur-takes-kabul-1504"]').click()""")
    page.wait_for_timeout(150)
    after_member_click = page.evaluate("() => state.activeEvent")
    check("Clicking a member row navigates to that event",
          after_member_click == "babur-takes-kabul-1504",
          f"activeEvent={after_member_click}")

    # 9. Exit collection — close button clears state.
    page.evaluate("clearCollection()")
    page.wait_for_timeout(100)
    after_clear = page.evaluate(
        "() => ({ ac: state.activeCollection, in: document.querySelector('#map').classList.contains('in-collection') })"
    )
    check("clearCollection() resets state and map class",
          after_clear["ac"] is None and after_clear["in"] is False,
          f"state={after_clear}")

    page.screenshot(path=str(ARTIFACTS / "render_test_collections.png"), full_page=True)
    browser.close()

if errors:
    print("\nERRORS:")
    for tag, msg in errors:
        print(f"  [{tag}] {msg}")
    raise SystemExit(1)

print("\nPASS — all collection UI checks succeeded.")
