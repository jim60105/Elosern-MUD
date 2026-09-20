// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// ---------------------------------------------------------------------------
// webclient-align-05-party-hud: party panel fixtures.
// ---------------------------------------------------------------------------
export const PARTY_PANEL_EMPTY_SAMPLE = {
  schema_version: 1,
  available: true,
  slots: [],
};

export const PARTY_PANEL_SAMPLE = {
  schema_version: 1,
  available: true,
  slots: [
    {
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "p_reina",
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
  ],
};

export const PARTY_PANEL_FULL_SAMPLE = {
  schema_version: 1,
  available: true,
  slots: [
    {
      identity: 101,
      display_name: "蕾娜",
      portrait_ref: "p_reina",
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
  ],
};

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