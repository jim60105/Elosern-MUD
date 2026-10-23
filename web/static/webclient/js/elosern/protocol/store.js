"use strict";

// The transport-generation reducer (split verbatim from protocol.js).

var C = require("./constants.js");
var core = require("./core.js");
var envelope = require("./envelope.js");
var mapPanels = require("./panels/map_panels.js");
var mapParts = require("./map_parts.js");

var canonicalJson = core.canonicalJson;
var checkEnvelope = core.checkEnvelope;
var createRetiredEpochSet = core.createRetiredEpochSet;
var MESSAGE_NAMES = C.MESSAGE_NAMES;
var validateSnapshot = envelope.validateSnapshot;
var validateUpdate = envelope.validateUpdate;
var validateActionResult = envelope.validateActionResult;
var validateProtocolError = envelope.validateProtocolError;

function createStore() {
var generation = 0;
var phase = "idle"; // idle | awaiting_initial_snapshot | active | detached
var activeEpoch = null;
var revision = null;
var mode = null;
var layoutVersion = null;
var serverTime = null;
var panels = {};
// On-demand map read models (define-map-panel-protocol): kept apart from the
// eager panels, retained across same-epoch snapshots and cleared with the
// epoch. Bounded part transfers assemble invisibly beside them.
var maps = {};
var assembler = mapParts.createMapAssembler();
var retired = createRetiredEpochSet();
var mutationsLocked = true;
var protocolError = null;
var lastActionResult = null;
var listeners = [];
var connected = false;

function cloneState() {
  var panelCopy = {};
  Object.keys(panels).forEach(function (name) {
    panelCopy[name] = JSON.parse(canonicalJson(panels[name]));
  });
  var mapCopy = {};
  Object.keys(maps).forEach(function (name) {
    mapCopy[name] = JSON.parse(canonicalJson(maps[name]));
  });
  return {
    generation: generation,
    phase: phase,
    activeEpoch: activeEpoch,
    revision: revision,
    mode: mode,
    layoutVersion: layoutVersion,
    serverTime: serverTime === null ? null : JSON.parse(canonicalJson(serverTime)),
    panels: panelCopy,
    maps: mapCopy,
    mutationsLocked: mutationsLocked,
    protocolError: protocolError === null ? null : JSON.parse(canonicalJson(protocolError)),
    lastActionResult: lastActionResult === null ? null : JSON.parse(canonicalJson(lastActionResult)),
    retiredEpochCount: retired.size(),
    connected: connected,
  };
}

function notify() {
  var snapshot = cloneState();
  listeners.slice().forEach(function (listener) {
    try {
      listener(snapshot);
    } catch (error) {
      // A broken renderer must never break the reducer.
    }
  });
}

function commitPresentation(meta, isSnapshot) {
  activeEpoch = meta.epoch;
  revision = meta.revision;
  mode = meta.mode;
  layoutVersion = meta.layoutVersion;
  serverTime = meta.serverTime;
  if (isSnapshot) {
    // A full snapshot replaces the complete store atomically, including
    // panels omitted from the new payload.
    panels = {};
  }
  // An update replaces only the named panels, each completely, and never
  // merges nested fields. Map panels land in their separate on-demand slot;
  // a snapshot never names them, so same-epoch maps survive it.
  Object.keys(meta.panels).forEach(function (name) {
    var target = Object.prototype.hasOwnProperty.call(mapPanels.MAP_PANEL_SCHEMAS, name) ? maps : panels;
    target[name] = JSON.parse(canonicalJson(meta.panels[name]));
  });
  // An unfinished transfer at or below the committed revision can never be
  // adopted any more; free it now.
  assembler.pruneThrough(meta.revision);
  phase = "active";
  // A reload-required (incompatible) protocol error keeps the graphical
  // controls locked even while ordinary presentations keep committing;
  // only a fresh transport generation (beginTransport) clears the error
  // and releases the lock.
  mutationsLocked = !!(protocolError && protocolError.reloadRequired);
  notify();
}

return {
  getState: cloneState,

  // Diagnostics for the bounded assembly (tests and debugging only).
  mapAssemblyStats: function () {
    return { live: assembler.liveCount(), bytes: assembler.bufferedBytes() };
  },

  subscribe: function (listener) {
    if (typeof listener !== "function") {
      throw new Error("subscribe requires a listener function");
    }
    listeners.push(listener);
    return function unsubscribe() {
      var index = listeners.indexOf(listener);
      if (index !== -1) {
        listeners.splice(index, 1);
      }
    };
  },

  setConnected: function (value) {
    connected = !!value;
    if (!value) {
      mutationsLocked = true;
    }
    notify();
  },

  // Start a new local transport generation. Retires the formerly active
  // epoch in the bounded set, clears panel state, and enters
  // awaiting_initial_snapshot with mutations locked.
  beginTransport: function (nextGeneration) {
    if (
      typeof nextGeneration !== "number" ||
      !Number.isInteger(nextGeneration) ||
      nextGeneration <= generation
    ) {
      throw new Error("beginTransport requires a strictly increasing generation");
    }
    generation = nextGeneration;
    if (activeEpoch !== null) {
      retired.add(activeEpoch);
    }
    activeEpoch = null;
    revision = null;
    mode = null;
    layoutVersion = null;
    serverTime = null;
    panels = {};
    maps = {};
    assembler.clear();
    phase = "awaiting_initial_snapshot";
    mutationsLocked = true;
    protocolError = null;
    lastActionResult = null;
    notify();
  },

  // Receive one server message. `messageGeneration` is the transport
  // generation captured when the receiver callback was registered; an
  // older receiver generation is discarded before epoch/revision checks.
  receive: function (messageGeneration, messageName, args, kwargs) {
    if (messageGeneration !== generation) {
      return { accepted: false, reason: "stale_generation" };
    }
    if (!Object.prototype.hasOwnProperty.call(MESSAGE_NAMES, messageName)) {
      return { accepted: false, reason: "unknown_message" };
    }
    if (!Array.isArray(args) || args.length < 1) {
      return { accepted: false, reason: "missing_envelope" };
    }
    var payload = args[0];

    if (messageName === "ui_snapshot" || messageName === "ui_update") {
      var meta;
      try {
        checkEnvelope(payload);
        meta =
          messageName === "ui_snapshot"
            ? validateSnapshot(payload)
            : validateUpdate(payload);
      } catch (error) {
        return { accepted: false, reason: "invalid", detail: error.message };
      }

      if (
        phase === "idle" ||
        phase === "awaiting_initial_snapshot" ||
        phase === "detached"
      ) {
        // Only a valid full snapshot with a non-retired epoch may
        // establish (or re-establish after an OOC detachment) active
        // state; updates never do.
        if (messageName !== "ui_snapshot") {
          return { accepted: false, reason: "update_cannot_establish_epoch" };
        }
        if (retired.has(meta.epoch)) {
          return { accepted: false, reason: "retired_epoch" };
        }
        // A detached store re-adopts only a genuinely fresh epoch; a
        // same-epoch snapshot would be a stale survivor of the retired
        // sequence.
        if (phase === "detached" && meta.epoch === activeEpoch) {
          return { accepted: false, reason: "different_epoch" };
        }
        // Establishing a sequence starts from an empty on-demand store.
        maps = {};
        assembler.clear();
        commitPresentation(meta, true);
        return { accepted: true, established: true, revision: meta.revision };
      }

      // Active: same-epoch, strictly newer revisions only.
      if (meta.epoch !== activeEpoch) {
        return { accepted: false, reason: "different_epoch" };
      }
      if (meta.revision <= revision) {
        return { accepted: false, reason: "not_newer" };
      }
      if (meta.part) {
        // One bounded map part: nothing (metadata included) is adopted until
        // the whole transfer decoded and validated.
        var outcome = assembler.offer(
          meta.part.panel,
          meta.part.header,
          meta.part.bytes,
          meta.revision,
          canonicalJson([meta.revision, meta.mode, meta.layoutVersion, meta.serverTime])
        );
        if (outcome.status === "partial") {
          return { accepted: true, partial: true, revision: meta.revision };
        }
        if (outcome.status !== "complete") {
          return { accepted: false, reason: outcome.reason, detail: outcome.detail };
        }
        var logicalPanels = {};
        logicalPanels[outcome.panel] = outcome.logical;
        meta.panels = logicalPanels;
      }
      commitPresentation(meta, messageName === "ui_snapshot");
      return { accepted: true, revision: meta.revision };
    }

    if (messageName === "ui_action_result") {
      var result;
      try {
        checkEnvelope(payload);
        result = validateActionResult(payload);
      } catch (error) {
        return { accepted: false, reason: "invalid", detail: error.message };
      }
      // While detached the pre-detachment epoch stays live so a bounded
      // no-puppet rejection for an in-flight request is still accepted
      // and can release the client's mutation lock.
      if (
        (phase !== "active" && phase !== "detached") ||
        result.epoch !== activeEpoch
      ) {
        return { accepted: false, reason: "different_epoch" };
      }
      lastActionResult = JSON.parse(canonicalJson(result));
      notify();
      return { accepted: true };
    }

    // ui_protocol_error
    var protocolErrorPayload;
    try {
      checkEnvelope(payload);
      protocolErrorPayload = validateProtocolError(payload);
    } catch (error) {
      return { accepted: false, reason: "invalid", detail: error.message };
    }
    protocolError = JSON.parse(canonicalJson(protocolErrorPayload));
    if (protocolErrorPayload.code === "no_puppet") {
      // The puppet detached (OOC): clear character panels, lock
      // mutations, and enter the detached phase. The active epoch is
      // retained so a late no-puppet rejection can still be accepted;
      // only a fresh-epoch snapshot re-establishes active state.
      phase = "detached";
      panels = {};
      maps = {};
      assembler.clear();
      mutationsLocked = true;
    }
    if (
      protocolErrorPayload.code === "unsupported_version" ||
      protocolErrorPayload.reloadRequired
    ) {
      mutationsLocked = true;
    }
    notify();
    return { accepted: true };
  },
};
}

module.exports = {
  createStore: createStore,
};
