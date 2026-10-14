// scene-artwork.js — the scene surface's retained-display rules (change
// unified-scene-rendering).
//
// The shared loading core (`lib/image-attempts.js` + `composables/useArtwork.js`)
// owns the ordered attempt walk, the reached faults and the exhausted state of
// one descriptor. A scene needs ONE thing on top of that: display content that
// outlives a single resolution — the successful image the player is already
// looking at — and the rules that say whether it may stay on screen.
//
// Everything here is a pure function of the committed descriptor, the core's
// own selected result and the previous retained entry:
//
//   * `authorizedTokens` reads the descriptor's own retention authorizations;
//   * `retainedEntry` validates and refreshes the retained display content;
//   * `displayedScene` picks what is on screen.
//
// No surface may invent a business fact here: the descriptor authorizes a
// source (a `{source_id, token}` pair the backend only emits while that
// source's prior known-good output is still applicable and readable), and the
// subject/generation-subject pair decides whether two resolutions are the same
// scene at all. A scene the backend does not authorize — a different logical
// place, a removed room binding, a revoked source — can therefore never keep
// previous pixels: its retained entry stops being applicable on the very
// commit that changed it.

// One retained display entry: what is on screen while a newer resolution is
// still resolving. Its `rank` is the stable source-layer rank the shared
// contract assigns that source, never an attempt-array index, and its `token`
// is the authorization the backend issued for exactly this content.
function entryFrom({ subjectId, generationSubject, sourceId, token, rank, resource, dimensions }) {
  return {
    subjectId: subjectId ?? null,
    generationSubject: generationSubject ?? null,
    sourceId: sourceId ?? null,
    token: token ?? null,
    rank: typeof rank === "number" ? rank : null,
    resourceId: resource?.resource_id ?? null,
    version: resource?.version ?? null,
    url: resource?.url ?? null,
    geometry: resource?.geometry ?? null,
    dimensions: dimensions ?? null,
  };
}

// The descriptor's retention authorizations as a source_id -> token map.
export function authorizedTokens(descriptor) {
  const tokens = new Map();
  const sources = Array.isArray(descriptor?.retention_sources) ? descriptor.retention_sources : [];
  for (const source of sources) {
    if (!source || typeof source.source_id !== "string" || typeof source.token !== "string") {
      continue;
    }
    tokens.set(source.source_id, source.token);
  }
  return tokens;
}

// Whether the previous retained entry still describes THIS committed scene.
//
// All three facts must hold: the same stable subject identity (the logical
// place), the same generation subject (so a different archetype — or a scene
// that claims no generation at all, like a malformed room — never inherits
// pixels), and an authorization whose token is still issued for that exact
// source. A locally failed resource never keeps its own pixels on screen
// (`failedKey`).
export function applicableRetained(previous, descriptor) {
  if (!previous || !descriptor) {
    return null;
  }
  if (previous.subjectId !== (descriptor.subject_id ?? null)) {
    return null;
  }
  if (previous.generationSubject !== (descriptor.generation_subject ?? null)) {
    return null;
  }
  const token = authorizedTokens(descriptor).get(previous.sourceId);
  if (!token || token !== previous.token) {
    return null;
  }
  return previous;
}

// The next retained entry after one committed descriptor.
//
// The previous entry is validated FIRST against the new descriptor, so a scene
// the backend no longer authorizes (a moved place, a removed binding, a
// revoked source) drops its pixels synchronously. A successful current
// resource then replaces the retained content only when it is genuinely higher
// or equally ranked (a lower-priority healthy fallback never displaces a good
// generated image) and only when its own source is authorized — a source with
// no retention authorization is display-only content the core already owns.
export function retainedEntry(previous, descriptor, selected) {
  const current = applicableRetained(previous, descriptor);
  if (!selected || !selected.url) {
    return current;
  }
  const token = authorizedTokens(descriptor).get(selected.sourceId);
  if (!token) {
    return current;
  }
  if (current && current.rank !== null && selected.rank !== null && selected.rank > current.rank) {
    return current;
  }
  return entryFrom({
    subjectId: descriptor.subject_id ?? null,
    generationSubject: descriptor.generation_subject ?? null,
    sourceId: selected.sourceId,
    token,
    rank: selected.rank,
    resource: selected,
    dimensions: selected.dimensions ?? null,
  });
}

// What the backdrop shows.
//
// A successful current candidate replaces retained content when it is at least
// as high a priority; otherwise the retained content stays while the current
// attempts and their reached faults keep processing (a pending or failed
// regeneration never blanks a good image). With neither, a provisional
// success — this scene's own bundled/terminal background, resolved outside the
// ordered walk — is what a freshly committed place shows while its preferred
// source is still loading. An unavailable panel shows nothing at all: its
// existence cannot be established from the current committed inputs, so no
// previously retained pixel may survive it.
export function displayedScene({ retained, selected, provisional, available = "ready" } = {}) {
  if (available !== "ready") {
    return null;
  }
  const current = selected && selected.url ? selected : null;
  if (current && (!retained || retained.rank === null || current.rank === null || current.rank <= retained.rank)) {
    return { url: current.url, rank: current.rank ?? null, sourceId: current.sourceId ?? null, kind: "current" };
  }
  if (retained?.url) {
    return { url: retained.url, rank: retained.rank, sourceId: retained.sourceId, kind: "retained" };
  }
  if (provisional?.url) {
    return {
      url: provisional.url,
      rank: provisional.rank ?? null,
      sourceId: provisional.sourceId ?? null,
      kind: "provisional",
    };
  }
  return null;
}
