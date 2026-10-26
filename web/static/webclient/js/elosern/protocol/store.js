"use strict";

// The transport-generation reducer (split verbatim from protocol.js).

var C = require("./constants.js");
var core = require("./core.js");
var envelope = require("./envelope.js");
var mapPanels = require("./panels/map_panels.js");
var mapParts = require("./map_parts.js");
var publicationParts = require("./publication_parts.js");

var canonicalJson = core.canonicalJson;
var checkEnvelope = core.checkEnvelope;
var createRetiredEpochSet = core.createRetiredEpochSet;
var MESSAGE_NAMES = C.MESSAGE_NAMES;
var validateSnapshot = envelope.validateSnapshot;
var validateUpdate = envelope.validateUpdate;
var validateActionResult = envelope.validateActionResult;
var validateProtocolError = envelope.validateProtocolError;
var validateAssembledPresentation = envelope.validateAssembledPresentation;

function createStore(options) {
options = options || {};
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
var mapPublications = {};
var assembler = mapParts.createMapAssembler();
// General publication assembly (webclient-publication-assembly): one bounded
// transfer independent of the specialized map assembler above.
// Bounded complete recovery (webclient-sync-recovery): one episode per
// transport generation. "needed" is one recorded failure awaiting the single
// automatic request, "requested" is that request in flight, "failed" is a
// terminal episode (the one attempt did not land); nothing but a valid
// complete snapshot, an explicit player attempt or a new generation moves a
// failed episode again.
var recovery = { status: "idle", cause: null, generation: 0, targetRevision: null };
var publicationAssembler = createPublicationAssembler();
var retired = createRetiredEpochSet();
var mutationsLocked = true;
var protocolError = null;
var lastActionResult = null;
var listeners = [];
var connected = false;

function createPublicationAssembler() {
  var capturedGeneration = generation;
  return publicationParts.createPublicationAssembler({
    now: options.now,
    setTimer: options.setTimer,
    clearTimer: options.clearTimer,
    onFailure: function (failure) {
      // An old transport's expiry/contradiction callback never touches the
      // live generation's state.
      if (capturedGeneration !== generation) {
        return;
      }
      noteRecovery(failure.reason);
    },
  });
}

// The incompatible-protocol condition is terminal for the sequence: a fresh
// transport generation is the only thing that clears it (beginTransport).
function protocolIncompatible() {
  return !!(
    protocolError &&
    (protocolError.reloadRequired === true ||
      protocolError.code === "unsupported_version")
  );
}

// One failure signal per episode. An idle or already-needed episode records a
// pending repair; a failure that lands while the single repair is requested
// proves that repair did not arrive intact, so the episode becomes terminal
// rather than requesting a second time. A failed episode is never re-armed by
// traffic; `targetRevision` names the revision an unadopted action result
// claimed, so adopting exactly that publication ends the episode.
function noteRecovery(cause, targetRevision) {
  if (recovery.status === "failed") {
    return false;
  }
  if (recovery.status === "requested") {
    enterFailed(cause);
    notify();
    return true;
  }
  recovery = {
    status: "needed",
    cause: cause,
    generation: generation,
    targetRevision: typeof targetRevision === "number" ? targetRevision : null,
  };
  mutationsLocked = true;
  notify();
  return true;
}

// A terminal episode keeps everything the sequence already committed and the
// graphical mutations locked; only the timers/buffers of an abandoned repair
// are released by the caller that knows the repair itself failed.
function enterFailed(cause) {
  recovery = {
    status: "failed",
    cause: cause,
    generation: generation,
    targetRevision: null,
  };
  mutationsLocked = true;
}

// The app's single sender/timeout owner turns a recorded need into exactly one
// request. `explicit` is the player's own synchronize intent, which may spend
// one further attempt after a failed automatic repair.
function markRecoveryRequested(explicit) {
  if (protocolIncompatible()) {
    return false;
  }
  if (
    recovery.status !== "needed" &&
    !(explicit && recovery.status === "failed")
  ) {
    return false;
  }
  recovery = {
    status: "requested",
    cause: recovery.cause,
    generation: generation,
    targetRevision: recovery.targetRevision,
  };
  mutationsLocked = true;
  notify();
  return true;
}

// A repair response that cannot arrive any more (its bounded response deadline
// expired) ends the episode and releases the abandoned transfer's timer and
// buffers, so a late part can never resurrect it.
function failRecovery(cause) {
  if (recovery.status !== "requested") {
    return false;
  }
  enterFailed(cause || recovery.cause);
  assembler.clear();
  publicationAssembler.clear();
  notify();
  return true;
}

// Re-arm the single request permission without adopting anything: a requested
// repair returns to "needed", so the episode (and its mutation lock) survives.
// A failed episode is never re-armed; a fresh generation or the player's own
// explicit attempt are its only exits.
function resetRecoveryEpisode() {
  if (recovery.status !== "requested") {
    return false;
  }
  recovery = {
    status: "needed",
    cause: recovery.cause,
    generation: generation,
    targetRevision: recovery.targetRevision,
  };
  notify();
  return true;
}

// A committed publication ends a pending episode when it is a valid complete
// snapshot, or when it adopts exactly the revision an unadopted action result
// claimed (the missed publication arrived after all). A failed episode is
// terminal only for further *requests*: the repair that finally lands still
// clears it.
function settleRecovery(isSnapshot, committedRevision) {
  if (recovery.status === "idle") {
    return;
  }
  if (
    isSnapshot ||
    (recovery.targetRevision !== null && committedRevision >= recovery.targetRevision)
  ) {
    recovery = { status: "idle", cause: null, generation: generation, targetRevision: null };
  }
}

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
    mapPublications: Object.assign({}, mapPublications),
    recovery: {
      status: recovery.status,
      cause: recovery.cause,
      generation: recovery.generation,
      targetRevision: recovery.targetRevision,
    },
    protocolIncompatible: protocolIncompatible(),
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

// Stage the eager panel map a presentation would commit, without touching the
// committed state. An update keeps every unchanged committed panel, applies the
// explicit removals, then replaces the named panels completely; a snapshot
// keeps nothing. Every retained and staged value is cloned, so a rejected or
// accepted presentation never aliases transport data or committed state.
function stagePanels(meta, isSnapshot) {
  var staged = {};
  if (!isSnapshot) {
    Object.keys(panels).forEach(function (name) {
      staged[name] = JSON.parse(canonicalJson(panels[name]));
    });
    meta.removedPanels.forEach(function (name) {
      delete staged[name];
    });
  }
  Object.keys(meta.panels).forEach(function (name) {
    if (Object.prototype.hasOwnProperty.call(mapPanels.MAP_PANEL_SCHEMAS, name)) {
      return;
    }
    staged[name] = JSON.parse(canonicalJson(meta.panels[name]));
  });
  return staged;
}

// A committed dialogue mode must always pair with a committed dialogue panel.
// The server re-renders dialogue as a candidate on every publication and may
// omit it when unchanged; the receiver therefore validates the relationship
// against the STAGED state rather than requiring the panel on every delta.
function dialogueConsistent(meta, staged) {
  if (meta.mode !== "dialogue") {
    return true;
  }
  return Object.prototype.hasOwnProperty.call(staged, "dialogue");
}

function commitPresentation(meta, isSnapshot, staged) {
  activeEpoch = meta.epoch;
  revision = meta.revision;
  mode = meta.mode;
  layoutVersion = meta.layoutVersion;
  serverTime = meta.serverTime;
  // A full snapshot replaces the complete eager store atomically, including
  // panels omitted from the new payload. An update replaces only the named
  // panels, each completely, never merges nested fields, and deletes exactly
  // the explicitly removed eager names. Map panels land in their separate
  // on-demand slot; a snapshot never names them, so same-epoch maps survive it.
  panels = staged;
  Object.keys(meta.panels).forEach(function (name) {
    if (!Object.prototype.hasOwnProperty.call(mapPanels.MAP_PANEL_SCHEMAS, name)) {
      return;
    }
    maps[name] = JSON.parse(canonicalJson(meta.panels[name]));
    mapPublications[name] = meta.revision;
  });
  // An unfinished transfer at or below the committed revision can never be
  // adopted any more; free it now.
  assembler.pruneThrough(meta.revision);
  publicationAssembler.pruneThrough(meta.revision);
  phase = "active";
  // A valid complete snapshot repairs the whole eager store, so it ends a
  // pending episode; a delta normally neither clears nor bypasses one, except
  // when it adopts exactly the publication an unadopted result claimed.
  settleRecovery(isSnapshot, meta.revision);
  // A reload-required (incompatible) protocol error keeps the graphical
  // controls locked even while ordinary presentations keep committing;
  // only a fresh transport generation (beginTransport) clears the error.
  // Outstanding recovery keeps them locked too, even while an unrelated
  // delta commits.
  mutationsLocked = protocolIncompatible() || recovery.status !== "idle";
  notify();
}

// Stage, validate the staged dialogue relationship and commit one admitted
// candidate. One shared path for intact frames and completed assemblies.
function commitCandidate(meta, messageName) {
  var isSnapshot = messageName === "ui_snapshot";
  var staged = stagePanels(meta, isSnapshot);
  if (!dialogueConsistent(meta, staged)) {
    return {
      accepted: false,
      reason: "invalid",
      detail: "dialogue mode requires a committed dialogue panel",
    };
  }
  commitPresentation(meta, isSnapshot, staged);
  return { accepted: true, revision: meta.revision };
}

// Establish initial state (or re-establish after detachment) from one
// complete validated snapshot. Only a snapshot may establish: the on-demand
// store starts empty and any provisional assembly from another epoch is
// released before the single commit.
function establishSnapshot(meta) {
  var staged = stagePanels(meta, true);
  if (!dialogueConsistent(meta, staged)) {
    return {
      accepted: false,
      reason: "invalid",
      detail: "dialogue mode requires a committed dialogue panel",
    };
  }
  maps = {};
  mapPublications = {};
  assembler.clear();
  publicationAssembler.clear();
  commitPresentation(meta, true, staged);
  return { accepted: true, established: true, revision: meta.revision };
}

// One ui_publication_part frame: validate the exact wire shape, admit it for
// the live generation/epoch, assemble invisibly, then validate, admit and
// commit the complete logical publication exactly as its intact form would.
function receivePublicationPart(payload) {
  var inspected;
  try {
    inspected = publicationParts.inspectPublicationPart(payload);
  } catch (error) {
    // A frame whose own epoch identity is obsolete or foreign never disturbs
    // the live generation: reject it inertly instead of attributing the
    // corruption to the active epoch.
    var epochHint =
      payload !== null && typeof payload === "object" && typeof payload.presentation_epoch === "string"
        ? payload.presentation_epoch
        : null;
    var revisionHint =
      payload !== null &&
      typeof payload === "object" &&
      typeof payload.revision === "number" &&
      Number.isInteger(payload.revision)
        ? payload.revision
        : null;
    if (epochHint !== null) {
      if (retired.has(epochHint)) {
        return { accepted: false, reason: "retired_epoch" };
      }
      if (phase === "active" && epochHint !== activeEpoch) {
        return { accepted: false, reason: "different_epoch" };
      }
      if (phase === "detached" && epochHint === activeEpoch) {
        return { accepted: false, reason: "different_epoch" };
      }
    }
    // An obsolete target stays an ordinary stale discard even when its chunks
    // are corrupt: it must never disturb newer in-flight work or start
    // recovery.
    if (phase === "active" && revisionHint !== null && revisionHint <= revision) {
      publicationAssembler.pruneThrough(revision);
      return { accepted: false, reason: "not_newer" };
    }
    // Otherwise the corrupt transfer cannot be identified: discard the live
    // assembly and record one recovery need.
    publicationAssembler.clear();
    noteRecovery("invalid");
    return {
      accepted: false,
      reason: "invalid",
      detail: error.message,
      recovery: "needed",
    };
  }

  var header = inspected.header;
  if (retired.has(header.epoch)) {
    return { accepted: false, reason: "retired_epoch" };
  }
  if (phase === "active") {
    if (header.epoch !== activeEpoch) {
      return { accepted: false, reason: "different_epoch" };
    }
  } else {
    // A delta can never establish initial state (nor re-establish a
    // detached store). A detached store accepts only a genuinely fresh epoch.
    if (header.kind === "delta") {
      return { accepted: false, reason: "update_cannot_establish_epoch" };
    }
    if (phase === "detached" && header.epoch === activeEpoch) {
      return { accepted: false, reason: "different_epoch" };
    }
  }

  // A trustworthy but obsolete header is rejected before its chunks are even
  // decoded, so a corrupted replay can never destroy newer work.
  if (phase === "active" && header.revision <= revision) {
    publicationAssembler.pruneThrough(revision);
    return { accepted: false, reason: "not_newer" };
  }

  var decoded;
  try {
    decoded = publicationParts.decodePublicationPartChunks(header, inspected.chunks);
  } catch (error) {
    // The epoch admitted this frame, so the corruption belongs to the live
    // sequence: discard the in-flight transfer and record one recovery need.
    publicationAssembler.clear();
    noteRecovery("invalid");
    return {
      accepted: false,
      reason: "invalid",
      detail: error.message,
      recovery: "needed",
    };
  }

  var outcome = publicationAssembler.accept(header, decoded, {
    phase: phase,
    committedRevision: revision,
  });
  if (outcome.status === "pending") {
    // A partial publication is invisible: no listener, revision, mutation
    // gate or recovery signal changes until the complete logical document
    // validates and commits.
    return { accepted: false, pending: true, revision: header.revision };
  }
  if (outcome.status === "failed") {
    var rejected = { accepted: false, reason: outcome.reason };
    if (outcome.detail) {
      rejected.detail = outcome.detail;
    }
    if (outcome.recover) {
      rejected.recovery = "needed";
    }
    return rejected;
  }

  var meta;
  try {
    meta = validateAssembledPresentation(outcome.kind, outcome.logical);
    if (meta.epoch !== header.epoch || meta.revision !== header.revision) {
      throw new Error("logical metadata disagrees with its part headers");
    }
    if (outcome.kind === "delta" && meta.baseRevision !== header.baseRevision) {
      throw new Error("logical base_revision disagrees with its part headers");
    }
  } catch (error) {
    noteRecovery("invalid");
    return {
      accepted: false,
      reason: "invalid",
      detail: error.message,
      recovery: "needed",
    };
  }

  if (phase === "idle" || phase === "awaiting_initial_snapshot" || phase === "detached") {
    var established = establishSnapshot(meta);
    if (!established.accepted) {
      noteRecovery("invalid");
      established.recovery = "needed";
    }
    return established;
  }
  if (meta.revision <= revision) {
    return { accepted: false, reason: "not_newer" };
  }
  if (outcome.kind === "delta" && meta.baseRevision !== revision) {
    // The exact base is rechecked at final adoption: an intervening commit
    // invalidates the assembled delta.
    noteRecovery("base_mismatch");
    return { accepted: false, reason: "base_mismatch", recovery: "needed" };
  }
  var committed = commitCandidate(
    meta,
    outcome.kind === "snapshot" ? "ui_snapshot" : "ui_update"
  );
  if (!committed.accepted) {
    noteRecovery("invalid");
    committed.recovery = "needed";
  }
  return committed;
}

return {
  getState: cloneState,

  // Diagnostics for the bounded assembly (tests and debugging only).
  mapAssemblyStats: function () {
    return { live: assembler.liveCount(), bytes: assembler.bufferedBytes() };
  },

  // Bounded diagnostics for the general publication assembly (tests and
  // debugging only; never buffered data).
  publicationAssemblyStats: function () {
    return publicationAssembler.stats();
  },

  // Bounded complete recovery (webclient-sync-recovery). `noteRecovery` is the
  // one failure recorder (also called from the reducer's own failure paths and
  // by the app for a result claiming an unadopted revision);
  // `markRecoveryRequested` and `failRecovery` are the app's single
  // sender/timeout owner's transitions. Every one of them reports whether it
  // changed the episode.
  noteRecovery: noteRecovery,
  markRecoveryRequested: markRecoveryRequested,
  failRecovery: failRecovery,
  resetRecoveryEpisode: resetRecoveryEpisode,

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
      // A closed transport will never deliver the missing parts: release both
      // assembly owners and their timers independently of each other.
      assembler.clear();
      publicationAssembler.clear();
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
    mapPublications = {};
    assembler.clear();
    publicationAssembler.clear();
    publicationAssembler = createPublicationAssembler();
    // A new transport generation is a fresh failure episode: the previous
    // episode's state (and its lock) never survives the reconnect.
    recovery = { status: "idle", cause: null, generation: generation, targetRevision: null };
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
      // A transport-corrupted presentation frame of the live sequence: nothing
      // can be admitted from it, so record the one repair episode.
      noteRecovery("missing_envelope");
      return { accepted: false, reason: "missing_envelope" };
    }
    var payload = args[0];

    if (messageName === "ui_publication_part") {
      return receivePublicationPart(payload);
    }

    if (messageName === "ui_snapshot" || messageName === "ui_update") {
      var meta;
      try {
        // An intact world map rides a ui_update under its own scoped frame
        // allowance (transport-world-map-panel); everything else, parts
        // included, keeps the generic envelope bounds.
        if (messageName === "ui_update" && mapPanels.carriesIntactWorldMap(payload)) {
          mapPanels.checkWorldMapEnvelope(payload);
        } else {
          checkEnvelope(payload);
        }
        meta =
          messageName === "ui_snapshot"
            ? validateSnapshot(payload)
            : validateUpdate(payload);
      } catch (error) {
        noteRecovery("invalid");
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
        var established = establishSnapshot(meta);
        if (!established.accepted) {
          noteRecovery("invalid");
          established.recovery = "needed";
        }
        return established;
      }

      // Active: same-epoch, strictly newer revisions only.
      if (meta.epoch !== activeEpoch) {
        return { accepted: false, reason: "different_epoch" };
      }
      if (meta.revision <= revision) {
        return { accepted: false, reason: "not_newer" };
      }
      if (messageName === "ui_update" && publicationAssembler.hasLive()) {
        // A later delta never skips an incomplete general publication: the
        // incomplete transfer is abandoned and one complete sync is
        // requested instead of committing the delta.
        publicationAssembler.clear();
        noteRecovery("incomplete_predecessor");
        return {
          accepted: false,
          reason: "incomplete_predecessor",
          recovery: "needed",
        };
      }
      if (messageName === "ui_update" && meta.baseRevision !== revision) {
        // A delta is admitted only against the exact committed baseline. The
        // rejected publication commits nothing and records one repair episode;
        // its notification carries the lock and the recovery state.
        noteRecovery("base_mismatch");
        return { accepted: false, reason: "base_mismatch" };
      }
      if (meta.part) {
        // One bounded map part: nothing (metadata included) is adopted until
        // the whole transfer decoded and validated. Parts repeat the same
        // exact base and target, so no partial map advances the revision.
        var outcome = assembler.offer(
          meta.part.panel,
          meta.part.header,
          meta.part.bytes,
          meta.revision,
          canonicalJson([
            meta.baseRevision,
            meta.revision,
            meta.mode,
            meta.layoutVersion,
            meta.serverTime,
            // The removal list is part of the one logical envelope: parts
            // with different removals are conflicting, not interchangeable.
            meta.removedPanels.slice().sort(),
          ])
        );
        if (outcome.status === "partial") {
          return { accepted: false, pending: true, revision: meta.revision };
        }
        if (outcome.status !== "complete") {
          return { accepted: false, reason: outcome.reason, detail: outcome.detail };
        }
        var logicalPanels = {};
        logicalPanels[outcome.panel] = outcome.logical;
        meta.panels = logicalPanels;
      }
      // Stage every replacement, removal, and metadata field before one commit
      // and one notification; a rejected stage leaves committed state intact.
      return commitCandidate(meta, messageName);
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
      mapPublications = {};
      assembler.clear();
      publicationAssembler.clear();
      mutationsLocked = true;
    }
    if (
      protocolErrorPayload.code === "unsupported_version" ||
      protocolErrorPayload.reloadRequired
    ) {
      // An incompatible protocol cannot be repaired by a fresh sync: the
      // controls stay locked behind the reload notice, and an outstanding
      // repair attempt ends without a second request.
      mutationsLocked = true;
      failRecovery("incompatible_protocol");
    } else {
      // A recoverable server-side presentation failure: one complete repair
      // (or the terminal failed episode if one is already requested).
      noteRecovery("protocol_error");
    }
    notify();
    return { accepted: true };
  },
};
}

module.exports = {
  createStore: createStore,
};
