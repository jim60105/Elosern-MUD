"use strict";


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
// active skills including innate, plus the 66 registered sexual acts of
// the catalogue); a multiple of 16 like the other presentation bounds.
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
var CONTEXT_ACTIONS_MAX_ITEM_KEY = 64;
var CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS = 43200;
var CONTEXT_ACTIONS_ACTION_CODES = [
  "explore.move",
  "explore.look",
  "explore.talk_open",
  "explore.talk_scripted",
  "explore.talk_freeform",
  "explore.party_invite",
  "explore.party_leave",
  "explore.engage",
  "explore.wait",
  "explore.possess",
  "explore.possess_release",
  "explore.deliver",
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
  "divine_mystery",
  "utility",
  "sexual_act",
  "holy_rite",
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
// world/rules/titles/ballot.py (the ballot writer); these constants mirror the
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
  "clergy",
  "romance",
];

// lore_codex panel bounds (mirror of web.webclient.presentation.lore_codex,
// webclient-lore-codex-panel). These constants are shared with the server
// through a dual-direction parity test.
var LORE_CODEX_SCHEMA_VERSION = 1;
var LORE_CODEX_MAX_ENTRIES_PER_CATEGORY = 32;
var LORE_CODEX_MAX_TOTAL_ENTRIES = 256;
var LORE_CODEX_MAX_CARD_FIELDS = 8;
var LORE_CODEX_MAX_KEY_CODE_POINTS = 64;
var LORE_CODEX_MAX_TITLE_CODE_POINTS = 64;
var LORE_CODEX_MAX_LABEL_CODE_POINTS = 32;
var LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS = 64;
var LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS = 1024;
var LORE_CODEX_CATEGORIES = [
  "race",
  "nation",
  "region",
  "monster",
  "element",
  "magic",
  "anchor",
  "guild",
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
var CREATION_AGE_MINIMUM = 0;
var CREATION_AGE_MAXIMUM = 10000;
var CREATION_APPARENT_AGE_MINIMUM = 0;
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
// v5 renames the `custom.adult` descriptor block to `custom.age` and drops
// the advertised minimums to 0 (age-range-0-10000).
var CREATION_SCHEMA_VERSION = 5;
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

// Quest log panel bounds (mirror of web.webclient.presentation.quest_log,
// quest-issuer-model change 8): at most MAX_QUEST_ROWS rows (the shared
// services quest-row cap) of the holder's stored records. The row cap and
// prose ceilings are shared with the server through a dual-direction
// parity contract.
var QUEST_LOG_SCHEMA_VERSION = 1;
var QUEST_LOG_MAX_ROWS = 12;
var QUEST_LOG_MAX_QUEST_ID = 64;
var QUEST_LOG_MAX_KEY = 64;
var QUEST_LOG_MAX_DISPLAY_NAME = 128;
var QUEST_LOG_MAX_ISSUER_KEY = 64;
var QUEST_LOG_MAX_LABEL = 128;
var QUEST_LOG_MAX_OBJECTIVE_LINE = 128;
var QUEST_LOG_MAX_DEADLINE_LINE = 64;
var QUEST_LOG_MAX_DETAIL = 512;
var QUEST_LOG_MAX_REWARD_LINE = 128;
var QUEST_LOG_MAX_TRACK_LABEL = 64;

// Dialogue panel bounds (mirror of web.webclient.presentation.dialogue,
// webclient-align-10): the choice cap mirrors MAX_SCRIPTED_KEYWORDS, the
// keyword bounds mirror the exploration keyword vocabulary, and the line
// bound is the shared dialogue-session prose bound (never the generic
// protocol ceiling) — the write path truncates to it, so over-bound
// dialogue is corruption and rejects.
var DIALOGUE_SCHEMA_VERSION = 1;
// Panel-owned bound tracked in lockstep with
// web.webclient.presentation.dialogue.DIALOGUE_MAX_CHOICES (align-11: four,
// independent of the exploration keyword-pool bound).
var DIALOGUE_MAX_CHOICES = 4;
var DIALOGUE_MAX_KEYWORD_ID = 64;
var DIALOGUE_MAX_KEYWORD_LABEL = 128;
var DIALOGUE_MAX_LINE = 2000;

// Roster panel bounds (mirror of web.webclient.presentation.roster,
// webclient-character-roster): at most ten character rows in ascending
// identity order; exactly one current character; locked exactly when in
// active combat.
var ROSTER_SCHEMA_VERSION = 2;
var ROSTER_MAX_ROWS = 10;
var ROSTER_MAX_NAME = 128;
var ROSTER_MAX_SUBJECT_KEY = 128;
var MAX_MEDIA_URL = 256;
var ROSTER_MAX_ALT = 512;
var ROSTER_MAX_STATUS = 16;
var ROSTER_MAX_PLACEHOLDER_LABEL = 128;
var ROSTER_LOCK_REASON = "戰鬥中無法切換角色";

var PANEL_ALLOWLIST = {
  gallery: 1,
  art: 2,
  status: 2,
  context_actions: 5,
  local_map: 1,
  party: 1,
  objectives: 1,
  services: 4,
  creation: 5,
  exploration: 3,
  character: 7,
  lineage: 1,
  dialogue: 1,
  title_ballot: 1,
  title_codex: 1,
  roster: 2,
  possession_banner: 1,
  lore_codex: 1,
  quest_log: 1,
};

var EPOCH_RE = /^[A-Za-z0-9_-]{22}$/;
var PANEL_NAME_RE = /^[a-z0-9_]{1,64}$/;
var IDENTIFIER_RE = /^[a-z0-9._]{1,64}$/;
var REQUEST_ID_RE = /^[A-Za-z0-9:_-]{1,64}$/;
var CORRELATION_RE = /^[0-9a-f]{32}$/;
var TOKEN_RE = /^[ae]\d+$/;
// Promoted to the shared table: the context_actions skill-group rows and the
// character panel rows pin the same key bound.
var CHARACTER_MAX_KEY = 64;

module.exports = {
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
  MAX_FULL_TITLE_CODE_POINTS: MAX_FULL_TITLE_CODE_POINTS,
  MAX_LOCATION_LABEL: MAX_LOCATION_LABEL,
  MAX_CONDITION_COUNT: MAX_CONDITION_COUNT,
  MAX_CONDITION_LABEL: MAX_CONDITION_LABEL,
  MAX_MODIFIER_KEYS: MAX_MODIFIER_KEYS,
  RESULT_DATA_STANDARD_RESERVE: RESULT_DATA_STANDARD_RESERVE,
  MAX_RESULT_DATA_FIELDS: MAX_RESULT_DATA_FIELDS,
  MAX_RESULT_DATA_BYTES: MAX_RESULT_DATA_BYTES,
  MODES: MODES,
  OUTCOMES: OUTCOMES,
  FORBIDDEN_RESULT_DATA_KEYS: FORBIDDEN_RESULT_DATA_KEYS,
  COMBAT_MODES: COMBAT_MODES,
  PROTOCOL_ERROR_CODES: PROTOCOL_ERROR_CODES,
  SEVERITIES: SEVERITIES,
  MAX_SESSION_ID_CODE_POINTS: MAX_SESSION_ID_CODE_POINTS,
  MAX_PARTICIPANTS: MAX_PARTICIPANTS,
  MAX_SKILLS: MAX_SKILLS,
  MAX_DISPLAY_NAME: MAX_DISPLAY_NAME,
  MAX_LABEL: MAX_LABEL,
  MAX_DESCRIPTION: MAX_DESCRIPTION,
  MAX_SKILL_TARGETS: MAX_SKILL_TARGETS,
  MAX_SHORTHANDS: MAX_SHORTHANDS,
  MAX_TOKEN: MAX_TOKEN,
  MAX_ACTION_KEYS: MAX_ACTION_KEYS,
  MAX_COST_KEYS: MAX_COST_KEYS,
  MAX_REASON_MESSAGE: MAX_REASON_MESSAGE,
  SESSION_MODES: SESSION_MODES,
  SESSION_STATES: SESSION_STATES,
  TEAMS: TEAMS,
  PARTICIPANT_STATES: PARTICIPANT_STATES,
  TARGET_SPECS: TARGET_SPECS,
  ALLOWED_SHORTHANDS: ALLOWED_SHORTHANDS,
  FREEFORM_SCALES_ALLOWED: FREEFORM_SCALES_ALLOWED,
  FREEFORM_SCALES_MAX: FREEFORM_SCALES_MAX,
  FREEFORM_LABELS_ALLOWED: FREEFORM_LABELS_ALLOWED,
  ROOT_ACTIONS: ROOT_ACTIONS,
  SECONDARY_ACTIONS: SECONDARY_ACTIONS,
  RECOVERY_SECONDARY_ACTIONS: RECOVERY_SECONDARY_ACTIONS,
  CONTEXT_ACTIONS_MAX_AFFORDANCES: CONTEXT_ACTIONS_MAX_AFFORDANCES,
  CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL: CONTEXT_ACTIONS_MAX_AFFORDANCE_LABEL,
  CONTEXT_ACTIONS_MAX_PARAM_KEYS: CONTEXT_ACTIONS_MAX_PARAM_KEYS,
  CONTEXT_ACTIONS_MAX_PARAM_STRING: CONTEXT_ACTIONS_MAX_PARAM_STRING,
  CONTEXT_ACTIONS_MAX_EXIT_REF: CONTEXT_ACTIONS_MAX_EXIT_REF,
  CONTEXT_ACTIONS_MAX_NODE_ID: CONTEXT_ACTIONS_MAX_NODE_ID,
  CONTEXT_ACTIONS_MAX_KEYWORD_ID: CONTEXT_ACTIONS_MAX_KEYWORD_ID,
  CONTEXT_ACTIONS_MAX_ITEM_KEY: CONTEXT_ACTIONS_MAX_ITEM_KEY,
  CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS: CONTEXT_ACTIONS_MAX_WEB_SKIP_SECONDS,
  CONTEXT_ACTIONS_ACTION_CODES: CONTEXT_ACTIONS_ACTION_CODES,
  CONTEXT_ACTIONS_SURFACES: CONTEXT_ACTIONS_SURFACES,
  CONTEXT_ACTIONS_DAYPARTS: CONTEXT_ACTIONS_DAYPARTS,
  OPTIONS_STATUSES: OPTIONS_STATUSES,
  OPTIONS_CARD_KINDS: OPTIONS_CARD_KINDS,
  MAX_OPTION_CARDS: MAX_OPTION_CARDS,
  MAX_OPTION_LABEL: MAX_OPTION_LABEL,
  MAX_OPTION_HINT: MAX_OPTION_HINT,
  MAX_OPTION_PARAMS: MAX_OPTION_PARAMS,
  OPTIONS_FREEFORM_ACTION_CODE: OPTIONS_FREEFORM_ACTION_CODE,
  OPTIONS_MAX_PARAM_STRING: OPTIONS_MAX_PARAM_STRING,
  SKILL_CATEGORY_KEYS: SKILL_CATEGORY_KEYS,
  LOCAL_MAP_MAX_NODES: LOCAL_MAP_MAX_NODES,
  LOCAL_MAP_MAX_EDGES: LOCAL_MAP_MAX_EDGES,
  LOCAL_MAP_MAX_LEGEND: LOCAL_MAP_MAX_LEGEND,
  LOCAL_MAP_MAX_STRING: LOCAL_MAP_MAX_STRING,
  LINEAGE_MAX_CHAINS: LINEAGE_MAX_CHAINS,
  LINEAGE_MAX_NODES_PER_CHAIN: LINEAGE_MAX_NODES_PER_CHAIN,
  LINEAGE_MAX_TEXT: LINEAGE_MAX_TEXT,
  LOCAL_MAP_MAX_TITLE: LOCAL_MAP_MAX_TITLE,
  LOCAL_MAP_MAX_NODE_ID: LOCAL_MAP_MAX_NODE_ID,
  LOCAL_MAP_MAX_EXIT_REF: LOCAL_MAP_MAX_EXIT_REF,
  LOCAL_MAP_COORD_MIN: LOCAL_MAP_COORD_MIN,
  LOCAL_MAP_COORD_MAX: LOCAL_MAP_COORD_MAX,
  LOCAL_MAP_VISIBILITIES: LOCAL_MAP_VISIBILITIES,
  LOCAL_MAP_LAYERS: LOCAL_MAP_LAYERS,
  LOCAL_MAP_ACTION_KINDS: LOCAL_MAP_ACTION_KINDS,
  NODE_ID_RE: NODE_ID_RE,
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
  SERVICES_QUEST_STATES: SERVICES_QUEST_STATES,
  SERVICES_ACTIONS: SERVICES_ACTIONS,
  SERVICES_BUY: SERVICES_BUY,
  SERVICES_SELL: SERVICES_SELL,
  TITLE_BALLOT_MAX_CANDIDATES: TITLE_BALLOT_MAX_CANDIDATES,
  TITLE_BALLOT_MAX_DISPLAY: TITLE_BALLOT_MAX_DISPLAY,
  TITLE_BALLOT_MAX_BASIS: TITLE_BALLOT_MAX_BASIS,
  TITLE_CODEX_MAX_ROWS: TITLE_CODEX_MAX_ROWS,
  TITLE_CODEX_MAX_DISPLAY: TITLE_CODEX_MAX_DISPLAY,
  TITLE_CODEX_MAX_BASIS: TITLE_CODEX_MAX_BASIS,
  TITLE_CODEX_MAX_FULL_TITLE: TITLE_CODEX_MAX_FULL_TITLE,
  TITLE_CODEX_MAX_BALLOT: TITLE_CODEX_MAX_BALLOT,
  TITLE_CODEX_BASIS_WIRE_MAX: TITLE_CODEX_BASIS_WIRE_MAX,
  TITLE_CODEX_CATEGORIES: TITLE_CODEX_CATEGORIES,
  LORE_CODEX_SCHEMA_VERSION: LORE_CODEX_SCHEMA_VERSION,
  LORE_CODEX_MAX_ENTRIES_PER_CATEGORY: LORE_CODEX_MAX_ENTRIES_PER_CATEGORY,
  LORE_CODEX_MAX_TOTAL_ENTRIES: LORE_CODEX_MAX_TOTAL_ENTRIES,
  LORE_CODEX_MAX_CARD_FIELDS: LORE_CODEX_MAX_CARD_FIELDS,
  LORE_CODEX_MAX_KEY_CODE_POINTS: LORE_CODEX_MAX_KEY_CODE_POINTS,
  LORE_CODEX_MAX_TITLE_CODE_POINTS: LORE_CODEX_MAX_TITLE_CODE_POINTS,
  LORE_CODEX_MAX_LABEL_CODE_POINTS: LORE_CODEX_MAX_LABEL_CODE_POINTS,
  LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS: LORE_CODEX_MAX_FIELD_NAME_CODE_POINTS,
  LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS: LORE_CODEX_MAX_FIELD_VALUE_CODE_POINTS,
  LORE_CODEX_CATEGORIES: LORE_CODEX_CATEGORIES,
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
  CREATION_MAX_PROPOSAL_NAME: CREATION_MAX_PROPOSAL_NAME,
  CREATION_MAX_DESCRIPTION: CREATION_MAX_DESCRIPTION,
  CREATION_MAX_EMPHASIS: CREATION_MAX_EMPHASIS,
  CREATION_MAX_BACKGROUND: CREATION_MAX_BACKGROUND,
  CREATION_MAX_PERSONA_BACKGROUND: CREATION_MAX_PERSONA_BACKGROUND,
  CREATION_MAX_SUBRACE_KEY: CREATION_MAX_SUBRACE_KEY,
  CREATION_MAX_SPECIALTY: CREATION_MAX_SPECIALTY,
  CREATION_MAX_LABEL: CREATION_MAX_LABEL,
  CREATION_MAX_EXPLANATION: CREATION_MAX_EXPLANATION,
  CREATION_MAX_CONCEPT: CREATION_MAX_CONCEPT,
  CREATION_AXES: CREATION_AXES,
  CREATION_PRESET_STAGE: CREATION_PRESET_STAGE,
  CREATION_CUSTOM_STAGE: CREATION_CUSTOM_STAGE,
  CREATION_PERSONA_KEYS: CREATION_PERSONA_KEYS,
  CREATION_SEX_VALUES: CREATION_SEX_VALUES,
  CREATION_SEX_DEFAULT: CREATION_SEX_DEFAULT,
  CREATION_MAX_SEX_OPTIONS: CREATION_MAX_SEX_OPTIONS,
  CREATION_SCHEMA_VERSION: CREATION_SCHEMA_VERSION,
  CREATION_MAX_AFFINITY_ELEMENTS: CREATION_MAX_AFFINITY_ELEMENTS,
  CREATION_AFFINITY_ELEMENTS: CREATION_AFFINITY_ELEMENTS,
  CREATION_AFFINITY_RACES: CREATION_AFFINITY_RACES,
  CREATION_AFFINITY_MAXIMUMS: CREATION_AFFINITY_MAXIMUMS,
  MESSAGE_NAMES: MESSAGE_NAMES,
  PARTY_SCHEMA_VERSION: PARTY_SCHEMA_VERSION,
  PARTY_MAX_ROWS: PARTY_MAX_ROWS,
  PARTY_MAX_DISPLAY_NAME: PARTY_MAX_DISPLAY_NAME,
  OBJECTIVES_SCHEMA_VERSION: OBJECTIVES_SCHEMA_VERSION,
  OBJECTIVES_MAX_ROWS: OBJECTIVES_MAX_ROWS,
  OBJECTIVES_MAX_QUEST_ID: OBJECTIVES_MAX_QUEST_ID,
  OBJECTIVES_MAX_DISPLAY_NAME: OBJECTIVES_MAX_DISPLAY_NAME,
  OBJECTIVES_MAX_OBJECTIVE_LINE: OBJECTIVES_MAX_OBJECTIVE_LINE,
  OBJECTIVES_MAX_DEADLINE_LINE: OBJECTIVES_MAX_DEADLINE_LINE,
  QUEST_LOG_SCHEMA_VERSION: QUEST_LOG_SCHEMA_VERSION,
  QUEST_LOG_MAX_ROWS: QUEST_LOG_MAX_ROWS,
  QUEST_LOG_MAX_QUEST_ID: QUEST_LOG_MAX_QUEST_ID,
  QUEST_LOG_MAX_KEY: QUEST_LOG_MAX_KEY,
  QUEST_LOG_MAX_DISPLAY_NAME: QUEST_LOG_MAX_DISPLAY_NAME,
  QUEST_LOG_MAX_ISSUER_KEY: QUEST_LOG_MAX_ISSUER_KEY,
  QUEST_LOG_MAX_LABEL: QUEST_LOG_MAX_LABEL,
  QUEST_LOG_MAX_OBJECTIVE_LINE: QUEST_LOG_MAX_OBJECTIVE_LINE,
  QUEST_LOG_MAX_DEADLINE_LINE: QUEST_LOG_MAX_DEADLINE_LINE,
  QUEST_LOG_MAX_DETAIL: QUEST_LOG_MAX_DETAIL,
  QUEST_LOG_MAX_REWARD_LINE: QUEST_LOG_MAX_REWARD_LINE,
  QUEST_LOG_MAX_TRACK_LABEL: QUEST_LOG_MAX_TRACK_LABEL,
  DIALOGUE_SCHEMA_VERSION: DIALOGUE_SCHEMA_VERSION,
  DIALOGUE_MAX_CHOICES: DIALOGUE_MAX_CHOICES,
  DIALOGUE_MAX_KEYWORD_ID: DIALOGUE_MAX_KEYWORD_ID,
  DIALOGUE_MAX_KEYWORD_LABEL: DIALOGUE_MAX_KEYWORD_LABEL,
  DIALOGUE_MAX_LINE: DIALOGUE_MAX_LINE,
  ROSTER_SCHEMA_VERSION: ROSTER_SCHEMA_VERSION,
  ROSTER_MAX_ROWS: ROSTER_MAX_ROWS,
  ROSTER_MAX_NAME: ROSTER_MAX_NAME,
  ROSTER_MAX_SUBJECT_KEY: ROSTER_MAX_SUBJECT_KEY,
  MAX_MEDIA_URL: MAX_MEDIA_URL,
  ROSTER_MAX_ALT: ROSTER_MAX_ALT,
  ROSTER_MAX_STATUS: ROSTER_MAX_STATUS,
  ROSTER_MAX_PLACEHOLDER_LABEL: ROSTER_MAX_PLACEHOLDER_LABEL,
  ROSTER_LOCK_REASON: ROSTER_LOCK_REASON,
  PANEL_ALLOWLIST: PANEL_ALLOWLIST,
  EPOCH_RE: EPOCH_RE,
  PANEL_NAME_RE: PANEL_NAME_RE,
  IDENTIFIER_RE: IDENTIFIER_RE,
  REQUEST_ID_RE: REQUEST_ID_RE,
  CORRELATION_RE: CORRELATION_RE,
  TOKEN_RE: TOKEN_RE,
  CHARACTER_MAX_KEY: CHARACTER_MAX_KEY,
};
