// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// ---------------------------------------------------------------------------
// webclient-align-05-party-hud: party panel fixtures.
// ---------------------------------------------------------------------------
export const PARTY_PANEL_EMPTY_SAMPLE = {
  schema_version: 2,
  available: true,
  slots: [],
};

export const PARTY_PANEL_SAMPLE = {
  schema_version: 2,
  available: true,
  slots: [
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
  ],
};

export const PARTY_PANEL_FULL_SAMPLE = {
  schema_version: 2,
  available: true,
  slots: [
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
  ],
};

// Existing bundled fixture art only; production never constructs these refs.
export const COMPANION_PORTRAIT_CATALOG = Object.fromEntries(
  PARTY_PANEL_FULL_SAMPLE.slots.map((row, index) => {
    const key = ["woman", "elder", "man", "girl"][index];
    return [String(row.identity), {
      subject_key: `portrait:character:t_companion_${index}`,
      status: "done", url: `/art/defaults/${key}.webp`,
      aspect_ratio: "3:4", alt: row.display_name, placeholder: null,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
      stage: { scale: 1, x: 0, y: 0 },
      // builtin-silhouette-stage-fallback: the decorative built-in
      // silhouette reference the server carries beside the resolved image.
      origin: "runtime",
      fallback: { key, url: `/art/defaults/${key}.webp`, face_rect: { x: 0.35, y: 0.03, w: 0.29, h: 0.16 } },
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