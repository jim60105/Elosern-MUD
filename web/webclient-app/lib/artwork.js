// artwork.js — the shared translation from committed panel facts to the load
// contract (change unified-gallery-image-contract).
//
// Two jobs, both read-only and both shared by every descriptor consumer:
//
//   * `artworkAvailability` turns the committed panel and the caller's own
//     required-surface visibility/admission facts into the explicit
//     availability input the shared lifecycle takes. A surface the committed
//     mode does not require, or an available panel with an intentional
//     no-admitted reference, is expected absence; a required panel that is
//     missing, is unavailable (presentation_unavailable /
//     internal_presenter_error) or claims an admitted reference it did not
//     actually carry is a failure. Nothing here ever synthesizes a descriptor:
//     an unavailable panel can never be read as generation progress.
//
//   * the descriptor SELECTORS the gallery surfaces need to present the
//     canonical facts: the highest-ranked image candidate, its geometry and
//     the terminal resource. They read the descriptor; they never select a
//     business subject, never pick a fallback and never mutate the payload.

export const ARTWORK_STATE_READY = "ready";
export const ARTWORK_STATE_EXPECTED_ABSENT = "expected_absent";
export const ARTWORK_STATE_FAILED = "failed";

// The availability input for one descriptor position.
//
// `panel` is the committed panel (any shape with `available`), `required`
// states whether the committed mode asks for this surface at all,
// `hasReference` states whether the committed payload intentionally admits
// exactly one reference for it, and `artwork` is the descriptor that reference
// resolved to (null when the panel claimed one and carried none).
export function artworkAvailability({ panel, required = true, hasReference = true, artwork = null, viewSubjectId = null } = {}) {
  const view = { view_subject_id: viewSubjectId ?? null };
  if (!required) {
    return { state: ARTWORK_STATE_EXPECTED_ABSENT, ...view };
  }
  if (!panel || panel.available !== true) {
    return { state: ARTWORK_STATE_FAILED, ...view };
  }
  if (!hasReference) {
    return { state: ARTWORK_STATE_EXPECTED_ABSENT, ...view };
  }
  if (!artwork) {
    return { state: ARTWORK_STATE_FAILED, ...view };
  }
  return { state: ARTWORK_STATE_READY, ...view };
}

// The ONE ordering rule for a descriptor's exact-original candidates: ranked
// image attempts, faults excluded. Rank decides priority; ties keep declaration
// order (`Array.prototype.sort` is stable), exactly like the shared reducer's
// own canonical order.
function orderedImageAttempts(artwork) {
  const attempts = Array.isArray(artwork?.attempts) ? artwork.attempts : [];
  return attempts
    .filter((entry) => entry?.type === "image" && entry.resource)
    .slice()
    .sort((left, right) => (left.rank ?? 0) - (right.rank ?? 0));
}

// The ordered image candidates of one descriptor, faults excluded.
export function artworkCandidates(artwork) {
  return orderedImageAttempts(artwork).map((entry) => entry.resource);
}

// The descriptor's exact original: its highest-ranked image candidate, or null
// for a row that carries a named fault (or nothing at all) instead.
export function artworkCandidate(artwork) {
  return artworkOriginal(artwork)?.resource ?? null;
}

// The exact original's own attempt entry (its stable source identity plus its
// resource), or null for a descriptor with no image candidate at all.
export function artworkOriginal(artwork) {
  return orderedImageAttempts(artwork)[0] ?? null;
}

// The identity of one exact original: its source layer plus its resource
// identity/version. Two sides of the same fact are compared with it — what the
// LIVE descriptor says its original is (`artworkOriginalIdentity`) and what a
// SUCCESSFUL observation actually decoded (`artworkSelectedIdentity`) — so an
// editor can never authorize a save from an observation of some other original.
//
// The subject id is deliberately not part of it, and neither is the descriptor
// revision: the revision also covers geometry, and the shared lifecycle keeps a
// decoded resource across a geometry-only re-presentation
// (`lib/image-attempts.js`), so a geometry-only revision must not retire a save
// the player can still make. The subject is redundant because a descriptor row's
// own identity is already inside both halves — the source layer names the exact
// card or catalog entry (`gallery.original:<image_id>`, `gallery.official:
// <identity>`) and a runtime resource path embeds its kind directory, subject
// key and image id — while the dispatched payload's subject comes independently
// from the committed panel (`GalleryPanel.send`).
export function artworkOriginalIdentity(artwork) {
  const entry = artworkOriginal(artwork);
  if (!artwork || !entry) {
    return null;
  }
  return [entry.source_id ?? "", entry.resource?.resource_id ?? "", entry.resource?.version ?? ""].join("|");
}

// The same identity as one SUCCESSFUL observation states it. The shared driver's
// selected result carries the source layer it reached and the resource it really
// decoded, so a proof derived from it can never borrow the live descriptor's
// identity: if the editor's descriptor changed while an in-flight element still
// settled, this names the original that actually decoded and the comparison
// refuses it.
export function artworkSelectedIdentity(selected) {
  if (!selected) {
    return null;
  }
  return [selected.sourceId ?? "", selected.resourceId ?? "", selected.version ?? ""].join("|");
}

// The applicable geometry of the descriptor's exact original, or null.
export function artworkGeometry(artwork) {
  return artworkCandidate(artwork)?.geometry ?? null;
}

// The terminal alpha-mask resource's URL, or null when the descriptor carries
// no terminal. Used to tell the silhouette fallback apart from a real original
// without re-deriving source order.
export function artworkTerminalUrl(artwork) {
  const terminal = artwork?.terminal;
  return terminal?.kind === "alpha_mask" ? terminal.resource?.url ?? null : null;
}

// The terminal alpha-mask resource's applicable geometry, or null.
export function artworkTerminalGeometry(artwork) {
  const terminal = artwork?.terminal;
  return terminal?.kind === "alpha_mask" ? terminal.resource?.geometry ?? null : null;
}
