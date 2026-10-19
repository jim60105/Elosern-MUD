// Story fixture slices: the party window's 技能 tab (webclient-party-skill-tab).
//
// The committed `character` v9 payload for the companion 蕾娜 (member 101 of
// PARTY_WINDOW_PANEL_SAMPLE), shaped like the approved prototype's skill
// book (docs/design/party-member-management/prototype-data.js SKILLS[2]):
// a divine heal she can cast in the field with a booked practice, a fresh
// unlock, an ice line whose first skill carries the element-mastery ladder
// and whose second is capped, a combat-only martial row, an unregistered
// row (identity and growth facts only), and two passives. The growth facts
// are the server's: `xp_to_next_level` is what remains of the level band.
// `selected_skill` is the server's answer to the tab's selection; the
// variants below name another row the way the server would republish it.

function active(key, label, growth, descriptor) {
  return {
    key,
    label,
    level: growth.level,
    xp_into_level: growth.into,
    xp_to_next_level: growth.capped ? 0 : growth.toNext,
    capped: Boolean(growth.capped),
    fresh: Boolean(growth.fresh),
    booked: Boolean(growth.booked),
    ...(descriptor ?? {}),
  };
}

const COMPANION_ACTIVES = [
  {
    category: "elemental_magic",
    label: "元素魔法",
    groups: [
      {
        group: "water",
        label: "水",
        skills: [
          active("ice_shard", "冰錐術", { level: 2, into: 18, toNext: 42 }, { cost: { mp: 6 }, target_spec: "single", usable_out_of_combat: false }),
          active("frost_touch", "寒霜之觸", { level: 10, into: 0, capped: true }, { cost: { mp: 4 }, target_spec: "single", usable_out_of_combat: false }),
        ],
      },
    ],
  },
  {
    category: "martial_arts",
    label: "武技",
    groups: [
      {
        group: null,
        label: null,
        skills: [
          active("staff_strike", "杖擊", { level: 1, into: 4.5, toNext: 35.5 }, { cost: { sp: 4 }, target_spec: "single", usable_out_of_combat: false }),
          active("old_kata", "old_kata", { level: 0, into: 0, toNext: 0 }),
        ],
      },
    ],
  },
  {
    category: "divine_mystery",
    label: "神聖奧祕",
    groups: [
      {
        group: null,
        label: null,
        skills: [
          active("healing_light", "治癒之光", { level: 2, into: 31, toNext: 19, booked: true }, { cost: { mp: 8 }, target_spec: "single", usable_out_of_combat: true }),
          active("mass_heal", "群體治癒", { level: 1, into: 1, toNext: 59, fresh: true }, { cost: { mp: 20 }, target_spec: "area", usable_out_of_combat: true }),
          active("prayer", "祈禱", { level: 4, into: 12, toNext: 68 }, { cost: {}, target_spec: "self", usable_out_of_combat: true }),
        ],
      },
    ],
  },
];

const COMPANION_PASSIVES = [
  {
    category: "enhancement",
    label: "強化",
    groups: [
      { group: null, label: null, skills: [{ key: "meditation", label: "冥想" }] },
      { group: "天賦", label: "天賦", skills: [{ key: "moon_affinity", label: "月之親和" }] },
    ],
  },
];

// The heal selected: its lineage position, no ladder (not freeform-eligible).
export const SKILL_TAB_HEAL_SELECTED = {
  key: "healing_light",
  lineage: {
    prerequisites: [{ key: "prayer", label: "祈禱", level: 2 }],
    next: [{ key: "mass_heal", label: "群體治癒", min_level: 3 }],
  },
};

// The ice line's entry selected while 蕾娜 holds water mastery: the full
// ladder, rungs above her proficiency carrying the level that unlocks them.
export const SKILL_TAB_LADDER_SELECTED = {
  key: "ice_shard",
  lineage: {
    prerequisites: [],
    next: [
      { key: "frost_touch", label: "寒霜之觸", min_level: 2 },
      { key: "ice_lance", label: "冰槍", min_level: 5 },
    ],
  },
  freeform_ladder: [
    { scale: 0.25, label: "1/4", mp_cost: 2 },
    { scale: 0.5, label: "1/2", mp_cost: 3 },
    { scale: 1, label: "1", mp_cost: 6 },
    { scale: 2, label: "2", unlock_level: 6 },
    { scale: 4, label: "4", unlock_level: 10 },
  ],
};

export const CHARACTER_SKILL_COMPANION_SAMPLE = {
  schema_version: 9,
  available: true,
  kind: "character",
  member_id: 101,
  full_title: "F級冒險者　月下藥師",
  traits: [],
  conditions: [],
  actives: COMPANION_ACTIVES,
  passives: COMPANION_PASSIVES,
  equipment: [],
  disguise: { active: false, description: "", displayed: [] },
  guild: { rank: "F", merit: 20 },
  wallet: 0,
  selected_skill: SKILL_TAB_HEAL_SELECTED,
};

// The same member with the ladder skill selected (the 威力與消耗 row).
export const CHARACTER_SKILL_LADDER_SAMPLE = {
  ...CHARACTER_SKILL_COMPANION_SAMPLE,
  selected_skill: SKILL_TAB_LADDER_SELECTED,
};

// The ladder skill without the element's mastery: the server sends the
// lineage but no ladder, so the tab shows no 威力與消耗 row.
export const CHARACTER_SKILL_NO_MASTERY_SAMPLE = {
  ...CHARACTER_SKILL_COMPANION_SAMPLE,
  selected_skill: { key: SKILL_TAB_LADDER_SELECTED.key, lineage: SKILL_TAB_LADDER_SELECTED.lineage },
};
