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
  // Depth 12 accommodates the nested `context_actions` v3 shape (envelope ->
  // panels -> panel -> skills -> category -> groups -> skill group -> skills ->
  // descriptor -> cost/freeform_scales), whose deepest legitimate leaf sits at
  // depth 11; must match web.webclient.presentation.protocol.MAX_DEPTH.
  var MAX_DEPTH = 12;
  var MAX_FIELDS = 64;
  // Clears the largest legitimate flat panel list: the `context_actions`
  // exploration form's affordance array (at most 320 entries).
  var MAX_LIST_ITEMS = 320;
  var MAX_STRING_CODE_POINTS = 2048;
  var MAX_PANEL_COUNT = 32;
  var MAX_LAYOUT_VERSION = 65535;
  var MAX_MESSAGE_CODE_POINTS = 512;
  var EPOCH_LENGTH = 22;
  var MAX_RETIRED_EPOCHS = 8;
  var MAX_ACTOR_NAME = 256;
  var MAX_ACTOR_IDENTITY = 64;
  var MAX_FULL_TITLE_CODE_POINTS = 128;
  var MAX_LOCATION_LABEL = 256;
  var MAX_CONDITION_COUNT = 32;
  var MAX_CONDITION_LABEL = 128;
  var MAX_MODIFIER_KEYS = 16;
  // Adapter data slot (ui_action_result success only). Must match
  // web.webclient.presentation.protocol.MAX_RESULT_DATA_FIELDS and
  // MAX_RESULT_DATA_BYTES and RESULT_DATA_STANDARD_RESERVE: eight fields, and
  // a canonical-JSON byte budget reserving the exact worst-case seven-field
  // success envelope (2,345 bytes; the 512-code-point message may be 2,048
  // UTF-8 bytes) plus the 8-byte ,"data": delimiter, so an emitted envelope
  // can never exceed MAX_CANONICAL_JSON_BYTES.
  var RESULT_DATA_STANDARD_RESERVE = 2345 + 8;
  var MAX_RESULT_DATA_FIELDS = 8;
  var MAX_RESULT_DATA_BYTES = MAX_CANONICAL_JSON_BYTES - RESULT_DATA_STANDARD_RESERVE;

  var MODES = ["creation", "exploration", "combat", "dialogue"];
  var OUTCOMES = ["success", "rejected", "stale", "error"];
  // State-identity and diagnostic key names an adapter data slot must never
  // carry at any nesting level (dot-segment heads included), mirroring
  // web.webclient.presentation.protocol.FORBIDDEN_RESULT_DATA_KEYS.
  var FORBIDDEN_RESULT_DATA_KEYS = [
    "actor",
    "session",
    "epoch",
    "revision",
    "presentation_epoch",
    "presentation_revision",
    "correlation_id",
    "exception",
    "traceback",
    "local_path",
  ];
  var COMBAT_MODES = ["hostile", "guild_exam"];
  var PROTOCOL_ERROR_CODES = [
    "unsupported_version",
    "presentation_unavailable",
    "internal_error",
    "malformed_envelope",
    "no_puppet",
  ];
  var SEVERITIES = ["beneficial", "informational", "warning", "harmful", "critical"];

  // context_actions panel bounds (mirror of web.webclient.presentation.combat_panel).
  var MAX_SESSION_ID_CODE_POINTS = 128;
  var MAX_PARTICIPANTS = 16;
  // Flattened active-skill descriptor bound. Raised from 32 to clear the
  // current theoretical maximum of 157 obtainable active skills (91 base
  // active skills including innate, plus the 65 registered sexual acts and
  // the pre-existing divine_sexual_arts); a multiple of 16 like the other
  // presentation bounds.
  var MAX_SKILLS = 192;
  var MAX_DISPLAY_NAME = 64;
  var MAX_LABEL = 128;
  var MAX_DESCRIPTION = 512;
  var MAX_SKILL_TARGETS = 16;
  var MAX_SHORTHANDS = 3;
  var MAX_TOKEN = 16;
  var MAX_ACTION_KEYS = 16;
  var MAX_COST_KEYS = 8;
  var MAX_REASON_MESSAGE = 512;
  var SESSION_MODES = ["hostile", "guild_exam"];
  var SESSION_STATES = ["ready", "recovery"];
  var TEAMS = ["party", "foes"];
  var PARTICIPANT_STATES = ["active", "fled", "knocked_out", "defeated"];
  var TARGET_SPECS = ["none", "self", "single", "area"];
  var ALLOWED_SHORTHANDS = ["all-enemies", "all-allies", "all"];
  var FREEFORM_SCALES_ALLOWED = [0.25, 0.5, 1, 2, 4];
  var FREEFORM_SCALES_MAX = 5;
  var FREEFORM_LABELS_ALLOWED = ["1/4", "1/2", "1", "2", "4"];
  var ROOT_ACTIONS = ["attack", "skills", "items", "defend", "flee"];
  var SECONDARY_ACTIONS = ["forfeit"];
  var RECOVERY_SECONDARY_ACTIONS = ["forfeit"];
  // Exploration available form bounds (mirror of
  // web.webclient.presentation.combat_panel).
  var CONTEXT_ACTIONS_MAX_AFFORDANCES = 320;
  var CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL = 128;
  var CONTEXT_ACTIONS_MAX_PARAM_KEYS = 8;
  var CONTEXT_ACTIONS_MAX_PARAM_STRING = 512;
  var CONTEXT_ACTIONS_MAX_EXIT_REF = 64;
  var CONTEXT_ACTIONS_MAX_NODE_ID = 128;
  var CONTEXT_ACTIONS_MAX_KEYWORD_ID = 64;
  var CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS = 43200;
  var CONTEXT_ACTIONS_ACTION_CODES = [
    "explore.move",
    "explore.look",
    "explore.talk_scripted",
    "explore.talk_freeform",
    "explore.party_invite",
    "explore.party_leave",
    "explore.engage",
    "explore.wait",
  ];
  var CONTEXT_ACTIONS_SURFACES = ["guild", "shop"];
  var CONTEXT_ACTIONS_DAYPARTS = ["midnight", "dawn", "noon", "dusk"];
  // Suggestions envelope bounds and enums (mirror of
  // web.webclient.presentation.options and the generative schema caps).
  var OPTIONS_STATUSES = ["generating", "ready", "degraded", "unavailable"];
  var OPTIONS_CARD_KINDS = ["known_action", "freeform"];
  var MAX_OPTION_CARDS = 5;
  var MAX_OPTION_LABEL = 24;
  var MAX_OPTION_HINT = 60;
  var MAX_OPTION_PARAMS = 4;
  var OPTIONS_FREEFORM_ACTION_CODE = "explore.talk_freeform";
  var OPTIONS_MAX_PARAM_STRING = 512;
  // SkillCategory enum values, in the registry's fixed declaration order
  // (mirror of world.skills.registry.SkillCategory).
  var SKILL_CATEGORY_KEYS = [
    "elemental_magic",
    "martial_arts",
    "enhancement",
    "innate_gift",
    "movement",
    "divine_mystery",
    "utility",
    "sexual_act",
  ];

  // local_map panel bounds (mirror of web.webclient.presentation.local_map,
  // design D10a).
  var LOCAL_MAP_MAX_NODES = 64;
  var LOCAL_MAP_MAX_EDGES = 128;
  var LOCAL_MAP_MAX_LEGEND = 16;
  var LOCAL_MAP_MAX_STRING = 256;

  // Exact shared lineage bounds -- must stay equal to
  // web.webclient.presentation.lineage (skill-lineage-panel design DD3).
  var LINEAGE_MAX_CHAINS = 16;
  var LINEAGE_MAX_NODES_PER_CHAIN = 32;
  var LINEAGE_MAX_TEXT = 128;
  var LOCAL_MAP_MAX_TITLE = 128;
  var LOCAL_MAP_MAX_NODE_ID = 128;
  var LOCAL_MAP_MAX_EXIT_REF = 64;
  var LOCAL_MAP_COORD_MIN = -1024;
  var LOCAL_MAP_COORD_MAX = 1024;
  var LOCAL_MAP_VISIBILITIES = [
    "current",
    "visible_unvisited",
    "visible_visited",
    "remembered",
  ];
  var LOCAL_MAP_LAYERS = ["grid", "wilderness", "instance", "interior"];
  var LOCAL_MAP_ACTION_KINDS = ["move"];
  var NODE_ID_RE = /^(grid|wild|room):[^:]+(?::[^:]+)*$/;

  // services panel bounds (mirror of web.webclient.presentation.services,
  // design D4). These constants are shared with the server through a
  // dual-direction parity test.
  var SERVICES_MAX_BOARD_ROWS = 12;
  var SERVICES_MAX_QUEST_ROWS = 12;
  var SERVICES_MAX_STOCK_ROWS = 12;
  var SERVICES_MAX_SELLABLE_ROWS = 12;
  var SERVICES_MAX_INVENTORY_ROWS = 32;
  var SERVICES_MAX_KEY = 64;
  var SERVICES_MAX_DISPLAY_NAME = 128;
  var SERVICES_MAX_SUMMARY = 128;
  var SERVICES_MAX_DETAIL = 512;
  var SERVICES_MAX_DEADLINE_LINE = 64;
  var SERVICES_MAX_RANK_KEY = 8;
  var SERVICES_MAX_HOST_DISPLAY_NAME = 256;
  var SERVICES_MAX_LABEL = 64;
  var SERVICES_MAX_REASON_MESSAGE = 128;
  var SERVICES_MAX_QUANTITY = 1000;
  var SERVICES_MIN_QUANTITY = 1;
  var SERVICES_MAX_PRESENTATION_KEY = 32;
  var SERVICES_MAX_PRESENTATION_SUMMARY = 240;
  var SERVICES_QUEST_STATES = ["in_progress", "completed", "failed"];
  var SERVICES_ACTIONS = [
    "guild.register",
    "guild.quest_accept",
    "guild.quest_abandon",
    "guild.quest_turnin",
    "guild.quest_track",
    "guild.exam_start",
    "shop.buy",
    "shop.sell",
    "inventory.use",
    "inventory.toggle_equip",
  ];
  var SERVICES_BUY = "shop.buy";
  var SERVICES_SELL = "shop.sell";

  // title_ballot panel bounds (mirror of web.webclient.presentation.
  // title_ballot, title-epithet-nomination D4). The values are owned by
  // world/rules/titles.py (the ballot writer); these constants mirror the
  // panel validator and must stay equal.
  var TITLE_BALLOT_MAX_CANDIDATES = 3;
  var TITLE_BALLOT_MAX_DISPLAY = 64;
  var TITLE_BALLOT_MAX_BASIS = 80;

  // title_codex panel bounds (mirror of web.webclient.presentation.
  // title_codex, title-codex-removal D5/D7). The values are owned by
  // world/rules/title_view.py; these constants mirror the panel validator
  // and must stay equal.
  var TITLE_CODEX_MAX_ROWS = 50;
  var TITLE_CODEX_MAX_DISPLAY = 64;
  var TITLE_CODEX_MAX_BASIS = 160;
  var TITLE_CODEX_MAX_FULL_TITLE = 128;
  var TITLE_CODEX_MAX_BALLOT = 3;
  var TITLE_CODEX_BASIS_WIRE_MAX = 80;
  var TITLE_CODEX_CATEGORIES = [
    "combat",
    "spell",
    "explore",
    "guild",
    "romance",
  ];

  // creation panel bounds (mirror of web.webclient.presentation.creation,
  // design D2). These constants are shared with the server through a
  // dual-direction parity test.
  var CREATION_MAX_PRESETS = 8;
  var CREATION_MAX_RACES = 8;
  var CREATION_MAX_SUBRACES = 16;
  var CREATION_MAX_PROFILES = 16;
  var CREATION_MIN_NAME_LENGTH = 1;
  var CREATION_MAX_NAME_LENGTH = 64;
  var CREATION_AGE_MINIMUM = 18;
  var CREATION_AGE_MAXIMUM = 10000;
  var CREATION_APPARENT_AGE_MINIMUM = 18;
  var CREATION_APPARENT_AGE_MAXIMUM = 10000;
  var CREATION_MAX_PRESET_KEY = 64;
  var CREATION_MAX_DISPLAY_NAME = 128;
  var CREATION_MAX_RACE_KEY = 64;
  // The proposal transient-fill display-name bound (mirror of
  // web.webclient.presentation.creation.MAX_PROPOSAL_NAME_CODE_POINTS).
  var CREATION_MAX_PROPOSAL_NAME = 64;
  var CREATION_MAX_DESCRIPTION = 512;
  var CREATION_MAX_EMPHASIS = 256;
  var CREATION_MAX_BACKGROUND = 256;
  // The shared persona-field bound (mirror of MAX_PERSONA_FIELD_LENGTH and
  // web.webclient.presentation.creation.MAX_PERSONA_BACKGROUND): the bound
  // applies per-field to the draft/proposal persona block.
  var CREATION_MAX_PERSONA_BACKGROUND = 600;
  var CREATION_MAX_SUBRACE_KEY = 64;
  var CREATION_MAX_SPECIALTY = 256;
  var CREATION_MAX_LABEL = 128;
  var CREATION_MAX_EXPLANATION = 256;
  // The concept input bound (mirror of the adapter/command/layer caps).
  var CREATION_MAX_CONCEPT = 500;
  var CREATION_AXES = ["hp", "mp", "sp", "atk_phys", "agility", "defense", "magic_power"];
  var CREATION_PRESET_STAGE = "preset_selected";
  var CREATION_CUSTOM_STAGE = "custom_filled";
  // The exact wire persona block keys (the three prose fields).
  var CREATION_PERSONA_KEYS = ["personality", "life_story", "habit"];
  // The sex vocabulary mirror (world/lore/sex.py). Keys only -- the option
  // LABELS are server-owned Traditional Chinese prose shipped in the panel's
  // `custom.sex` descriptor; no label literal lives in this bundle. The
  // pinned dual-direction comparison lives in
  // tests/test_creation_parity_contract.py.
  var CREATION_SEX_VALUES = ["female", "male", "other"];
  var CREATION_SEX_DEFAULT = "other";
  // Structural ceiling for the option list (mirror of MAX_SEX_OPTIONS); the
  // vocabulary itself is pinned exactly, the bound must never bind real data.
  var CREATION_MAX_SEX_OPTIONS = 8;
  // The creation panel schema version (mirror of CREATION_SCHEMA_VERSION):
  // v3 widens the optional transient concept proposal slot with the five
  // optional transient-fill keys (bump-creation-panel-proposal-v3), on top of
  // the v2 player-owned draft persona key (retool-concept-transient-fill
  // D1/D3).
  // v4 adds the server-labelled `custom.sex` option list and the required
  // draft `sex` member (namegen-creation-ui).
  var CREATION_SCHEMA_VERSION = 4;
  // Affinity picker bounds (mirror of web.webclient.presentation.creation and
  // the deterministic max_affinity_elements mapping). The race maxima are
  // 2/1/0 for human/beastfolk/elf; the element set is exactly the eight lore
  // elements.
  var CREATION_MAX_AFFINITY_ELEMENTS = 8;
  var CREATION_AFFINITY_ELEMENTS = [
    "fire", "water", "wind", "earth", "lightning", "ice", "light", "dark",
  ];
  var CREATION_AFFINITY_RACES = ["human", "beastfolk", "elf"];
  var CREATION_AFFINITY_MAXIMUMS = { human: 2, beastfolk: 1, elf: 0 };

  var MESSAGE_NAMES = {
    ui_snapshot: true,
    ui_update: true,
    ui_action_result: true,
    ui_protocol_error: true,
  };

  // The registered production panel allowlist. Each key maps to its exact
  // schema version; unknown panel names reject the whole presentation message.
  // Party panel bounds (mirror of web.webclient.presentation.party,
  // webclient-align-04): at most four companion rows reusing the NPC
  // display-name bound; bond_stage is a canonical stage NAME string.
  var PARTY_SCHEMA_VERSION = 1;
  var PARTY_MAX_ROWS = 4;
  var PARTY_MAX_DISPLAY_NAME = 128;

  // Objectives panel bounds (mirror of web.webclient.presentation.objectives,
  // webclient-align-06): at most three tracked quest rows; the row cap mirrors
  // world.quests.runtime.MAX_TRACKED_QUESTS.
  var OBJECTIVES_SCHEMA_VERSION = 1;
  var OBJECTIVES_MAX_ROWS = 3;
  var OBJECTIVES_MAX_QUEST_ID = 64;
  var OBJECTIVES_MAX_DISPLAY_NAME = 128;
  var OBJECTIVES_MAX_OBJECTIVE_LINE = 128;
  var OBJECTIVES_MAX_DEADLINE_LINE = 64;

  // Dialogue panel bounds (mirror of web.webclient.presentation.dialogue,
  // webclient-align-10): the choice cap mirrors MAX_SCRIPTED_KEYWORDS, the
  // keyword bounds mirror the exploration keyword vocabulary, and the line
  // bound is the shared dialogue-session prose bound (never the generic
  // protocol ceiling) — the write path truncates to it, so over-bound
  // dialogue is corruption and rejects.
  var DIALOGUE_SCHEMA_VERSION = 1;
  var DIALOGUE_MAX_CHOICES = 16;
  var DIALOGUE_MAX_KEYWORD_ID = 64;
  var DIALOGUE_MAX_KEYWORD_LABEL = 128;
  var DIALOGUE_MAX_LINE = 2000;

  var PANEL_ALLOWLIST = {
    art: 1,
    status: 2,
    context_actions: 5,
    local_map: 1,
    party: 1,
    objectives: 1,
    services: 4,
    creation: 4,
    exploration: 1,
    character: 7,
    lineage: 1,
    dialogue: 1,
    title_ballot: 1,
    title_codex: 1,
  };

  var EPOCH_RE = /^[A-Za-z0-9_-]{22}$/;
  var PANEL_NAME_RE = /^[a-z0-9_]{1,64}$/;
  var IDENTIFIER_RE = /^[a-z0-9._]{1,64}$/;
  var REQUEST_ID_RE = /^[A-Za-z0-9:_-]{1,64}$/;
  var CORRELATION_RE = /^[0-9a-f]{32}$/;
  var TOKEN_RE = /^[ae]\d+$/;

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
        if (value < -MAX_SAFE_INTEGER || value > MAX_SAFE_INTEGER) {
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
    // Null prototype: an own "__proto__"/"constructor"/"toString" key from a
    // JSON-parsed payload must read as unknown, not inherit a truthy value
    // from Object.prototype (webclient-align-04 final review — every panel's
    // exact-shape gate relies on this helper).
    var known = Object.create(null);
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

  function isForbiddenResultDataKey(name) {
    var segments = String(name).split(".");
    for (var i = 0; i < segments.length; i++) {
      if (FORBIDDEN_RESULT_DATA_KEYS.indexOf(segments[i]) !== -1) {
        return true;
      }
    }
    return false;
  }

  // Mirror of web.webclient.presentation.protocol._validate_result_data.
  function validateResultData(value) {
    if (!isPlainObject(value)) {
      throw new Error("data must be a JSON object");
    }
    var keys = Object.keys(value);
    if (keys.length > MAX_RESULT_DATA_FIELDS) {
      throw new Error(
        "data exceeds the maximum of " + MAX_RESULT_DATA_FIELDS + " fields"
      );
    }
    var rejectReserved = function (name) {
      validateIdentifier(name, "data field name");
      if (isForbiddenResultDataKey(name)) {
        throw new Error("data field name '" + name + "' carries a reserved state key");
      }
    };
    var walk = function (node) {
      if (Array.isArray(node)) {
        for (var j = 0; j < node.length; j++) {
          walk(node[j]);
        }
        return;
      }
      if (node === null || node === undefined) {
        return;
      }
      var kind = typeof node;
      if (kind === "object") {
        // Dates, RegExps, Maps, and class instances reach the wire as `{}` or
        // worse; the Python validator rejects them as unsupported types.
        if (Object.prototype.toString.call(node) !== "[object Object]") {
          throw new Error("data contains an unsupported JSON value type");
        }
        var nodeKeys = Object.keys(node);
        for (var k = 0; k < nodeKeys.length; k++) {
          rejectReserved(nodeKeys[k]);
          walk(node[nodeKeys[k]]);
        }
        return;
      }
      if (kind !== "string" && kind !== "number" && kind !== "boolean") {
        throw new Error("data contains an unsupported JSON value type");
      }
    };
    walk(value);
    // Depth 1 is the slot's own position inside the envelope, mirroring the
    // Python check so a data leaf can never sit deeper than MAX_DEPTH
    // measured from the envelope root.
    checkGlobalSafety(value, 1);
    if (utf8Bytes(canonicalJson(value)) > MAX_RESULT_DATA_BYTES) {
      throw new Error(
        "data canonical JSON exceeds " + MAX_RESULT_DATA_BYTES + " bytes"
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

  // Exact available status panel v2 schema (composed full title optional).
  function validateStatusPanel(payload) {
    requireExactFields(
      payload,
      "status panel",
      ["schema_version", "available", "actor", "resources", "conditions", "disguise_active", "combat"],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 2) {
      throw new Error("unsupported status panel schema_version");
    }

    var actor = payload.actor;
    requireExactFields(actor, "actor", ["name", "identity", "location"], ["full_title"]);
    requireString(actor.name, "actor.name", MAX_ACTOR_NAME);
    requireString(actor.identity, "actor.identity", MAX_ACTOR_IDENTITY);
    if (Object.prototype.hasOwnProperty.call(actor, "full_title")) {
      requireString(
        actor.full_title,
        "actor.full_title",
        MAX_FULL_TITLE_CODE_POINTS
      );
      if (!actor.full_title.trim()) {
        throw new Error("actor.full_title must be non-empty when present");
      }
    }
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

  function validateToken(value) {
    if (typeof value !== "string" || !TOKEN_RE.test(value) || value.length > MAX_TOKEN) {
      throw new Error("participant token must be aN or eN");
    }
    return value;
  }

  function validateSession(value) {
    requireExactFields(
      value,
      "combat session",
      ["session_id", "mode", "round", "state", "reason"],
      []
    );
    var sessionId = requireString(value.session_id, "session_id", MAX_SESSION_ID_CODE_POINTS);
    if (!sessionId.trim()) {
      throw new Error("session_id must be non-empty");
    }
    if (SESSION_MODES.indexOf(value.mode) === -1) {
      throw new Error("session mode must be hostile or guild_exam");
    }
    requireInt(value.round, "round", 0, MAX_SAFE_INTEGER);
    if (SESSION_STATES.indexOf(value.state) === -1) {
      throw new Error("session state must be ready or recovery");
    }
    var reason = value.reason;
    if (reason === null) {
      if (value.state !== "ready") {
        throw new Error("a recovery session requires a reason");
      }
    } else {
      var hasCorrelation = false;
      requireExactFields(reason, "session reason", ["code", "message"], []);
      validateIdentifier(reason.code, "session reason code");
      requireString(reason.message, "session reason message", MAX_REASON_MESSAGE);
      if (value.state !== "recovery") {
        throw new Error("a ready session must have a null reason");
      }
    }
    return value;
  }

  function validateParticipant(value) {
    requireExactFields(
      value,
      "participant",
      ["identity", "token", "display_name", "team", "state", "hp_current", "hp_maximum", "portrait_ref"],
      []
    );
    requireInt(value.identity, "identity", 1, MAX_SAFE_INTEGER);
    validateToken(value.token);
    var displayName = requireString(value.display_name, "display_name", MAX_DISPLAY_NAME);
    if (!displayName.trim()) {
      throw new Error("participant display_name must be non-empty");
    }
    if (TEAMS.indexOf(value.team) === -1) {
      throw new Error("participant team must be party or foes");
    }
    if (PARTICIPANT_STATES.indexOf(value.state) === -1) {
      throw new Error("participant state is not a stable value");
    }
    requireInt(value.hp_current, "hp_current", 0, MAX_SAFE_INTEGER);
    requireInt(value.hp_maximum, "hp_maximum", 1, MAX_SAFE_INTEGER);
    if (value.hp_current > value.hp_maximum) {
      throw new Error("participant hp_current must not exceed its maximum");
    }
    var portraitRef = value.portrait_ref;
    if (portraitRef !== null) {
      if (typeof portraitRef !== "string" || !/^[0-9]+$/.test(portraitRef)) {
        throw new Error("portrait_ref must be an opaque decimal catalog key or null");
      }
      if (portraitRef.length > 32) {
        throw new Error("portrait_ref exceeds its bound");
      }
    }
    return value;
  }

  function validateDisabledReason(value) {
    if (value === null) {
      return null;
    }
    requireExactFields(value, "disabled_reason", ["code", "message"], []);
    validateIdentifier(value.code, "disabled_reason code");
    requireString(value.message, "disabled_reason message", MAX_REASON_MESSAGE);
    return value;
  }

  function validateFreeformScales(value, baseMp) {
    if (value === null || value === undefined) {
      return [];
    }
    if (
      baseMp === null ||
      baseMp === undefined ||
      typeof baseMp !== "number" ||
      !Number.isInteger(baseMp) ||
      baseMp <= 0
    ) {
      throw new Error("a skill without an mp cost cannot carry freeform_scales");
    }
    if (!Array.isArray(value) || value.length === 0) {
      throw new Error("freeform_scales must be a non-empty array when present");
    }
    if (value.length > FREEFORM_SCALES_MAX) {
      throw new Error("freeform_scales may not exceed the canonical scale table");
    }
    value.forEach(function (entry, index) {
      requireExactFields(entry, "freeform_scales entry", ["scale", "label", "mp_cost"], []);
      var scale = entry.scale;
      if (scale !== FREEFORM_SCALES_ALLOWED[index]) {
        throw new Error("freeform_scales must be ascending over the allowed scale set");
      }
      var label = requireString(entry.label, "freeform_scales label", 8);
      if (label !== FREEFORM_LABELS_ALLOWED[index]) {
        throw new Error("freeform_scales label must be the canonical label of its scale");
      }
      var mpCost = requireInt(entry.mp_cost, "freeform_scales mp_cost", 1, MAX_SAFE_INTEGER);
      if (mpCost !== Math.max(1, Math.floor(baseMp * scale + 0.5))) {
        throw new Error("freeform_scales mp_cost is inconsistent with the scaled base cost");
      }
    });
    return value;
  }

  function validateSkill(value) {
    requireExactFields(
      value,
      "skill",
      ["key", "label", "description", "cost", "target_spec", "element", "enabled", "disabled_reason", "targets", "shorthands"],
      ["freeform_scales"]
    );
    validateIdentifier(value.key, "skill key");
    var label = requireString(value.label, "skill label", MAX_LABEL);
    if (!label.trim()) {
      throw new Error("skill label must be non-empty");
    }
    var description = requireString(value.description, "skill description", MAX_DESCRIPTION);
    if (!description.trim()) {
      throw new Error("skill description must be non-empty");
    }
    var cost = value.cost;
    if (!isPlainObject(cost) || Object.keys(cost).length > MAX_COST_KEYS) {
      throw new Error("skill cost must be a bounded object");
    }
    Object.keys(cost).forEach(function (resource) {
      validateIdentifier(resource, "cost resource key");
      requireInt(cost[resource], "cost amount", 0, MAX_SAFE_INTEGER);
    });
    if (TARGET_SPECS.indexOf(value.target_spec) === -1) {
      throw new Error("skill target_spec is not a stable value");
    }
    if (value.element !== null) {
      validateIdentifier(value.element, "skill element");
    }
    requireBool(value.enabled, "enabled");
    var disabledReason = validateDisabledReason(value.disabled_reason);
    if (!value.enabled && disabledReason === null) {
      throw new Error("a disabled skill requires a disabled_reason");
    }
    if (value.enabled && disabledReason !== null) {
      throw new Error("an enabled skill must not carry a disabled_reason");
    }
    var targets = value.targets;
    if (!Array.isArray(targets) || targets.length > MAX_SKILL_TARGETS) {
      throw new Error("skill targets exceed their bound");
    }
    var seenTargets = {};
    targets.forEach(function (target) {
      if (typeof target !== "number" || !Number.isInteger(target) || target <= 0) {
        throw new Error("skill targets must be positive integers");
      }
      if (seenTargets[target]) {
        throw new Error("skill targets must be unique");
      }
      seenTargets[target] = true;
    });
    var shorthands = value.shorthands;
    if (!Array.isArray(shorthands) || shorthands.length > MAX_SHORTHANDS) {
      throw new Error("skill shorthands exceed their bound");
    }
    var seenShorthands = {};
    shorthands.forEach(function (shorthand) {
      if (ALLOWED_SHORTHANDS.indexOf(shorthand) === -1) {
        throw new Error("skill carries an unapproved shorthand");
      }
      if (seenShorthands[shorthand]) {
        throw new Error("skill shorthands must be unique");
      }
      seenShorthands[shorthand] = true;
    });
    if (value.target_spec !== "area" && shorthands.length > 0) {
      throw new Error("only area skills may carry shorthands");
    }
    if (value.freeform_scales !== undefined) {
      if (typeof value.cost.mp !== "number" || !Number.isInteger(value.cost.mp) || value.cost.mp <= 0) {
        throw new Error("a skill without an mp cost cannot carry freeform_scales");
      }
      validateFreeformScales(value.freeform_scales, value.cost.mp);
    }
    return value;
  }

  function validateActionKeys(value, name) {
    if (!Array.isArray(value) || value.length > MAX_ACTION_KEYS) {
      throw new Error(name + " exceed their bound");
    }
    var seen = {};
    value.forEach(function (key) {
      validateIdentifier(key, name + " key");
      if (seen[key]) {
        throw new Error(name + " must be unique");
      }
      seen[key] = true;
    });
    return value;
  }

  // Exact available context_actions combat/exploration panel v4 schema.
  function validateContextActionsAffordanceParams(actionId, params) {
    if (!isPlainObject(params)) {
      throw new Error("affordance params must be a JSON object");
    }
    if (Object.keys(params).length > CONTEXT_ACTIONS_MAX_PARAM_KEYS) {
      throw new Error("affordance params exceed their bound");
    }
    Object.keys(params).forEach(function (key) {
      var child = params[key];
      if (typeof child === "string" && codePoints(child) > CONTEXT_ACTIONS_MAX_PARAM_STRING) {
        throw new Error("affordance params string exceeds its bound");
      }
    });
    if (actionId === "explore.move") {
      requireExactFields(params, "move params", ["exit_ref", "current_node"], []);
      if (
        typeof params.exit_ref !== "string" ||
        params.exit_ref.length < 1 ||
        params.exit_ref.length > CONTEXT_ACTIONS_MAX_EXIT_REF
      ) {
        throw new Error("exit_ref must be 1.." + CONTEXT_ACTIONS_MAX_EXIT_REF + " ASCII characters");
      }
      if (/[^\x00-\x7F]/.test(params.exit_ref)) {
        throw new Error("exit_ref must be ASCII");
      }
      requireString(params.current_node, "current_node", CONTEXT_ACTIONS_MAX_NODE_ID);
      if (!NODE_ID_RE.test(params.current_node)) {
        throw new Error("current_node is not a canonical node ID");
      }
      return params;
    }
    if (actionId === "explore.look") {
      if (Object.keys(params).length === 1 && params.room !== undefined) {
        if (params.room !== true) {
          throw new Error("explore.look room must be the exact boolean true");
        }
        return params;
      }
      requireExactFields(params, "look params", ["target_id"], []);
      requireInt(params.target_id, "target_id", 1, MAX_SAFE_INTEGER);
      return params;
    }
    if (actionId === "explore.talk_scripted") {
      requireExactFields(params, "talk_scripted params", ["npc_id", "keyword_id"], []);
      requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
      var keywordId = requireString(params.keyword_id, "keyword_id", CONTEXT_ACTIONS_MAX_KEYWORD_ID);
      if (!keywordId.trim()) {
        throw new Error("keyword_id must be non-empty");
      }
      return params;
    }
    if (actionId === "explore.talk_freeform") {
      // Binding-only shape: no validator produces npc_id without speech.
      requireExactFields(params, "freeform params", ["npc_id"], []);
      requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
      return params;
    }
    if (actionId === "explore.party_invite") {
      requireExactFields(params, "party_invite params", ["npc_id", "message"], []);
      requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
      requireString(params.message, "message", MAX_MESSAGE_CODE_POINTS);
      return params;
    }
    if (actionId === "explore.party_leave") {
      requireExactFields(params, "party_leave params", ["npc_id"], []);
      requireInt(params.npc_id, "npc_id", 1, MAX_SAFE_INTEGER);
      return params;
    }
    if (actionId === "explore.engage") {
      requireExactFields(params, "engage params", ["monster_id"], []);
      requireInt(params.monster_id, "monster_id", 1, MAX_SAFE_INTEGER);
      return params;
    }
    if (actionId === "explore.wait") {
      if (Object.keys(params).length === 1 && params.daypart !== undefined) {
        if (CONTEXT_ACTIONS_DAYPARTS.indexOf(params.daypart) === -1) {
          throw new Error("explore.wait daypart is not a stable value");
        }
        return params;
      }
      if (Object.keys(params).length === 1 && params.seconds !== undefined) {
        requireInt(params.seconds, "seconds", 1, CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS);
        return params;
      }
      if (Object.keys(params).length === 1 && params.sleep !== undefined) {
        if (params.sleep !== true) {
          throw new Error("explore.wait sleep must be the exact boolean true");
        }
        return params;
      }
      throw new Error("explore.wait requires exactly one of daypart, seconds, or sleep");
    }
    throw new Error("affordance params carry an unregistered action code");
  }

  function validateContextActionsAffordance(value) {
    if (!isPlainObject(value)) {
      throw new Error("affordance must be a JSON object");
    }
    requireExactFields(
      value,
      "affordance",
      ["label", "navigation", "enabled", "disabled_reason"],
      ["action_id", "params", "freeform", "surface"]
    );
    var label = requireString(value.label, "label", CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL);
    if (!label.trim()) {
      throw new Error("affordance label must be non-empty");
    }
    var navigation = requireBool(value.navigation, "navigation");
    var enabled = requireBool(value.enabled, "enabled");
    var disabledReason = validateDisabledReason(value.disabled_reason);
    if (disabledReason === null) {
      if (!enabled) {
        throw new Error("a disabled affordance requires a disabled_reason");
      }
    } else if (enabled) {
      throw new Error("an enabled affordance must not carry a disabled_reason");
    }
    if (navigation) {
      requireExactFields(
        value,
        "navigation affordance",
        ["surface", "label", "navigation", "enabled", "disabled_reason"],
        []
      );
      if (CONTEXT_ACTIONS_SURFACES.indexOf(value.surface) === -1) {
        throw new Error("affordance surface is not a stable value");
      }
      return {
        surface: value.surface,
        label: label,
        navigation: true,
        enabled: enabled,
        disabled_reason: disabledReason,
      };
    }
    requireExactFields(
      value,
      "action affordance",
      ["action_id", "label", "params", "freeform", "navigation", "enabled", "disabled_reason"],
      []
    );
    var actionId = validateIdentifier(value.action_id, "action_id");
    if (CONTEXT_ACTIONS_ACTION_CODES.indexOf(actionId) === -1) {
      throw new Error("action_id is not a registered exploration action");
    }
    if (typeof value.freeform !== "boolean") {
      throw new Error("affordance freeform must be a boolean");
    }
    if (value.freeform !== (actionId === "explore.talk_freeform")) {
      throw new Error("freeform must be true exactly for explore.talk_freeform");
    }
    var params = validateContextActionsAffordanceParams(actionId, value.params);
    return {
      action_id: actionId,
      label: label,
      params: params,
      freeform: value.freeform,
      navigation: false,
      enabled: enabled,
      disabled_reason: disabledReason,
    };
  }

  function validateContextActionsExplorationForm(payload) {
    requireExactFields(
      payload,
      "context_actions exploration form",
      ["schema_version", "available", "kind", "affordances", "suggestions"],
      []
    );
    if (payload.available !== true || payload.kind !== "exploration") {
      throw new Error("exploration form must be available with kind exploration");
    }
    if (
      !Array.isArray(payload.affordances) ||
      payload.affordances.length > CONTEXT_ACTIONS_MAX_AFFORDANCES
    ) {
      throw new Error(
        "affordances must be a list of at most " + CONTEXT_ACTIONS_MAX_AFFORDANCES + " entries"
      );
    }
    var affordances = payload.affordances.map(validateContextActionsAffordance);
    return {
      schema_version: 5,
      available: true,
      kind: "exploration",
      affordances: affordances,
      suggestions: validateSuggestions(payload.suggestions),
    };
  }

  // Whether a label contains at least one CJK Unified Ideograph.
  function hasCjk(text) {
    if (typeof text !== "string") {
      return false;
    }
    for (var index = 0; index < text.length; index++) {
      var code = text.charCodeAt(index);
      if (code >= 0x4e00 && code <= 0x9fff) {
        return true;
      }
    }
    return false;
  }

  // Validate one suggestion card's params: for a known_action card the
  // canonical validator-normalized payload of its action (safe ints, bounded
  // strings, plus the literal boolean true for the explore.look room-survey
  // form — any other boolean rejected); for a freeform card the exact
  // {"npc_id": positive int} binding.
  function validateSuggestionParams(actionCode, kind, params) {
    if (!isPlainObject(params)) {
      throw new Error("suggestion params must be a JSON object");
    }
    var keys = Object.keys(params);
    if (keys.length < 1 || keys.length > MAX_OPTION_PARAMS) {
      throw new Error("suggestion params exceed their bound");
    }
    if (kind === "freeform") {
      return validateContextActionsAffordanceParams(actionCode, params);
    }
    for (var i = 0; i < keys.length; i++) {
      var child = params[keys[i]];
      if (typeof child === "boolean") {
        if (actionCode === "explore.look" && params.room === true && keys.length === 1) {
          continue;
        }
        throw new Error("suggestion params carry an unsupported boolean");
      }
      if (typeof child === "number") {
        if (!Number.isInteger(child) || child < 0 || child > MAX_SAFE_INTEGER) {
          throw new Error("suggestion params integer is out of bounds");
        }
        continue;
      }
      if (typeof child === "string") {
        if (codePoints(child) > OPTIONS_MAX_PARAM_STRING) {
          throw new Error("suggestion params string exceeds its bound");
        }
        continue;
      }
      throw new Error("suggestion params carry an unsupported value type");
    }
    return validateContextActionsAffordanceParams(actionCode, params);
  }

  function validateSuggestionCard(value) {
    requireExactFields(
      value,
      "suggestion card",
      ["kind", "action_code", "label", "params"],
      ["hint"]
    );
    var kind = value.kind;
    if (OPTIONS_CARD_KINDS.indexOf(kind) === -1) {
      throw new Error("suggestion card kind is not a stable value");
    }
    var actionCode = validateIdentifier(value.action_code, "action_code");
    if (CONTEXT_ACTIONS_ACTION_CODES.indexOf(actionCode) === -1) {
      throw new Error("action_code is not a registered exploration action");
    }
    if ((kind === "freeform") !== (actionCode === OPTIONS_FREEFORM_ACTION_CODE)) {
      throw new Error("freeform cards must carry exactly explore.talk_freeform");
    }
    var label = requireString(value.label, "label", MAX_OPTION_LABEL);
    var labelPoints = codePoints(label);
    if (labelPoints < 1 || labelPoints > MAX_OPTION_LABEL) {
      throw new Error("suggestion label must be 1..24 code points");
    }
    if (!hasCjk(label)) {
      throw new Error("suggestion label must contain a CJK code point");
    }
    var params = validateSuggestionParams(actionCode, kind, value.params);
    var hint = null;
    if (
      Object.prototype.hasOwnProperty.call(value, "hint") &&
      value.hint !== null
    ) {
      hint = requireString(value.hint, "hint", MAX_OPTION_HINT);
    }
    return {
      kind: kind,
      action_code: actionCode,
      label: label,
      params: params,
      hint: hint,
    };
  }

  // Validate one exact suggestions envelope: status decides the exact key set
  // (status alone for generating/unavailable; status + cards for
  // ready/degraded); ready sets number 3..5, degraded sets 0..5.
  function validateSuggestions(value) {
    if (!isPlainObject(value)) {
      throw new Error("suggestions must be a JSON object");
    }
    var status = value.status;
    if (OPTIONS_STATUSES.indexOf(status) === -1) {
      throw new Error("suggestions status is not a stable value");
    }
    if (status === "generating" || status === "unavailable") {
      var statusKeys = Object.keys(value);
      if (statusKeys.length !== 1 || statusKeys[0] !== "status") {
        throw new Error("generating/unavailable suggestions carry only status");
      }
      return { status: status };
    }
    var keys = Object.keys(value);
    if (keys.length !== 2 || keys.indexOf("status") === -1 || keys.indexOf("cards") === -1) {
      throw new Error("ready/degraded suggestions carry exactly status and cards");
    }
    if (!Array.isArray(value.cards)) {
      throw new Error("suggestions cards must be an array");
    }
    var minimum = status === "ready" ? 3 : 0;
    if (value.cards.length < minimum || value.cards.length > MAX_OPTION_CARDS) {
      throw new Error(
        "suggestions cards must number " + minimum + ".." + MAX_OPTION_CARDS
      );
    }
    var cards = value.cards.map(validateSuggestionCard);
    return { status: status, cards: cards };
  }

  function validateContextActionsPanel(payload) {
    requireExactFields(
      payload,
      "context_actions panel",
      ["schema_version", "available", "kind"],
      ["session", "participants", "root_actions", "secondary_actions", "skills", "affordances", "suggestions"]
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 5) {
      throw new Error("unsupported context_actions panel schema_version");
    }
    if (payload.available !== true) {
      throw new Error("context_actions panel must be available");
    }
    if (payload.kind === "exploration") {
      return validateContextActionsExplorationForm(payload);
    }
    if (payload.kind !== "combat") {
      throw new Error("context_actions panel kind must be combat or exploration");
    }
    requireExactFields(
      payload,
      "context_actions panel",
      ["schema_version", "available", "kind", "session", "participants", "root_actions", "secondary_actions", "skills", "suggestions"],
      []
    );

    var session = validateSession(payload.session);

    var participants = payload.participants;
    if (!Array.isArray(participants) || participants.length > MAX_PARTICIPANTS) {
      throw new Error("participants exceed their bound");
    }
    participants.forEach(validateParticipant);

    var rootActions = validateActionKeys(payload.root_actions, "root_actions");
    var secondaryActions = validateActionKeys(payload.secondary_actions, "secondary_actions");

    if (session.state === "ready") {
      if (
        rootActions.length !== ROOT_ACTIONS.length ||
        rootActions.some(function (key, index) { return key !== ROOT_ACTIONS[index]; })
      ) {
        throw new Error("ready session must expose the exact root actions");
      }
      if (
        secondaryActions.length !== SECONDARY_ACTIONS.length ||
        secondaryActions.some(function (key, index) { return key !== SECONDARY_ACTIONS[index]; })
      ) {
        throw new Error("ready session must expose confirmed Forfeit");
      }
    } else {
      if (rootActions.length > 0) {
        throw new Error("recovery session exposes no cast or flee action");
      }
      if (
        secondaryActions.length !== RECOVERY_SECONDARY_ACTIONS.length ||
        secondaryActions.some(function (key, index) { return key !== RECOVERY_SECONDARY_ACTIONS[index]; })
      ) {
        throw new Error("recovery session must retain confirmed Forfeit");
      }
    }

    var skills = payload.skills;
    if (!Array.isArray(skills) || skills.length > SKILL_CATEGORY_KEYS.length) {
      throw new Error("category groups exceed their bound");
    }
    var skillViews = [];
    skills.forEach(function (category) {
      requireExactFields(
        category,
        "category group",
        ["category", "label", "groups"],
        []
      );
      validateIdentifier(category.category, "category key");
      if (SKILL_CATEGORY_KEYS.indexOf(category.category) === -1) {
        throw new Error("category key is not a registered category");
      }
      var label = requireString(category.label, "category label", MAX_LABEL);
      if (!label.trim()) {
        throw new Error("category label must be non-empty");
      }
      if (!Array.isArray(category.groups) || category.groups.length === 0) {
        throw new Error("category groups must be non-empty");
      }
      category.groups.forEach(function (subGroup) {
        requireExactFields(
          subGroup,
          "skill group",
          ["group", "label", "skills"],
          []
        );
        if (subGroup.group === null) {
          if (subGroup.label !== null) {
            throw new Error("a null group key requires a null label");
          }
        } else {
          // A bounded non-empty string, not an identifier: sexual-act
          // sub-groups are keyed by their Traditional Chinese line names
          // (獨處, 羞恥, ...), mirroring the character panel's contract.
          requireString(subGroup.group, "skill group key", CHARACTER_MAX_KEY);
          if (!subGroup.group.trim()) {
            throw new Error("a non-null group key must be non-empty");
          }
          if (typeof subGroup.label !== "string" || !subGroup.label.trim()) {
            throw new Error("a non-null group key requires a non-empty label");
          }
        }
        if (!Array.isArray(subGroup.skills) || subGroup.skills.length === 0) {
          throw new Error("skill group skills must be non-empty");
        }
        subGroup.skills.forEach(function (skill) {
          validateSkill(skill);
          skillViews.push(skill);
        });
      });
    });
    if (skillViews.length > MAX_SKILLS) {
      throw new Error("flattened skill count exceeds their bound");
    }

    var identitySet = {};
    participants.forEach(function (participant) {
      identitySet[participant.identity] = true;
    });
    skillViews.forEach(function (skill) {
      skill.targets.forEach(function (target) {
        if (!identitySet[target]) {
          throw new Error("skill targets must reference a presented participant");
        }
      });
    });
    var skillKeys = {};
    skillViews.forEach(function (skill) {
      if (skillKeys[skill.key]) {
        throw new Error("skill keys must be unique");
      }
      skillKeys[skill.key] = true;
    });
    // Combat proposals are out of scope: the combat form always reports the
    // suggestions envelope as exactly unavailable.
    var combatSuggestions = validateSuggestions(payload.suggestions);
    if (
      combatSuggestions.status !== "unavailable" ||
      Object.keys(combatSuggestions).length !== 1
    ) {
      throw new Error("combat suggestions must be exactly unavailable");
    }
    return Object.assign({}, payload, { suggestions: combatSuggestions });
  }

  // Exact available local_map panel v1 schema (design D10a).
  function requireNodeId(value, field) {
    requireString(value, field, LOCAL_MAP_MAX_NODE_ID);
    if (!NODE_ID_RE.test(value)) {
      throw new Error(field + " is not a canonical node ID");
    }
    return value;
  }

  function requireExitRef(value, field) {
    if (
      typeof value !== "string" ||
      value.length < 1 ||
      value.length > LOCAL_MAP_MAX_EXIT_REF
    ) {
      throw new Error(
        field + " must be 1.." + LOCAL_MAP_MAX_EXIT_REF + " ASCII characters"
      );
    }
    // eslint-disable-next-line no-control-regex
    if (/[^\x00-\x7F]/.test(value)) {
      throw new Error(field + " must be ASCII");
    }
    return value;
  }

  function requireCoord(value, field) {
    requireInt(value, field, LOCAL_MAP_COORD_MIN, LOCAL_MAP_COORD_MAX);
    return value;
  }

  function validateLocalMapAction(value) {
    if (value === null) {
      return null;
    }
    requireExactFields(value, "action", ["kind", "exit_ref", "destination"], []);
    if (LOCAL_MAP_ACTION_KINDS.indexOf(value.kind) === -1) {
      throw new Error("action kind is not a stable value");
    }
    requireExitRef(value.exit_ref, "action.exit_ref");
    requireNodeId(value.destination, "action.destination");
    return {
      kind: value.kind,
      exit_ref: value.exit_ref,
      destination: value.destination,
    };
  }

  function validateLocalMapNode(value) {
    requireExactFields(
      value,
      "node",
      ["id", "label", "x", "y", "visibility", "current", "anchor", "landmark", "action"],
      []
    );
    var nodeId = requireNodeId(value.id, "node.id");
    var label = requireString(value.label, "node.label", LOCAL_MAP_MAX_STRING);
    if (!label.trim()) {
      throw new Error("node.label must be non-empty");
    }
    var x = requireCoord(value.x, "node.x");
    var y = requireCoord(value.y, "node.y");
    if (LOCAL_MAP_VISIBILITIES.indexOf(value.visibility) === -1) {
      throw new Error("node.visibility is not a stable value");
    }
    var current = requireBool(value.current, "current");
    var anchor = requireBool(value.anchor, "anchor");
    var landmark = requireBool(value.landmark, "landmark");
    var action = validateLocalMapAction(value.action);
    if (value.visibility === "current" && !current) {
      throw new Error("the current node must carry current=true");
    }
    if (current && value.visibility !== "current") {
      throw new Error("a non-current node must not carry current=true");
    }
    return {
      id: nodeId,
      label: label,
      x: x,
      y: y,
      visibility: value.visibility,
      current: current,
      anchor: anchor,
      landmark: landmark,
      action: action,
    };
  }

  function validateLocalMapEdge(value) {
    requireExactFields(
      value,
      "edge",
      ["source", "destination", "label", "known", "traversable"],
      []
    );
    var source = requireNodeId(value.source, "edge.source");
    var destination = requireNodeId(value.destination, "edge.destination");
    var label = requireString(value.label, "edge.label", LOCAL_MAP_MAX_STRING);
    var known = requireBool(value.known, "known");
    var traversable = requireBool(value.traversable, "traversable");
    if (source === destination) {
      throw new Error("an edge must connect two distinct nodes");
    }
    return {
      source: source,
      destination: destination,
      label: label,
      known: known,
      traversable: traversable,
    };
  }

  function validateLineageNode(value) {
    requireExactFields(
      value,
      "lineage node",
      [
        "skill_key",
        "display_name_zh",
        "owned",
        "usable",
        "level",
        "xp_into_level",
        "xp_to_next_level",
        "capped",
        "prereq_text_zh",
      ],
      []
    );
    var skillKey = validateIdentifier(value.skill_key, "skill_key");
    var displayName = requireString(
      value.display_name_zh,
      "display_name_zh",
      LINEAGE_MAX_TEXT
    );
    if (!displayName.trim()) {
      throw new Error("display_name_zh must be non-empty");
    }
    var prereqText = requireString(
      value.prereq_text_zh,
      "prereq_text_zh",
      LINEAGE_MAX_TEXT
    );
    return {
      skill_key: skillKey,
      display_name_zh: displayName,
      owned: requireBool(value.owned, "owned"),
      usable: requireBool(value.usable, "usable"),
      level: requireInt(value.level, "level", 0, MAX_SAFE_INTEGER),
      xp_into_level: requireNumber(
        value.xp_into_level,
        "xp_into_level",
        0,
        MAX_SAFE_INTEGER
      ),
      xp_to_next_level: requireNumber(
        value.xp_to_next_level,
        "xp_to_next_level",
        0,
        MAX_SAFE_INTEGER
      ),
      capped: requireBool(value.capped, "capped"),
      prereq_text_zh: prereqText,
    };
  }

  function validateLineageChain(value) {
    requireExactFields(
      value,
      "lineage chain",
      ["root_skill_key", "element_or_style_zh", "consumed", "meter", "nodes"],
      []
    );
    var rootKey = validateIdentifier(value.root_skill_key, "root_skill_key");
    var label = requireString(
      value.element_or_style_zh,
      "element_or_style_zh",
      LINEAGE_MAX_TEXT
    );
    if (!label.trim()) {
      throw new Error("element_or_style_zh must be non-empty");
    }
    if (!Array.isArray(value.nodes) || value.nodes.length < 1 || value.nodes.length > LINEAGE_MAX_NODES_PER_CHAIN) {
      throw new Error(
        "nodes must be a list of 1.." + LINEAGE_MAX_NODES_PER_CHAIN + " entries"
      );
    }
    var nodeViews = value.nodes.map(validateLineageNode);
    if (nodeViews[0].skill_key !== rootKey) {
      throw new Error("truncated chains keep their head: nodes[0] must be the root");
    }
    return {
      root_skill_key: rootKey,
      element_or_style_zh: label,
      consumed: requireBool(value.consumed, "consumed"),
      meter: requireNumber(value.meter, "meter", 0, 1),
      nodes: nodeViews,
    };
  }

  function validateLineagePanel(payload) {
    requireExactFields(
      payload,
      "lineage panel",
      ["schema_version", "available", "kind", "completed_count", "total_count", "chains"],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 1) {
      throw new Error("unsupported lineage panel schema_version");
    }
    // Mirror the Python validate_lineage: the exported validator rejects the
    // unavailable discriminator directly (rubber-duck R2-2); the dispatcher's
    // guard is defense in depth, not the only gate.
    requireBool(payload.available, "available");
    if (payload.available !== true) {
      throw new Error("lineage panel available must be true in the available form");
    }
    if (payload.kind !== "lineage") {
      throw new Error("lineage panel kind must be lineage");
    }
    var completed = requireInt(
      payload.completed_count,
      "completed_count",
      0,
      MAX_SAFE_INTEGER
    );
    var total = requireInt(payload.total_count, "total_count", 0, MAX_SAFE_INTEGER);
    if (completed > total) {
      throw new Error("completed_count must not exceed total_count");
    }
    if (!Array.isArray(payload.chains) || payload.chains.length > LINEAGE_MAX_CHAINS) {
      throw new Error(
        "chains must be a list of at most " + LINEAGE_MAX_CHAINS + " entries"
      );
    }
    var chainViews = payload.chains.map(validateLineageChain);
    var result = {
      schema_version: 1,
      available: true,
      kind: "lineage",
      completed_count: completed,
      total_count: total,
      chains: chainViews,
    };
    // Envelope guarantee: the presenter truncates until a real payload fits;
    // the validator enforces the serialized byte size directly and fails
    // closed over the envelope.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("lineage payload exceeds the OOB envelope limit");
    }
    return result;
  }

  function validateLocalMapPanel(payload) {
    requireExactFields(
      payload,
      "local_map panel",
      ["schema_version", "available", "layer", "current_node", "title", "nodes", "edges", "legend"],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 1) {
      throw new Error("unsupported local_map panel schema_version");
    }
    if (LOCAL_MAP_LAYERS.indexOf(payload.layer) === -1) {
      throw new Error("layer is not a stable value");
    }
    var currentNode = requireNodeId(payload.current_node, "current_node");
    var prefix = currentNode.split(":")[0];
    if (payload.layer === "grid" && prefix !== "grid") {
      throw new Error("a grid-layer payload must have a grid current node");
    }
    if (payload.layer === "wilderness" && prefix !== "wild") {
      throw new Error("a wilderness-layer payload must have a wild current node");
    }
    if (
      (payload.layer === "instance" || payload.layer === "interior") &&
      prefix !== "room"
    ) {
      throw new Error("an instance/interior payload must have a room current node");
    }
    var title = requireString(payload.title, "title", LOCAL_MAP_MAX_TITLE);
    if (!title.trim()) {
      throw new Error("title must be non-empty");
    }

    var nodes = payload.nodes;
    if (!Array.isArray(nodes) || nodes.length < 1 || nodes.length > LOCAL_MAP_MAX_NODES) {
      throw new Error("nodes must be a list of 1.." + LOCAL_MAP_MAX_NODES + " entries");
    }
    var nodeViews = nodes.map(validateLocalMapNode);
    var currentCount = nodeViews.filter(function (node) {
      return node.current;
    }).length;
    if (currentCount !== 1) {
      throw new Error("the payload must mark exactly one current node");
    }
    if (!nodeViews.some(function (node) {
      return node.id === currentNode;
    })) {
      throw new Error("current_node must be present in nodes");
    }
    var nodeIds = nodeViews.map(function (node) {
      return node.id;
    });
    var unique = {};
    nodeIds.forEach(function (id) {
      if (unique[id]) {
        throw new Error("node ids must be unique");
      }
      unique[id] = true;
    });

    var edges = payload.edges;
    if (!Array.isArray(edges) || edges.length > LOCAL_MAP_MAX_EDGES) {
      throw new Error("edges must be a list of at most " + LOCAL_MAP_MAX_EDGES + " entries");
    }
    var edgeViews = edges.map(validateLocalMapEdge);
    edgeViews.forEach(function (edge) {
      if (!unique[edge.source]) {
        throw new Error("edge.source must reference a presented node");
      }
      if (!unique[edge.destination]) {
        throw new Error("edge.destination must reference a presented node");
      }
    });

    var legend = payload.legend;
    if (!Array.isArray(legend) || legend.length > LOCAL_MAP_MAX_LEGEND) {
      throw new Error("legend must be a list of at most " + LOCAL_MAP_MAX_LEGEND + " entries");
    }
    var legendViews = legend.map(function (entry) {
      var text = requireString(entry, "legend", LOCAL_MAP_MAX_STRING);
      if (!text.trim()) {
        throw new Error("legend entries must be non-empty");
      }
      return text;
    });

    var result = {
      schema_version: 1,
      available: true,
      layer: payload.layer,
      current_node: currentNode,
      title: title,
      nodes: nodeViews,
      edges: edgeViews,
      legend: legendViews,
    };
    // Envelope guarantee (design D10a): the per-field bounds are ceilings, not
    // a guarantee that any combination of them fits, so the validator enforces
    // the serialized byte size directly and fails closed over the envelope.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("local_map payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // -------------------------------------------------------------------------
  // services panel validator (mirror of web.webclient.presentation.services,
  // design D4). Shared bounds are guarded by a dual-direction parity test.
  // -------------------------------------------------------------------------

  function validateServicesAction(value) {
    requireExactFields(
      value,
      "service action",
      ["action_id", "label", "enabled", "disabled_reason", "quantity"],
      []
    );
    validateIdentifier(value.action_id, "action_id");
    if (SERVICES_ACTIONS.indexOf(value.action_id) === -1) {
      throw new Error("service action_id is not a registered service action");
    }
    var label = requireString(value.label, "label", SERVICES_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("action label must be non-empty");
    }
    var enabled = requireBool(value.enabled, "enabled");
    var disabledReason = value.disabled_reason;
    if (disabledReason === null) {
      if (!enabled) {
        throw new Error("a disabled action requires a disabled_reason");
      }
    } else {
      requireExactFields(
        disabledReason,
        "disabled_reason",
        ["code", "message"],
        []
      );
      validateIdentifier(disabledReason.code, "disabled_reason code");
      var message = requireString(
        disabledReason.message,
        "disabled_reason message",
        SERVICES_MAX_REASON_MESSAGE
      );
      if (!message.trim()) {
        throw new Error("disabled_reason message must be non-empty");
      }
      if (enabled) {
        throw new Error("an enabled action must not carry a disabled_reason");
      }
    }
    var quantity = value.quantity;
    if (quantity === null) {
      if (
        enabled &&
        (value.action_id === SERVICES_BUY || value.action_id === SERVICES_SELL)
      ) {
        throw new Error("a buy/sell action requires quantity bounds");
      }
    } else {
      if (
        value.action_id !== SERVICES_BUY &&
        value.action_id !== SERVICES_SELL
      ) {
        throw new Error("only buy/sell actions may carry quantity bounds");
      }
      requireExactFields(quantity, "quantity bounds", ["min", "max"], []);
      var minimum = requireInt(
        quantity.min,
        "quantity.min",
        SERVICES_MIN_QUANTITY,
        SERVICES_MAX_QUANTITY
      );
      var maximum = requireInt(
        quantity.max,
        "quantity.max",
        SERVICES_MIN_QUANTITY,
        SERVICES_MAX_QUANTITY
      );
      if (minimum > maximum) {
        throw new Error("quantity min must not exceed max");
      }
    }
    return value;
  }

  function validateServicesRegistration(value) {
    requireExactFields(value, "registration", ["registered", "register"], []);
    var registered = requireBool(value.registered, "registered");
    var register = validateServicesAction(value.register);
    if (register.action_id !== "guild.register") {
      throw new Error("registration.register must be guild.register");
    }
    if (registered === register.enabled) {
      throw new Error(
        "registration.register enabled state must contradict registered"
      );
    }
    return value;
  }

  function validateServicesBoardRow(value) {
    requireExactFields(
      value,
      "board row",
      ["definition_key", "display_name", "objective_summary", "reward_summary", "rank", "accept"],
      []
    );
    var definitionKey = requireString(value.definition_key, "definition_key", SERVICES_MAX_KEY);
    if (!definitionKey.trim()) {
      throw new Error("board definition_key must be non-empty");
    }
    var boardDisplayName = requireString(value.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
    if (!boardDisplayName.trim()) {
      throw new Error("board display_name must be non-empty");
    }
    var objectiveSummary = requireString(value.objective_summary, "objective_summary", SERVICES_MAX_SUMMARY);
    if (!objectiveSummary.trim()) {
      throw new Error("board objective_summary must be non-empty");
    }
    var rewardSummary = requireString(value.reward_summary, "reward_summary", SERVICES_MAX_SUMMARY);
    if (!rewardSummary.trim()) {
      throw new Error("board reward_summary must be non-empty");
    }
    var boardRank = requireString(value.rank, "rank", SERVICES_MAX_RANK_KEY);
    if (!boardRank.trim()) {
      throw new Error("board rank must be non-empty");
    }
    var accept = validateServicesAction(value.accept);
    if (accept.action_id !== "guild.quest_accept") {
      throw new Error("board accept must be guild.quest_accept");
    }
    return value;
  }

  function validateServicesQuestRow(value) {
    requireExactFields(
      value,
      "quest row",
      [
        "quest_id",
        "definition_key",
        "display_name",
        "state",
        "stage_index",
        "stage_progress",
        "objective_summary",
        "deadline_line",
        "detail",
        "abandon",
        "turnin",
        "tracked",
      ],
      []
    );
    var questId = requireString(value.quest_id, "quest_id", SERVICES_MAX_KEY);
    if (!questId.trim()) {
      throw new Error("quest_id must be non-empty");
    }
    var questDefinitionKey = requireString(value.definition_key, "definition_key", SERVICES_MAX_KEY);
    if (!questDefinitionKey.trim()) {
      throw new Error("quest definition_key must be non-empty");
    }
    var questDisplayName = requireString(value.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
    if (!questDisplayName.trim()) {
      throw new Error("quest display_name must be non-empty");
    }
    if (SERVICES_QUEST_STATES.indexOf(value.state) === -1) {
      throw new Error("quest state is not a stable value");
    }
    requireInt(value.stage_index, "stage_index", 0, MAX_SAFE_INTEGER);
    requireInt(value.stage_progress, "stage_progress", 0, MAX_SAFE_INTEGER);
    var questObjective = requireString(value.objective_summary, "objective_summary", SERVICES_MAX_SUMMARY);
    if (!questObjective.trim()) {
      throw new Error("quest objective_summary must be non-empty");
    }
    if (value.deadline_line !== null) {
      var deadline = requireString(
        value.deadline_line,
        "deadline_line",
        SERVICES_MAX_DEADLINE_LINE
      );
      if (!deadline.trim()) {
        throw new Error("deadline_line must be non-empty when set");
      }
    }
    var detail = requireString(value.detail, "detail", SERVICES_MAX_DETAIL);
    if (!detail.trim()) {
      throw new Error("quest detail must be non-empty");
    }
    var abandon = validateServicesAction(value.abandon);
    var turnin = validateServicesAction(value.turnin);
    if (abandon.action_id !== "guild.quest_abandon") {
      throw new Error("quest abandon must be guild.quest_abandon");
    }
    if (turnin.action_id !== "guild.quest_turnin") {
      throw new Error("quest turnin must be guild.quest_turnin");
    }
    requireBool(value.tracked, "tracked");
    return value;
  }

  function validateServicesRank(value) {
    requireExactFields(
      value,
      "rank",
      ["rank", "merit", "next_rank", "next_threshold", "eligible", "exam_start"],
      []
    );
    if (value.rank !== null) {
      var rankKey = requireString(value.rank, "rank", SERVICES_MAX_RANK_KEY);
      if (!rankKey.trim()) {
        throw new Error("rank must be non-empty when set");
      }
    }
    requireInt(value.merit, "merit", 0, MAX_SAFE_INTEGER);
    if (value.next_rank !== null) {
      requireString(value.next_rank, "next_rank", SERVICES_MAX_RANK_KEY);
    }
    if (value.next_threshold !== null) {
      requireInt(value.next_threshold, "next_threshold", 1, MAX_SAFE_INTEGER);
    }
    if ((value.next_rank === null) !== (value.next_threshold === null)) {
      throw new Error(
        "next_rank and next_threshold must both be set or null"
      );
    }
    var eligible = requireBool(value.eligible, "eligible");
    var examStart = validateServicesAction(value.exam_start);
    if (examStart.action_id !== "guild.exam_start") {
      throw new Error("rank exam_start must be guild.exam_start");
    }
    if (eligible !== examStart.enabled) {
      throw new Error("rank eligible must match exam_start enabled");
    }
    return value;
  }

  function validateServicesGuild(value) {
    requireExactFields(value, "guild", ["registration", "board", "quests", "rank"], []);
    validateServicesRegistration(value.registration);
    if (!Array.isArray(value.board) || value.board.length > SERVICES_MAX_BOARD_ROWS) {
      throw new Error("board must be a list of at most " + SERVICES_MAX_BOARD_ROWS + " rows");
    }
    value.board.forEach(validateServicesBoardRow);
    if (!Array.isArray(value.quests) || value.quests.length > SERVICES_MAX_QUEST_ROWS) {
      throw new Error("quests must be a list of at most " + SERVICES_MAX_QUEST_ROWS + " rows");
    }
    value.quests.forEach(validateServicesQuestRow);
    if (value.rank !== null) {
      validateServicesRank(value.rank);
    }
    return value;
  }

  function validateServicesStockRow(value) {
    requireExactFields(
      value,
      "stock row",
      ["item_key", "display_name", "buy_copper", "sell_copper", "stock", "max_stock", "buy"],
      []
    );
    var stockItemKey = requireString(value.item_key, "item_key", SERVICES_MAX_KEY);
    if (!stockItemKey.trim()) {
      throw new Error("stock item_key must be non-empty");
    }
    var stockDisplayName = requireString(value.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
    if (!stockDisplayName.trim()) {
      throw new Error("stock display_name must be non-empty");
    }
    requireInt(value.buy_copper, "buy_copper", 0, MAX_SAFE_INTEGER);
    requireInt(value.sell_copper, "sell_copper", 0, MAX_SAFE_INTEGER);
    requireInt(value.stock, "stock", 0, MAX_SAFE_INTEGER);
    requireInt(value.max_stock, "max_stock", 1, MAX_SAFE_INTEGER);
    var buy = validateServicesAction(value.buy);
    if (buy.action_id !== SERVICES_BUY) {
      throw new Error("stock buy must be shop.buy");
    }
    return value;
  }

  function validateServicesSellableRow(value) {
    requireExactFields(
      value,
      "sellable row",
      ["item_key", "display_name", "sell_copper", "held", "sell"],
      []
    );
    var sellableItemKey = requireString(value.item_key, "item_key", SERVICES_MAX_KEY);
    if (!sellableItemKey.trim()) {
      throw new Error("sellable item_key must be non-empty");
    }
    var sellableDisplayName = requireString(value.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
    if (!sellableDisplayName.trim()) {
      throw new Error("sellable display_name must be non-empty");
    }
    requireInt(value.sell_copper, "sell_copper", 0, MAX_SAFE_INTEGER);
    requireInt(value.held, "held", 1, MAX_SAFE_INTEGER);
    var sell = validateServicesAction(value.sell);
    if (sell.action_id !== SERVICES_SELL) {
      throw new Error("sellable sell must be shop.sell");
    }
    return value;
  }

  function validateServicesShop(value) {
    requireExactFields(value, "shop", ["open", "stock", "sellable"], []);
    requireBool(value.open, "open");
    if (!Array.isArray(value.stock) || value.stock.length > SERVICES_MAX_STOCK_ROWS) {
      throw new Error("stock must be a list of at most " + SERVICES_MAX_STOCK_ROWS + " rows");
    }
    value.stock.forEach(validateServicesStockRow);
    if (
      !Array.isArray(value.sellable) ||
      value.sellable.length > SERVICES_MAX_SELLABLE_ROWS
    ) {
      throw new Error(
        "sellable must be a list of at most " + SERVICES_MAX_SELLABLE_ROWS + " rows"
      );
    }
    value.sellable.forEach(validateServicesSellableRow);
    return value;
  }

  function requirePresentationKey(value, field) {
    if (
      typeof value !== "string" ||
      value.length < 1 ||
      value.length > SERVICES_MAX_PRESENTATION_KEY ||
      !/^[a-z_]+$/.test(value)
    ) {
      throw new Error(
        field + " must be 1.." + SERVICES_MAX_PRESENTATION_KEY + " lowercase ASCII letters or underscores"
      );
    }
    return value;
  }

  function requirePresentation(value, field) {
    if (value === null) {
      return null;
    }
    if (!isPlainObject(value)) {
      throw new Error(field + " must be a JSON object or null");
    }
    requireExactFields(value, field, ["kind", "icon_key", "rarity", "summary"], []);
    var kind = requirePresentationKey(value.kind, field + ".kind");
    var iconKey = requirePresentationKey(value.icon_key, field + ".icon_key");
    var rarity = requirePresentationKey(value.rarity, field + ".rarity");
    var summary = value.summary;
    if (typeof summary !== "string") {
      throw new Error(field + ".summary must be a string");
    }
    if (codePoints(summary) < 1 || codePoints(summary) > SERVICES_MAX_PRESENTATION_SUMMARY) {
      throw new Error(
        field + ".summary must be 1.." + SERVICES_MAX_PRESENTATION_SUMMARY + " Unicode code points"
      );
    }
    return value;
  }

  function validateServicesInventory(value) {
    requireExactFields(value, "inventory", ["rows", "wallet"], []);
    var rows = value.rows;
    if (!Array.isArray(rows) || rows.length > SERVICES_MAX_INVENTORY_ROWS) {
      throw new Error(
        "inventory rows must be a list of at most " + SERVICES_MAX_INVENTORY_ROWS + " entries"
      );
    }
    requireInt(value.wallet, "wallet", 0, MAX_SAFE_INTEGER);
    rows.forEach(function (row) {
      requireExactFields(
        row,
        "inventory row",
        [
          "item_key",
          "display_name",
          "held",
          "equipped",
          "presentation",
          "action",
        ],
        []
      );
      var inventoryItemKey = requireString(row.item_key, "item_key", SERVICES_MAX_KEY);
      if (!inventoryItemKey.trim()) {
        throw new Error("inventory item_key must be non-empty");
      }
      var inventoryDisplayName = requireString(row.display_name, "display_name", SERVICES_MAX_DISPLAY_NAME);
      if (!inventoryDisplayName.trim()) {
        throw new Error("inventory display_name must be non-empty");
      }
      requireInt(row.held, "held", 1, MAX_SAFE_INTEGER);
      requireBool(row.equipped, "equipped");
      requirePresentation(row.presentation, "inventory row.presentation");
      if (row.action !== null) {
        validateServicesAction(row.action);
        if (
          row.action.action_id !== "inventory.use" &&
          row.action.action_id !== "inventory.toggle_equip"
        ) {
          throw new Error("inventory row action id is not allowed");
        }
      }
    });
    return value;
  }

  function validateServicesPagination(value) {
    requireExactFields(
      value,
      "pagination",
      ["board_total", "quest_total", "stock_total", "sellable_total", "inventory_total"],
      []
    );
    requireInt(value.board_total, "board_total", 0, SERVICES_MAX_BOARD_ROWS);
    requireInt(value.quest_total, "quest_total", 0, SERVICES_MAX_QUEST_ROWS);
    requireInt(value.stock_total, "stock_total", 0, SERVICES_MAX_STOCK_ROWS);
    requireInt(value.sellable_total, "sellable_total", 0, SERVICES_MAX_SELLABLE_ROWS);
    requireInt(value.inventory_total, "inventory_total", 0, SERVICES_MAX_INVENTORY_ROWS);
    return value;
  }

  // Exact available services panel v2 schema (design D4).
  function validateServicesPanel(payload) {
    requireExactFields(
      payload,
      "services panel",
      [
        "schema_version",
        "available",
        "kind",
        "host",
        "player",
        "guild",
        "shop",
        "inventory",
        "pagination",
      ],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 4) {
      throw new Error("unsupported services schema_version");
    }
    if (payload.available !== true || payload.kind !== "services") {
      throw new Error("services panel must be available with kind services");
    }

    if (payload.host !== null) {
      requireExactFields(payload.host, "host", ["identity", "display_name"], []);
      var identity = payload.host.identity;
      if (
        typeof identity !== "string" ||
        identity.length < 1 ||
        identity.length > SERVICES_MAX_KEY ||
        !/^[\x00-\x7F]+$/.test(identity)
      ) {
        throw new Error("host.identity must be 1..64 opaque ASCII characters");
      }
      requireString(
        payload.host.display_name,
        "host.display_name",
        SERVICES_MAX_HOST_DISPLAY_NAME
      );
    }

    var player = payload.player;
    requireExactFields(
      player,
      "player",
      ["wallet", "guild_registered", "guild_rank", "guild_merit", "next_rank", "next_threshold"],
      []
    );
    requireInt(player.wallet, "wallet", 0, MAX_SAFE_INTEGER);
    var guildRegistered = requireBool(player.guild_registered, "guild_registered");
    if (player.guild_rank !== null) {
      requireString(player.guild_rank, "guild_rank", SERVICES_MAX_RANK_KEY);
    }
    requireInt(player.guild_merit, "guild_merit", 0, MAX_SAFE_INTEGER);
    if (player.next_rank !== null) {
      requireString(player.next_rank, "next_rank", SERVICES_MAX_RANK_KEY);
    }
    if (player.next_threshold !== null) {
      requireInt(player.next_threshold, "next_threshold", 1, MAX_SAFE_INTEGER);
    }
    if ((player.next_rank === null) !== (player.next_threshold === null)) {
      throw new Error(
        "player next_rank and next_threshold must both be set or null"
      );
    }
    if (player.guild_rank === null && guildRegistered) {
      throw new Error(
        "an unregistered player must not carry a guild rank in the summary"
      );
    }

    var guild = payload.guild;
    var shop = payload.shop;
    var inventory = payload.inventory;
    if (guild !== null) {
      validateServicesGuild(guild);
    }
    if (shop !== null) {
      validateServicesShop(shop);
    }
    if (inventory !== null) {
      validateServicesInventory(inventory);
    }
    var pagination = validateServicesPagination(payload.pagination);
    validateServicesPaginationTotals(pagination, guild, shop, inventory);

    var result = {
      schema_version: 4,
      available: true,
      kind: "services",
      host: payload.host,
      player: {
        wallet: player.wallet,
        guild_registered: guildRegistered,
        guild_rank: player.guild_rank,
        guild_merit: player.guild_merit,
        next_rank: player.next_rank,
        next_threshold: player.next_threshold,
      },
      guild: guild,
      shop: shop,
      inventory: inventory,
      pagination: pagination,
    };
    // Envelope guarantee (design D4): per-field bounds are ceilings, not a
    // guarantee that any combination of them fits, so the validator enforces
    // the serialized byte size directly and fails closed over the envelope.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("services payload exceeds the OOB envelope limit");
    }
    return result;
  }

  function validateServicesPaginationTotals(pagination, guild, shop, inventory) {
    if (guild === null) {
      if (pagination.board_total !== 0 || pagination.quest_total !== 0) {
        throw new Error(
          "pagination board/quest totals must be zero when guild is null"
        );
      }
    } else {
      if (pagination.board_total !== guild.board.length) {
        throw new Error("pagination board_total must match shipped rows");
      }
      if (pagination.quest_total !== guild.quests.length) {
        throw new Error("pagination quest_total must match shipped rows");
      }
    }
    if (shop === null) {
      if (pagination.stock_total !== 0 || pagination.sellable_total !== 0) {
        throw new Error(
          "pagination stock/sellable totals must be zero when shop is null"
        );
      }
    } else {
      if (pagination.stock_total !== shop.stock.length) {
        throw new Error("pagination stock_total must match shipped rows");
      }
      if (pagination.sellable_total !== shop.sellable.length) {
        throw new Error("pagination sellable_total must match shipped rows");
      }
    }
    if (inventory === null) {
      if (pagination.inventory_total !== 0) {
        throw new Error(
          "pagination inventory_total must be zero when inventory is null"
        );
      }
    } else if (pagination.inventory_total !== inventory.rows.length) {
      throw new Error("pagination inventory_total must match shipped rows");
    }
  }

  // ---------------------------------------------------------------------------
  // creation panel v2 validator (mirror of web.webclient.presentation.creation).
  // ---------------------------------------------------------------------------

  function validateCreationPresetCard(value) {
    requireExactFields(
      value,
      "preset card",
      ["key", "display_name", "race", "race_description", "subrace", "emphasis", "background"],
      []
    );
    var key = validateIdentifier(value.key, "preset key");
    if (codePoints(key) > CREATION_MAX_PRESET_KEY) {
      throw new Error("preset key exceeds its bound");
    }
    requireString(value.display_name, "display_name", CREATION_MAX_DISPLAY_NAME);
    var race = validateIdentifier(value.race, "preset race");
    if (codePoints(race) > CREATION_MAX_RACE_KEY) {
      throw new Error("preset race exceeds its bound");
    }
    requireString(value.race_description, "race_description", CREATION_MAX_DESCRIPTION);
    if (value.subrace !== null) {
      var subrace = validateIdentifier(value.subrace, "preset subrace");
      if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
        throw new Error("preset subrace exceeds its bound");
      }
    }
    requireString(value.emphasis, "emphasis", CREATION_MAX_EMPHASIS);
    requireString(value.background, "background", CREATION_MAX_BACKGROUND);
    return value;
  }

  function validateCreationName(value) {
    requireExactFields(value, "name bounds", ["min_length", "max_length"], []);
    var minimum = requireInt(value.min_length, "min_length", 1, MAX_SAFE_INTEGER);
    var maximum = requireInt(value.max_length, "max_length", 1, MAX_SAFE_INTEGER);
    if (
      minimum !== CREATION_MIN_NAME_LENGTH ||
      maximum !== CREATION_MAX_NAME_LENGTH
    ) {
      throw new Error("name bounds do not match the advertised contract");
    }
    return value;
  }

  function validateCreationAdult(value) {
    requireExactFields(
      value,
      "adult bounds",
      ["age_minimum", "age_maximum", "apparent_age_minimum", "apparent_age_maximum"],
      []
    );
    var ageMinimum = requireInt(value.age_minimum, "age_minimum", 1, MAX_SAFE_INTEGER);
    var ageMaximum = requireInt(value.age_maximum, "age_maximum", 1, MAX_SAFE_INTEGER);
    var apparentMinimum = requireInt(
      value.apparent_age_minimum,
      "apparent_age_minimum",
      1,
      MAX_SAFE_INTEGER
    );
    var apparentMaximum = requireInt(
      value.apparent_age_maximum,
      "apparent_age_maximum",
      1,
      MAX_SAFE_INTEGER
    );
    if (
      ageMinimum !== CREATION_AGE_MINIMUM ||
      ageMaximum !== CREATION_AGE_MAXIMUM ||
      apparentMinimum !== CREATION_APPARENT_AGE_MINIMUM ||
      apparentMaximum !== CREATION_APPARENT_AGE_MAXIMUM
    ) {
      throw new Error("adult bounds do not match the advertised contract");
    }
    return value;
  }

  function validateCreationRaceOption(value) {
    requireExactFields(value, "race option", ["key", "description", "subraces"], []);
    var key = validateIdentifier(value.key, "race key");
    if (codePoints(key) > CREATION_MAX_RACE_KEY) {
      throw new Error("race key exceeds its bound");
    }
    requireString(value.description, "description", CREATION_MAX_DESCRIPTION);
    if (value.subraces !== null) {
      if (!Array.isArray(value.subraces) || value.subraces.length > CREATION_MAX_SUBRACES) {
        throw new Error("race subraces must be a list or null within its bound");
      }
      value.subraces.forEach(function (entry) {
        var subrace = validateIdentifier(entry, "race subrace");
        if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
          throw new Error("race subrace exceeds its bound");
        }
      });
    }
    return value;
  }

  function validateCreationSubraces(value) {
    if (!isPlainObject(value) || Object.keys(value).length > CREATION_MAX_SUBRACES) {
      throw new Error("subraces must be an object within its bound");
    }
    var keys = Object.keys(value);
    for (var i = 0; i < keys.length; i++) {
      var subraceKey = validateIdentifier(keys[i], "subrace key");
      if (codePoints(subraceKey) > CREATION_MAX_SUBRACE_KEY) {
        throw new Error("subrace key exceeds its bound");
      }
      var entry = value[keys[i]];
      requireExactFields(
        entry,
        "subrace entry",
        ["display_name_zh", "common_name_zh", "specialty"],
        []
      );
      requireString(entry.display_name_zh, "display_name_zh", CREATION_MAX_SPECIALTY);
      requireString(entry.common_name_zh, "common_name_zh", CREATION_MAX_SPECIALTY);
      requireString(entry.specialty, "specialty", CREATION_MAX_SPECIALTY);
    }
    return value;
  }

  function validateCreationAxis(value) {
    requireExactFields(
      value,
      "allocation axis",
      ["axis", "label", "explanation", "minimum", "maximum"],
      []
    );
    var axis = validateIdentifier(value.axis, "axis");
    if (CREATION_AXES.indexOf(axis) === -1) {
      throw new Error("axis " + axis + " is not an allocatable starting axis");
    }
    requireString(value.label, "label", CREATION_MAX_LABEL);
    requireString(value.explanation, "explanation", CREATION_MAX_EXPLANATION);
    var minimum = requireInt(value.minimum, "minimum", 0, MAX_SAFE_INTEGER);
    var maximum = requireInt(value.maximum, "maximum", 0, MAX_SAFE_INTEGER);
    if (minimum > maximum) {
      throw new Error("axis minimum must not exceed maximum");
    }
    return value;
  }

  function validateCreationProfile(value) {
    requireExactFields(value, "profile", ["race", "subrace", "budget", "axes"], []);
    var race = validateIdentifier(value.race, "profile race");
    if (codePoints(race) > CREATION_MAX_RACE_KEY) {
      throw new Error("profile race exceeds its bound");
    }
    if (value.subrace !== null) {
      var subrace = validateIdentifier(value.subrace, "profile subrace");
      if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
        throw new Error("profile subrace exceeds its bound");
      }
    }
    requireInt(value.budget, "budget", 0, MAX_SAFE_INTEGER);
    if (!Array.isArray(value.axes) || value.axes.length !== 7) {
      throw new Error("profile axes must contain exactly seven axes");
    }
    var axisKeys = {};
    value.axes.forEach(function (axis) {
      validateCreationAxis(axis);
      axisKeys[axis.axis] = true;
    });
    var expected = {};
    CREATION_AXES.forEach(function (axis) {
      expected[axis] = true;
    });
    var keyCount = Object.keys(axisKeys).length;
    var expectedCount = Object.keys(expected).length;
    if (keyCount !== expectedCount) {
      throw new Error("profile axes must match the seven starting axes");
    }
    return value;
  }

  function validateCreationCustom(value) {
    requireExactFields(
      value,
      "custom",
      ["name", "adult", "races", "subraces", "profiles", "affinity", "sex"],
      []
    );
    validateCreationName(value.name);
    validateCreationAdult(value.adult);
    if (!Array.isArray(value.races) || value.races.length === 0 || value.races.length > CREATION_MAX_RACES) {
      throw new Error("races must be a non-empty list within its bound");
    }
    value.races.forEach(validateCreationRaceOption);
    validateCreationSubraces(value.subraces);
    if (!Array.isArray(value.profiles) || value.profiles.length === 0 || value.profiles.length > CREATION_MAX_PROFILES) {
      throw new Error("profiles must be a non-empty list within its bound");
    }
    value.profiles.forEach(validateCreationProfile);
    validateCreationAffinity(value.affinity);
    validateCreationSex(value.sex);
    return value;
  }

  function validateCreationSex(value) {
    // Mirror of web.webclient.presentation.creation._validate_sex_options:
    // the list is exactly the sex vocabulary, in registry order, each option
    // carrying exactly {key, label} with a non-empty bounded label.
    if (
      !Array.isArray(value) ||
      value.length === 0 ||
      value.length > CREATION_MAX_SEX_OPTIONS
    ) {
      throw new Error("sex must be a non-empty bounded option list");
    }
    var keys = [];
    value.forEach(function (entry) {
      requireExactFields(entry, "sex option", ["key", "label"], []);
      var key = validateIdentifier(entry.key, "sex key");
      if (codePoints(key) > CREATION_MAX_SUBRACE_KEY) {
        throw new Error("sex key exceeds its bound");
      }
      requireString(entry.label, "sex label", CREATION_MAX_LABEL);
      if (!entry.label.trim()) {
        throw new Error("sex label must be non-empty");
      }
      keys.push(key);
    });
    if (keys.join(",") !== CREATION_SEX_VALUES.join(",")) {
      throw new Error("sex options must be exactly the sex vocabulary in order");
    }
  }

  function validateCreationAffinity(value) {
    if (!isPlainObject(value)) {
      throw new Error("affinity must be an object");
    }
    var keys = Object.keys(value).sort().join(",");
    if (keys !== CREATION_AFFINITY_RACES.slice().sort().join(",")) {
      throw new Error("affinity must map human, beastfolk, and elf");
    }
    CREATION_AFFINITY_RACES.forEach(function (raceKey) {
      validateCreationRaceAffinity(value[raceKey], raceKey);
    });
  }

  function validateCreationRaceAffinity(value, raceKey) {
    requireExactFields(value, "affinity " + raceKey, ["maximum", "elements"], []);
    var maximum = requireInt(value.maximum, "maximum", 0, MAX_SAFE_INTEGER);
    if (maximum !== CREATION_AFFINITY_MAXIMUMS[raceKey]) {
      throw new Error(
        "affinity " + raceKey + " maximum does not match the race bound"
      );
    }
    if (
      !Array.isArray(value.elements) ||
      value.elements.length === 0 ||
      value.elements.length > CREATION_MAX_AFFINITY_ELEMENTS
    ) {
      throw new Error("affinity elements must be a non-empty bounded list");
    }
    var seen = {};
    var elementKeys = [];
    value.elements.forEach(function (entry) {
      requireExactFields(entry, "affinity element", ["key", "label"], []);
      var key = validateIdentifier(entry.key, "affinity key");
      if (CREATION_AFFINITY_ELEMENTS.indexOf(key) === -1) {
        throw new Error("affinity key " + key + " is not a lore element");
      }
      if (seen[key]) {
        throw new Error("affinity element keys must be unique");
      }
      seen[key] = true;
      elementKeys.push(key);
      requireString(entry.label, "affinity label", CREATION_MAX_LABEL);
      if (!entry.label.trim()) {
        throw new Error("affinity element label must be non-empty");
      }
    });
    var expected = CREATION_AFFINITY_ELEMENTS.slice().sort();
    if (elementKeys.slice().sort().join(",") !== expected.join(",")) {
      throw new Error("affinity elements must be exactly the eight lore elements");
    }
  }

  function validateCreationDraftAffinity(value, raceKey) {
    if (value === null) {
      return [];
    }
    if (!Array.isArray(value)) {
      throw new Error("affinity_elements must be a list or null");
    }
    if (value.length > CREATION_MAX_AFFINITY_ELEMENTS) {
      throw new Error("affinity_elements exceeds its bound");
    }
    if (raceKey === "elf" && value.length > 0) {
      throw new Error(
        "an elf must not supply affinity_elements; the subrace is the authority"
      );
    }
    if (value.length > CREATION_AFFINITY_MAXIMUMS[raceKey]) {
      throw new Error(
        "affinity_elements exceeds the " + raceKey + " maximum of " +
        CREATION_AFFINITY_MAXIMUMS[raceKey]
      );
    }
    var seen = {};
    value.forEach(function (entry) {
      if (CREATION_AFFINITY_ELEMENTS.indexOf(entry) === -1) {
        throw new Error("unknown affinity element " + entry);
      }
      if (seen[entry]) {
        throw new Error("duplicate affinity element " + entry);
      }
      seen[entry] = true;
    });
    return value.slice();
  }

  function validateCreationPersona(value) {
    // One required nullable persona block: null is the explicit "no persona"
    // value; any other value carries exactly the three prose fields, each a
    // 1..600 code-point non-blank string.
    if (value === null) {
      return null;
    }
    if (!isPlainObject(value)) {
      throw new Error("persona must be null or a JSON object");
    }
    requireExactFields(value, "persona", CREATION_PERSONA_KEYS, []);
    var persona = {};
    CREATION_PERSONA_KEYS.forEach(function (key) {
      var text = value[key];
      if (typeof text !== "string" || !text.trim()) {
        throw new Error("persona." + key + " must be non-empty text");
      }
      if (codePoints(text) > CREATION_MAX_PERSONA_BACKGROUND) {
        throw new Error("persona." + key + " exceeds its bound");
      }
      persona[key] = text;
    });
    return persona;
  }

  function validateCreationDraft(value) {
    if (value === null) {
      return value;
    }
    if (!isPlainObject(value)) {
      throw new Error("draft must be a JSON object or null");
    }
    if (value.mode === "preset") {
      requireExactFields(value, "preset draft", ["mode", "stage", "preset_key"], []);
      if (value.stage !== CREATION_PRESET_STAGE) {
        throw new Error("unsupported preset draft stage");
      }
      var presetKey = validateIdentifier(value.preset_key, "draft preset_key");
      if (codePoints(presetKey) > CREATION_MAX_PRESET_KEY) {
        throw new Error("draft preset_key exceeds its bound");
      }
      return {
        mode: "preset",
        stage: CREATION_PRESET_STAGE,
        preset_key: presetKey,
      };
    }
    if (value.mode === "custom") {
      requireExactFields(
        value,
        "custom draft",
        ["mode", "stage", "display_name", "age", "apparent_age", "race", "subrace", "allocations", "background", "affinity_elements", "persona", "sex"],
        []
      );
      if (value.stage !== CREATION_CUSTOM_STAGE) {
        throw new Error("unsupported custom draft stage");
      }
      requireString(value.display_name, "display_name", CREATION_MAX_DISPLAY_NAME);
      requireInt(value.age, "age", CREATION_AGE_MINIMUM, CREATION_AGE_MAXIMUM);
      requireInt(
        value.apparent_age,
        "apparent_age",
        CREATION_APPARENT_AGE_MINIMUM,
        CREATION_APPARENT_AGE_MAXIMUM
      );
      var race = validateIdentifier(value.race, "draft race");
      if (codePoints(race) > CREATION_MAX_RACE_KEY) {
        throw new Error("draft race exceeds its bound");
      }
      var subrace = validateIdentifier(value.subrace, "draft subrace");
      if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
        throw new Error("draft subrace exceeds its bound");
      }
      var background = value.background;
      if (background !== null) {
        background = requireString(background, "draft background", CREATION_MAX_PERSONA_BACKGROUND);
        if (!background.trim()) {
          background = null;
        }
      }
      // The draft stores the concrete normalized member (mirror of the
      // wizard normalizer and _validate_draft; namegen-creation-ui D2/D3).
      if (CREATION_SEX_VALUES.indexOf(value.sex) === -1) {
        throw new Error("draft sex is not a vocabulary member");
      }
      return {
        mode: "custom",
        stage: CREATION_CUSTOM_STAGE,
        display_name: value.display_name,
        age: value.age,
        apparent_age: value.apparent_age,
        race: race,
        subrace: subrace,
        allocations: validateCreationDraftAllocations(value),
        background: background,
        affinity_elements: validateCreationDraftAffinity(value.affinity_elements, race),
        persona: validateCreationPersona(value.persona),
        sex: value.sex,
      };
    }
    throw new Error("draft has an unknown mode");
  }

  function validateCreationDraftAllocations(value) {
    var allocations = value.allocations;
    if (!isPlainObject(allocations)) {
      throw new Error("draft allocations must be an object");
    }
    var allocationKeys = Object.keys(allocations).slice().sort();
    var expectedKeys = CREATION_AXES.slice().sort();
    if (allocationKeys.join(",") !== expectedKeys.join(",")) {
      throw new Error("draft allocations must contain exactly the seven axes");
    }
    CREATION_AXES.forEach(function (axis) {
      requireInt(allocations[axis], axis, 0, 10000);
    });
    return allocations;
  }

  function validateCreationProposal(value) {
    // The optional top-level transient concept proposal: exactly revision (a
    // positive session-monotonic sequence number), race, nullable subrace,
    // the seven axes, and a mandatory three-field persona block, plus five
    // optional transient-fill keys present only when the validated proposal
    // carried a value — an absent key is never encoded as null
    // (bump-creation-panel-proposal-v3 D1).
    requireExactFields(
      value,
      "proposal",
      ["revision", "race", "subrace", "allocations", "persona"],
      ["display_name", "age", "apparent_age", "background", "affinity_elements"]
    );
    var revision = requireInt(value.revision, "revision", 1, MAX_SAFE_INTEGER);
    var race = validateIdentifier(value.race, "proposal race");
    if (codePoints(race) > CREATION_MAX_RACE_KEY) {
      throw new Error("proposal race exceeds its bound");
    }
    var subrace = null;
    if (value.subrace !== null) {
      subrace = validateIdentifier(value.subrace, "proposal subrace");
      if (codePoints(subrace) > CREATION_MAX_SUBRACE_KEY) {
        throw new Error("proposal subrace exceeds its bound");
      }
    }
    var persona = validateCreationPersona(value.persona);
    if (persona === null) {
      throw new Error("proposal persona must be a block");
    }
    var checked = {
      revision: revision,
      race: race,
      subrace: subrace,
      allocations: validateCreationDraftAllocations(value),
      persona: persona,
    };
    if (value.display_name !== undefined) {
      var displayName = value.display_name;
      if (typeof displayName !== "string" || !displayName) {
        throw new Error("proposal display_name must be non-empty text");
      }
      if (codePoints(displayName) > CREATION_MAX_PROPOSAL_NAME) {
        throw new Error("proposal display_name exceeds its bound");
      }
      checked.display_name = displayName;
    }
    if (value.age !== undefined) {
      checked.age = requireInt(value.age, "age", CREATION_AGE_MINIMUM, CREATION_AGE_MAXIMUM);
    }
    if (value.apparent_age !== undefined) {
      checked.apparent_age = requireInt(
        value.apparent_age,
        "apparent_age",
        CREATION_APPARENT_AGE_MINIMUM,
        CREATION_APPARENT_AGE_MAXIMUM
      );
    }
    if (value.background !== undefined) {
      var background = value.background;
      if (typeof background !== "string" || !background) {
        throw new Error("proposal background must be non-empty text");
      }
      if (codePoints(background) > CREATION_MAX_PERSONA_BACKGROUND) {
        throw new Error("proposal background exceeds its bound");
      }
      checked.background = background;
    }
    if (value.affinity_elements !== undefined) {
      var elements = value.affinity_elements;
      if (!Array.isArray(elements) || elements.length > CREATION_MAX_AFFINITY_ELEMENTS) {
        throw new Error(
          "proposal affinity_elements must be a list of at most " +
          CREATION_MAX_AFFINITY_ELEMENTS + " element keys"
        );
      }
      var seen = {};
      elements.forEach(function (entry) {
        if (CREATION_AFFINITY_ELEMENTS.indexOf(entry) === -1) {
          throw new Error("proposal affinity_elements has unknown element " + entry);
        }
        if (seen[entry]) {
          throw new Error("proposal affinity_elements duplicates element " + entry);
        }
        seen[entry] = true;
      });
      checked.affinity_elements = elements.slice();
    }
    return checked;
  }

  function validateCreationPanel(payload) {
    requireExactFields(
      payload,
      "creation panel",
      ["schema_version", "available", "kind", "draft", "presets", "custom"],
      ["proposal"]
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== CREATION_SCHEMA_VERSION) {
      throw new Error("unsupported creation schema_version");
    }
    if (payload.available !== true || payload.kind !== "creation") {
      throw new Error("creation panel must be available with kind creation");
    }
    if (!Array.isArray(payload.presets) || payload.presets.length === 0 || payload.presets.length > CREATION_MAX_PRESETS) {
      throw new Error("presets must be a non-empty list within its bound");
    }
    payload.presets.forEach(validateCreationPresetCard);
    validateCreationCustom(payload.custom);
    var draft = validateCreationDraft(payload.draft);
    var result = {
      schema_version: CREATION_SCHEMA_VERSION,
      available: true,
      kind: "creation",
      draft: draft,
      presets: payload.presets,
      custom: payload.custom,
    };
    // The proposal key ships only while the session slot holds a proposal;
    // a null value is never legal (the presenter omits the key).
    if (payload.proposal !== undefined) {
      result.proposal = validateCreationProposal(payload.proposal);
    }
    // Envelope guarantee (design D2): per-field bounds are ceilings, not a
    // guarantee that any combination of them fits, so the validator enforces
    // the serialized byte size directly and fails closed over the envelope.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("creation payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // ---------------------------------------------------------------------------
  // exploration panel v1 validators (mirror of
  // web.webclient.presentation.exploration, design D10). Shared bounds are
  // guarded by a dual-direction parity test.
  // ---------------------------------------------------------------------------

  var EXPLORATION_MAX_MOVE_EXITS = 12;
  var EXPLORATION_MAX_LOOK_ENTITIES = 32;
  var EXPLORATION_MAX_LOOK_OBJECTS = 32;
  var EXPLORATION_MAX_INTERACT_TARGETS = 32;
  var EXPLORATION_MAX_AFFORDANCES = 8;
  var EXPLORATION_MAX_SCRIPTED_KEYWORDS = 16;
  var EXPLORATION_MAX_EXIT_REF = 64;
  var EXPLORATION_MAX_NODE_ID = 128;
  var EXPLORATION_MAX_DISPLAY_NAME = 128;
  var EXPLORATION_MAX_KIND = 32;
  var EXPLORATION_MAX_LABEL = 128;
  var EXPLORATION_MAX_KEYWORD_ID = 64;
  var EXPLORATION_MAX_KEYWORD_LABEL = 128;
  var EXPLORATION_MAX_REASON_MESSAGE = 128;
  var EXPLORATION_ACTION_KINDS = ["action", "navigate"];
  var EXPLORATION_ACTION_IDS = [
    "explore.talk_scripted",
    "explore.talk_freeform",
    "explore.party_invite",
    "explore.party_leave",
    "explore.engage",
  ];
  var EXPLORATION_SURFACES = ["guild", "shop"];
  var EXPLORATION_ENTITY_KINDS = ["character", "npc", "monster"];

  function requireNodeId(value, field) {
    requireString(value, field, EXPLORATION_MAX_NODE_ID);
    if (!NODE_ID_RE.test(value)) {
      throw new Error(field + " is not a canonical node ID");
    }
    return value;
  }

  function requireExitRef(value, field) {
    if (
      typeof value !== "string" ||
      value.length < 1 ||
      value.length > EXPLORATION_MAX_EXIT_REF
    ) {
      throw new Error(
        field + " must be 1.." + EXPLORATION_MAX_EXIT_REF + " ASCII characters"
      );
    }
    // eslint-disable-next-line no-control-regex
    if (/[^\x00-\x7F]/.test(value)) {
      throw new Error(field + " must be ASCII");
    }
    return value;
  }

  function requireIdentity(value, field) {
    return requireInt(value, field, 1, MAX_SAFE_INTEGER);
  }

  function validateExplorationDisabledReason(value) {
    if (value === null) {
      return null;
    }
    requireExactFields(value, "disabled_reason", ["code", "message"], []);
    validateIdentifier(value.code, "disabled_reason code");
    var reasonMessage = requireString(
      value.message,
      "disabled_reason message",
      EXPLORATION_MAX_REASON_MESSAGE
    );
    if (!reasonMessage.trim()) {
      throw new Error("disabled_reason message must be non-empty");
    }
    return value;
  }

  function validateExplorationKeyword(value) {
    requireExactFields(value, "scripted keyword", ["keyword_id", "label"], []);
    var keywordId = requireString(value.keyword_id, "keyword_id", EXPLORATION_MAX_KEYWORD_ID);
    if (!keywordId.trim()) {
      throw new Error("keyword_id must be non-empty");
    }
    var keywordLabel = requireString(value.label, "keyword label", EXPLORATION_MAX_KEYWORD_LABEL);
    if (!keywordLabel.trim()) {
      throw new Error("keyword label must be non-empty");
    }
    return value;
  }

  function validateExplorationAffordance(value) {
    if (!isPlainObject(value)) {
      throw new Error("affordance must be a JSON object");
    }
    var kind = value.kind;
    if (EXPLORATION_ACTION_KINDS.indexOf(kind) === -1) {
      throw new Error("affordance kind is not a stable value");
    }
    requireExactFields(
      value,
      "affordance",
      ["kind", "label", "enabled", "disabled_reason"],
      ["action_id", "surface"]
    );
    var label = requireString(value.label, "label", EXPLORATION_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("affordance label must be non-empty");
    }
    var enabled = requireBool(value.enabled, "enabled");
    var disabledReason = validateExplorationDisabledReason(value.disabled_reason);
    if (disabledReason === null) {
      if (!enabled) {
        throw new Error("a disabled affordance requires a disabled_reason");
      }
    } else if (enabled) {
      throw new Error("an enabled affordance must not carry a disabled_reason");
    }

    if (kind === "action") {
      requireExactFields(
        value,
        "action affordance",
        ["kind", "action_id", "label", "enabled", "disabled_reason"],
        []
      );
      var actionId = validateIdentifier(value.action_id, "action_id");
      if (EXPLORATION_ACTION_IDS.indexOf(actionId) === -1) {
        throw new Error("action_id is not a registered exploration action");
      }
      return {
        kind: kind,
        action_id: actionId,
        label: label,
        enabled: enabled,
        disabled_reason: disabledReason,
      };
    }
    requireExactFields(
      value,
      "navigation affordance",
      ["kind", "surface", "label", "enabled", "disabled_reason"],
      []
    );
    if (EXPLORATION_SURFACES.indexOf(value.surface) === -1) {
      throw new Error("surface is not a stable value");
    }
    return {
      kind: kind,
      surface: value.surface,
      label: label,
      enabled: enabled,
      disabled_reason: disabledReason,
    };
  }

  function validateExplorationLookEntity(value) {
    requireExactFields(
      value,
      "look entity",
      ["identity", "display_name", "kind", "portrait_ref"],
      []
    );
    requireIdentity(value.identity, "entity.identity");
    var displayName = requireString(value.display_name, "display_name", EXPLORATION_MAX_DISPLAY_NAME);
    if (!displayName.trim()) {
      throw new Error("entity display_name must be non-empty");
    }
    if (EXPLORATION_ENTITY_KINDS.indexOf(value.kind) === -1) {
      throw new Error("entity kind is not a stable value");
    }
    if (value.portrait_ref !== null) {
      throw new Error("portrait_ref must be null in this schema version");
    }
    return value;
  }

  function validateExplorationLookObject(value) {
    requireExactFields(value, "look object", ["identity", "display_name"], []);
    requireIdentity(value.identity, "object.identity");
    var objectName = requireString(value.display_name, "display_name", EXPLORATION_MAX_DISPLAY_NAME);
    if (!objectName.trim()) {
      throw new Error("object display_name must be non-empty");
    }
    return value;
  }

  function validateExplorationLookRoom(value) {
    requireExactFields(value, "look room", ["identity", "display_name", "room"], []);
    requireIdentity(value.identity, "room.identity");
    var roomName = requireString(value.display_name, "display_name", EXPLORATION_MAX_DISPLAY_NAME);
    if (!roomName.trim()) {
      throw new Error("room display_name must be non-empty");
    }
    if (value.room !== true) {
      throw new Error("room marker must be true");
    }
    return value;
  }

  function validateExplorationLook(value) {
    requireExactFields(value, "look", ["room", "entities", "objects"], []);
    validateExplorationLookRoom(value.room);
    if (!Array.isArray(value.entities) || value.entities.length > EXPLORATION_MAX_LOOK_ENTITIES) {
      throw new Error("look entities must be a list of at most " + EXPLORATION_MAX_LOOK_ENTITIES + " entries");
    }
    value.entities.forEach(validateExplorationLookEntity);
    if (!Array.isArray(value.objects) || value.objects.length > EXPLORATION_MAX_LOOK_OBJECTS) {
      throw new Error("look objects must be a list of at most " + EXPLORATION_MAX_LOOK_OBJECTS + " entries");
    }
    value.objects.forEach(validateExplorationLookObject);
    return value;
  }

  function validateExplorationInteractTarget(value) {
    requireExactFields(
      value,
      "interact target",
      ["identity", "display_name", "portrait_ref", "affordances"],
      ["keywords"]
    );
    requireIdentity(value.identity, "target.identity");
    var targetName = requireString(value.display_name, "display_name", EXPLORATION_MAX_DISPLAY_NAME);
    if (!targetName.trim()) {
      throw new Error("target display_name must be non-empty");
    }
    if (value.portrait_ref !== null) {
      throw new Error("portrait_ref must be null in this schema version");
    }
    if (
      !Array.isArray(value.affordances) ||
      value.affordances.length > EXPLORATION_MAX_AFFORDANCES
    ) {
      throw new Error("affordances must be a list of at most " + EXPLORATION_MAX_AFFORDANCES + " entries");
    }
    value.affordances.forEach(validateExplorationAffordance);
    if (Object.prototype.hasOwnProperty.call(value, "keywords")) {
      if (
        !Array.isArray(value.keywords) ||
        value.keywords.length > EXPLORATION_MAX_SCRIPTED_KEYWORDS
      ) {
        throw new Error(
          "keywords must be a list of at most " + EXPLORATION_MAX_SCRIPTED_KEYWORDS + " entries"
        );
      }
      value.keywords.forEach(validateExplorationKeyword);
      var hasScripted = value.affordances.some(function (affordance) {
        return (
          affordance.kind === "action" &&
          affordance.action_id === "explore.talk_scripted"
        );
      });
      if (value.keywords.length > 0 && !hasScripted) {
        throw new Error("keywords require a talk_scripted affordance on the target");
      }
    }
    return value;
  }

  function validateExplorationAvailability(value, name) {
    requireExactFields(value, name, ["available"], []);
    requireBool(value.available, "available");
    return value;
  }

  function validateExplorationMoveRow(value) {
    requireExactFields(
      value,
      "move row",
      ["exit_ref", "label", "destination", "enabled", "disabled_reason"],
      []
    );
    requireExitRef(value.exit_ref, "exit_ref");
    var label = requireString(value.label, "label", EXPLORATION_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("exit label must be non-empty");
    }
    requireNodeId(value.destination, "destination");
    var enabled = requireBool(value.enabled, "enabled");
    var disabledReason = validateExplorationDisabledReason(value.disabled_reason);
    if (disabledReason === null) {
      if (!enabled) {
        throw new Error("a disabled exit requires a disabled_reason");
      }
    } else if (enabled) {
      throw new Error("an enabled exit must not carry a disabled_reason");
    }
    return value;
  }

  // Exact available exploration panel v1 schema (design D10).
  function validateExplorationPanel(payload) {
    requireExactFields(
      payload,
      "exploration panel",
      [
        "schema_version",
        "available",
        "kind",
        "move",
        "look",
        "interact",
        "character",
        "quests",
        "inventory",
      ],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 1) {
      throw new Error("unsupported exploration schema_version");
    }
    if (payload.available !== true || payload.kind !== "exploration") {
      throw new Error("exploration panel must be available with kind exploration");
    }

    if (!Array.isArray(payload.move) || payload.move.length > EXPLORATION_MAX_MOVE_EXITS) {
      throw new Error("move must be a list of at most " + EXPLORATION_MAX_MOVE_EXITS + " rows");
    }
    payload.move.forEach(validateExplorationMoveRow);
    validateExplorationLook(payload.look);
    if (
      !Array.isArray(payload.interact) ||
      payload.interact.length > EXPLORATION_MAX_INTERACT_TARGETS
    ) {
      throw new Error("interact must be a list of at most " + EXPLORATION_MAX_INTERACT_TARGETS + " targets");
    }
    var seen = {};
    payload.interact.forEach(function (target) {
      validateExplorationInteractTarget(target);
      if (seen[target.identity]) {
        throw new Error("interact target identities must be unique");
      }
      seen[target.identity] = true;
    });
    validateExplorationAvailability(payload.character, "character");
    validateExplorationAvailability(payload.quests, "quests");
    validateExplorationAvailability(payload.inventory, "inventory");

    var result = {
      schema_version: 1,
      available: true,
      kind: "exploration",
      move: payload.move,
      look: payload.look,
      interact: payload.interact,
      character: payload.character,
      quests: payload.quests,
      inventory: payload.inventory,
    };
    // Envelope guarantee (design D10): per-field bounds are ceilings, not a
    // guarantee that any combination of them fits, so the validator enforces
    // the serialized byte size directly and fails closed over the envelope.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("exploration payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // ---------------------------------------------------------------------------
  // character panel v1 validators (mirror of
  // web.webclient.presentation.character, design D10). Shared bounds are
  // guarded by a dual-direction parity test.
  // ---------------------------------------------------------------------------

  var CHARACTER_MAX_TRAIT_ROWS = 32;
  var CHARACTER_MAX_ACTIVE_ROWS = 32;
  var CHARACTER_MAX_PASSIVE_ROWS = 32;
  var CHARACTER_MAX_EQUIPMENT_ROWS = 32;
  var CHARACTER_MAX_DISPLAYED_ROWS = 32;
  // The category-group count bound equals len(SkillCategory) plus one on the
  // server: the extra slot is the synthetic "unknown" fallback group that
  // holds keys absent from SKILL_REGISTRY.
  var CHARACTER_MAX_CATEGORY_GROUPS = 9;
  var CHARACTER_MAX_KEY = 64;
  var CHARACTER_MAX_LABEL = 128;
  var CHARACTER_MAX_DESCRIPTION = 256;
  var CHARACTER_MAX_SLOT = 32;
  // v5 breakdown bounds (mirror of web.webclient.presentation.character):
  // the per-stat layer bound, the P3 adjustment-summary bound, and the
  // closed source/kind alphabets.
  var CHARACTER_MAX_LAYERS = 16;
  var CHARACTER_MAX_ADJUSTMENT = CHARACTER_MAX_DESCRIPTION;
  var CHARACTER_LAYER_SOURCES = ["skill", "condition", "equipment"];
  var CHARACTER_LAYER_KINDS = ["mult", "flat", "pct"];
  // Fixed level vocabularies for the character panel's intimate section
  // (mirror of world/lore/sexual_vocab.py, the shared vocabulary source).
  var CHARACTER_INTIMATE_AROUSAL_LEVELS = ["平靜", "微興奮", "中等", "高度", "極限"];
  var CHARACTER_INTIMATE_WETNESS_LEVELS = ["乾燥", "微濕", "濕潤", "大量", "泛濫"];
  var CHARACTER_INTIMATE_SHAME_LEVELS = ["無", "輕微", "中等", "強烈", "成癮"];
  var CHARACTER_INTIMATE_EXPOSURE_LEVELS = ["極低", "低", "中等", "高", "極高"];
  var CHARACTER_INTIMATE_CLIMAX_PHASE_LEVELS = ["未達", "接近", "進行中", "餘韻"];

  function validateCharacterKey(value, field) {
    var key = validateIdentifier(value, field);
    if (codePoints(key) > CHARACTER_MAX_KEY) {
      throw new Error(field + " exceeds its bound");
    }
    return key;
  }

  function requireNumber(value, field, minimum, maximum) {
    // JSON numbers with the wire bounds: finite, safe-ranged, non-boolean.
    if (typeof value !== "number" || !isFinite(value)) {
      throw new Error(field + " must be a finite number");
    }
    if (value < minimum || value > maximum || Math.abs(value) > MAX_SAFE_INTEGER) {
      throw new Error(field + " must be within " + minimum + ".." + maximum);
    }
    return value;
  }

  // Breakdown row pieces (expose-stat-breakdown-read-model): the exact
  // {source, name, kind, amount} layer and the seven-field trait row. The
  // numeric fields accept JSON numbers (a scaled rule-table grant produces
  // fractional values such as 2.5), never booleans or non-finite numbers.
  function validateCharacterBreakdownLayer(value) {
    requireExactFields(value, "breakdown layer", ["source", "name", "kind", "amount"], []);
    if (CHARACTER_LAYER_SOURCES.indexOf(value.source) === -1) {
      throw new Error("breakdown layer source is not a stable value");
    }
    var name = requireString(value.name, "name", CHARACTER_MAX_LABEL);
    if (!name.trim()) {
      throw new Error("breakdown layer name must be non-empty");
    }
    if (CHARACTER_LAYER_KINDS.indexOf(value.kind) === -1) {
      throw new Error("breakdown layer kind is not a stable value");
    }
    var amount = requireNumber(
      value.amount,
      "breakdown layer amount",
      -MAX_SAFE_INTEGER,
      MAX_SAFE_INTEGER
    );
    if (amount === 0) {
      throw new Error("breakdown layer amount must be non-zero");
    }
    return value;
  }

  function validateCharacterTraitRow(value) {
    requireExactFields(
      value,
      "trait row",
      ["key", "label", "base", "current", "max", "effective", "layers"],
      []
    );
    validateCharacterKey(value.key, "trait key");
    var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("trait label must be non-empty");
    }
    requireInt(value.base, "base", 0, MAX_SAFE_INTEGER);
    requireNumber(value.current, "current", 0, MAX_SAFE_INTEGER);
    if (value.max !== null) {
      requireInt(value.max, "max", 1, MAX_SAFE_INTEGER);
      if (value.current > value.max) {
        throw new Error("trait current must not exceed maximum");
      }
    }
    requireNumber(value.effective, "effective", 0, MAX_SAFE_INTEGER);
    // The defining row contract: a gauge row's effective value IS its
    // maximum; a static row exposes its authoritative effective total through
    // the total-display field. A payload contradicting either is rejected at
    // the boundary instead of letting two incompatible totals diverge.
    if (value.max !== null) {
      if (value.effective !== value.max) {
        throw new Error("gauge trait effective must equal its maximum");
      }
    } else if (value.current !== value.effective) {
      throw new Error("static trait current must equal effective");
    }
    if (!Array.isArray(value.layers) || value.layers.length > CHARACTER_MAX_LAYERS) {
      throw new Error(
        "layers must be a list of at most " + CHARACTER_MAX_LAYERS + " rows"
      );
    }
    value.layers.forEach(validateCharacterBreakdownLayer);
    return value;
  }

  function validateCharacterPassiveRow(value) {
    requireExactFields(value, "passive row", ["key", "label"], []);
    validateCharacterKey(value.key, "passive key");
    var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("passive label must be non-empty");
    }
    return value;
  }

  function validateCharacterActiveSkillRow(value) {
    requireExactFields(
      value,
      "active skill row",
      ["key", "label"],
      ["cost", "target_spec", "usable_out_of_combat", "freeform_scales"]
    );
    validateCharacterKey(value.key, "active key");
    var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("active skill label must be non-empty");
    }
    var cost = value.cost;
    if (cost !== undefined) {
      if (!isPlainObject(cost) || Object.keys(cost).length > MAX_COST_KEYS) {
        throw new Error("skill cost must be a bounded object");
      }
      Object.keys(cost).forEach(function (resource) {
        validateIdentifier(resource, "cost resource key");
        requireInt(cost[resource], "cost amount", 0, MAX_SAFE_INTEGER);
      });
    }
    if (value.target_spec !== undefined && TARGET_SPECS.indexOf(value.target_spec) === -1) {
      throw new Error("skill target_spec is not a stable value");
    }
    if (value.usable_out_of_combat !== undefined && typeof value.usable_out_of_combat !== "boolean") {
      throw new Error("skill usable_out_of_combat must be a boolean");
    }
    var baseMp =
      isPlainObject(cost) && Number.isInteger(cost.mp) && cost.mp > 0 ? cost.mp : null;
    if (value.freeform_scales !== undefined) {
      validateFreeformScales(value.freeform_scales, baseMp);
    }
    // Python omits the field when it is null; normalize identically.
    if (value.freeform_scales === null) {
      delete value.freeform_scales;
    }
    return value;
  }

  function validateCharacterSkillGroup(value, rowValidator) {
    requireExactFields(value, "skill group", ["group", "label", "skills"], []);
    if (value.group !== null) {
      var group = requireString(value.group, "group", CHARACTER_MAX_KEY);
      if (!group.trim()) {
        throw new Error("group must be non-empty when set");
      }
    }
    if (value.label !== null) {
      var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
      if (!label.trim()) {
        throw new Error("label must be non-empty when set");
      }
    }
    if ((value.group === null) !== (value.label === null)) {
      throw new Error("group and label must both be set or both be null");
    }
    if (!Array.isArray(value.skills)) {
      throw new Error("skills must be a list");
    }
    value.skills.forEach(rowValidator || validateCharacterPassiveRow);
    return value;
  }

  function validateCharacterCategoryGroup(value, rowValidator) {
    requireExactFields(value, "category group", ["category", "label", "groups"], []);
    validateCharacterKey(value.category, "category key");
    var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("category label must be non-empty");
    }
    if (!Array.isArray(value.groups) || value.groups.length === 0) {
      throw new Error("a category group must carry a non-empty groups list");
    }
    value.groups.forEach(function (group) {
      validateCharacterSkillGroup(group, rowValidator);
    });
    return value;
  }

  function characterFlattenedSkillCount(categoryGroups) {
    var count = 0;
    categoryGroups.forEach(function (category) {
      category.groups.forEach(function (group) {
        count += group.skills.length;
      });
    });
    return count;
  }

  // Equipment row: the identity fields plus the required (possibly empty)
  // server-formatted adjustment summary.
  function validateCharacterEquipmentRow(value) {
    requireExactFields(
      value,
      "equipment row",
      ["slot", "item_key", "display_name", "adjustment"],
      []
    );
    var slot = requireString(value.slot, "slot", CHARACTER_MAX_SLOT);
    if (!slot.trim()) {
      throw new Error("slot must be non-empty");
    }
    validateCharacterKey(value.item_key, "item_key");
    var displayName = requireString(value.display_name, "display_name", CHARACTER_MAX_LABEL);
    if (!displayName.trim()) {
      throw new Error("equipment display_name must be non-empty");
    }
    requireString(value.adjustment, "adjustment", CHARACTER_MAX_ADJUSTMENT);
    return value;
  }

  function validateCharacterDisplayedRow(value) {
    requireExactFields(value, "displayed row", ["key", "label", "value"], []);
    validateCharacterKey(value.key, "displayed key");
    var label = requireString(value.label, "label", CHARACTER_MAX_LABEL);
    if (!label.trim()) {
      throw new Error("displayed label must be non-empty");
    }
    requireInt(value.value, "value", 0, MAX_SAFE_INTEGER);
    return value;
  }

  function validateCharacterDisguise(value) {
    requireExactFields(value, "disguise", ["active", "description", "displayed"], []);
    var active = requireBool(value.active, "active");
    var description = requireString(value.description, "description", CHARACTER_MAX_DESCRIPTION);
    if (!Array.isArray(value.displayed) || value.displayed.length > CHARACTER_MAX_DISPLAYED_ROWS) {
      throw new Error("displayed must be a list of at most " + CHARACTER_MAX_DISPLAYED_ROWS + " rows");
    }
    value.displayed.forEach(validateCharacterDisplayedRow);
    if (!active && value.displayed.length > 0) {
      throw new Error("an undisguised actor must have an empty displayed list");
    }
    if (active && !description.trim()) {
      throw new Error("disguise description must be non-empty when active");
    }
    return value;
  }

  function validateCharacterGuild(value) {
    requireExactFields(value, "guild", ["rank", "merit"], []);
    if (value.rank !== null) {
      var rank = requireString(value.rank, "rank", CHARACTER_MAX_KEY);
      if (!rank.trim()) {
        throw new Error("rank must be non-empty when set");
      }
    }
    requireInt(value.merit, "merit", 0, MAX_SAFE_INTEGER);
    return value;
  }

  var CHARACTER_MAX_PERSONA = 600;
  var CHARACTER_PERSONA_FIELDS = [
    "background",
    "personality",
    "life_story",
    "habit",
  ];

  function validateCharacterPersona(value) {
    // The four editable persona prose keys (persona-editing D3): each is
    // independently nullable, whitespace-nulling, and bounded at the shared
    // 600-code-point cap. Structural keys never appear in this section.
    requireExactFields(value, "persona", CHARACTER_PERSONA_FIELDS, []);
    var result = {};
    for (var i = 0; i < CHARACTER_PERSONA_FIELDS.length; i++) {
      var field = CHARACTER_PERSONA_FIELDS[i];
      if (value[field] === null) {
        result[field] = null;
        continue;
      }
      var text = requireString(
        value[field],
        "persona." + field,
        CHARACTER_MAX_PERSONA
      );
      result[field] = text.trim() ? text.trim() : null;
    }
    return result;
  }

  // Nullable intimate section of the character panel (webclient-intimate-status-section).
  // `null` means the actor has no sexual-state record; otherwise the section
  // carries exactly the six intimate fields, each level field checked against
  // its fixed vocabulary and `climax_today` as a non-negative safe integer.
  function validateCharacterIntimateLevel(value, field, vocabulary) {
    var level = requireString(value, field, CHARACTER_MAX_LABEL);
    if (vocabulary.indexOf(level) === -1) {
      throw new Error(field + " is not a member of its fixed vocabulary");
    }
    return level;
  }

  function validateCharacterIntimate(value) {
    if (value === null) {
      return null;
    }
    requireExactFields(
      value,
      "intimate",
      ["arousal", "wetness", "shame", "exposure", "climax_phase", "climax_today"],
      []
    );
    return {
      arousal: validateCharacterIntimateLevel(value.arousal, "intimate.arousal", CHARACTER_INTIMATE_AROUSAL_LEVELS),
      wetness: validateCharacterIntimateLevel(value.wetness, "intimate.wetness", CHARACTER_INTIMATE_WETNESS_LEVELS),
      shame: validateCharacterIntimateLevel(value.shame, "intimate.shame", CHARACTER_INTIMATE_SHAME_LEVELS),
      exposure: validateCharacterIntimateLevel(value.exposure, "intimate.exposure", CHARACTER_INTIMATE_EXPOSURE_LEVELS),
      climax_phase: validateCharacterIntimateLevel(value.climax_phase, "intimate.climax_phase", CHARACTER_INTIMATE_CLIMAX_PHASE_LEVELS),
      climax_today: requireInt(value.climax_today, "intimate.climax_today", 0, MAX_SAFE_INTEGER),
    };
  }

  // Exact available character panel v7 schema (design D10: skill category
  // grouping + the intimate-status section; expose-stat-breakdown-read-model
  // added the breakdown trait rows and the adjustment-bearing equipment
  // rows; render-equipment-breakdown-webclient closed the transitional v4
  // tolerance window; title-system added the optional composed full_title).
  // Shared bounds are guarded by a dual-direction parity test.
  function validateCharacterAvailablePanel(payload) {
    requireExactFields(
      payload,
      "character panel",
      [
        "schema_version",
        "available",
        "kind",
        "traits",
        "actives",
        "passives",
        "equipment",
        "disguise",
        "guild",
        "wallet",
        "persona",
        "intimate",
      ],
      ["full_title"]
    );
    var fullTitle = null;
    if (Object.prototype.hasOwnProperty.call(payload, "full_title")) {
      fullTitle = requireString(
        payload.full_title,
        "full_title",
        MAX_FULL_TITLE_CODE_POINTS
      );
      if (!fullTitle.trim()) {
        throw new Error("full_title must be non-empty when present");
      }
    }
    if (payload.schema_version !== 7) {
      throw new Error("unsupported character schema_version");
    }
    if (payload.available !== true || payload.kind !== "character") {
      throw new Error("character panel must be available with kind character");
    }
    if (!Array.isArray(payload.traits) || payload.traits.length > CHARACTER_MAX_TRAIT_ROWS) {
      throw new Error("traits must be a list of at most " + CHARACTER_MAX_TRAIT_ROWS + " rows");
    }
    var traitKeys = {};
    payload.traits.forEach(function (row) {
      validateCharacterTraitRow(row);
      if (traitKeys[row.key]) {
        throw new Error("trait keys must be unique");
      }
      traitKeys[row.key] = true;
    });
    if (!Array.isArray(payload.actives) || payload.actives.length > CHARACTER_MAX_CATEGORY_GROUPS) {
      throw new Error(
        "actives must be a list of at most " + CHARACTER_MAX_CATEGORY_GROUPS + " category groups"
      );
    }
    payload.actives.forEach(function (group) {
      validateCharacterCategoryGroup(group, validateCharacterActiveSkillRow);
    });
    if (characterFlattenedSkillCount(payload.actives) > CHARACTER_MAX_ACTIVE_ROWS) {
      throw new Error(
        "actives must contain at most " + CHARACTER_MAX_ACTIVE_ROWS + " skill rows in total"
      );
    }
    if (!Array.isArray(payload.passives) || payload.passives.length > CHARACTER_MAX_CATEGORY_GROUPS) {
      throw new Error(
        "passives must be a list of at most " + CHARACTER_MAX_CATEGORY_GROUPS + " category groups"
      );
    }
    payload.passives.forEach(function (group) {
      validateCharacterCategoryGroup(group, validateCharacterPassiveRow);
    });
    if (characterFlattenedSkillCount(payload.passives) > CHARACTER_MAX_PASSIVE_ROWS) {
      throw new Error(
        "passives must contain at most " + CHARACTER_MAX_PASSIVE_ROWS + " skill rows in total"
      );
    }
    if (!Array.isArray(payload.equipment) || payload.equipment.length > CHARACTER_MAX_EQUIPMENT_ROWS) {
      throw new Error("equipment must be a list of at most " + CHARACTER_MAX_EQUIPMENT_ROWS + " rows");
    }
    payload.equipment.forEach(validateCharacterEquipmentRow);
    validateCharacterDisguise(payload.disguise);
    validateCharacterGuild(payload.guild);
    requireInt(payload.wallet, "wallet", 0, MAX_SAFE_INTEGER);
    var persona = validateCharacterPersona(payload.persona);

    var intimate = validateCharacterIntimate(payload.intimate);
    var result = {
      schema_version: 7,
      available: true,
      kind: "character",
      traits: payload.traits,
      actives: payload.actives,
      passives: payload.passives,
      equipment: payload.equipment,
      disguise: payload.disguise,
      guild: payload.guild,
      wallet: payload.wallet,
      persona: persona,
      intimate: intimate,
    };
    if (fullTitle !== null) {
      result.full_title = fullTitle;
    }
    // Envelope guarantee (design D10): an over-limit payload fails closed.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("character payload exceeds the OOB envelope limit");
    }
    return result;
  }

  function validateCharacterPanel(payload) {
    // Version gate (mirror of the server validator): 7 is the only accepted
    // schema version (persona-editing four-key persona section).
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 7) {
      throw new Error("unsupported character schema_version");
    }
    return validateCharacterAvailablePanel(payload);
  }

  // Panel discriminator dispatch: the unavailable form is common to every
  // registered panel; the available form is validated against its schema.

  // Exact available art panel v1 schema (mirror of
  // web.webclient.presentation.art, webclient-art-panel D1).
  var ART_PLACEHOLDER_KINDS = ["missing", "unavailable"];
  var ART_ROLES = ["隊友", "敵方", "對話對象", "人物"];

  function validateArtPlaceholder(value) {
    if (value === null) {
      return null;
    }
    requireExactFields(value, "art placeholder", ["kind", "label"], []);
    if (ART_PLACEHOLDER_KINDS.indexOf(value.kind) === -1) {
      throw new Error("placeholder kind is not a stable value");
    }
    var label = requireString(value.label, "placeholder label", 128);
    if (!label.trim()) {
      throw new Error("placeholder label must be non-empty");
    }
    return { kind: value.kind, label: label };
  }

  function validateArtScene(value) {
    requireExactFields(
      value,
      "art scene",
      ["archetype", "label", "subject_key", "status", "url", "aspect_ratio", "alt", "placeholder"],
      []
    );
    if (value.archetype !== null) {
      var archetype = requireString(value.archetype, "archetype", 64);
      if (!archetype.trim()) {
        throw new Error("scene archetype must be non-empty");
      }
    }
    var label = requireString(value.label, "scene label", 128);
    if (!label.trim()) {
      throw new Error("scene label must be non-empty");
    }
    if (value.subject_key !== null) {
      requireString(value.subject_key, "scene subject_key", 128);
    }
    var status = value.status;
    if (status !== null) {
      requireString(status, "scene status", 16);
      if (["missing", "pending", "failed", "done"].indexOf(status) === -1) {
        throw new Error("scene status is not a stable value");
      }
    }
    var url = value.url;
    if (url !== null) {
      requireString(url, "scene url", 128);
      if (url.indexOf("/art/") !== 0) {
        throw new Error("scene url must be a same-origin media URL");
      }
    }
    if (value.aspect_ratio !== null && value.aspect_ratio !== "16:9") {
      throw new Error("scene aspect_ratio must be 16:9");
    }
    var alt = requireString(value.alt, "scene alt", 512);
    if (!alt.trim()) {
      throw new Error("scene alt must be non-empty");
    }
    var placeholder = validateArtPlaceholder(value.placeholder);
    if (placeholder === null && status !== "done") {
      throw new Error("scene placeholder must be present unless done");
    }
    if (placeholder !== null && status === "done") {
      throw new Error("a done scene must not carry a placeholder");
    }
    return {
      archetype: value.archetype,
      label: label,
      subject_key: value.subject_key,
      status: status,
      url: url,
      aspect_ratio: value.aspect_ratio,
      alt: alt,
      placeholder: placeholder,
    };
  }

  function validateArtContext(value) {
    requireExactFields(value, "art context", ["name", "role"], []);
    var name = requireString(value.name, "context name", 64);
    if (!name.trim()) {
      throw new Error("context name must be non-empty");
    }
    var role = requireString(value.role, "context role", 16);
    if (ART_ROLES.indexOf(role) === -1) {
      throw new Error("context role is not a stable value");
    }
    return { name: name, role: role };
  }

  function validateArtCatalogEntry(value) {
    requireExactFields(
      value,
      "art catalog entry",
      ["subject_key", "status", "url", "aspect_ratio", "alt", "placeholder", "context"],
      []
    );
    if (value.subject_key !== null) {
      requireString(value.subject_key, "catalog subject_key", 128);
    }
    var status = value.status;
    if (status !== null) {
      requireString(status, "catalog status", 16);
      if (["missing", "pending", "failed", "done"].indexOf(status) === -1) {
        throw new Error("catalog status is not a stable value");
      }
    }
    var url = value.url;
    if (url !== null) {
      requireString(url, "catalog url", 128);
      if (url.indexOf("/art/") !== 0) {
        throw new Error("catalog url must be a same-origin media URL");
      }
    }
    if (value.aspect_ratio !== null && value.aspect_ratio !== "3:4") {
      throw new Error("catalog aspect_ratio must be 3:4");
    }
    var alt = requireString(value.alt, "catalog alt", 512);
    if (!alt.trim()) {
      throw new Error("catalog alt must be non-empty");
    }
    validateArtPlaceholder(value.placeholder);
    validateArtContext(value.context);
    return value;
  }

  function validateArtPanel(payload) {
    requireExactFields(
      payload,
      "art panel",
      ["schema_version", "available", "kind", "scene", "portrait_catalog"],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 1) {
      throw new Error("unsupported art schema_version");
    }
    if (payload.available !== true || payload.kind !== "scene") {
      throw new Error("art panel must be available with kind scene");
    }

    var scene = validateArtScene(payload.scene);
    var catalog = payload.portrait_catalog;
    if (!isPlainObject(catalog) || Object.keys(catalog).length > 32) {
      throw new Error("portrait_catalog must be a bounded object");
    }
    var entries = {};
    var keys = Object.keys(catalog);
    for (var i = 0; i < keys.length; i++) {
      var key = keys[i];
      if (!/^[0-9]+$/.test(key)) {
        throw new Error("catalog keys must be opaque decimal strings");
      }
      entries[key] = validateArtCatalogEntry(catalog[key]);
    }

    var result = {
      schema_version: 1,
      available: true,
      kind: "scene",
      scene: scene,
      portrait_catalog: entries,
    };
    // Envelope guarantee (design D7): per-field bounds are ceilings, not a
    // guarantee that any combination of them fits, so the validator enforces
    // the serialized byte size directly and fails closed over the envelope.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("art payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // -------------------------------------------------------------------------
  // title_ballot panel validator (mirror of web.webclient.presentation.
  // title_ballot, title-epithet-nomination D4). Zero candidates is the
  // legitimate idle form; the rules layer never truncates the basis, and
  // neither does this mirror.
  // -------------------------------------------------------------------------

  function validateTitleBallotCandidate(value, position) {
    requireExactFields(
      value,
      "title ballot candidate",
      ["index", "display", "basis"],
      []
    );
    requireInt(value.index, "candidate index", 1, TITLE_BALLOT_MAX_CANDIDATES);
    if (value.index !== position) {
      throw new Error("candidate indices must be strictly 1..n ascending");
    }
    requireString(value.display, "candidate display", TITLE_BALLOT_MAX_DISPLAY);
    if (codePoints(value.display) < 1) {
      throw new Error("candidate display must be non-empty");
    }
    requireString(value.basis, "candidate basis", TITLE_BALLOT_MAX_BASIS);
    if (codePoints(value.basis) < 1) {
      throw new Error("candidate basis must be non-empty");
    }
    return {
      index: value.index,
      display: value.display,
      basis: value.basis,
    };
  }

  // Exact available title_ballot panel v1 schema.
  function validateTitleBallotPanel(payload) {
    requireExactFields(
      payload,
      "title_ballot panel",
      ["schema_version", "available", "kind", "candidates"],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 1) {
      throw new Error("unsupported title_ballot schema_version");
    }
    if (payload.available !== true || payload.kind !== "title_ballot") {
      throw new Error(
        "title_ballot panel must be available with kind title_ballot"
      );
    }
    var candidates = payload.candidates;
    if (!Array.isArray(candidates)) {
      throw new Error("title ballot candidates must be a list");
    }
    if (candidates.length > TITLE_BALLOT_MAX_CANDIDATES) {
      throw new Error(
        "title ballot candidates must hold at most " +
          TITLE_BALLOT_MAX_CANDIDATES +
          " entries"
      );
    }
    var normalized = [];
    for (var i = 0; i < candidates.length; i++) {
      normalized.push(validateTitleBallotCandidate(candidates[i], i + 1));
    }
    var result = {
      schema_version: 1,
      available: true,
      kind: "title_ballot",
      candidates: normalized,
    };
    // Envelope guarantee: the per-field ceilings keep any legal ballot far
    // below the envelope limit; an over-limit payload can only come from a
    // producer bug and fails closed.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("title_ballot payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // -------------------------------------------------------------------------
  // title_codex panel validator (mirror of web.webclient.presentation.
  // title_codex, title-codex-removal D5/D7). Bounds are owned by
  // world/rules/title_view.py; the hint/flavor exclusivity and the category
  // closed set are re-asserted here exactly as the Python validator does.
  // -------------------------------------------------------------------------

  function inCategorySet(value) {
    for (var i = 0; i < TITLE_CODEX_CATEGORIES.length; i++) {
      if (TITLE_CODEX_CATEGORIES[i] === value) {
        return true;
      }
    }
    return false;
  }

  function validateTitleCodexFixedRow(value, position) {
    var label = "title codex fixed row " + position;
    requireExactFields(
      value,
      label,
      [
        "key",
        "display",
        "category",
        "hint",
        "flavor",
        "unlocked",
        "granted_tick",
      ],
      []
    );
    validateIdentifier(value.key, label + " key");
    requireString(value.display, label + " display", TITLE_CODEX_MAX_DISPLAY);
    if (codePoints(value.display.trim()) < 1) {
      throw new Error(label + " display must be non-empty");
    }
    requireString(value.category, label + " category", 32);
    if (!inCategorySet(value.category)) {
      throw new Error(label + " category is outside the closed set");
    }
    var unlocked = requireBool(value.unlocked, label + " unlocked");
    var hint = requireString(value.hint, label + " hint", TITLE_CODEX_MAX_BASIS);
    var flavor = requireString(
      value.flavor,
      label + " flavor",
      TITLE_CODEX_MAX_BASIS
    );
    if (unlocked && codePoints(hint) > 0) {
      throw new Error(label + " unlocked row must not carry a hint");
    }
    if (!unlocked && codePoints(flavor) > 0) {
      throw new Error(label + " locked row must not carry flavor");
    }
    requireInt(value.granted_tick, label + " granted_tick", 0, MAX_SAFE_INTEGER);
    return {
      key: value.key,
      display: value.display,
      category: value.category,
      hint: hint,
      flavor: flavor,
      unlocked: unlocked,
      granted_tick: value.granted_tick,
    };
  }

  function validateTitleCodexEpithetRow(value, position) {
    var label = "title codex epithet row " + position;
    requireExactFields(
      value,
      label,
      ["display", "basis", "granted_tick", "equipped", "can_remove"],
      []
    );
    requireString(value.display, label + " display", TITLE_CODEX_MAX_DISPLAY);
    if (codePoints(value.display.trim()) < 1) {
      throw new Error(label + " display must be non-empty");
    }
    requireString(value.basis, label + " basis", TITLE_CODEX_MAX_BASIS);
    requireInt(value.granted_tick, label + " granted_tick", 0, MAX_SAFE_INTEGER);
    var equipped = requireBool(value.equipped, label + " equipped");
    // The server owns the gate verdict; the client renders the flag and
    // evaluates no removal rule of its own.
    var canRemove = requireBool(value.can_remove, label + " can_remove");
    return {
      display: value.display,
      basis: value.basis,
      granted_tick: value.granted_tick,
      equipped: equipped,
      can_remove: canRemove,
    };
  }

  function validateTitleCodexBallotEntry(value, position) {
    var label = "title codex pending ballot " + position;
    requireExactFields(value, label, ["display", "basis"], []);
    requireString(value.display, label + " display", TITLE_CODEX_MAX_DISPLAY);
    if (codePoints(value.display.trim()) < 1) {
      throw new Error(label + " display must be non-empty");
    }
    requireString(value.basis, label + " basis", TITLE_CODEX_BASIS_WIRE_MAX);
    return { display: value.display, basis: value.basis };
  }

  function validateTitleCodexEquipped(value) {
    requireExactFields(value, "title codex equipped", ["fixed", "epithet"], []);
    if (value.fixed !== null) {
      validateIdentifier(value.fixed, "equipped.fixed");
    }
    if (value.epithet !== null) {
      requireString(value.epithet, "equipped.epithet", TITLE_CODEX_MAX_DISPLAY);
      if (codePoints(value.epithet) < 1) {
        throw new Error("equipped.epithet must be non-empty or null");
      }
    }
    return { fixed: value.fixed, epithet: value.epithet };
  }

  // Exact available title_codex panel v1 schema.
  function validateTitleCodexPanel(payload) {
    requireExactFields(
      payload,
      "title_codex panel",
      [
        "schema_version",
        "available",
        "kind",
        "fixed_rows",
        "epithet_rows",
        "equipped",
        "full_title",
        "unlocked",
        "total",
        "pending_ballot",
      ],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== 1) {
      throw new Error("unsupported title_codex schema_version");
    }
    if (payload.available !== true || payload.kind !== "title_codex") {
      throw new Error(
        "title_codex panel must be available with kind title_codex"
      );
    }
    if (!Array.isArray(payload.fixed_rows)) {
      throw new Error("title codex fixed_rows must be a list");
    }
    if (payload.fixed_rows.length > TITLE_CODEX_MAX_ROWS) {
      throw new Error(
        "title codex fixed_rows must hold at most " + TITLE_CODEX_MAX_ROWS + " entries"
      );
    }
    if (!Array.isArray(payload.epithet_rows)) {
      throw new Error("title codex epithet_rows must be a list");
    }
    if (payload.epithet_rows.length > TITLE_CODEX_MAX_ROWS) {
      throw new Error(
        "title codex epithet_rows must hold at most " +
          TITLE_CODEX_MAX_ROWS +
          " entries"
      );
    }
    if (!Array.isArray(payload.pending_ballot)) {
      throw new Error("title codex pending_ballot must be a list");
    }
    if (payload.pending_ballot.length > TITLE_CODEX_MAX_BALLOT) {
      throw new Error(
        "title codex pending_ballot must hold at most " +
          TITLE_CODEX_MAX_BALLOT +
          " entries"
      );
    }
    var unlocked = requireInt(payload.unlocked, "unlocked", 0, MAX_SAFE_INTEGER);
    var total = requireInt(payload.total, "total", 0, MAX_SAFE_INTEGER);
    if (unlocked > total) {
      throw new Error("unlocked must not exceed total");
    }
    requireString(payload.full_title, "full_title", TITLE_CODEX_MAX_FULL_TITLE);
    var fixedRows = [];
    for (var f = 0; f < payload.fixed_rows.length; f++) {
      fixedRows.push(validateTitleCodexFixedRow(payload.fixed_rows[f], f + 1));
    }
    var epithetRows = [];
    for (var e = 0; e < payload.epithet_rows.length; e++) {
      epithetRows.push(
        validateTitleCodexEpithetRow(payload.epithet_rows[e], e + 1)
      );
    }
    var ballot = [];
    for (var b = 0; b < payload.pending_ballot.length; b++) {
      ballot.push(validateTitleCodexBallotEntry(payload.pending_ballot[b], b + 1));
    }
    var result = {
      schema_version: 1,
      available: true,
      kind: "title_codex",
      fixed_rows: fixedRows,
      epithet_rows: epithetRows,
      equipped: validateTitleCodexEquipped(payload.equipped),
      full_title: payload.full_title,
      unlocked: unlocked,
      total: total,
      pending_ballot: ballot,
    };
    // Envelope guarantee mirrors the Python validator's closing check.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("title_codex payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // Party panel validator (mirror of web.webclient.presentation.party).
  // Rows reuse the NPC wire vocabulary; the raw affinity number can never
  // appear because bond_stage is a bounded non-empty string; HP fields are
  // zero-clamped bounds with NO current/maximum cross assertion (traits are
  // truth — the Python validator documents the same rule).
  // Unpaired UTF-16 surrogate halves are rejected on both sides: they are
  // not valid JSON text and cannot survive the Python UTF-8 byte check.
  function hasLoneSurrogate(value) {
    var pendingHigh = false;
    for (var i = 0; i < value.length; i++) {
      var code = value.charCodeAt(i);
      if (pendingHigh) {
        if (code < 0xdc00 || code > 0xdfff) {
          return true;
        }
        pendingHigh = false;
        continue;
      }
      if (code >= 0xd800 && code <= 0xdbff) {
        pendingHigh = true;
      } else if (code >= 0xdc00 && code <= 0xdfff) {
        return true;
      }
    }
    return pendingHigh;
  }

  function validatePartySlot(value, index) {
    var name = "party slot " + index;
    requireExactFields(
      value,
      name,
      ["identity", "display_name", "portrait_ref", "hp_current", "hp_maximum", "bond_stage"],
      []
    );
    var identity = requireInt(value.identity, "identity", 1, MAX_SAFE_INTEGER);
    var displayName = requireString(value.display_name, "display_name", PARTY_MAX_DISPLAY_NAME);
    if (displayName.length === 0 || hasLoneSurrogate(displayName)) {
      throw new Error("slot display_name must be non-empty");
    }
    if (value.portrait_ref !== null) {
      throw new Error("portrait_ref must be null in this schema version");
    }
    var hpCurrent = requireInt(value.hp_current, "hp_current", 0, MAX_SAFE_INTEGER);
    var hpMaximum = requireInt(value.hp_maximum, "hp_maximum", 0, MAX_SAFE_INTEGER);
    var bondStage = requireString(value.bond_stage, "bond_stage", PARTY_MAX_DISPLAY_NAME);
    if (bondStage.length === 0 || hasLoneSurrogate(bondStage)) {
      throw new Error("slot bond_stage must be a non-empty stage name");
    }
    return {
      identity: identity,
      display_name: displayName,
      portrait_ref: null,
      hp_current: hpCurrent,
      hp_maximum: hpMaximum,
      bond_stage: bondStage,
    };
  }

  function validatePartyPanel(payload) {
    requireExactFields(payload, "party panel", ["schema_version", "available", "slots"], []);
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== PARTY_SCHEMA_VERSION) {
      throw new Error("unsupported party schema_version");
    }
    if (payload.available !== true) {
      throw new Error("party panel must be available");
    }
    var slots = payload.slots;
    if (!Array.isArray(slots)) {
      throw new Error("party slots must be a list");
    }
    if (slots.length > PARTY_MAX_ROWS) {
      throw new Error("party slots must hold at most " + PARTY_MAX_ROWS + " rows");
    }
    var normalized = [];
    var seen = {};
    for (var i = 0; i < slots.length; i++) {
      var row = validatePartySlot(slots[i], i + 1);
      if (Object.prototype.hasOwnProperty.call(seen, row.identity)) {
        throw new Error("party slot identities must be unique");
      }
      seen[row.identity] = true;
      normalized.push(row);
    }
    var result = {
      schema_version: PARTY_SCHEMA_VERSION,
      available: true,
      slots: normalized,
    };
    // Envelope guarantee mirrors the Python validator's closing check.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("party payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // Objectives panel validator (mirror of
  // web.webclient.presentation.objectives, webclient-align-06). At most three
  // tracked quest rows in quest-log order; reward_copper is a non-negative
  // integer or null; same surrogate guards as the party mirror.
  function validateObjectivesRow(value, index) {
    var name = "objective row " + index;
    requireExactFields(
      value,
      name,
      [
        "quest_id",
        "display_name",
        "objective_line",
        "stage_index",
        "stage_total",
        "stage_progress",
        "objective_quantity",
        "reward_copper",
        "deadline_line",
      ],
      []
    );
    var questId = requireString(value.quest_id, "quest_id", OBJECTIVES_MAX_QUEST_ID);
    if (!questId.trim() || hasLoneSurrogate(questId)) {
      throw new Error(name + " quest_id must be non-empty");
    }
    var displayName = requireString(
      value.display_name,
      "display_name",
      OBJECTIVES_MAX_DISPLAY_NAME
    );
    if (!displayName.trim() || hasLoneSurrogate(displayName)) {
      throw new Error(name + " display_name must be non-empty");
    }
    var objectiveLine = requireString(
      value.objective_line,
      "objective_line",
      OBJECTIVES_MAX_OBJECTIVE_LINE
    );
    if (!objectiveLine.trim() || hasLoneSurrogate(objectiveLine)) {
      throw new Error(name + " objective_line must be non-empty");
    }
    requireInt(value.stage_index, "stage_index", 0, MAX_SAFE_INTEGER);
    requireInt(value.stage_total, "stage_total", 1, MAX_SAFE_INTEGER);
    requireInt(value.stage_progress, "stage_progress", 0, MAX_SAFE_INTEGER);
    requireInt(value.objective_quantity, "objective_quantity", 1, MAX_SAFE_INTEGER);
    if (value.reward_copper !== null) {
      requireInt(value.reward_copper, "reward_copper", 0, MAX_SAFE_INTEGER);
    }
    if (value.deadline_line !== null) {
      var deadline = requireString(
        value.deadline_line,
        "deadline_line",
        OBJECTIVES_MAX_DEADLINE_LINE
      );
      if (!deadline.trim() || hasLoneSurrogate(deadline)) {
        throw new Error(name + " deadline_line must be non-empty when set");
      }
    }
    return value;
  }

  function validateObjectivesPanel(payload) {
    requireExactFields(
      payload,
      "objectives panel",
      ["schema_version", "available", "rows"],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== OBJECTIVES_SCHEMA_VERSION) {
      throw new Error("unsupported objectives schema_version");
    }
    if (payload.available !== true) {
      throw new Error("objectives panel must be available");
    }
    var rows = payload.rows;
    if (!Array.isArray(rows)) {
      throw new Error("objectives rows must be a list");
    }
    if (rows.length > OBJECTIVES_MAX_ROWS) {
      throw new Error(
        "objectives rows must hold at most " + OBJECTIVES_MAX_ROWS + " entries"
      );
    }
    var normalized = [];
    var seen = {};
    for (var i = 0; i < rows.length; i++) {
      var row = validateObjectivesRow(rows[i], i + 1);
      if (Object.prototype.hasOwnProperty.call(seen, row.quest_id)) {
        throw new Error("objective quest_ids must be unique");
      }
      seen[row.quest_id] = true;
      normalized.push(row);
    }
    var result = {
      schema_version: OBJECTIVES_SCHEMA_VERSION,
      available: true,
      rows: normalized,
    };
    // Envelope guarantee mirrors the Python validator's closing check.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("objectives payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // Dialogue panel validator (mirror of web.webclient.presentation.dialogue,
  // webclient-align-10). Available form is exactly schema_version, available,
  // kind, host (party-row triple with a null portrait_ref), bond_stage (a
  // stage NAME or null — never a number), a bounded line, and at most
  // DIALOGUE_MAX_CHOICES unique {keyword_id, label} rows. Every string
  // rejects lone surrogates exactly like the Python validator; over-bound or
  // corrupt values reject, never truncate.
  function validateDialoguePanel(payload) {
    requireExactFields(
      payload,
      "dialogue panel",
      ["schema_version", "available", "kind", "host", "bond_stage", "line", "choices"],
      []
    );
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== DIALOGUE_SCHEMA_VERSION) {
      throw new Error("unsupported dialogue schema_version");
    }
    if (payload.available !== true) {
      throw new Error("dialogue panel must be available");
    }
    if (payload.kind !== "dialogue") {
      throw new Error("dialogue kind must be dialogue");
    }
    requireExactFields(
      payload.host,
      "dialogue host",
      ["identity", "display_name", "portrait_ref"],
      []
    );
    requireInt(payload.host.identity, "identity", 1, MAX_SAFE_INTEGER);
    var hostName = requireString(
      payload.host.display_name,
      "display_name",
      PARTY_MAX_DISPLAY_NAME
    );
    if (!hostName.trim() || hasLoneSurrogate(hostName)) {
      throw new Error("host display_name must be non-empty");
    }
    if (payload.host.portrait_ref !== null) {
      throw new Error("portrait_ref must be null in this schema version");
    }
    if (payload.bond_stage !== null) {
      var bondStage = requireString(
        payload.bond_stage,
        "bond_stage",
        PARTY_MAX_DISPLAY_NAME
      );
      if (!bondStage.trim() || hasLoneSurrogate(bondStage)) {
        throw new Error("bond_stage must be non-empty when set");
      }
    }
    var line = requireString(payload.line, "line", DIALOGUE_MAX_LINE);
    if (!line.trim() || hasLoneSurrogate(line)) {
      throw new Error("dialogue line must be non-empty");
    }
    var choices = payload.choices;
    if (!Array.isArray(choices)) {
      throw new Error("dialogue choices must be a list");
    }
    if (choices.length > DIALOGUE_MAX_CHOICES) {
      throw new Error(
        "dialogue choices must hold at most " + DIALOGUE_MAX_CHOICES + " entries"
      );
    }
    var seen = {};
    for (var i = 0; i < choices.length; i++) {
      var choice = choices[i];
      var name = "dialogue choice " + (i + 1);
      requireExactFields(choice, name, ["keyword_id", "label"], []);
      var keywordId = requireString(
        choice.keyword_id,
        "keyword_id",
        DIALOGUE_MAX_KEYWORD_ID
      );
      if (!keywordId.trim() || hasLoneSurrogate(keywordId)) {
        throw new Error(name + " keyword_id must be non-empty");
      }
      var label = requireString(
        choice.label,
        "label",
        DIALOGUE_MAX_KEYWORD_LABEL
      );
      if (!label.trim() || hasLoneSurrogate(label)) {
        throw new Error(name + " label must be non-empty");
      }
      if (Object.prototype.hasOwnProperty.call(seen, keywordId)) {
        throw new Error("dialogue choice keyword ids must be unique");
      }
      seen[keywordId] = true;
    }
    var result = {
      schema_version: DIALOGUE_SCHEMA_VERSION,
      available: true,
      kind: "dialogue",
      host: payload.host,
      bond_stage: payload.bond_stage,
      line: line,
      choices: choices,
    };
    // Envelope guarantee mirrors the Python validator's closing check.
    if (jsonByteSize(result) > MAX_CANONICAL_JSON_BYTES) {
      throw new Error("dialogue payload exceeds the OOB envelope limit");
    }
    return result;
  }

  // Panel discriminator dispatch: the unavailable form is common to every
  // registered panel; the available form is validated against its schema.
  function validateUnavailablePanel(payload, schemaVersion) {
    // The common unavailable discriminator: exactly schema_version, available
    // false, and a bounded reason. schema_version matches the panel's
    // registered version (so a v2 panel like context_actions is accepted).
    requireExactFields(payload, "panel", ["schema_version", "available", "reason"], []);
    requireInt(payload.schema_version, "schema_version", 1, MAX_SAFE_INTEGER);
    if (payload.schema_version !== schemaVersion) {
      throw new Error("unsupported panel schema_version");
    }
    if (payload.available !== false) {
      throw new Error("available must be false for the unavailable form");
    }
    var reason = payload.reason;
    var hasCorrelation = Object.prototype.hasOwnProperty.call(reason, "correlation_id");
    requireExactFields(
      reason,
      "panel reason",
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

  function validatePanel(name, schemaVersion, payload) {
    if (!isPlainObject(payload)) {
      throw new Error("panel " + name + " must be a JSON object");
    }
    requireInt(payload.schema_version, "panel schema_version", 1, MAX_SAFE_INTEGER);
    // Every panel (character included, since render-equipment-
    // breakdown-webclient retired the transitional character v4 branch)
    // must match its registered version exactly.
    if (payload.schema_version !== schemaVersion) {
      throw new Error(
        "panel " + name + " schema_version does not match registered version"
      );
    }
    if (payload.available === false) {
      return validateUnavailablePanel(payload, schemaVersion);
    }
    if (payload.available !== true) {
      throw new Error("panel " + name + " is missing the availability discriminator");
    }
    if (name === "art") {
      return validateArtPanel(payload);
    }
    if (name === "exploration") {
      return validateExplorationPanel(payload);
    }
    if (name === "character") {
      return validateCharacterPanel(payload);
    }
    if (name === "title_codex") {
      return validateTitleCodexPanel(payload);
    }
    if (name === "status") {
      return validateStatusPanel(payload);
    }
    if (name === "context_actions") {
      return validateContextActionsPanel(payload);
    }
    if (name === "local_map") {
      return validateLocalMapPanel(payload);
    }
    if (name === "party") {
      return validatePartyPanel(payload);
    }
    if (name === "objectives") {
      return validateObjectivesPanel(payload);
    }
    if (name === "dialogue") {
      return validateDialoguePanel(payload);
    }
    if (name === "services") {
      return validateServicesPanel(payload);
    }
    if (name === "creation") {
      return validateCreationPanel(payload);
    }
    if (name === "lineage") {
      return validateLineagePanel(payload);
    }
    if (name === "title_ballot") {
      return validateTitleBallotPanel(payload);
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
      ["correlation_id", "data"]
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
    var hasData = Object.prototype.hasOwnProperty.call(payload, "data");
    if (hasData && payload.outcome !== "success") {
      throw new Error("data is forbidden for a non-success result");
    }
    var result = {
      protocolVersion: PROTOCOL_VERSION,
      epoch: payload.presentation_epoch,
      requestId: payload.request_id,
      outcome: payload.outcome,
      code: payload.code,
      message: payload.message,
      presentationRevision: payload.presentation_revision,
      correlationId: correlationId,
    };
    if (hasData) {
      result.data = validateResultData(payload.data);
    }
    return result;
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
    MAX_RESULT_DATA_FIELDS: MAX_RESULT_DATA_FIELDS,
    MAX_RESULT_DATA_BYTES: MAX_RESULT_DATA_BYTES,
    RESULT_DATA_STANDARD_RESERVE: RESULT_DATA_STANDARD_RESERVE,
    EPOCH_LENGTH: EPOCH_LENGTH,
    MAX_RETIRED_EPOCHS: MAX_RETIRED_EPOCHS,
    MAX_ACTOR_NAME: MAX_ACTOR_NAME,
    MAX_ACTOR_IDENTITY: MAX_ACTOR_IDENTITY,
    MAX_FULL_TITLE_CODE_POINTS: MAX_FULL_TITLE_CODE_POINTS,
    MAX_LOCATION_LABEL: MAX_LOCATION_LABEL,
    MAX_CONDITION_COUNT: MAX_CONDITION_COUNT,
    MAX_CONDITION_LABEL: MAX_CONDITION_LABEL,
    MAX_MODIFIER_KEYS: MAX_MODIFIER_KEYS,
    LOCAL_MAP_MAX_NODES: LOCAL_MAP_MAX_NODES,
    LOCAL_MAP_MAX_EDGES: LOCAL_MAP_MAX_EDGES,
    LOCAL_MAP_MAX_LEGEND: LOCAL_MAP_MAX_LEGEND,
    LOCAL_MAP_MAX_STRING: LOCAL_MAP_MAX_STRING,
    LOCAL_MAP_MAX_TITLE: LOCAL_MAP_MAX_TITLE,
    LOCAL_MAP_MAX_NODE_ID: LOCAL_MAP_MAX_NODE_ID,
    LOCAL_MAP_MAX_EXIT_REF: LOCAL_MAP_MAX_EXIT_REF,
    LOCAL_MAP_COORD_MIN: LOCAL_MAP_COORD_MIN,
    LOCAL_MAP_COORD_MAX: LOCAL_MAP_COORD_MAX,
    LOCAL_MAP_VISIBILITIES: LOCAL_MAP_VISIBILITIES.slice(),
    LOCAL_MAP_LAYERS: LOCAL_MAP_LAYERS.slice(),
    LOCAL_MAP_ACTION_KINDS: LOCAL_MAP_ACTION_KINDS.slice(),
    SERVICES_MAX_BOARD_ROWS: SERVICES_MAX_BOARD_ROWS,
    SERVICES_MAX_QUEST_ROWS: SERVICES_MAX_QUEST_ROWS,
    SERVICES_MAX_STOCK_ROWS: SERVICES_MAX_STOCK_ROWS,
    SERVICES_MAX_SELLABLE_ROWS: SERVICES_MAX_SELLABLE_ROWS,
    SERVICES_MAX_INVENTORY_ROWS: SERVICES_MAX_INVENTORY_ROWS,
    SERVICES_MAX_KEY: SERVICES_MAX_KEY,
    SERVICES_MAX_DISPLAY_NAME: SERVICES_MAX_DISPLAY_NAME,
    SERVICES_MAX_SUMMARY: SERVICES_MAX_SUMMARY,
    SERVICES_MAX_DETAIL: SERVICES_MAX_DETAIL,
    SERVICES_MAX_DEADLINE_LINE: SERVICES_MAX_DEADLINE_LINE,
    SERVICES_MAX_RANK_KEY: SERVICES_MAX_RANK_KEY,
    SERVICES_MAX_HOST_DISPLAY_NAME: SERVICES_MAX_HOST_DISPLAY_NAME,
    SERVICES_MAX_LABEL: SERVICES_MAX_LABEL,
    SERVICES_MAX_REASON_MESSAGE: SERVICES_MAX_REASON_MESSAGE,
    SERVICES_MAX_QUANTITY: SERVICES_MAX_QUANTITY,
    SERVICES_MIN_QUANTITY: SERVICES_MIN_QUANTITY,
    SERVICES_MAX_PRESENTATION_KEY: SERVICES_MAX_PRESENTATION_KEY,
    SERVICES_MAX_PRESENTATION_SUMMARY: SERVICES_MAX_PRESENTATION_SUMMARY,
    SERVICES_QUEST_STATES: SERVICES_QUEST_STATES.slice(),
    SERVICES_ACTIONS: SERVICES_ACTIONS.slice(),
    EXPLORATION_MAX_MOVE_EXITS: EXPLORATION_MAX_MOVE_EXITS,
    EXPLORATION_MAX_LOOK_ENTITIES: EXPLORATION_MAX_LOOK_ENTITIES,
    EXPLORATION_MAX_LOOK_OBJECTS: EXPLORATION_MAX_LOOK_OBJECTS,
    EXPLORATION_MAX_INTERACT_TARGETS: EXPLORATION_MAX_INTERACT_TARGETS,
    EXPLORATION_MAX_AFFORDANCES: EXPLORATION_MAX_AFFORDANCES,
    EXPLORATION_MAX_SCRIPTED_KEYWORDS: EXPLORATION_MAX_SCRIPTED_KEYWORDS,
    EXPLORATION_MAX_EXIT_REF: EXPLORATION_MAX_EXIT_REF,
    EXPLORATION_MAX_NODE_ID: EXPLORATION_MAX_NODE_ID,
    TITLE_BALLOT_MAX_CANDIDATES: TITLE_BALLOT_MAX_CANDIDATES,
    TITLE_BALLOT_MAX_DISPLAY: TITLE_BALLOT_MAX_DISPLAY,
    TITLE_BALLOT_MAX_BASIS: TITLE_BALLOT_MAX_BASIS,
    EXPLORATION_MAX_DISPLAY_NAME: EXPLORATION_MAX_DISPLAY_NAME,
    EXPLORATION_MAX_KIND: EXPLORATION_MAX_KIND,
    EXPLORATION_MAX_LABEL: EXPLORATION_MAX_LABEL,
    EXPLORATION_MAX_KEYWORD_ID: EXPLORATION_MAX_KEYWORD_ID,
    EXPLORATION_MAX_KEYWORD_LABEL: EXPLORATION_MAX_KEYWORD_LABEL,
    EXPLORATION_MAX_REASON_MESSAGE: EXPLORATION_MAX_REASON_MESSAGE,
    EXPLORATION_ACTION_KINDS: EXPLORATION_ACTION_KINDS.slice(),
    EXPLORATION_ACTION_IDS: EXPLORATION_ACTION_IDS.slice(),
    EXPLORATION_SURFACES: EXPLORATION_SURFACES.slice(),
    EXPLORATION_ENTITY_KINDS: EXPLORATION_ENTITY_KINDS.slice(),
    CONTEXT_ACTIONS_MAX_AFFORDANCES: CONTEXT_ACTIONS_MAX_AFFORDANCES,
    CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL: CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL,
    CONTEXT_ACTIONS_MAX_PARAM_KEYS: CONTEXT_ACTIONS_MAX_PARAM_KEYS,
    CONTEXT_ACTIONS_MAX_PARAM_STRING: CONTEXT_ACTIONS_MAX_PARAM_STRING,
    CONTEXT_ACTIONS_ACTION_CODES: CONTEXT_ACTIONS_ACTION_CODES.slice(),
    CONTEXT_ACTIONS_SURFACES: CONTEXT_ACTIONS_SURFACES.slice(),
    CHARACTER_MAX_TRAIT_ROWS: CHARACTER_MAX_TRAIT_ROWS,
    CHARACTER_MAX_ACTIVE_ROWS: CHARACTER_MAX_ACTIVE_ROWS,
    CHARACTER_MAX_PASSIVE_ROWS: CHARACTER_MAX_PASSIVE_ROWS,
    CHARACTER_MAX_CATEGORY_GROUPS: CHARACTER_MAX_CATEGORY_GROUPS,
    CHARACTER_MAX_EQUIPMENT_ROWS: CHARACTER_MAX_EQUIPMENT_ROWS,
    CHARACTER_MAX_DISPLAYED_ROWS: CHARACTER_MAX_DISPLAYED_ROWS,
    CHARACTER_MAX_KEY: CHARACTER_MAX_KEY,
    CHARACTER_MAX_LABEL: CHARACTER_MAX_LABEL,
    CHARACTER_MAX_DESCRIPTION: CHARACTER_MAX_DESCRIPTION,
    CHARACTER_MAX_SLOT: CHARACTER_MAX_SLOT,
    CHARACTER_MAX_PERSONA: CHARACTER_MAX_PERSONA,
    CHARACTER_PERSONA_FIELDS: CHARACTER_PERSONA_FIELDS.slice(),
    CREATION_MAX_PRESETS: CREATION_MAX_PRESETS,
    CREATION_MAX_RACES: CREATION_MAX_RACES,
    CREATION_MAX_SUBRACES: CREATION_MAX_SUBRACES,
    CREATION_MAX_PROFILES: CREATION_MAX_PROFILES,
    CREATION_MIN_NAME_LENGTH: CREATION_MIN_NAME_LENGTH,
    CREATION_MAX_NAME_LENGTH: CREATION_MAX_NAME_LENGTH,
    CREATION_AGE_MINIMUM: CREATION_AGE_MINIMUM,
    CREATION_AGE_MAXIMUM: CREATION_AGE_MAXIMUM,
    CREATION_APPARENT_AGE_MINIMUM: CREATION_APPARENT_AGE_MINIMUM,
    CREATION_APPARENT_AGE_MAXIMUM: CREATION_APPARENT_AGE_MAXIMUM,
    CREATION_MAX_PRESET_KEY: CREATION_MAX_PRESET_KEY,
    CREATION_MAX_DISPLAY_NAME: CREATION_MAX_DISPLAY_NAME,
    CREATION_MAX_RACE_KEY: CREATION_MAX_RACE_KEY,
    CREATION_MAX_DESCRIPTION: CREATION_MAX_DESCRIPTION,
    CREATION_MAX_EMPHASIS: CREATION_MAX_EMPHASIS,
    CREATION_MAX_BACKGROUND: CREATION_MAX_BACKGROUND,
    CREATION_MAX_PERSONA_BACKGROUND: CREATION_MAX_PERSONA_BACKGROUND,
    CREATION_MAX_SUBRACE_KEY: CREATION_MAX_SUBRACE_KEY,
    CREATION_MAX_SPECIALTY: CREATION_MAX_SPECIALTY,
    CREATION_MAX_LABEL: CREATION_MAX_LABEL,
    CREATION_MAX_PROPOSAL_NAME: CREATION_MAX_PROPOSAL_NAME,
    CREATION_MAX_EXPLANATION: CREATION_MAX_EXPLANATION,
    CREATION_AXES: CREATION_AXES.slice(),
    CREATION_SCHEMA_VERSION: CREATION_SCHEMA_VERSION,
    CREATION_PERSONA_KEYS: CREATION_PERSONA_KEYS.slice(),
    CREATION_SEX_VALUES: CREATION_SEX_VALUES.slice(),
    CREATION_SEX_DEFAULT: CREATION_SEX_DEFAULT,
    CREATION_MAX_SEX_OPTIONS: CREATION_MAX_SEX_OPTIONS,
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
    validateArtPanel: validateArtPanel,
    validateExplorationPanel: validateExplorationPanel,
    validateCharacterPanel: validateCharacterPanel,
    validateCharacterTraitRow: validateCharacterTraitRow,
    validateCharacterEquipmentRow: validateCharacterEquipmentRow,
    validateCharacterBreakdownLayer: validateCharacterBreakdownLayer,
    validateCharacterActiveSkillRow: validateCharacterActiveSkillRow,
    validateContextActionsPanel: validateContextActionsPanel,
    validateSuggestions: validateSuggestions,
    validateSuggestionCard: validateSuggestionCard,
    OPTIONS_STATUSES: OPTIONS_STATUSES.slice(),
    OPTIONS_CARD_KINDS: OPTIONS_CARD_KINDS.slice(),
    MAX_OPTION_CARDS: MAX_OPTION_CARDS,
    MAX_OPTION_LABEL: MAX_OPTION_LABEL,
    MAX_OPTION_HINT: MAX_OPTION_HINT,
    MAX_OPTION_PARAMS: MAX_OPTION_PARAMS,
    OPTIONS_FREEFORM_ACTION_CODE: OPTIONS_FREEFORM_ACTION_CODE,
    OPTIONS_MAX_PARAM_STRING: OPTIONS_MAX_PARAM_STRING,
    validateLocalMapPanel: validateLocalMapPanel,
    validateServicesPanel: validateServicesPanel,
    validatePartyPanel: validatePartyPanel,
    validateObjectivesPanel: validateObjectivesPanel,
    validateDialoguePanel: validateDialoguePanel,
    DIALOGUE_SCHEMA_VERSION: DIALOGUE_SCHEMA_VERSION,
    DIALOGUE_MAX_CHOICES: DIALOGUE_MAX_CHOICES,
    PARTY_SCHEMA_VERSION: PARTY_SCHEMA_VERSION,
    PARTY_MAX_ROWS: PARTY_MAX_ROWS,
    OBJECTIVES_SCHEMA_VERSION: OBJECTIVES_SCHEMA_VERSION,
    OBJECTIVES_MAX_ROWS: OBJECTIVES_MAX_ROWS,
    PARTY_MAX_DISPLAY_NAME: PARTY_MAX_DISPLAY_NAME,
    validateCreationPanel: validateCreationPanel,
    validateCreationPersona: validateCreationPersona,
    validateCreationProposal: validateCreationProposal,
    validateLineagePanel: validateLineagePanel,
    LINEAGE_MAX_CHAINS: LINEAGE_MAX_CHAINS,
    LINEAGE_MAX_NODES_PER_CHAIN: LINEAGE_MAX_NODES_PER_CHAIN,
    LINEAGE_MAX_TEXT: LINEAGE_MAX_TEXT,
    validateTitleBallotPanel: validateTitleBallotPanel,
    validateTitleCodexPanel: validateTitleCodexPanel,
    TITLE_CODEX_MAX_ROWS: TITLE_CODEX_MAX_ROWS,
    TITLE_CODEX_MAX_DISPLAY: TITLE_CODEX_MAX_DISPLAY,
    TITLE_CODEX_MAX_BASIS: TITLE_CODEX_MAX_BASIS,
    TITLE_CODEX_MAX_FULL_TITLE: TITLE_CODEX_MAX_FULL_TITLE,
    TITLE_CODEX_MAX_BALLOT: TITLE_CODEX_MAX_BALLOT,
    TITLE_CODEX_BASIS_WIRE_MAX: TITLE_CODEX_BASIS_WIRE_MAX,
    TITLE_CODEX_CATEGORIES: TITLE_CODEX_CATEGORIES.slice(),
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
      var phase = "idle"; // idle | awaiting_initial_snapshot | active | detached
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
        // A reload-required (incompatible) protocol error keeps the graphical
        // controls locked even while ordinary presentations keep committing;
        // only a fresh transport generation (beginTransport) clears the error
        // and releases the lock.
        mutationsLocked = !!(protocolError && protocolError.reloadRequired);
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
    },
  };
});
