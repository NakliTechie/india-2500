// validators.js — JS port of validators/validate_*.py vocab + length checks.
// Goal: surface errors in the form before the contributor downloads, so they
// don't have to learn the schema by failing CI. The Python validators remain
// authoritative on the server side; this is a fast UX layer.

export const ERAS = [
  "vedic", "mahajanapada", "maurya", "post-maurya", "gupta",
  "early-medieval", "sultanate", "mughal", "maratha",
  "colonial", "independence", "republic",
];

export const CATEGORIES = [
  "political", "military", "religious", "cultural", "scientific",
  "economic", "dynastic", "colonial-administration", "resistance", "reform",
];

export const PRECISIONS = ["day", "month", "year", "decade", "century"];

export const LOCATION_TYPES = ["point", "city", "region", "route"];

export const COUNTRIES = [
  "IN", "PK", "BD", "NP", "BT", "LK", "AF",
  "UZ", "TJ", "TM", "KZ", "KG",
  "MM", "CN", "IR", "RU", "MN",
  "AE", "OM", "SA", "YE",
  "TH", "LA", "VN", "KH",
  "OFF",
];

export const COUNTRY_NAMES = {
  IN: "India",
  PK: "Pakistan", BD: "Bangladesh", NP: "Nepal", BT: "Bhutan",
  LK: "Sri Lanka", AF: "Afghanistan",
  UZ: "Uzbekistan", TJ: "Tajikistan", TM: "Turkmenistan",
  KZ: "Kazakhstan", KG: "Kyrgyzstan",
  MM: "Myanmar", CN: "China", IR: "Iran", RU: "Russia",
  MN: "Mongolia",
  AE: "United Arab Emirates", OM: "Oman",
  SA: "Saudi Arabia", YE: "Yemen",
  TH: "Thailand", LA: "Laos", VN: "Vietnam", KH: "Cambodia",
  OFF: "Off-map (outside the asset's bounding box)",
};

export const LINK_TYPES = ["wikipedia", "primary", "archive", "related", "secondary"];
export const SOURCE_TYPES = ["scholarly", "primary", "secondary", "reference"];
export const THREAD_KINDS = ["narrative", "causal-chain", "thematic", "counterfactual"];
export const STEP_KINDS = ["event-ref", "moment"];

export const ID_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/;

// Asset bounding box — lat min, lat max, lon min, lon max
export const BBOX = [5.0, 55.0, 55.0, 105.0];

/* ----------------------------------------------------------------------
   Field-level checks. Each returns a list of {level: 'error'|'warn', msg}.
   Empty list = field passes.
   ---------------------------------------------------------------------- */

export function checkId(id) {
  const out = [];
  if (!id) out.push({level: "error", msg: "ID is required."});
  else if (!ID_RE.test(id)) out.push({level: "error", msg: "ID must be kebab-case (lowercase, digits, hyphens). Example: my-event-1947"});
  return out;
}

export function checkTooltip(s) {
  const out = [];
  if (!s) out.push({level: "error", msg: "Tooltip cannot be empty."});
  else if (s.length > 80) out.push({level: "error", msg: `Tooltip is ${s.length} chars (hard cap is 80).`});
  else if (s.length > 60) out.push({level: "warn", msg: `Tooltip is ${s.length} chars; consider trimming under 60.`});
  return out;
}

export function checkSummary(s) {
  const out = [];
  if (!s) out.push({level: "error", msg: "Summary cannot be empty."});
  else if (s.length > 160) out.push({level: "error", msg: `Summary is ${s.length} chars (hard cap is 160).`});
  else if (s.length > 140) out.push({level: "warn", msg: `Summary is ${s.length} chars; consider trimming under 140.`});
  return out;
}

export function checkDetail(s) {
  const out = [];
  if (!s) {
    out.push({level: "warn", msg: "Detail is empty. Most events benefit from an 80–150 word paragraph."});
  } else {
    const words = s.trim().split(/\s+/).length;
    if (words < 80) out.push({level: "warn", msg: `Detail is ${words} words; aim for 80–150.`});
    else if (words > 200) out.push({level: "warn", msg: `Detail is ${words} words (>200 — consider tightening).`});
  }
  return out;
}

export function checkTitle(s) {
  const out = [];
  if (!s) out.push({level: "error", msg: "Title is required."});
  else if (s.length > 60) out.push({level: "warn", msg: `Title is ${s.length} chars; >60 may not display well in headers.`});
  return out;
}

const DATE_RE = /^-?\d{1,4}(-\d{2}(-\d{2})?)?$/;
export function checkDateString(s) {
  if (!s) return [{level: "error", msg: "Date is required."}];
  if (!DATE_RE.test(s)) return [{level: "error", msg: "Date format is YYYY, YYYY-MM, YYYY-MM-DD, or -YYYY for BCE."}];
  return [];
}

export function parseYear(s) {
  if (typeof s === "number") return s;
  if (!s) return null;
  if (s.startsWith("-")) {
    const parts = s.split("-");
    if (parts.length === 1) return parseInt(s, 10);
    return -parseInt(parts[1], 10);
  }
  return parseInt(s.split("-")[0], 10);
}

export function checkLatLon(lat, lon, country) {
  const out = [];
  if (lat == null || lat === "") out.push({level: "error", msg: "Latitude is required."});
  else if (lat < -90 || lat > 90) out.push({level: "error", msg: `Latitude ${lat} is out of range (-90 to 90).`});
  if (lon == null || lon === "") out.push({level: "error", msg: "Longitude is required."});
  else if (lon < -180 || lon > 180) out.push({level: "error", msg: `Longitude ${lon} is out of range (-180 to 180).`});
  // BBOX check on point 0 only
  if (lat != null && lon != null && country && country !== "OFF") {
    if (lat < BBOX[0] || lat > BBOX[1] || lon < BBOX[2] || lon > BBOX[3]) {
      out.push({level: "error", msg: `Coordinates (${lat}, ${lon}) fall outside the asset's bounding box. Set country to "OFF" if intentional, or check for a typo.`});
    }
  }
  return out;
}

export function checkVocab(value, allowed, label) {
  if (!value) return [{level: "error", msg: `${label} is required.`}];
  if (!allowed.includes(value)) return [{level: "error", msg: `${label} "${value}" is not a recognised value.`}];
  return [];
}

/* ----------------------------------------------------------------------
   Whole-event validation — collects field-level results into a single
   {ok, errors, warnings} report.
   ---------------------------------------------------------------------- */

export function validateEvent(ev) {
  const errors = [];
  const warnings = [];
  const collect = (results) => {
    for (const r of results) (r.level === "error" ? errors : warnings).push(r.msg);
  };

  collect(checkId(ev.id));
  collect(checkTitle(ev.title));
  collect(checkTooltip(ev.tooltip));
  collect(checkSummary(ev.summary));
  collect(checkDetail(ev.detail));

  if (!ev.date) errors.push("Date object is required.");
  else {
    collect(checkDateString(ev.date.start));
    collect(checkDateString(ev.date.end));
    if (ev.date.start && ev.date.end) {
      const ys = parseYear(ev.date.start), ye = parseYear(ev.date.end);
      if (ys != null && ye != null && ys > ye) errors.push(`Start year ${ys} is after end year ${ye}.`);
    }
    collect(checkVocab(ev.date.precision, PRECISIONS, "date.precision"));
    if (ev.date.approximate == null) errors.push("Approximate flag (true/false) required.");
    if (!ev.date.display) errors.push("Display string for the date is required.");
  }

  if (!ev.location) errors.push("Location object is required.");
  else {
    collect(checkVocab(ev.location.type, LOCATION_TYPES, "location.type"));
    if (!ev.location.name) errors.push("Location name is required.");
    collect(checkVocab(ev.location.country, COUNTRIES, "location.country"));
    const pts = ev.location.points || [];
    if (pts.length === 0) errors.push("At least one point (lat/lon) is required.");
    pts.forEach((p, i) => {
      if (i === 0) collect(checkLatLon(p.lat, p.lon, ev.location.country));
      else collect(checkLatLon(p.lat, p.lon, null));
    });
    if (ev.location.type === "route" && pts.length < 2) {
      errors.push("Route locations need at least 2 points.");
    }
  }

  collect(checkVocab(ev.era, ERAS, "era"));

  if (!Array.isArray(ev.category) || ev.category.length === 0) {
    errors.push("At least one category is required.");
  } else {
    ev.category.forEach(c => collect(checkVocab(c, CATEGORIES, "category")));
  }

  const links = ev.links || [];
  if (links.length === 0 || !links.some(l => l.type === "wikipedia")) {
    errors.push("A Wikipedia link (type='wikipedia') is required.");
  }
  links.forEach((l, i) => {
    if (!l.url) errors.push(`Link ${i + 1} is missing the URL.`);
    if (!LINK_TYPES.includes(l.type)) errors.push(`Link ${i + 1} type "${l.type}" is not recognised.`);
  });

  if (typeof ev.verified !== "boolean") errors.push("Verified flag (true/false) is required.");

  return {ok: errors.length === 0, errors, warnings};
}

export function validateThread(t) {
  const errors = [];
  const warnings = [];
  const collect = (results) => {
    for (const r of results) (r.level === "error" ? errors : warnings).push(r.msg);
  };

  collect(checkId(t.id));
  if (!t.title) errors.push("Title is required.");
  if (!t.summary) errors.push("Summary is required.");
  collect(checkVocab(t.kind, THREAD_KINDS, "kind"));

  const eras = t.era_span || [];
  if (!Array.isArray(eras) || eras.length === 0) {
    errors.push("Era span must include at least one era.");
  } else {
    eras.forEach(e => {
      if (!ERAS.includes(e)) errors.push(`Era span value "${e}" is not a recognised era.`);
    });
  }

  const ds = t.date_span || {};
  if (!ds.start || !ds.end) errors.push("Date span (start, end) is required.");

  const steps = t.steps || [];
  if (steps.length < 3) errors.push(`Thread has only ${steps.length} steps; minimum is 3.`);
  if (steps.length > 12) warnings.push(`Thread has ${steps.length} steps; consider splitting (>10 is heavy).`);

  steps.forEach((s, i) => {
    if (!s.event_id) errors.push(`Step ${i + 1}: event_id is required.`);
    if (!s.note) errors.push(`Step ${i + 1}: note is required.`);
    const isLast = i === steps.length - 1;
    if (isLast && s.transition) errors.push("Final step's transition must be empty (it has no next step).");
    if (!isLast && !s.transition) errors.push(`Step ${i + 1}: transition is required (the bridge to the next step).`);
  });

  if (!t.coda) errors.push("Coda (closing argument) is required.");
  else {
    const w = t.coda.trim().split(/\s+/).length;
    if (w < 20) warnings.push(`Coda is ${w} words (<20 — feels truncated).`);
    if (w > 150) warnings.push(`Coda is ${w} words (>150 — consider trimming).`);
  }

  if (typeof t.verified !== "boolean") errors.push("Verified flag (true/false) is required.");

  return {ok: errors.length === 0, errors, warnings};
}

export function validatePerson(person) {
  const errors = [];
  const warnings = [];
  const collect = (results) => {
    for (const r of results) (r.level === "error" ? errors : warnings).push(r.msg);
  };

  collect(checkId(person.id));
  if (!person.name) errors.push("Name is required.");
  collect(checkTooltip(person.tooltip));
  collect(checkSummary(person.summary));
  collect(checkVocab(person.era, ERAS, "era"));

  const ls = person.lifespan || {};
  if (!ls.born) errors.push("Birth date (lifespan.born) is required.");
  else collect(checkDateString(ls.born));
  if (ls.died != null) collect(checkDateString(ls.died));

  ["birthplace", "deathplace"].forEach(label => {
    const p = ls[label];
    if (label === "deathplace" && ls.died == null) return;
    if (!p) {
      errors.push(`Lifespan ${label} is required.`);
      return;
    }
    if (!p.name) errors.push(`Lifespan ${label}: name required.`);
    collect(checkVocab(p.country, COUNTRIES, `lifespan.${label}.country`));
    collect(checkLatLon(p.lat, p.lon, p.country));
  });

  const links = person.links || [];
  if (!links.some(l => l.type === "wikipedia")) {
    errors.push("A Wikipedia link (type='wikipedia') is required.");
  }

  const track = person.track || [];
  if (track.length === 0) errors.push("Track must have at least one step.");

  const momentIds = new Set();
  let prevYear = null;
  track.forEach((step, i) => {
    const sloc = `Step ${i + 1}`;
    collect(checkVocab(step.kind, STEP_KINDS, `${sloc}.kind`));
    if (step.kind === "event-ref") {
      if (!step.event_id) errors.push(`${sloc}: event_id is required.`);
      if (!step.role) errors.push(`${sloc}: role is required (the person's specific part in this event).`);
    } else if (step.kind === "moment") {
      collect(checkId(step.id));
      if (step.id) {
        if (momentIds.has(step.id)) errors.push(`${sloc}: moment id "${step.id}" is duplicated within this person's track.`);
        momentIds.add(step.id);
      }
      collect(checkTooltip(step.tooltip));
      collect(checkSummary(step.summary));
      const d = step.date || {};
      collect(checkDateString(d.start));
      collect(checkDateString(d.end));
      if (!d.precision) errors.push(`${sloc}: date.precision is required.`);
      if (d.approximate == null) errors.push(`${sloc}: date.approximate (true/false) is required.`);
      if (!d.display) errors.push(`${sloc}: date display string is required.`);
      const loc = step.location || {};
      if (!loc.name) errors.push(`${sloc}: location.name is required.`);
      collect(checkVocab(loc.country, COUNTRIES, `${sloc}.location.country`));
      const pts = loc.points || [];
      if (pts.length === 0) errors.push(`${sloc}: at least one point (lat/lon) is required.`);
      else collect(checkLatLon(pts[0].lat, pts[0].lon, loc.country));
      const y = parseYear(d.start);
      if (y != null && prevYear != null && y < prevYear) {
        errors.push(`${sloc}: year ${y} is before previous step's year ${prevYear}. Track must be chronological.`);
      }
      if (y != null) prevYear = y;
    }
  });

  if (typeof person.verified !== "boolean") errors.push("Verified flag (true/false) is required.");

  return {ok: errors.length === 0, errors, warnings};
}
