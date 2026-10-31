// Pure projections of the wilderness travel presentation (OpenSpec change
// wilderness-travel-interface). No Vue, no DOM, no rules: every value is read
// from committed panels, and nothing here derives a fatigue stage, a reveal or
// a route.

import { LIGHT_PHASE_NAMES } from "../../lib/area_map_view.js";

/** The committed scene identity `{ subject_id }`, or null when none is admitted. */
export function travelRoom(art) {
  const subject = art && art.available === true ? art.scene?.artwork?.subject_id : null;
  return typeof subject === "string" && subject.length > 0 ? Object.freeze({ subject_id: subject }) : null;
}

/**
 * The travel selection of one committed state.
 *
 * `mode` is true while the committed mode is exploration and the committed
 * scene identity is a wilderness one; there is no server travel mode and no
 * prose, click or cached scene can select it. `layout` additionally requires
 * that no conversation, dream or creation surface owns the stage, so dialogue
 * and the other surfaces keep their own layouts and travel returns when they
 * end.
 */
export function travelSelection({ mode, panels = {}, creation = false }) {
  const room = travelRoom(panels.art);
  const inWilderness = mode === "exploration" && !!room && room.subject_id.startsWith("wilderness:");
  const dialogue = panels.dialogue;
  const conversing = !!dialogue && dialogue.available === true && dialogue.kind === "dialogue";
  const dreaming = panels.dream?.state?.open === true;
  return Object.freeze({
    mode: inWilderness,
    layout: inWilderness && !conversing && !dreaming && !creation,
    room,
  });
}

// The stage keys the medallion styling reads; anything else is shown plainly.
const STAGES = new Set(["normal", "light", "moderate", "severe", "forced_sleep", "sleeping"]);

function fatigueRows(status) {
  return status && status.available !== false && Array.isArray(status.fatigue) ? status.fatigue : [];
}

/**
 * The medallion members in display order.
 *
 * `figures` is the shell's controlled/party identity projection
 * (`companionFigures`: the controlled body first, then the party in its own
 * order, with the owner's body at a possessed companion's slot). The
 * controlled body is always shown, once. Any other figure is present exactly
 * when the committed status carries its own fatigue row, because the server
 * emits one row per source-present traveller; party rows carry no
 * co-location fact of their own. Each member joins its own row by its
 * string-normalized identity; a missing row reads unavailable, never full.
 * `controlledIdentity` (the status actor identity) keys a front figure the
 * roster has not named yet.
 */
export function medallionMembers(figures, status, controlledIdentity = null) {
  const rows = new Map(fatigueRows(status).map((row) => [String(row.identity), row]));
  const seen = new Set();
  const out = [];
  (Array.isArray(figures) ? figures : []).forEach((given, index) => {
    // The controlled front may stand before the roster names it; the status
    // actor identity (the session's controlled figure) then keys its row.
    const figure =
      given && index === 0 && (given.identity === null || given.identity === undefined) && controlledIdentity != null
        ? { ...given, identity: controlledIdentity }
        : given;
    if (!figure || figure.identity === null || figure.identity === undefined) return;
    const key = String(figure.identity);
    const controlled = index === 0 || figure.isControlled === true;
    if (seen.has(key) || (!controlled && !rows.has(key))) return;
    if (controlled && out.some((member) => member.controlled)) return;
    seen.add(key);
    const row = rows.get(key) ?? null;
    out.push(
      Object.freeze({
        key,
        identity: figure.identity,
        name: figure.displayName || row?.name || "",
        artwork: figure.artwork ?? null,
        panel: figure.panel ?? null,
        hasReference: figure.hasReference !== false,
        controlled,
        available: row !== null,
        reserve: row ? row.reserve_percent : null,
        stage: row && STAGES.has(row.stage) ? row.stage : null,
        label: row ? row.label : null,
        asleep: row ? row.asleep === true : false,
      }),
    );
  });
  return out;
}

/** The thresholds the reserve bar notches, in percent (design §8). */
export const RESERVE_NOTCHES = Object.freeze([20, 40, 70]);

/** The medallion's accessible name: name, reserve and the supplied stage label. */
export function medallionLabel(member) {
  if (!member.available) return `${member.name}：精力資料無法取得`;
  return `${member.name}：精力 ${member.reserve}%（${member.label}）`;
}


/**
 * The place card's two lines while the travel layout is shown
 * (wilderness-travel-window-ui; interface design §3): `<district>・<terrain>`
 * from the party cell's own disclosed run, and the server's time line with
 * the supplied light phase. A cell with no disclosed district falls back to
 * the window's caption (the current cell's district, else its region).
 * Null without an adopted grid, so the ordinary labels stay.
 */
export function travelPlace(grid, timeLabel) {
  if (!grid || !grid.party) return null;
  const { x, y } = grid.party;
  const col = x - grid.origin.x;
  const row = y - grid.origin.y;
  const cell = col >= 0 && row >= 0 && col < grid.width && row < grid.height ? grid.cells[row * grid.width + col] : null;
  const district = cell?.display?.district_name ?? grid.districtName ?? null;
  const terrain = cell?.display?.terrain_label ?? null;
  const location = [district, terrain].filter((part) => typeof part === "string" && part !== "").join("・");
  // The supplied phase's word (the phase itself is the server's).
  const phase = LIGHT_PHASE_NAMES[grid.lightPhase] ?? null;
  const time = typeof timeLabel === "string" && timeLabel !== "" ? [timeLabel, phase].filter(Boolean).join("・") : null;
  return Object.freeze({ location: location || null, time });
}
