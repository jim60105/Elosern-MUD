"use strict";

var core = require("../core.js");
function validateDreamPanel(payload) {
  core.requireExactFields(payload, "dream", ["schema_version", "available", "state"], []);
  if (payload.schema_version !== 1 || payload.available !== true) throw new Error("invalid dream panel");
  var state = payload.state;
  if (state === null) return payload;
  core.requireExactFields(state, "dream state", [
    "session_id", "revision", "completed", "remaining", "can_input", "can_confirm",
    "can_draft", "can_awaken", "pending", "open", "confirmed", "failure", "opening",
    "scene", "dialogue", "direction_parts", "thread_choices", "draft_preferences", "track", "sleep", "ending", "ending_phase",
  ], []);
  if (typeof state.session_id !== "string" || !state.session_id.length || state.session_id.length > 64) throw new Error("invalid dream identity");
  core.requireInt(state.revision, "dream revision", 1, Number.MAX_SAFE_INTEGER);
  core.requireInt(state.completed, "dream completed", 0, 6);
  core.requireInt(state.remaining, "dream remaining", 0, 6);
  if (state.completed + state.remaining !== 6) throw new Error("invalid dream budget");
  ["can_input", "can_confirm", "can_draft", "can_awaken", "pending", "open", "confirmed", "failure"].forEach(function (key) {
    core.requireBool(state[key], key);
  });
  if (state.can_input && (!state.open || state.pending || state.remaining === 0)) throw new Error("invalid dream input choice");
  ["opening", "scene", "dialogue", "ending", "ending_phase"].forEach(function (key) {
    if (typeof state[key] !== "string" || Array.from(state[key]).length > 2048) throw new Error("invalid dream prose");
  });
  if (!Array.isArray(state.direction_parts) || state.direction_parts.length > 2 ||
      state.direction_parts.some(function (part) { return typeof part !== "string" || Array.from(part).length > 2000; })) throw new Error("invalid dream direction");
  if (!Array.isArray(state.thread_choices) || state.thread_choices.length > 32 ||
      state.thread_choices.some(function (thread) { return typeof thread !== "string" || !thread.length || thread.length > 128; })) throw new Error("invalid dream thread choices");
  if (state.draft_preferences !== null && !core.isPlainObject(state.draft_preferences)) throw new Error("invalid draft preferences");
  core.requireExactFields(state.track, "dream track", ["version", "completed", "pleasure", "level", "ordinal", "climax_phase", "converging"], []);
  core.requireInt(state.track.version, "track version", 1, Number.MAX_SAFE_INTEGER);
  core.requireInt(state.track.completed, "track count", 0, 6);
  core.requireInt(state.track.pleasure, "track pleasure", 0, 100);
  core.requireInt(state.track.ordinal, "track ordinal", 0, 4);
  core.requireBool(state.track.converging, "converging");
  if (state.track.completed !== state.completed || typeof state.track.level !== "string" || typeof state.track.climax_phase !== "string") throw new Error("invalid dream track");
  core.requireExactFields(state.sleep, "dream sleep", ["tick_from", "tick_to", "requested_seconds", "seconds", "event_kinds"], []);
  ["tick_from", "tick_to", "requested_seconds", "seconds"].forEach(function (key) {
    core.requireInt(state.sleep[key], key, 0, Number.MAX_SAFE_INTEGER);
  });
  if (state.sleep.tick_to - state.sleep.tick_from !== state.sleep.seconds ||
      !Array.isArray(state.sleep.event_kinds) ||
      state.sleep.event_kinds.some(function (kind) { return typeof kind !== "string" || kind.length > 64; })) throw new Error("invalid sleep result");
  return payload;
}
module.exports = { validateDreamPanel: validateDreamPanel };
