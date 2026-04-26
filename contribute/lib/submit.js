// submit.js — three submission paths for contributor forms.
//
// 1. Download:   downloads the JSON file the contributor just built.
// 2. Pull request: opens GitHub's create-file URL with the JSON pre-populated.
//                  GitHub auto-forks the repo if the contributor doesn't own
//                  it; they click "Propose new file" and a PR opens.
// 3. Issue:      opens a GitHub new-issue URL with the JSON in the body.
//                For contributors without a GitHub account or for content
//                that needs editorial discussion before it's PR-ready.

const OWNER = "naklitechie";
const REPO  = "india-2500";
const BRANCH = "main";

// kind = 'event' | 'thread' | 'person' | 'collection'
function dataPath(kind) {
  if (kind === "event")      return "data/events";
  if (kind === "thread")     return "data/threads";
  if (kind === "person")     return "data/people";
  if (kind === "collection") return "data/collections";
  throw new Error(`Unknown kind: ${kind}`);
}

function suggestFilename(kind, slug) {
  const safe = (slug || "new").replace(/[^a-z0-9-]/g, "-").replace(/-+/g, "-").replace(/^-|-$/g, "") || "new";
  if (kind === "event")      return `events_${safe}.json`;
  if (kind === "thread")     return `threads_${safe}.json`;
  if (kind === "person")     return `people_${safe}.json`;
  if (kind === "collection") return `collections_${safe}.json`;
}

export function downloadJson(jsonText, filename) {
  const blob = new Blob([jsonText], {type: "application/json;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/* GitHub create-file URL — opens GitHub's web editor with the file
   pre-populated. If the contributor doesn't have write access (typical for
   public contributors), GitHub auto-forks and lands them in their fork.
   Limit: ~2000 char URLs work everywhere; large JSON may hit some browser
   limits but in practice events <50KB encode fine.

   For very large content (a person with a long track, or a multi-event
   batch), the GitHub UI also has a 1MB-ish content limit on the create-file
   form. Falling back to download is the right escape hatch.
*/
export function openPullRequest(jsonText, kind, slug) {
  const filename = suggestFilename(kind, slug);
  const path = dataPath(kind);
  const params = new URLSearchParams({
    filename,
    value: jsonText,
  });
  const url = `https://github.com/${OWNER}/${REPO}/new/${BRANCH}/${path}/?${params.toString()}`;

  if (url.length > 8000) {
    alert(
      "This contribution is too large to send via the GitHub web URL " +
      "(over 8000 characters). Please use Download to save the JSON file, " +
      "then attach it to a pull request manually, or split into smaller files."
    );
    return false;
  }

  window.open(url, "_blank", "noopener");
  return true;
}

/* GitHub issue URL — for contributors without an account or for content
   that needs editorial discussion before it's PR-ready. */
export function openIssue(jsonText, kind, slug) {
  const filename = suggestFilename(kind, slug);
  const path = dataPath(kind);
  const title = `[${kind}] new contribution: ${slug || "(untitled)"}`;
  const body = [
    `**Submitted from the contribute form** for \`${path}/${filename}\`.`,
    ``,
    `Reviewer: please paste the JSON below into the file path above.`,
    ``,
    "```json",
    jsonText,
    "```",
    "",
    "## Sources / context",
    "",
    "<!-- Add at least two independent sources for any verified claim. -->",
    "",
    "1. ",
    "2. ",
  ].join("\n");

  const params = new URLSearchParams({
    title,
    body,
    labels: `contribution,${kind}`,
  });
  const url = `https://github.com/${OWNER}/${REPO}/issues/new?${params.toString()}`;

  if (url.length > 8000) {
    alert(
      "This contribution is too large to embed in a GitHub issue URL " +
      "(over 8000 characters). Please use Download instead, then attach " +
      "the JSON file to a new issue manually."
    );
    return false;
  }

  window.open(url, "_blank", "noopener");
  return true;
}

export function suggestFilenameFor(kind, slug) {
  return suggestFilename(kind, slug);
}
