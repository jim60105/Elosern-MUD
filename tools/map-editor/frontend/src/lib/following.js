// Continuous file following on the client (frontend design D3 §1.1).
//
// The page shows one `displayed` snapshot; commands are always built against
// it. Every complete workspace the service returns is either adopted at once
// or held:
//
// - another service session (a restart) is held until the explicit
//   "reconnect and read" action: writes resume only after that fresh read,
//   and nothing (permission, drafts, commands) is restored or replayed;
// - an adopted external change is held while the page has an uncommitted
//   field draft, until the explicit "load new version" action, which discards
//   the drafts. Once no draft is left, the held snapshot is adopted silently;
// - everything else (own command results, stale/unavailable status, artifact
//   status) is adopted immediately.
//
// A held snapshot never loosens a guard: a command built against the
// displayed one carries its older revision and fingerprints and is rejected.

export const ADOPT = "adopt";
export const HOLD_DRAFT = "hold-draft";
export const HOLD_RESTART = "hold-restart";

function sequence(workspace) {
  return workspace?.external_change?.sequence ?? 0;
}

export function followDecision({ displayed, incoming, drafts = 0 }) {
  if (!incoming) return ADOPT;
  if (!displayed) return ADOPT;
  if (incoming.session_generation !== displayed.session_generation) return HOLD_RESTART;
  if (drafts > 0 && sequence(incoming) !== sequence(displayed)) return HOLD_DRAFT;
  return ADOPT;
}

// Documents that changed between the displayed and the held snapshot, as the
// service recorded them (only for an external change).
export function changedDocuments(displayed, pending) {
  if (!pending || sequence(pending) === sequence(displayed)) return [];
  return pending.external_change?.documents ?? [];
}

// Keep a selection by qualified identity; report one that no longer exists.
export function preserveSelection(selected, exists) {
  if (!selected) return { selected: null, removed: null };
  return exists(selected) ? { selected, removed: null } : { selected: null, removed: selected };
}
