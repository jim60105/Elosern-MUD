"use strict";

var artwork = require("../artwork.js");
var core = require("../core.js");
// Mirrors world.narrative.authoring's bounded shown-requirement contract: the
// readable planning rows a confirmation may freeze, and the identity of the
// persisted version they were shown at.
var MAX_REQUIREMENTS = 8;
var MAX_REQUIREMENT_TEXT = 200;
var MAX_REQUIREMENT_VERSION = 128;
var REQUIREMENT_KINDS = ["place", "new_character", "private_commission"];
// Mirrors world.narrative.dream_proposal's bounded working proposal and change
// report: the applier refuses anything outside these shapes, so the panel that
// renders them refuses the same values before they can reach the stage.
var MAX_SUMMARY = 2000;
var MAX_LIST_ITEMS = 32;
var MAX_ITEM_TEXT = 200;
var LIST_FIELDS = ["themes", "atmosphere", "participants", "emphasis", "exclusions"];
var PROPOSAL_FIELDS = ["summary"].concat(LIST_FIELDS, ["requirements"]);
var STAGES = ["conversing", "finalized"];
var CHANGE_SUMMARIES = [null, "formed", "changed"];
// The thread's own identifier bound (world.narrative.threads).
var MAX_THREAD_ID = 128;

var codePoints = core.codePoints;

function requireRequirementRow(row, label) {
  core.requireExactFields(row, label, ["kind", "text"], []);
  if (REQUIREMENT_KINDS.indexOf(row.kind) < 0 ||
      typeof row.text !== "string" || !row.text.trim() ||
      codePoints(row.text) > MAX_REQUIREMENT_TEXT) throw new Error("invalid " + label);
}

function requireRequirements(rows, label) {
  if (!Array.isArray(rows) || rows.length > MAX_REQUIREMENTS) throw new Error("invalid " + label);
  rows.forEach(function (row) { requireRequirementRow(row, label); });
}

function requireListItems(items, label) {
  if (!Array.isArray(items) || items.length > MAX_LIST_ITEMS) throw new Error("invalid " + label);
  items.forEach(function (item) {
    if (typeof item !== "string" || !item.trim() || codePoints(item) > MAX_ITEM_TEXT) {
      throw new Error("invalid " + label);
    }
  });
}

function requireProposal(proposal) {
  core.requireExactFields(proposal, "dream proposal", PROPOSAL_FIELDS, []);
  if (typeof proposal.summary !== "string" || codePoints(proposal.summary) > MAX_SUMMARY) {
    throw new Error("invalid dream proposal");
  }
  LIST_FIELDS.forEach(function (field) { requireListItems(proposal[field], "dream proposal list"); });
  requireRequirements(proposal.requirements, "dream requirement");
}

// The change report is one bounded delta of the last settled exchange, so each
// half carries the same list and row bounds the proposal itself obeys.
function requireChangeReport(changes) {
  if (changes === null) return;
  core.requireExactFields(changes, "dream changes", ["summary", "lists", "requirements"], []);
  if (CHANGE_SUMMARIES.indexOf(changes.summary) < 0) throw new Error("invalid dream change summary");
  core.requireExactFields(changes.lists, "dream change lists", LIST_FIELDS, []);
  LIST_FIELDS.forEach(function (field) {
    var entry = changes.lists[field];
    core.requireExactFields(entry, "dream change list", ["added", "removed"], []);
    requireListItems(entry.added, "dream change list");
    requireListItems(entry.removed, "dream change list");
  });
  core.requireExactFields(changes.requirements, "dream change requirements", ["added", "removed"], []);
  requireRequirements(changes.requirements.added, "dream requirement");
  requireRequirements(changes.requirements.removed, "dream requirement");
}

function validateDreamPanel(payload) {
  core.requireExactFields(payload, "dream", ["schema_version", "available", "state"], []);
  if (payload.schema_version !== 4 || payload.available !== true) throw new Error("invalid dream panel");
  var state = payload.state;
  if (state === null) return payload;
  core.requireExactFields(state, "dream state", [
    "session_id", "revision", "completed", "remaining", "can_input", "can_confirm",
    "can_finalize", "can_choose_thread", "can_edit", "can_draft", "can_awaken",
    "pending", "open", "confirmed", "failure", "drafted",
    "opening", "scene", "scene_art", "dialogue", "direction_parts", "thread_choices",
    "draft_preferences", "track", "sleep", "ending", "ending_phase",
    "requirements", "requirement_version", "stage", "proposal", "changes", "thread_id",
  ], []);
  if (typeof state.session_id !== "string" || !state.session_id.length || state.session_id.length > 64) throw new Error("invalid dream identity");
  core.requireInt(state.revision, "dream revision", 1, Number.MAX_SAFE_INTEGER);
  core.requireInt(state.completed, "dream completed", 0, 6);
  core.requireInt(state.remaining, "dream remaining", 0, 6);
  if (state.completed + state.remaining !== 6) throw new Error("invalid dream budget");
  ["can_input", "can_confirm", "can_finalize", "can_choose_thread", "can_edit",
    "can_draft", "can_awaken", "pending", "open", "confirmed", "failure", "drafted"].forEach(function (key) {
    core.requireBool(state[key], key);
  });
  if (STAGES.indexOf(state.stage) < 0) throw new Error("invalid dream stage");
  ["opening", "scene", "dialogue", "ending", "ending_phase"].forEach(function (key) {
    if (typeof state[key] !== "string" || codePoints(state[key]) > 2048) throw new Error("invalid dream prose");
  });
  // The stage decides what a surface may offer, so the flags are checked as one
  // consistent set: free text while conversing, choosing and finalizing only
  // before the conversation stops, editing and confirmation only after it.
  if (state.can_input &&
      (!state.open || state.pending || state.remaining === 0 || state.stage !== "conversing")) {
    throw new Error("invalid dream input choice");
  }
  if ((state.can_finalize || state.can_choose_thread) &&
      (!state.open || state.pending || state.stage !== "conversing")) {
    throw new Error("invalid dream stage choice");
  }
  if ((state.can_edit || state.can_confirm) &&
      (!state.open || state.stage !== "finalized")) {
    throw new Error("invalid dream edit choice");
  }
  // The sixth settled exchange finalizes the session in the same save that
  // records it, so a capped session can never still be conversing.
  if (state.open && state.remaining === 0 && state.stage !== "finalized") {
    throw new Error("invalid dream stage budget");
  }
  // The dream stage's artwork is the SAME canonical scene descriptor every
  // other scene surface carries (mirror of
  // world.art.presenter.describe_dream_scene through
  // web.webclient.presentation.artwork.validate_artwork): the shared validator
  // owns the exact fact shape, the source bounds and the media ceilings, so a
  // retired raw URL string fails the wire instead of being adapted.
  artwork.validateArtwork(state.scene_art);
  if (!Array.isArray(state.direction_parts) || state.direction_parts.length > 2 ||
      state.direction_parts.some(function (part) { return typeof part !== "string" || codePoints(part) > 2000; })) throw new Error("invalid dream direction");
  if (!Array.isArray(state.thread_choices) || state.thread_choices.length > 32) throw new Error("invalid dream thread choices");
  state.thread_choices.forEach(function (thread) {
    core.requireExactFields(thread, "dream thread choice", ["id", "label"], []);
    if (typeof thread.id !== "string" || !thread.id.length || thread.id.length > MAX_THREAD_ID ||
        typeof thread.label !== "string" || !thread.label.trim() || codePoints(thread.label) > 160) throw new Error("invalid dream thread choice");
  });
  if (state.thread_id !== null &&
      (typeof state.thread_id !== "string" || !state.thread_id.length ||
       state.thread_id.length > MAX_THREAD_ID)) throw new Error("invalid dream thread identity");
  requireProposal(state.proposal);
  requireChangeReport(state.changes);
  if (state.draft_preferences !== null && !core.isPlainObject(state.draft_preferences)) throw new Error("invalid draft preferences");
  requireRequirements(state.requirements, "dream requirement");
  // A row set without an identity is a proposal the server has not persisted
  // yet, which is a published shape: only the identity's own shape is checked.
  if (state.requirement_version !== null &&
      (typeof state.requirement_version !== "string" || !state.requirement_version.length ||
       state.requirement_version.length > MAX_REQUIREMENT_VERSION)) throw new Error("invalid dream requirement version");
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
