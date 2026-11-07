// Story fixture slices: see stories/fixtures.js (facade) for the public surface.

// ---------------------------------------------------------------------------
// B2 action-dock family fixtures (webclient-vue-03-showcase-action).
//
// Every value mirrors a validated `context_actions` v6 slice — the exact
// server-authored shapes (the v6 exploration form's action/navigation
// affordances) — so the offline showcase and the live (C1 store) views
// cannot drift. Fixed literals only.
// ---------------------------------------------------------------------------

// v5 exploration-form action + navigation affordances, one bounded frame:
// enabled and disabled action entries (disabled_reason carries the
// server-authored note) and a local navigation surface.
export const EXPLORATION_AFFORDANCES_SAMPLE = [
  {
    action_id: "explore.move",
    label: "走往北岸大道",
    params: { exit_ref: "north", current_node: 42 },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.look",
    label: "觀察房間",
    params: { room: true },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.talk_freeform",
    label: "與灰婆婆自由交談",
    params: { npc_id: 9 },
    freeform: true,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.wait",
    label: "等待",
    params: { daypart: "dusk" },
    freeform: false,
    navigation: false,
    enabled: false,
    disabled_reason: { code: "recovery", message: "正在調息，無法行動" },
  },
  {
    surface: "guild",
    label: "公會",
    navigation: true,
    enabled: true,
    disabled_reason: null,
  },
];

// A target selection frame (`target-<identity>` item keys) — the combat
// target menu shape: identity/display_name/state derived entries.
export const TARGET_ITEMS_SAMPLE = [
  { identity: "e1", label: "灰袍盜賊", enabled: true, disabled_reason: null },
  { identity: "e2", label: "斷刃巡衛", enabled: false, disabled_reason: { code: "down", message: "已倒地" } },
  { identity: "a2", label: "同行劍士", enabled: true, disabled_reason: null },
];