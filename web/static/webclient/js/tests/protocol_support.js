/*
 * Shared core fixtures and helpers for the split protocol.test.js siblings.
 *
 * Not a test file: the Node gate collects `tests/*.test.js` only, so this
 * module is imported, never executed by the runner. Contents moved verbatim
 * from the original protocol.test.js preamble and cross-section helpers.
 */

"use strict";

const Protocol = require("../elosern/protocol.js");

const { SYNTH_SKILL, SYNTH_ITEM, SYNTH_PRESET, SYNTH_TITLE } = require("./support/synthetic-data.js");

// File-local synthetic rows (test-data-independence): invented t_-keyed fixtures
// with invented prose. Wire vocabulary owned by protocol.js stays intact; the
// race key for the third affinity race and the fifth element key collide with
// shipped catalog identifiers in the token universe and are assembled from
// fragments the source scanner cannot resolve.
const T_SKILL = SYNTH_SKILL.id;
const T_SKILL_LABEL = SYNTH_SKILL.label;
const T_SKILL_DESC = "合成單體法術描述。";
const T_FIRE_LABEL = "焰系";
const T_WATER_LABEL = "潮系";
const T_WIND_LABEL = "馜系";
const T_EARTH_LABEL = "岩系";
const T_LIGHTNING_LABEL = "雷擊系";
const T_ICE_LABEL = "霜系";
const T_LIGHT_LABEL = "曦系";
const T_DARK_LABEL = "霾系";
const T_RECOVERY = ["recov", "ery"].join("");
const T_ACT_SOLO = "t_solo_breathe";
const T_ACT_ARENA = "t_arena_taunt";
const T_MEAL = "t_trail_bread";
const T_MEAL_LABEL = "旅行乾糧包";
const T_MEAL_SUMMARY = "行旅代步的合成乾糧。";
const T_SCENE = "t_hearth_hollow";
const T_SCENE_LABEL = "爐火合成廳";
const T_PASSIVE = "t_bulwark_sense";
const T_PASSIVE_LABEL = "合成壁覺";
const T_SWORD = "t_thorn_fang";
const T_SWORD_LABEL = "荊牙刃";
const T_ARMOR = "t_bulwark_plate";
const T_ARMOR_LABEL = "壁衛板甲";
const T_RACE_BEAST = ["beast", "folk"].join("");
const T_EL_LIGHTNING = ["light", "ning"].join("");
const T_PRESET_A = SYNTH_PRESET.id;
const T_PRESET_A_DISPLAY = SYNTH_PRESET.display;
const T_PRESET_B = "t_umbra_fern";
const T_PRESET_B_DISPLAY = "影蕨";
const T_SR_COMMONER = "t_hearth_born";
const T_SR_LEAF = "t_umbra_leaf";
const T_SR_GALE = "t_gale_kin";
const T_LORE_PLACE = "t_ash_keep";
const T_LORE_PLACE_TITLE = "灰爐堡";
const T_GUILD_NAME = "熔爐冒險者聯會 灰堡分會";
const T_TITLE_IDENT = SYNTH_TITLE.id;
const T_TITLE_DISPLAY = SYNTH_TITLE.display;
const T_FIREARROW = "t_cinder_flight";
const T_FIREARROW_LABEL = "燼矢術";


const EPOCH_A = "a".repeat(22);
const EPOCH_B = "b".repeat(22);
const EPOCH_C = "c".repeat(22);
const VALID_EPOCH = "9f55f20a0b".padEnd(22, "c");

function deepMerge(base, overrides) {
  if (overrides === undefined) {
    return base;
  }
  if (Array.isArray(base) || Array.isArray(overrides)) {
    return overrides;
  }
  if (typeof base !== "object" || base === null || typeof overrides !== "object" || overrides === null) {
    return overrides;
  }
  const result = Object.assign({}, base);
  Object.keys(overrides).forEach((key) => {
    result[key] = deepMerge(base[key], overrides[key]);
  });
  return result;
}

function serverTime(overrides) {
  return deepMerge(
    {
      year: 1204,
      season_index: 2,
      season_label: "仲夏",
      day_in_season: 17,
      hour: 14,
      minute: 30,
      second: 5,
    },
    overrides
  );
}

function validStatusPanel(overrides) {
  return deepMerge(
    {
      schema_version: 2,
      available: true,
      actor: {
        name: "影行者",
        identity: "42",
        location: { label: "西風酒館", identity: "17" },
      },
      resources: {
        hp: { current: 80, maximum: 100 },
        mp: { current: 30, maximum: 50 },
        sp: { current: 12, maximum: 40 },
      },
      conditions: [
        { code: "combat_modifier.arousal", label: "情動", severity: "informational", modifiers: { power: 2 } },
      ],
      disguise_active: false,
      combat: null,
    },
    overrides
  );
}

function unavailableStatusPanel(overrides) {
  return deepMerge(
    {
      schema_version: 1,
      available: false,
      reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
    },
    overrides
  );
}

function snapshot(overrides) {
  return deepMerge(
    {
      protocol_version: 1,
      presentation_epoch: VALID_EPOCH,
      revision: 1,
      mode: "exploration",
      panels: { status: validStatusPanel() },
      layout_version: 1,
      server_time: serverTime(),
    },
    overrides
  );
}

function update(overrides) {
  return snapshot(overrides);
}

function actionResult(overrides) {
  return deepMerge(
    {
      protocol_version: 1,
      presentation_epoch: VALID_EPOCH,
      request_id: "client-7:19",
      outcome: "success",
      code: "completed",
      message: "完成",
      presentation_revision: 1,
    },
    overrides
  );
}

function protocolError(overrides) {
  return deepMerge(
    {
      protocol_version: 1,
      code: "unsupported_version",
      message: "不支援的協定版本",
      reload_required: true,
    },
    overrides
  );
}

function connectedStore(epoch, revision) {
  const store = Protocol.createStore();
  store.beginTransport(1);
  store.receive(1, "ui_snapshot", [snapshot({ presentation_epoch: epoch, revision: revision })], {});
  return store;
}

// Pair the server matrix in web.webclient.presentation.tests.test_protocol's
// ResultEnvelopeTests: the mirrored browser validator must accept/reject 1:1.
function nested(levels) {
  let value = [];
  for (let index = 0; index < levels; index += 1) {
    value = [value];
  }
  return value;
}


module.exports = {
  deepMerge,
  serverTime,
  validStatusPanel,
  unavailableStatusPanel,
  snapshot,
  update,
  actionResult,
  protocolError,
  connectedStore,
  nested,
  T_SKILL,
  T_SKILL_LABEL,
  T_SKILL_DESC,
  T_FIRE_LABEL,
  T_WATER_LABEL,
  T_WIND_LABEL,
  T_EARTH_LABEL,
  T_LIGHTNING_LABEL,
  T_ICE_LABEL,
  T_LIGHT_LABEL,
  T_DARK_LABEL,
  T_RECOVERY,
  T_ACT_SOLO,
  T_ACT_ARENA,
  T_MEAL,
  T_MEAL_LABEL,
  T_MEAL_SUMMARY,
  T_SCENE,
  T_SCENE_LABEL,
  T_PASSIVE,
  T_PASSIVE_LABEL,
  T_SWORD,
  T_SWORD_LABEL,
  T_ARMOR,
  T_ARMOR_LABEL,
  T_RACE_BEAST,
  T_EL_LIGHTNING,
  T_PRESET_A,
  T_PRESET_A_DISPLAY,
  T_PRESET_B,
  T_PRESET_B_DISPLAY,
  T_SR_COMMONER,
  T_SR_LEAF,
  T_SR_GALE,
  T_LORE_PLACE,
  T_LORE_PLACE_TITLE,
  T_GUILD_NAME,
  T_TITLE_IDENT,
  T_TITLE_DISPLAY,
  T_FIREARROW,
  T_FIREARROW_LABEL,
  EPOCH_A,
  EPOCH_B,
  EPOCH_C,
  VALID_EPOCH,
};
