// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

import { fixtureDigest } from "./art_panels.js";

// ---------------------------------------------------------------------------
// webclient-align-05-party-hud: party panel fixtures.
// ---------------------------------------------------------------------------
// Version-3 rows: row 0 is the commander (the player's own row, with no bond
// stage or membership), then one row per companion. Every fixture companion is
// a general member; membership metadata and the separate general quota are part
// of the extended payload.
const companion = (row) => ({
  role: "companion",
  mp_current: 0,
  mp_maximum: 0,
  sp_current: 0,
  sp_maximum: 0,
  knocked_out: false,
  unread: false,
  ...row,
  membership: row.membership ?? { general: true, temporary_commissions: [] },
});
const commander = (row) => ({
  role: "commander",
  portrait_ref: null,
  knocked_out: false,
  unread: false,
  bond_stage: null,
  membership: null,
  ...row,
});
const COMMANDER_ROW = commander({
  identity: 42,
  display_name: "影行者",
  hp_current: 80,
  hp_maximum: 100,
  mp_current: 30,
  mp_maximum: 50,
  sp_current: 12,
  sp_maximum: 40,
});

export const PARTY_PANEL_EMPTY_SAMPLE = {
  schema_version: 3,
  available: true,
  general_quota: { used: 0, limit: 4 },
  viewed_member_id: COMMANDER_ROW.identity,
  slots: [COMMANDER_ROW],
};

export const PARTY_PANEL_SAMPLE = {
  schema_version: 3,
  available: true,
  general_quota: { used: 2, limit: 4 },
  viewed_member_id: 101,
  slots: [
    COMMANDER_ROW,
    companion({
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "101",
      hp_current: 180,
      hp_maximum: 220,
      mp_current: 60,
      mp_maximum: 80,
      sp_current: 24,
      sp_maximum: 40,
      bond_stage: "親睦",
    }),
    companion({
      identity: 102,
      display_name: "幽",
      portrait_ref: null,
      hp_current: 144,
      hp_maximum: 160,
      mp_current: 90,
      mp_maximum: 120,
      sp_current: 10,
      sp_maximum: 30,
      bond_stage: "信賴",
    }),
  ],
};

export const PARTY_PANEL_FULL_SAMPLE = {
  schema_version: 3,
  available: true,
  general_quota: { used: 4, limit: 4 },
  viewed_member_id: 102,
  slots: [
    COMMANDER_ROW,
    companion({
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "101",
      hp_current: 180,
      hp_maximum: 220,
      mp_current: 60,
      mp_maximum: 80,
      sp_current: 24,
      sp_maximum: 40,
      bond_stage: "親睦",
    }),
    companion({
      identity: 102,
      display_name: "幽",
      portrait_ref: null,
      hp_current: 144,
      hp_maximum: 160,
      mp_current: 90,
      mp_maximum: 120,
      sp_current: 10,
      sp_maximum: 30,
      bond_stage: "信賴",
      unread: true,
    }),
    companion({
      identity: 103,
      display_name: "艾德蒙",
      portrait_ref: null,
      hp_current: 250,
      hp_maximum: 250,
      mp_current: 40,
      mp_maximum: 60,
      sp_current: 30,
      sp_maximum: 50,
      bond_stage: "熟稔",
    }),
    companion({
      identity: 104,
      display_name: "雪莉",
      portrait_ref: null,
      hp_current: 95,
      hp_maximum: 110,
      mp_current: 70,
      mp_maximum: 100,
      sp_current: 18,
      sp_maximum: 30,
      bond_stage: "初識",
    }),
  ],
};

// Existing bundled fixture art only; production never constructs these refs.
// Each catalog value is exactly `{artwork, context}` — the complete canonical
// descriptor plus its bounded display context — and the descriptor carries the
// committed built-in silhouette as its own alpha terminal
// (builtin-silhouette-stage-fallback).
// The companion rows alone: row 0 is the commander's own row and is never a
// lineup figure, drawer companion or catalog subject.
export const PARTY_COMPANION_ROWS = PARTY_PANEL_FULL_SAMPLE.slots.filter(
  (row) => row.role === "companion",
);
export const COMPANION_PORTRAIT_CATALOG = Object.fromEntries(
  PARTY_COMPANION_ROWS.map((row, index) => {
    const key = ["woman", "elder", "man", "girl"][index];
    return [String(row.identity), {
      artwork: {
        subject_id: `portrait:character:t_companion_${index}`,
        revision: fixtureDigest(`companion-${index}`),
        generation_subject: `portrait:character:t_companion_${index}`,
        generation_state: "done",
        attempts: [{
          type: "image",
          source_id: `portrait.default:t_companion_${index}`,
          rank: 30,
          resource: {
            resource_id: `defaults/${key}.webp`,
            version: fixtureDigest(`companion-resource-${index}`),
            url: `/art/defaults/${key}.webp`,
            origin: "runtime",
            geometry: {
              image_size: null,
              face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
              stage: { scale: 1, x: 0, y: 0 },
              aspect_ratio: "3:4",
            },
          },
        }],
        terminal: {
          kind: "alpha_mask",
          source_id: `portrait.alpha:${key}`,
          rank: 100,
          resource: {
            resource_id: `defaults/${key}.webp`,
            version: fixtureDigest(`companion-terminal-${index}`),
            url: `/art/defaults/${key}.webp`,
            origin: "silhouette",
            geometry: {
              image_size: null,
              face_rect: { x: 0.35, y: 0.03, w: 0.29, h: 0.16 },
              stage: null,
              aspect_ratio: "3:4",
            },
          },
        },
        retention_sources: [],
      },
      context: { name: row.display_name, role: "隊友" },
    }];
  }),
);

export const PARTY_COMBAT_PARTICIPANTS_SAMPLE = [
  { identity: 101, token: "a2", display_name: "蕾娜", team: "party", state: "active" },
  { identity: 102, token: "a3", display_name: "幽", team: "party", state: "active" },
];

export const PARTY_INTERACT_TARGETS_SAMPLE = [
  {
    identity: 201,
    display_name: "對話精靈",
    affordances: [
      {
        kind: "action",
        action_id: "explore.party_invite",
        label: "邀請",
        enabled: true,
        disabled_reason: null,
      },
    ],
  },
  {
    identity: 101,
    display_name: "蕾娜",
    affordances: [
      {
        kind: "action",
        action_id: "explore.party_leave",
        label: "解散",
        enabled: true,
        disabled_reason: null,
      },
    ],
  },
];

// The committed `party_member` v1 panel for the commander form: the four
// persona prose keys, the intimate level words, and the one server-authored
// persona-edit descriptor. `character` v8 no longer carries either section, so
// the character-status drawer reads them here.
export const PARTY_MEMBER_PANEL_SAMPLE = {
  schema_version: 1,
  available: true,
  kind: "party_member",
  member_id: 101,
  role: "commander",
  companion: null,
  commander: {
    persona: {
      background: "渡口成長起來的灰誓成員，習慣在黃昏開張前巡完整條街。",
      personality: "沉穩寡言，對生人保持距離。",
      life_story: "在渡口碼頭長大，十六歲跟著商隊上了路。",
      habit: "清晨練劍，黃昏沿著主街巡一圈。",
    },
    intimate: {
      arousal: "中等",
      wetness: "微濕",
      shame: "輕微",
      exposure: "中等",
      climax_phase: "未達",
      climax_today: 2,
    },
    actions: [
      {
        action_id: "character.persona.update",
        params: {},
        enabled: true,
        reason: null,
      },
    ],
  },
};