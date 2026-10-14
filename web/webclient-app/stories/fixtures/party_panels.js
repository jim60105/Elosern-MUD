// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

import { fixtureDigest } from "./art_panels.js";

// ---------------------------------------------------------------------------
// webclient-align-05-party-hud: party panel fixtures.
// ---------------------------------------------------------------------------
// Every fixture companion is a general member; membership metadata and the
// separate general quota are part of the extended version-2 party payload.
const withMembership = (rows) =>
  rows.map((row) => ({
    ...row,
    membership: row.membership ?? { general: true, temporary_commissions: [] },
  }));

export const PARTY_PANEL_EMPTY_SAMPLE = {
  schema_version: 2,
  available: true,
  general_quota: { used: 0, limit: 4 },
  slots: [],
};

export const PARTY_PANEL_SAMPLE = {
  schema_version: 2,
  available: true,
  general_quota: { used: 2, limit: 4 },
  slots: withMembership([
    {
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "101",
      hp_current: 180,
      hp_maximum: 220,
      bond_stage: "親睦",
    },
    {
      identity: 102,
      display_name: "幽",
      portrait_ref: null,
      hp_current: 144,
      hp_maximum: 160,
      bond_stage: "信賴",
    },
  ]),
};

export const PARTY_PANEL_FULL_SAMPLE = {
  schema_version: 2,
  available: true,
  general_quota: { used: 4, limit: 4 },
  slots: withMembership([
    {
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "101",
      hp_current: 180,
      hp_maximum: 220,
      bond_stage: "親睦",
    },
    {
      identity: 102,
      display_name: "幽",
      portrait_ref: null,
      hp_current: 144,
      hp_maximum: 160,
      bond_stage: "信賴",
    },
    {
      identity: 103,
      display_name: "艾德蒙",
      portrait_ref: null,
      hp_current: 250,
      hp_maximum: 250,
      bond_stage: "熟稔",
    },
    {
      identity: 104,
      display_name: "雪莉",
      portrait_ref: null,
      hp_current: 95,
      hp_maximum: 110,
      bond_stage: "初識",
    },
  ]),
};

// Existing bundled fixture art only; production never constructs these refs.
// Each catalog value is exactly `{artwork, context}` — the complete canonical
// descriptor plus its bounded display context — and the descriptor carries the
// committed built-in silhouette as its own alpha terminal
// (builtin-silhouette-stage-fallback).
export const COMPANION_PORTRAIT_CATALOG = Object.fromEntries(
  PARTY_PANEL_FULL_SAMPLE.slots.map((row, index) => {
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