// Shared fixtures for the C1 (webclient-vue-07-wire-store) store integration
// tests: the exact protocol envelope and panel shapes the Node-gated UMD
// test suite (web/static/webclient/js/tests/protocol.test.js) already proves
// valid, so the store is driven by exactly the payloads the preserved reducer
// accepts.

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
  for (const key of Object.keys(overrides)) {
    result[key] = deepMerge(base[key], overrides[key]);
  }
  return result;
}

export const EPOCH_A = "a".repeat(22);
export const EPOCH_B = "b".repeat(22);
export const EPOCH_C = "c".repeat(22);

export function serverTime(overrides = undefined) {
  return deepMerge(
    {
      year: 1204,
      season_index: 0,
      season_label: "春季",
      day_in_season: 3,
      hour: 12,
      minute: 0,
      second: 0,
    },
    overrides,
  );
}

export function statusPanel(overrides = undefined) {
  return deepMerge(
    {
      schema_version: 1,
      available: true,
      actor: {
        name: "影行者",
        identity: "42",
        location: { label: "測試起點", identity: "17" },
      },
      resources: {
        hp: { current: 80, maximum: 100 },
        mp: { current: 30, maximum: 50 },
        sp: { current: 12, maximum: 40 },
      },
      conditions: [],
      disguise_active: false,
      combat: null,
    },
    overrides,
  );
}

export function explorationActions(overrides = undefined) {
  return deepMerge(
    {
      schema_version: 5,
      available: true,
      kind: "exploration",
      affordances: [
        {
          action_id: "explore.wait",
          label: "等待",
          params: { daypart: "dusk" },
          freeform: false,
          navigation: false,
          enabled: true,
          disabled_reason: null,
        },
        {
          action_id: "explore.wait",
          label: "調息",
          params: { sleep: true },
          freeform: false,
          navigation: false,
          enabled: false,
          disabled_reason: { code: "recovery", message: "正在調息，未能行動" },
        },
        { surface: "guild", label: "公會", navigation: true, enabled: true, disabled_reason: null },
      ],
      suggestions: { status: "generating" },
    },
    overrides,
  );
}

export function combatActions(overrides = undefined) {
  return deepMerge(
    {
      schema_version: 5,
      available: true,
      kind: "combat",
      session: { session_id: "s-1", mode: "hostile", round: 1, state: "ready", reason: null },
      participants: [
        {
          identity: 7,
          token: "e1",
          display_name: "灰袍盜賊",
          team: "foes",
          state: "active",
          hp_current: 80,
          hp_maximum: 100,
          portrait_ref: null,
        },
        {
          identity: 8,
          token: "a1",
          display_name: "同行劍士",
          team: "party",
          state: "active",
          hp_current: 100,
          hp_maximum: 100,
          portrait_ref: null,
        },
      ],
      root_actions: ["attack", "skills", "items", "defend", "flee"],
      secondary_actions: ["forfeit"],
      skills: [],
      // The UMD reducer's exact-field validation: a combat-form panel's
      // `suggestions` must be exactly { status: "unavailable" }.
      suggestions: { status: "unavailable" },
    },
    overrides,
  );
}

export function localMapPanel(overrides = undefined) {
  return deepMerge(
    {
      schema_version: 1,
      available: true,
      layer: "interior",
      current_node: "room:42",
      title: "石板廣場",
      nodes: [
        {
          id: "room:42",
          label: "石板廣場",
          x: 0,
          y: 0,
          visibility: "current",
          current: true,
          anchor: true,
          landmark: true,
          action: null,
        },
        {
          id: "room:43",
          label: "西風酒館",
          x: 1,
          y: 0,
          visibility: "visible_visited",
          current: false,
          anchor: false,
          landmark: true,
          action: { kind: "move", exit_ref: "east", destination: "room:43" },
        },
        {
          id: "room:44",
          label: "北岸大道",
          x: 0,
          y: 1,
          visibility: "visible_unvisited",
          current: false,
          anchor: false,
          landmark: false,
          action: null,
        },
      ],
      edges: [
        { source: "room:42", destination: "room:43", label: "東", known: true, traversable: true },
        { source: "room:42", destination: "room:44", label: "北", known: true, traversable: true },
      ],
      legend: ["★ 安全地標"],
    },
    overrides,
  );
}

export function snapshot(overrides = undefined) {
  return deepMerge(
    {
      protocol_version: 1,
      presentation_epoch: EPOCH_A,
      revision: 1,
      mode: "exploration",
      panels: { status: statusPanel() },
      layout_version: 1,
      server_time: serverTime(),
    },
    overrides,
  );
}

export function update(overrides = undefined) {
  return snapshot(overrides);
}

export function actionResult(overrides = undefined) {
  return deepMerge(
    {
      protocol_version: 1,
      presentation_epoch: EPOCH_A,
      request_id: "session:1",
      outcome: "success",
      code: "completed",
      message: "完成",
      presentation_revision: 2,
    },
    overrides,
  );
}

export function protocolError(overrides = undefined) {
  return deepMerge(
    {
      protocol_version: 1,
      code: "no_puppet",
      message: "你已離開角色",
      reload_required: false,
    },
    overrides,
  );
}

export function createFakeSender() {
  const sent = { actions: [], texts: [] };
  return {
    sent,
    sendAction(envelope) {
      sent.actions.push(envelope);
    },
    sendText(text) {
      sent.texts.push(text);
    },
  };
}
