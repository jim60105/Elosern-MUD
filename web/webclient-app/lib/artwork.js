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

// The ordered image candidates of one descriptor, faults excluded.
export function artworkCandidates(artwork) {
  const attempts = Array.isArray(artwork?.attempts) ? artwork.attempts : [];
  return attempts
    .filter((entry) => entry?.type === "image" && entry.resource)
    .slice()
    .sort((left, right) => (left.rank ?? 0) - (right.rank ?? 0));
}

// The descriptor's exact original: its highest-ranked image candidate, or null
// for a row that carries a named fault (or nothing at all) instead.
export function artworkCandidate(artwork) {
  return artworkCandidates(artwork)[0]?.resource ?? null;
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
