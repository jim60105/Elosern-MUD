// The travel log group of the composed Elosern store (OpenSpec change
// wilderness-travel-log-ui; interface design §9): the typed, chronological
// travel band entries, published as `view.travel.entries`.
//
// - Entries come only from the committed `travel_log` panel: server-identified
//   notices with server-rendered text. Nothing here reads room prose or
//   decides importance.
// - Each newly seen notice is appended once, in order, and its text is
//   written once to the full log through the ordinary narrative append. The
//   seen-id set lives as long as the full log (the store), so a replayed
//   batch — a later snapshot, a reconnect or a new epoch — never writes a
//   second full-log line.
// - The retained list is bounded (128) and belongs to one `generation|epoch`
//   session; it retires with that session. A replay after the retirement may
//   list a notice again, never append it to the full log again.
// - A recognized non-success `explore.move` result during travel adds one
//   local refusal entry keyed by its request id (`appendTravelRefusal`), with
//   the committed server time and the server's message. The recognized-result
//   handler stays the single full-log owner of that line.
// - A never-seen `landmark_reached` notice is handed to the travel store's
//   arrival slot (`noteTravelArrival`, wilderness-travel-route-ui).

import { travelSelection } from "../../components/travel/travel-model.js";

export const MAX_TRAVEL_LOG_ENTRIES = 128;
// The seen-id memory: far above one retained list plus one replay batch.
export const MAX_TRAVEL_LOG_SEEN = 1024;

export function applyTravelLog(ctx) {
  let session = null;
  let entries = [];
  let lastPanel = null;
  let published = Object.freeze([]);
  const seen = new Set();
  const seenOrder = [];

  function remember(id) {
    if (seen.has(id)) return;
    seen.add(id);
    seenOrder.push(id);
    while (seenOrder.length > MAX_TRAVEL_LOG_SEEN) seen.delete(seenOrder.shift());
  }

  function keyOf(rs) {
    return `${rs.generation}|${rs.activeEpoch}`;
  }

  function push(entry) {
    entries.push(entry);
    while (entries.length > MAX_TRAVEL_LOG_ENTRIES) entries.shift();
    published = Object.freeze(entries.slice());
  }

  function listed(id) {
    return entries.some((entry) => entry.id === id);
  }

  function retire(next) {
    session = next;
    entries = [];
    lastPanel = null;
    published = Object.freeze([]);
  }

  function freezeEntry(raw, local = false) {
    return Object.freeze({
      id: raw.id,
      kind: raw.kind,
      day: raw.day,
      time: raw.time,
      text: raw.text,
      params: Object.freeze({ ...(raw.params || {}) }),
      local,
    });
  }

  /** Adopt the committed `travel_log` panel; runs at the start of every publish. */
  ctx.syncTravelLog = function syncTravelLog(rs) {
    if (!rs || rs.activeEpoch == null) return;
    const key = keyOf(rs);
    if (key !== session) retire(key);
    const panel = rs.panels?.travel_log;
    if (!panel || panel === lastPanel) return;
    lastPanel = panel;
    if (panel.available !== true || !Array.isArray(panel.entries)) return;
    for (const raw of panel.entries) {
      if (listed(raw.id)) continue;
      const fresh = !seen.has(raw.id);
      remember(raw.id);
      const entry = freezeEntry(raw);
      push(entry);
      if (fresh) ctx.appendText("sys", raw.text);
      // A landmark arrival seen for the first time ever is the arrival
      // card's one opener (wilderness-travel-route-ui); a replay never is.
      if (fresh && entry.kind === "landmark_reached") ctx.noteTravelArrival?.(entry, rs);
    }
  };

  /** One local refusal entry for a recognized failed travel step. */
  ctx.appendTravelRefusal = function appendTravelRefusal(requestId, message) {
    const rs = ctx.reducer.getCommittedState();
    if (rs.activeEpoch == null || typeof requestId !== "string" || !requestId) return false;
    const shown = travelSelection({ mode: rs.mode, panels: rs.panels || {}, creation: ctx.creation != null }).layout;
    if (!shown) return false;
    if (keyOf(rs) !== session) retire(keyOf(rs));
    const id = `refusal:${keyOf(rs)}:${requestId}`;
    if (seen.has(id)) return false;
    remember(id);
    const time = rs.serverTime
      ? `${String(rs.serverTime.hour).padStart(2, "0")}:${String(rs.serverTime.minute).padStart(2, "0")}`
      : "";
    // The client has no calendar arithmetic: a local entry joins the day of
    // the newest retained notice (none before the first one).
    const day = entries.length ? entries[entries.length - 1].day : null;
    push(freezeEntry({ id, kind: "refusal", day, time, text: String(message || ""), params: {} }, true));
    return true;
  };

  /** The retained entries, oldest first (a frozen array per change). */
  ctx.travelLogEntries = function travelLogEntries() {
    return published;
  };
}
