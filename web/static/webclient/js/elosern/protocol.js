/*
 * Elosern WebClient OOB protocol reducer.
 *
 * DOM-independent client-side envelope validation and state reduction. Mirrors
 * the exact version-1 contract owned by `web/webclient/presentation/protocol.py`
 * so the browser enforces the same field sets, global bounds, panel
 * discriminators, epoch/revision ordering, and atomic replacement rules before
 * any renderer observes state.
 *
 * The module has no `document` or `window` access at load time. In the browser
 * it attaches to `window.Elosern.Protocol`; under Node it exports the same API
 * via `module.exports` for the DOM-independent test suite.
 */
(function (root, factory) {
  "use strict";
  if (typeof module !== "undefined" && module.exports) {
    module.exports = factory();
  } else {
    root.Elosern = root.Elosern || {};
    root.Elosern.Protocol = factory();
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  // ---------------------------------------------------------------------------
  // Constants (must stay equal or smaller than the Python protocol table).
  // ---------------------------------------------------------------------------

  var PROTOCOL_VERSION = 1;
  var MAX_SAFE_INTEGER = 9007199254740991;
  var MAX_CANONICAL_JSON_BYTES = 65536;
  var MAX_DEPTH = 8;
  var MAX_FIELDS = 64;
  var MAX_LIST_ITEMS = 128;
  var MAX_STRING_CODE_POINTS = 2048;
  var MAX_PANEL_COUNT = 32;
  var MAX_LAYOUT_VERSION = 65535;
  var MAX_MESSAGE_CODE_POINTS = 512;
  var EPOCH_LENGTH = 22;
  var MAX_RETIRED_EPOCHS = 8;
  var MAX_ACTOR_NAME = 256;
  var MAX_ACTOR_IDENTITY = 64;
  var MAX_LOCATION_LABEL = 256;
  var MAX_CONDITION_COUNT = 32;
  var MAX_CONDITION_LABEL = 128;
  var MAX_MODIFIER_KEYS = 16;

  var MODES = ["creation", "exploration", "combat"];
  var OUTCOMES = ["success", "rejected", "stale", "error"];
  var COMBAT_MODES = ["hostile", "guild_exam"];
  var PROTOCOL_ERROR_CODES = [
    "unsupported_version",
    "presentation_unavailable",
    "internal_error",
    "malformed_envelope",
  ];
  var SEVERITIES = ["beneficial", "informational", "warning", "harmful", "critical"];

  var MESSAGE_NAMES = {
    ui_snapshot: true,
    ui_update: true,
    ui_action_result: true,
    ui_protocol_error: true,
  };

  // The registered production panel allowlist. Each key maps to its exact
  // schema version; unknown panel names reject the whole presentation message.
  var PANEL_ALLOWLIST = { status: 1 };

  var EPOCH_RE = /^[A-Za-z0-9_-]{22}$/;
  var PANEL_NAME_RE = /^[a-z0-9_]{1,64}$/;
  var IDENTIFIER_RE = /^[a-z0-9._]{1,64}$/;
  var REQUEST_ID_RE = /^[A-Za-z0-9:_-]{1,64}$/;
  var CORRELATION_RE = /^[0-9a-f]{32}$/;

  // ---------------------------------------------------------------------------
  // Small value helpers.
  // ---------------------------------------------------------------------------

  // Bounded in-memory set of retired epochs (presentation-only).
  function createRetiredEpochSet() {
    var order = [];
    var members = {};
    return {
      add: function (epoch) {
        if (Object.prototype.hasOwnProperty.call(members, epoch)) {
          return;
        }
        members[epoch] = true;
        order.push(epoch);
        while (order.length > MAX_RETIRED_EPOCHS) {
          var oldest = order.shift();
          delete members[oldest];
        }
      },
      has: function (epoch) {
        return Object.prototype.hasOwnProperty.call(members, epoch);
      },
      clear: function () {
        order = [];
        members = {};
      },
      size: function () {
        return order.length;
      },
    };
  }

  function isPlainObject(value) {
    return (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value)
    );
  }

  // Count Unicode code points (handles surrogate pairs correctly).
  function codePoints(value) {
    if (typeof value !== "string") {
      return 0;
    }
    var count = 0;
    for (var index = 0; index < value.length; index++) {
      var charCode = value.charCodeAt(index);
      if (charCode >= 0xd800 && charCode <= 0xdbff) {
        index += 1;
      }
      count += 1;
    }
    return count;
  }

  // UTF-8 byte length of a string (code points above U+007F take 2-4 bytes).
  function utf8Bytes(value) {
    var bytes = 0;
    for (var index = 0; index < value.length; index++) {
      var charCode = value.charCodeAt(index);
      if (charCode >= 0xd800 && charCode <= 0xdbff) {
        index += 1;
        var high = charCode;
        var low = value.charCodeAt(index);
        var point = (high - 0xd800) * 0x400 + (low - 0xdc00) + 0x10000;
        bytes += point > 0xffff ? 4 : 3;
      } else if (charCode > 0x7ff) {
        bytes += 3;
      } else if (charCode > 0x7f) {
        bytes += 2;
      } else {
        bytes += 1;
      }
    }
    return bytes;
  }

  // Canonical JSON serialization: no whitespace, sorted keys, like the server.
  function canonicalJson(value) {
    if (value === null || typeof value !== "object") {
      return JSON.stringify(value);
    }
    if (Array.isArray(value)) {
      return "[" + value.map(canonicalJson).join(",") + "]";
    }
    var keys = Object.keys(value).sort();
    var parts = [];
    for (var i = 0; i < keys.length; i++) {
      parts.push(
        JSON.stringify(keys[i]) + ":" + canonicalJson(value[keys[i]])
      );
    }
    return "{" + parts.join(",") + "}";
  }

  function jsonByteSize(value) {
    return utf8Bytes(canonicalJson(value));
  }

  // ---------------------------------------------------------------------------
  // Global JSON-safety bound table (mirror of protocol.check_json_safety).
  // ---------------------------------------------------------------------------

  function checkGlobalSafety(value, depth) {
    depth = depth || 0;
    if (depth > MAX_DEPTH) {
      throw new Error("nesting exceeds maximum depth " + MAX_DEPTH);
    }
    if (isPlainObject(value)) {
      var keys = Object.keys(value);
      if (keys.length > MAX_FIELDS) {
        throw new Error("object exceeds maximum of " + MAX_FIELDS + " fields");
      }
      for (var i = 0; i < keys.length; i++) {
        if (codePoints(keys[i]) > MAX_STRING_CODE_POINTS) {
          throw new Error("object key exceeds the maximum string length");
        }
        checkGlobalSafety(value[keys[i]], depth + 1);
      }
    } else if (Array.isArray(value)) {
      if (value.length > MAX_LIST_ITEMS) {
        throw new Error("list exceeds maximum of " + MAX_LIST_ITEMS + " items");
      }
      for (var j = 0; j < value.length; j++) {
        checkGlobalSafety(value[j], depth + 1);
      }
    } else if (typeof value === "number") {
      if (!isFinite(value)) {
        throw new Error("non-finite numbers are forbidden");
      }
      if (Number.isInteger(value)) {
        if (value < 0 || value > MAX_SAFE_INTEGER) {
          throw new Error("integer is outside the JavaScript-safe range");
        }
      }
    } else if (typeof value === "string") {
      if (codePoints(value) > MAX_STRING_CODE_POINTS) {
        throw new Error(
          "string exceeds the maximum of " + MAX_STRING_CODE_POINTS + " code points"
        );
      }
    }
  }

  function checkEnvelope(value) {
    checkGlobalSafety(value);
    if (jsonByteSize(value) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("canonical JSON exceeds " + MAX_CANONICAL_JSON_BYTES + " bytes");
    }
  }

  // ---------------------------------------------------------------------------
  // Exact-field helpers.
  // ---------------------------------------------------------------------------

  function requireExactFields(payload, name, required, optional) {
    if (!isPlainObject(payload)) {
      throw new Error(name + " must be a JSON object");
    }
    var known = {};
    required.forEach(function (field) {
      known[field] = true;
    });
    optional.forEach(function (field) {
      known[field] = true;
    });
    var unknown = Object.keys(payload).filter(function (field) {
      return !known[field];
    });
    if (unknown.length > 0) {
      throw new Error(name + " has unknown fields " + unknown.join(","));
    }
    required.forEach(function (field) {
      if (!Object.prototype.hasOwnProperty.call(payload, field)) {
        throw new Error(name + " is missing required field " + field);
      }
    });
    // Optional fields may be present or absent; the caller enforces the
    // conditional requirement itself.
  }

  function requireInt(value, field, minimum, maximum) {
    if (typeof value !== "number" || !Number.isInteger(value)) {
      throw new Error(field + " must be an integer");
    }
    if (value < minimum || value > maximum || value > MAX_SAFE_INTEGER) {
      throw new Error(field + " must be within " + minimum + ".." + maximum);
    }
    return value;
  }

  function requireBool(value, field) {
    if (typeof value !== "boolean") {
      throw new Error(field + " must be a boolean");
    }
    return value;
  }

  function requireString(value, field, maximum) {
    if (typeof value !== "string") {
      throw new Error(field + " must be a string");
    }
    if (codePoints(value) > maximum) {
      throw new Error(field + " exceeds the maximum of " + maximum + " code points");
    }
    return value;
  }

  function validateEpoch(value) {
    if (typeof value !== "string" || !EPOCH_RE.test(value)) {
      throw new Error(
        "presentation_epoch must be exactly " + EPOCH_LENGTH + " URL-safe ASCII characters"
      );
    }
    return value;
  }

  function validateIdentifier(value, field) {
    if (typeof value !== "string" || !IDENTIFIER_RE.test(value)) {
      throw new Error(
        field + " must be a 1..64 lowercase dotted or underscored identifier"
      );
    }
    return value;
  }

  function validatePanelName(value) {
    if (typeof value !== "string" || !PANEL_NAME_RE.test(value)) {
      throw new Error("panel names must be 1..64 lowercase identifier characters");
    }
    return value;
  }

  function validateRequestId(value) {
    if (typeof value !== "string" || !REQUEST_ID_RE.test(value)) {
      throw new Error(
        "request_id must be 1..64 characters of ASCII letters, digits, colon, underscore, or hyphen"
      );
    }
    return value;
  }

  function validateMessage(value, field) {
    var length = codePoints(value);
    if (length < 1 || length > MAX_MESSAGE_CODE_POINTS) {
      throw new Error(
        field + " must be 1.." + MAX_MESSAGE_CODE_POINTS + " Unicode code points"
      );
    }
    return value;
  }

  function validateCorrelationId(value) {
    if (typeof value !== "string" || !CORRELATION_RE.test(value)) {
      throw new Error(
        "correlation_id must be exactly 32 lowercase hexadecimal characters"
      );
    }
    return value;
  }

  function validateServerTime(value) {
    requireExactFields(
      value,
      "server_time",
      ["year", "season_index", "season_label", "day_in_season", "hour", "minute", "second"],
      []
    );
    requireInt(value.year, "year", 0, MAX_SAFE_INTEGER);
    requireInt(value.season_index, "season_index", 0, 3);
    var seasonLabel = requireString(value.season_label, "season_label", 32);
    if (!seasonLabel.trim()) {
      throw new Error("season_label must be non-empty");
    }
    requireInt(value.day_in_season, "day_in_season", 1, 90);
    requireInt(value.hour, "hour", 0, 23);
    requireInt(value.minute, "minute", 0, 59);
    requireInt(value.second, "second", 0, 59);
    return {
      year: value.year,
      season_index: value.season_index,
      season_label: seasonLabel,
      day_in_season: value.day_in_season,
      hour: value.hour,
      minute: value.minute,
      second: value.second,
    };
  }

  function validateStatusCondition(value) {
    if (!isPlainObject(value)) {
      throw new Error("conditions entries must be JSON objects");
    }
    var hasRemaining = Object.prototype.hasOwnProperty.call(value, "remaining_seconds");
    var hasModifiers = Object.prototype.hasOwnProperty.call(value, "modifiers");
    var conditional = [];
    if (hasRemaining) {
      conditional.push("remaining_seconds");
    }
    if (hasModifiers) {
      conditional.push("modifiers");
    }
    requireExactFields(value, "condition", ["code", "label", "severity"], conditional);
    validateIdentifier(value.code, "condition.code");
    requireString(value.label, "condition.label", MAX_CONDITION_LABEL);
    if (SEVERITIES.indexOf(value.severity) === -1) {
      throw new Error("condition.severity is not a stable severity");
    }
    if (hasRemaining) {
      requireInt(value.remaining_seconds, "condition.remaining_seconds", 0, MAX_SAFE_INTEGER);
    }
    if (hasModifiers) {
      checkGlobalSafety(value.modifiers);
      var modifierKeys = Object.keys(value.modifiers);
      if (modifierKeys.length > MAX_MODIFIER_KEYS) {
        throw new Error(
          "condition.modifiers exceeds the maximum of " + MAX_MODIFIER_KEYS + " keys"
        );
      }
    }
    return value;
  }

  // Exact available status panel v1 schema.
  function validateStatusPanel(payload) {
    if (payload.available === false) {
      requireExactFields(payload, "status panel", ["schema_version", "available", "reason"], []);
      requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
      if (payload.schema_version !== 1) {
        throw new Error("unsupported status panel schema_version");
      }
      var reason = payload.reason;
      var hasCorrelation = Object.prototype.hasOwnProperty.call(reason, "correlation_id");
      requireExactFields(
        reason,
        "status panel reason",
        ["code", "message"],
        hasCorrelation ? ["correlation_id"] : []
      );
      validateIdentifier(reason.code, "reason.code");
      validateMessage(reason.message, "reason.message");
      if (hasCorrelation) {
        validateCorrelationId(reason.correlation_id);
      }
      return payload;
    }

    requireExactFields(
      payload,
      "status panel",
      ["schema_version", "available", "actor", "resources", "conditions", "disguise_active", "combat"],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 1) {
      throw new Error("unsupported status panel schema_version");
    }

    var actor = payload.actor;
    requireExactFields(actor, "actor", ["name", "identity", "location"], []);
    requireString(actor.name, "actor.name", MAX_ACTOR_NAME);
    requireString(actor.identity, "actor.identity", MAX_ACTOR_IDENTITY);
    if (actor.location !== null) {
      requireExactFields(actor.location, "actor.location", ["label", "identity"], []);
      requireString(actor.location.label, "actor.location.label", MAX_LOCATION_LABEL);
      requireString(actor.location.identity, "actor.location.identity", MAX_ACTOR_IDENTITY);
    }

    var resources = payload.resources;
    if (!isPlainObject(resources)) {
      throw new Error("resources must be a JSON object");
    }
    var resourceKeys = Object.keys(resources);
    if (resourceKeys.length !== 3) {
      throw new Error("resources must contain exactly hp, mp, and sp");
    }
    ["hp", "mp", "sp"].forEach(function (key) {
      var gauge = resources[key];
      requireExactFields(gauge, "resource " + key, ["current", "maximum"], []);
      requireInt(gauge.current, "resource " + key + ".current", 0, MAX_SAFE_INTEGER);
      requireInt(gauge.maximum, "resource " + key + ".maximum", 1, MAX_SAFE_INTEGER);
      if (gauge.current > gauge.maximum) {
        throw new Error(
          "resource " + key + ".current must not exceed its maximum"
        );
      }
    });

    var conditions = payload.conditions;
    if (!Array.isArray(conditions)) {
      throw new Error("conditions must be an array");
    }
    if (conditions.length > MAX_CONDITION_COUNT) {
      throw new Error(
        "conditions exceeds the maximum of " + MAX_CONDITION_COUNT + " entries"
      );
    }
    for (var index = 0; index < conditions.length; index++) {
      validateStatusCondition(conditions[index]);
    }

    requireBool(payload.disguise_active, "disguise_active");
    if (payload.combat !== null) {
      requireExactFields(payload.combat, "combat", ["mode", "round"], []);
      if (COMBAT_MODES.indexOf(payload.combat.mode) === -1) {
        throw new Error("combat.mode must be hostile or guild_exam");
      }
      requireInt(payload.combat.round, "combat.round", 0, MAX_SAFE_INTEGER);
    }
    return payload;
  }

  // Panel discriminator dispatch: the unavailable form is common to every
  // registered panel; the available form is validated against its schema.
  function validatePanel(name, schemaVersion, payload) {
    if (!isPlainObject(payload)) {
      throw new Error("panel " + name + " must be a JSON object");
    }
    requireInt(payload.schema_version, "panel schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== schemaVersion) {
      throw new Error(
        "panel " + name + " schema_version does not match registered version"
      );
    }
    if (payload.available === false) {
      // The common unavailable discriminator; validateStatusPanel handles it.
      validateStatusPanel(payload);
      return payload;
    }
    if (payload.available !== true) {
      throw new Error("panel " + name + " is missing the availability discriminator");
    }
    if (name === "status") {
      return validateStatusPanel(payload);
    }
    throw new Error("panel " + name + " has no registered schema");
  }

  function validatePanels(value, knownPanels, nonempty) {
    if (!isPlainObject(value)) {
      throw new Error("panels must be a JSON object");
    }
    if (nonempty && Object.keys(value).length === 0) {
      throw new Error("panels must not be empty");
    }
    if (Object.keys(value).length > MAX_PANEL_COUNT) {
      throw new Error("panels exceeds the maximum of " + MAX_PANEL_COUNT + " panels");
    }
    var normalized = {};
    var names = Object.keys(value);
    for (var i = 0; i < names.length; i++) {
      var name = validatePanelName(names[i]);
      if (!Object.prototype.hasOwnProperty.call(knownPanels, name)) {
        throw new Error("panels contains unknown panel name " + name);
      }
      normalized[name] = validatePanel(name, knownPanels[name], value[name]);
    }
    return normalized;
  }

  function validateCommonMetadata(payload, name, knownPanels, panelsNonempty) {
    requireExactFields(
      payload,
      name,
      ["protocol_version", "presentation_epoch", "revision", "mode", "panels", "layout_version", "server_time"],
      []
    );
    requireInt(payload.protocol_version, "protocol_version", 1, 1);
    if (payload.protocol_version !== PROTOCOL_VERSION) {
      throw new Error("unsupported protocol_version");
    }
    var epoch = validateEpoch(payload.presentation_epoch);
    var revision = requireInt(payload.revision, "revision", 1, MAX_SAFE_INTEGER);
    if (MODES.indexOf(payload.mode) === -1) {
      throw new Error("mode must be one of " + MODES.join(","));
    }
    var layoutVersion = requireInt(payload.layout_version, "layout_version", 1, MAX_LAYOUT_VERSION);
    var panels = validatePanels(payload.panels, knownPanels, panelsNonempty);
    var serverTime = validateServerTime(payload.server_time);
    return {
      protocolVersion: PROTOCOL_VERSION,
      epoch: epoch,
      revision: revision,
      mode: payload.mode,
      panels: panels,
      layoutVersion: layoutVersion,
      serverTime: serverTime,
    };
  }

  function validateSnapshot(payload) {
    return validateCommonMetadata(payload, "ui_snapshot", PANEL_ALLOWLIST, true);
  }

  function validateUpdate(payload) {
    return validateCommonMetadata(payload, "ui_update", PANEL_ALLOWLIST, true);
  }

  function validateActionResult(payload) {
    requireExactFields(
      payload,
      "ui_action_result",
      ["protocol_version", "presentation_epoch", "request_id", "outcome", "code", "message", "presentation_revision"],
      ["correlation_id"]
    );
    requireInt(payload.protocol_version, "protocol_version", 1, 1);
    validateEpoch(payload.presentation_epoch);
    validateRequestId(payload.request_id);
    if (OUTCOMES.indexOf(payload.outcome) === -1) {
      throw new Error("outcome must be one of " + OUTCOMES.join(","));
    }
    validateIdentifier(payload.code, "code");
    validateMessage(payload.message, "message");
    requireInt(payload.presentation_revision, "presentation_revision", 0, MAX_SAFE_INTEGER);
    var correlationId = null;
    if (payload.outcome === "error") {
      correlationId = validateCorrelationId(payload.correlation_id);
    } else if (Object.prototype.hasOwnProperty.call(payload, "correlation_id")) {
      throw new Error("correlation_id is forbidden for a non-error result");
    }
    return {
      protocolVersion: PROTOCOL_VERSION,
      epoch: payload.presentation_epoch,
      requestId: payload.request_id,
      outcome: payload.outcome,
      code: payload.code,
      message: payload.message,
      presentationRevision: payload.presentation_revision,
      correlationId: correlationId,
    };
  }

  function validateProtocolError(payload) {
    requireExactFields(
      payload,
      "ui_protocol_error",
      ["protocol_version", "code", "message", "reload_required"],
      ["correlation_id"]
    );
    requireInt(payload.protocol_version, "protocol_version", 1, 1);
    validateIdentifier(payload.code, "code");
    if (PROTOCOL_ERROR_CODES.indexOf(payload.code) === -1) {
      throw new Error("unknown protocol error code");
    }
    validateMessage(payload.message, "message");
    requireBool(payload.reload_required, "reload_required");
    var correlationId = null;
    if (payload.code === "internal_error") {
      correlationId = validateCorrelationId(payload.correlation_id);
    } else if (Object.prototype.hasOwnProperty.call(payload, "correlation_id")) {
      throw new Error("correlation_id is forbidden outside internal_error");
    }
    return {
      protocolVersion: PROTOCOL_VERSION,
      code: payload.code,
      message: payload.message,
      reloadRequired: payload.reload_required,
      correlationId: correlationId,
    };
  }

  // ---------------------------------------------------------------------------
  // Public validation entry points (also used directly by tests).
  // ---------------------------------------------------------------------------

  return {
    PROTOCOL_VERSION: PROTOCOL_VERSION,
    MAX_SAFE_INTEGER: MAX_SAFE_INTEGER,
    MAX_CANONICAL_JSON_BYTES: MAX_CANONICAL_JSON_BYTES,
    MAX_DEPTH: MAX_DEPTH,
    MAX_FIELDS: MAX_FIELDS,
    MAX_LIST_ITEMS: MAX_LIST_ITEMS,
    MAX_STRING_CODE_POINTS: MAX_STRING_CODE_POINTS,
    MAX_PANEL_COUNT: MAX_PANEL_COUNT,
    MAX_LAYOUT_VERSION: MAX_LAYOUT_VERSION,
    MAX_MESSAGE_CODE_POINTS: MAX_MESSAGE_CODE_POINTS,
    EPOCH_LENGTH: EPOCH_LENGTH,
    MAX_RETIRED_EPOCHS: MAX_RETIRED_EPOCHS,
    MAX_ACTOR_NAME: MAX_ACTOR_NAME,
    MAX_ACTOR_IDENTITY: MAX_ACTOR_IDENTITY,
    MAX_LOCATION_LABEL: MAX_LOCATION_LABEL,
    MAX_CONDITION_COUNT: MAX_CONDITION_COUNT,
    MAX_CONDITION_LABEL: MAX_CONDITION_LABEL,
    MAX_MODIFIER_KEYS: MAX_MODIFIER_KEYS,
    MODES: MODES.slice(),
    OUTCOMES: OUTCOMES.slice(),
    COMBAT_MODES: COMBAT_MODES.slice(),
    PROTOCOL_ERROR_CODES: PROTOCOL_ERROR_CODES.slice(),
    PANEL_ALLOWLIST: Object.assign({}, PANEL_ALLOWLIST),

    checkEnvelope: checkEnvelope,
    checkGlobalSafety: checkGlobalSafety,
    jsonByteSize: jsonByteSize,
    canonicalJson: canonicalJson,
    validateEpoch: validateEpoch,
    validateServerTime: validateServerTime,
    validateSnapshot: validateSnapshot,
    validateUpdate: validateUpdate,
    validateActionResult: validateActionResult,
    validateProtocolError: validateProtocolError,
    validateStatusPanel: validateStatusPanel,
    validatePanel: validatePanel,

    // The only accepted client->server synchronization body.
    syncEnvelope: function () {
      return { protocol_version: PROTOCOL_VERSION };
    },

    createRetiredEpochSet: createRetiredEpochSet,

    // -----------------------------------------------------------------------
    // The transport-generation reducer.
    // -----------------------------------------------------------------------
    createStore: function () {
      var generation = 0;
      var phase = "idle"; // idle | awaiting_initial_snapshot | active
      var activeEpoch = null;
      var revision = null;
      var mode = null;
      var layoutVersion = null;
      var serverTime = null;
      var panels = {};
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
        return {
          generation: generation,
          phase: phase,
          activeEpoch: activeEpoch,
          revision: revision,
          mode: mode,
          layoutVersion: layoutVersion,
          serverTime: serverTime === null ? null : JSON.parse(canonicalJson(serverTime)),
          panels: panelCopy,
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
        // merges nested fields.
        Object.keys(meta.panels).forEach(function (name) {
          panels[name] = JSON.parse(canonicalJson(meta.panels[name]));
        });
        phase = "active";
        mutationsLocked = false;
        notify();
      }

      return {
        getState: cloneState,

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

            if (phase === "idle" || phase === "awaiting_initial_snapshot") {
              // Only the first valid full snapshot of the current generation
              // with a non-retired epoch may establish active state.
              if (messageName !== "ui_snapshot") {
                return { accepted: false, reason: "update_cannot_establish_epoch" };
              }
              if (retired.has(meta.epoch)) {
                return { accepted: false, reason: "retired_epoch" };
              }
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
            if (phase !== "active" || result.epoch !== activeEpoch) {
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
    },
  };
});
