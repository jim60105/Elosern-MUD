// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// ---------------------------------------------------------------------------
// B3 data-family fixtures (webclient-vue-04-showcase-data).
//
// Every value mirrors a validated OOB payload — the `status` panel at schema
// version 1 (web/webclient/presentation/status.py) and the `character` panel
// at schema version 5 (web/webclient/presentation/character.py) — and the
// character's skill data keeps the character payload's category/group/
// {key,label} grouping with the optional OOB skill-descriptor detail fields
// (the context_actions v5 descriptor shape: cost, target_spec,
// freeform_scales, shorthands) attached to some rows only. Fixed literals
// only, so the offline showcase and the live (C1 store) views cannot drift.
// ---------------------------------------------------------------------------

// A committed `status` v1 payload (design-draft actor at 霧骨渡口): mixed
// gauge states, one buff with a remaining duration, one deterministic
// combat-modifier condition carrying its exact applied modifiers, an active
// disguise, and no combat session.
export const STATUS_PANEL_SAMPLE = {
  schema_version: 2,
  available: true,
  actor: {
    name: "艾倫·灰誓",
    identity: "char-42",
    location: { label: "霧骨渡口", identity: "room-7" },
  },
  resources: {
    hp: { current: 231, maximum: 405 },
    mp: { current: 139, maximum: 420 },
    sp: { current: 68, maximum: 68 },
  },
  conditions: [
    {
      code: "fastwind",
      label: "疾風",
      severity: "beneficial",
      remaining_seconds: 60,
    },
    {
      code: "shame_exposure",
      label: "高露出",
      severity: "harmful",
      modifiers: { defense: -15, agility: -10 },
    },
    {
      code: "fog_veil",
      label: "霧隱",
      severity: "informational",
    },
  ],
  disguise_active: true,
  combat: null,
};

// A titled variant: the HUD head renders the composed full title as the
// addressed name when `actor.full_title` is present (title-system D6).
export const STATUS_PANEL_TITLED_SAMPLE = {
  ...STATUS_PANEL_SAMPLE,
  actor: {
    ...STATUS_PANEL_SAMPLE.actor,
    full_title: "F級冒險者　南門新客",
  },
};

// The same actor mid-combat (guild examination), for the combat story.
export const STATUS_PANEL_COMBAT_SAMPLE = {
  ...STATUS_PANEL_SAMPLE,
  conditions: [
    {
      code: "combat_focus",
      label: "專注",
      severity: "warning",
      remaining_seconds: 10,
      modifiers: { atk_phys: 5 },
    },
  ],
  disguise_active: false,
  combat: { mode: "guild_exam", round: 3 },
};

// The compact, condition-free variant: all gauges full, nothing else.
export const STATUS_PANEL_MINIMAL_SAMPLE = {
  ...STATUS_PANEL_SAMPLE,
  resources: {
    hp: { current: 405, maximum: 405 },
    mp: { current: 420, maximum: 420 },
    sp: { current: 68, maximum: 68 },
  },
  conditions: [],
  disguise_active: false,
  combat: null,
};