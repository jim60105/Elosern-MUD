// The shared helpers and constants of the composed Elosern store
// (webclient-vue-07-wire-store split): module-level pure functions and
// frozen vocabulary extracted verbatim from the original single-file store.
// Every group module imports from here; the facade re-exports
// `resolveLocationLabel` (its public seam consumed by stores/store_slices
// tests via `stores/elosern.js`).

export const NARRATIVE_KINDS = ["in", "out", "sys", "err"];
export const MAX_NARRATIVE_LINES = 500;
// The one stable fallback line for a recognized non-success action result
// that carries no usable server message (webclient-action-result-feedback
// D-D). The protocol validator guarantees a 1..512 code point message, so
// this exists only for malformed-edge safety and never paraphrases server
// text.
export const ACTION_RESULT_FALLBACK_MESSAGE = "動作未生效，請重試或返回上層。";
// The non-success outcomes (mirrors the protocol OUTCOMES vocabulary); a
// recognized result with one of these speaks once through the narrative
// feed (webclient-action-result-feedback D-A/D-B).
export const NON_SUCCESS_OUTCOMES = ["rejected", "stale", "error"];
export const MAX_COMMAND_HISTORY = 50;
export const NAVIGATION_ITEM_KEYS = new Set(["character", "quests", "inventory", "bag"]);
// The registered production panel allowlist (mirrors the UMD allowlist in
// elosern/protocol.js and web/webclient/presentation/protocol.py).
export const PANEL_ALLOWLIST = [
  "gallery",
  "art",
  "status",
  "context_actions",
  "local_map",
  "party",
  "objectives",
  "services",
  "creation",
  "exploration",
  "character",
  "lineage",
  "dialogue",
  "title_ballot",
  "title_codex",
  "roster",
  "possession_banner",
  "lore_codex",
  "quest_log",
];

// D5 (webclient-minimap-04-island-single-affordance): top-meta locationLabel
// fallback resolution:
// 1. local_map panel's current node label (when available, carries
//    current_node, matches a node, and has non-empty string label)
// 2. status panel's actor.location.label
// 3. null (TopBar renders 「位置：--」)
//
// Why the map label wins: the status panel's label is the raw room
// key (「Wilderness」 for every wilderness cell), while the map
// payload's current-node label is the presenter's authored place
// name (the region display name on the wilderness layer). Neither
// payload contract changes: the shell chooses between two labels the
// server already committed at the same revision.
export function resolveLocationLabel(panels) {
  if (!panels) return null;
  const lm = panels.local_map;
  if (lm && lm.available === true && lm.current_node) {
    const node = Array.isArray(lm.nodes)
      ? lm.nodes.find((n) => n.id === lm.current_node)
      : null;
    if (node && typeof node.label === "string" && node.label !== "") {
      return node.label;
    }
  }
  const statusLabel = panels.status?.actor?.location?.label;
  if (typeof statusLabel === "string" && statusLabel !== "") {
    return statusLabel;
  }
  return null;
}

// Display conversion of the committed `server_time` (unit conversion at
// display only, mirroring the B1 TopBar `timeLabel` fixture shape).
export function formatTimeLabel(serverTime) {
  if (!serverTime) {
    return null;
  }
  const hour = String(serverTime.hour).padStart(2, "0");
  const minute = String(serverTime.minute).padStart(2, "0");
  return `${serverTime.season_label} ${serverTime.day_in_season} 日 · ${hour}:${minute}`;
}

// The committed transport phase maps to the ConnectOverlay status slice the
// B1 component accepts (connecting/waiting/offline/ready). `loggedIn` is the
// client-local session state delivered by the evennia.js `logged_in` OOB
// event: a connected socket that has not logged in yet waits for login
// (an anonymous session never receives a snapshot, so the phase alone cannot
// distinguish "snapshot in flight" from "not logged in").
export function connectionStatusFor(connected, loggedIn, phase) {
  if (!connected) {
    return "offline";
  }
  if (!loggedIn || phase === "detached") {
    return "waiting";
  }
  if (phase === "active") {
    return "ready";
  }
  return "connecting";
}

// The defensive panel read (webclient-frontend-utils): the committed panel
// for `key`, or null when the panels map (or the key) is absent. The helper
// returns the raw panel-or-null ONLY — the per-field `available`/type guards
// stay at each read because the predicates genuinely differ (e.g.
// `available === true` for party/objectives/roster vs `available !== false`
// for vitals/exploration).
export function readPanel(rs, key) {
  return (rs.panels && rs.panels[key]) || null;
}

// The focus-frame items from the committed `context_actions` panel: the
// exploration form's affordances (action + navigation entries) or the combat
// form's participants (target entries).
export function focusItemsFor(panel) {
  if (!panel || panel.available !== true) {
    return [];
  }
  if (panel.kind === "exploration") {
    return Array.isArray(panel.affordances) ? panel.affordances : [];
  }
  if (panel.kind === "combat") {
    // Combat participants carry a numeric `identity` and a `display_name`;
    // normalize them to the preserved target-entry shape the B2 dock-items
    // contract expects ({ identity, label, enabled }).
    const participants = Array.isArray(panel.participants) ? panel.participants : [];
    return participants.map((p) => ({
      identity: p.identity == null ? "" : String(p.identity),
      label: p.display_name || p.label || "",
      enabled: p.enabled !== false,
    }));
  }
  return [];
}

// Whether the creation overlay is the presenting surface: the committed
// `creation` panel exists and is not explicitly unavailable — exactly the
// mount predicate `AppClient` uses for `CreationOverlay` (duck finding 1:
// the overlay's presence, not the creation-dock state `creationPanelOf`).
// While it is mounted it renders the action result itself, so the
// narrative feed gains no duplicate line (webclient-action-result-feedback
// D-C).
export function creationOverlayPresenting(rs) {
  const panel = (rs.panels && rs.panels.creation) || null;
  return !!panel && panel.available !== false;
}
