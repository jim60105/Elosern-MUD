/*
 * Shared panel fixture builders for the split protocol.test.js siblings.
 *
 * Not a test file: the Node gate collects `tests/*.test.js` only, so this
 * module is imported, never executed by the runner. Contents moved verbatim
 * from the original protocol.test.js section helpers; the envelope helpers it builds on (deepMerge, nested) live in ./protocol_support.js.
 */

"use strict";

const { T_FIRE_LABEL, T_MEAL, T_MEAL_LABEL, T_MEAL_SUMMARY, T_PASSIVE, T_PASSIVE_LABEL, T_RECOVERY, T_SKILL, T_SKILL_DESC, T_SKILL_LABEL, T_SWORD, deepMerge, nested } = require("./protocol_support.js");

function validCombatSkill(overrides) {
  return deepMerge(
    {
      key: T_SKILL,
      label: T_SKILL_LABEL,
      description: T_SKILL_DESC,
      cost: { mp: 20 },
      target_spec: "single",
      element: "fire",
      enabled: true,
      disabled_reason: null,
      targets: [2],
      shorthands: [],
    },
    overrides
  );
}

function validSkillGroup(overrides) {
  return deepMerge(
    {
      group: "fire",
      label: T_FIRE_LABEL,
      skills: [validCombatSkill()],
    },
    overrides
  );
}

function validCategoryGroup(overrides) {
  return deepMerge(
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [validSkillGroup()],
    },
    overrides
  );
}

function validCombatParticipant(overrides) {
  return deepMerge(
    {
      identity: 2,
      token: "e1",
      display_name: "哥布林",
      team: "foes",
      state: "active",
      hp_current: 100,
      hp_maximum: 100,
      portrait_ref: null,
    },
    overrides
  );
}

function validCombatPanel(overrides) {
  return deepMerge(
    {
      schema_version: 5,
      available: true,
      kind: "combat",
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 0,
        state: "ready",
        reason: null,
      },
      participants: [validCombatParticipant()],
      root_actions: ["attack", "skills", "items", "defend", "flee"],
      secondary_actions: ["forfeit"],
      skills: [validCategoryGroup()],
      suggestions: { status: "unavailable" },
    },
    overrides
  );
}

function validRecoveryPanel(overrides) {
  return deepMerge(
    {
      schema_version: 5,
      available: true,
      kind: "combat",
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 2,
        state: T_RECOVERY,
        reason: { code: "missing_participant", message: "戰鬥成員已無法確認。" },
      },
      participants: [],
      root_actions: [],
      secondary_actions: ["forfeit"],
      skills: [],
      suggestions: { status: "unavailable" },
    },
    overrides
  );
}

// Wrap a flat skill list into one nested category group for payload tests.
function nestedSkills(...skills) {
  return [validCategoryGroup({ groups: [validSkillGroup({ skills: skills })] })];
}

function validSuggestions(overrides) {
  return deepMerge(
    {
      status: "unavailable",
    },
    overrides
  );
}

function validContextActionsExplorationPanel(overrides) {
  return deepMerge(
    {
      schema_version: 5,
      available: true,
      kind: "exploration",
      affordances: [],
      suggestions: validSuggestions(),
    },
    overrides
  );
}

function validServicesAction(overrides) {
  return Object.assign(
    {
      action_id: "guild.register",
      label: "註冊為冒險者",
      enabled: true,
      disabled_reason: null,
      quantity: null,
    },
    overrides || {}
  );
}

function validServicesBoardRow(overrides) {
  return Object.assign(
    {
      definition_key: "introductory_hunt",
      display_name: "討伐低階魔物",
      objective_summary: "討伐 1 隻低階魔物",
      reward_summary: "獎勵：銅 50、功績 25、治療藥水 × 2",
      rank: "F",
      accept: validServicesAction({ action_id: "guild.quest_accept", label: "接取" }),
    },
    overrides || {}
  );
}

function validServicesQuestRow(overrides) {
  return Object.assign(
    {
      quest_id: "introductory_hunt:1",
      definition_key: "introductory_hunt",
      display_name: "討伐低階魔物",
      state: "in_progress",
      stage_index: 0,
      stage_progress: 0,
      objective_summary: "討伐 1 隻低階魔物",
      deadline_line: null,
      detail: "討伐低階魔物\n狀態：進行中\n階段：1\n目標：討伐 1 隻低階魔物\n進度：0 / 1\n獎勵：銅 50、功績 25、治療藥水 × 2",
      abandon: validServicesAction({ action_id: "guild.quest_abandon", label: "放棄" }),
      turnin: validServicesAction({
        action_id: "guild.quest_turnin",
        label: "回報",
        enabled: false,
        disabled_reason: { code: "quest_transition", message: "這個任務目前無法進行此操作。" },
      }),
      tracked: false,
    },
    overrides || {}
  );
}

function validServicesStockRow(overrides) {
  return Object.assign(
    {
      item_key: T_MEAL,
      display_name: T_MEAL_LABEL,
      buy_copper: 10,
      sell_copper: 5,
      stock: 20,
      max_stock: 20,
      buy: validServicesAction({ action_id: "shop.buy", label: "購買", quantity: { min: 1, max: 20 } }),
    },
    overrides || {}
  );
}

function validServicesSellableRow(overrides) {
  return Object.assign(
    {
      item_key: T_MEAL,
      display_name: T_MEAL_LABEL,
      sell_copper: 5,
      held: 2,
      sell: validServicesAction({ action_id: "shop.sell", label: "販賣", quantity: { min: 1, max: 2 } }),
    },
    overrides || {}
  );
}

function validServicesPanel(overrides) {
  return Object.assign(
    {
      schema_version: 4,
      available: true,
      kind: "services",
      host: null,
      player: {
        wallet: 1000,
        guild_registered: false,
        guild_rank: null,
        guild_merit: 0,
        next_rank: null,
        next_threshold: null,
      },
      guild: {
        registration: {
          registered: false,
          register: validServicesAction(),
        },
        board: [],
        quests: [],
        rank: null,
      },
      shop: null,
      inventory: {
        rows: [
          {
            item_key: T_MEAL,
            display_name: T_MEAL_LABEL,
            held: 1,
            equipped: false,
            action: null,
            presentation: {
              kind: "food",
              icon_key: "food",
              rarity: "common",
              summary: T_MEAL_SUMMARY,
            },
          },
          {
            item_key: "mystery_relic",
            display_name: "mystery_relic",
            held: 2,
            equipped: false,
            action: null,
            presentation: null,
          },
        ],
        wallet: 1000,
      },
      pagination: {
        board_total: 0,
        quest_total: 0,
        stock_total: 0,
        sellable_total: 0,
        inventory_total: 2,
      },
    },
    overrides || {}
  );
}

function validExplorationAffordance(overrides) {
  return Object.assign(
    {
      kind: "action",
      action_id: "explore.talk_open",
      label: "交談",
      enabled: true,
      disabled_reason: null,
    },
    overrides || {}
  );
}

function validExplorationMoveRow(overrides) {
  return Object.assign(
    {
      exit_ref: "42",
      label: "東",
      destination: "room:7",
      enabled: true,
      disabled_reason: null,
    },
    overrides || {}
  );
}

function validExplorationLookEntity(overrides) {
  return Object.assign(
    { identity: 5, display_name: "南門守衛", kind: "npc", portrait_ref: null },
    overrides || {}
  );
}

function validExplorationLookObject(overrides) {
  return Object.assign({ identity: 6, display_name: "木箱" }, overrides || {});
}

function validExplorationTarget(overrides) {
  return Object.assign(
    {
      identity: 5,
      display_name: "南門守衛",
      portrait_ref: null,
      affordances: [validExplorationAffordance()],
    },
    overrides || {}
  );
}

function validExplorationPanel(overrides) {
  return Object.assign(
    {
      schema_version: 3,
      available: true,
      kind: "exploration",
      move: [validExplorationMoveRow()],
      look: {
        room: { identity: 3, display_name: "南門", room: true },
        entities: [validExplorationLookEntity()],
        objects: [validExplorationLookObject()],
      },
      interact: [validExplorationTarget()],
      character: { available: true },
      quests: { available: true },
      inventory: { available: true },
    },
    overrides || {}
  );
}

function validCharacterTraitRow(overrides) {
  return Object.assign(
    {
      key: "hp",
      label: "生命",
      base: 10,
      current: 10,
      max: 10,
      effective: 10,
      layers: [],
    },
    overrides || {}
  );
}

function validCharacterPanel(overrides) {
  return Object.assign(
    {
      schema_version: 7,
      available: true,
      kind: "character",
      traits: [
        validCharacterTraitRow(),
        validCharacterTraitRow({
          key: "atk_phys",
          label: "攻擊",
          base: 3,
          current: 5,
          max: null,
          effective: 5,
          layers: [{ source: "equipment", name: "鐵劍", kind: "flat", amount: 2 }],
        }),
      ],
      actives: [
        {
          category: "elemental_magic",
          label: "元素魔法",
          groups: [
            { group: "fire", label: T_FIRE_LABEL, skills: [{ key: T_SKILL, label: T_SKILL_LABEL }] },
          ],
        },
      ],
      passives: [
        {
          category: "enhancement",
          label: "強化",
          groups: [
            {
              group: null,
              label: null,
              skills: [{ key: T_PASSIVE, label: T_PASSIVE_LABEL }],
            },
          ],
        },
      ],
      equipment: [
        { slot: "weapon_main", item_key: T_SWORD, display_name: "鐵劍", adjustment: "攻擊 +2" },
      ],
      disguise: { active: false, description: "", displayed: [] },
      guild: { rank: null, merit: 0 },
      wallet: 100,
      persona: { background: null, personality: null, life_story: null, habit: null },
      intimate: null,
    },
    overrides || {}
  );
}

function validRosterPortrait(overrides) {
  return Object.assign(
    {
      subject_key: "character:1",
      status: "done",
      url: "/art/portraits/character_1.png",
      aspect_ratio: "3:4",
      alt: "英雄肖像",
      placeholder: null,
      face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
    },
    overrides || {}
  );
}

function validRosterCharacter(overrides) {
  return Object.assign(
    {
      identity: 1,
      name: "艾莉亞",
      current: true,
      pending: false,
      portrait: validRosterPortrait(),
    },
    overrides || {}
  );
}

function validRosterPanel(overrides) {
  return Object.assign(
    {
      schema_version: 2,
      available: true,
      characters: [validRosterCharacter()],
      max_characters: 5,
      can_create: true,
      switch_locked: false,
      lock_reason: null,
    },
    overrides || {}
  );
}


module.exports = {
  validCombatSkill,
  validSkillGroup,
  validCategoryGroup,
  validCombatParticipant,
  validCombatPanel,
  validRecoveryPanel,
  nestedSkills,
  validSuggestions,
  validContextActionsExplorationPanel,
  validServicesAction,
  validServicesBoardRow,
  validServicesQuestRow,
  validServicesStockRow,
  validServicesSellableRow,
  validServicesPanel,
  validExplorationAffordance,
  validExplorationMoveRow,
  validExplorationLookEntity,
  validExplorationLookObject,
  validExplorationTarget,
  validExplorationPanel,
  validCharacterTraitRow,
  validCharacterPanel,
  validRosterPortrait,
  validRosterCharacter,
  validRosterPanel,
};
