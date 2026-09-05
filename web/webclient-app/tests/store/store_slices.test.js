// C1 (webclient-vue-07-wire-store) view-slice tests: the store holds only
// data derived from the OOB panel allowlist and the transport text stream
// (the "truthful data scope" scenario), and its slice shapes match the B-wave
// component props (the A2 architecture-reference contract — no drift between
// the mock-driven showcase and the live store-backed views).

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { resolveLocationLabel, useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";
import { MARKUP_STRESS_SAMPLE, NARRATIVE_SAMPLE, STATUS_SLICE_SAMPLE } from "../../stories/fixtures.js";

const PANEL_ALLOWLIST = [
  "art",
  "status",
  "context_actions",
  "local_map",
  "party",
  "objectives",
  "services",
  "creation",
  "exploration",
  "character",
  "lineage",
  "dialogue",
  "title_ballot",
  "title_codex",
  "roster",
];

function openActiveSession(store) {
  store.beginTransport(1);
  store.setConnected(true);
  // The real protocol delivers `logged_in` before any snapshot; model the
  // authenticated session so the store's status slice reaches "ready".
  store.setLoggedIn(true);
  const result = store.receive(1, "ui_snapshot", [fx.snapshot()], {});
  expect(result.accepted).toBe(true);
  return store;
}

describe("store view slices", () => {
  let store;

  beforeEach(() => {
    setActivePinia(createPinia());
    store = useElosernStore();
  });

  it("accepts a dialogue-mode snapshot and commits the dialogue panel", () => {
    openActiveSession(store);
    const dialoguePanel = {
      schema_version: 1,
      available: true,
      kind: "dialogue",
      host: { identity: 41, display_name: "公會職員", portrait_ref: null },
      bond_stage: "熟人",
      line: "歡迎來到冒險者公會。",
      choices: [
        { keyword_id: "公會", label: "公會" },
        { keyword_id: "任務", label: "任務" },
      ],
    };
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 4,
          presentation_epoch: fx.EPOCH_A,
          mode: "dialogue",
          panels: { status: fx.statusPanel(), dialogue: dialoguePanel },
        }),
      ],
      {},
    );
    expect(result.accepted).toBe(true);
    expect(store.view.mode).toBe("dialogue");
    expect(store.view.panels.dialogue).toEqual(dialoguePanel);
  });

  it("exposes the status/time slice with the B1 TopBar fixture shape", () => {
    openActiveSession(store);
    expect(store.view.statusSlice.connected).toBe(true);
    expect(store.view.statusSlice.locationLabel).toBe("測試起點");
    expect(store.view.statusSlice.timeLabel).toBe("春季 3 日 · 12:00");
    expect(store.view.statusSlice).toEqual({
      connected: STATUS_SLICE_SAMPLE.connected,
      locationLabel: STATUS_SLICE_SAMPLE.locationLabel,
      timeLabel: STATUS_SLICE_SAMPLE.timeLabel,
    });
  });

  it("holds only allowlist-sourced or text-sourced data, never invented data", () => {
    openActiveSession(store);
    for (const name of Object.keys(store.view.panels)) {
      expect(PANEL_ALLOWLIST).toContain(name);
    }

    for (const line of store.narrative) {
      expect(["in", "out", "sys", "err"]).toContain(line.kind);
      expect(typeof line.text).toBe("string");
    }
  });

  it("drives the narrative slice from appended transport text lines", () => {
    openActiveSession(store);
    for (const line of NARRATIVE_SAMPLE) {
      store.appendText(line.kind, line.text);
    }
    // The narrative slice (projected to {kind, text}) must match the B1
    // fixture exactly: same kind/text shapes, no invented lines.
    const projected = store.narrative.map((line) => ({ kind: line.kind, text: line.text }));
    expect(projected).toEqual(NARRATIVE_SAMPLE.map((line) => ({ kind: line.kind, text: line.text })));

    // "out" lines carry a renderable token view from the preserved
    // NarrativeMarkup pipeline; the other kinds stay literal (tokens === null).
    for (const line of store.narrative) {
      if (line.kind === "out") {
        expect(Array.isArray(line.tokens)).toBe(true);
        expect(line.tokens.length).toBeGreaterThan(0);
      } else {
        expect(line.tokens).toBe(null);
      }
    }
  });

  it("tokenizes narrative markup through the preserved pipeline (allowlist + degrade)", () => {
    for (const fixture of MARKUP_STRESS_SAMPLE) {
      const line = store.appendText(fixture.kind, fixture.text);
      expect(Array.isArray(line.tokens)).toBe(true);
      const kindsForToken = line.tokens.map((token) => token.kind);
      const textValues = line.tokens.filter((token) => token.kind === "text").map((token) => token.value);
      if (fixture.text.includes("<span")) {
        // The allowlist keeps <span> open tokens.
        expect(kindsForToken).toContain("open");
        // An unaccepted <div> degrades: its contents stay a literal
        // text token.
        expect(textValues).toContain("原樣保留");
      } else {
        // <br> produces break tokens.
        expect(kindsForToken).toContain("break");
      }
    }
  });

  it("counts only new narrative output lines as unread until seen", () => {
    openActiveSession(store);
    expect(store.unreadCount).toBe(0);
    store.appendText("in", "look");
    expect(store.unreadCount).toBe(0);
    store.appendText("out", "石板廣場 夜色沉靜。");
    store.appendText("sys", "—— 一則新的敘事 ——");
    store.appendText("out", "霧燈 在街角閃爍。");
    expect(store.unreadCount).toBe(2);
    store.markNarrativeSeen();
    expect(store.unreadCount).toBe(0);
    store.appendText("out", "冷風颳過後頸。");
    expect(store.unreadCount).toBe(1);
  });

  it("derives the local-map model from the committed panel and nulls it when absent", () => {
    expect(store.view.localMapModel).toBe(null);
    openActiveSession(store);
    store.receive(
      1,
      "ui_update",
       [fx.update({ revision: 2, panels: { local_map: fx.localMapPanel() } })],
      {},
    );
    const model = store.view.localMapModel;
    expect(model).not.toEqual(null);
    // The model is the preserved LocalMap render model over the committed
    // panel: the bounded layout lattice for the in-view field, the edge and
    // legend lists, and the remembered remote nodes.
    expect(model.nodes.length).toBe(3);
    expect(model.cols).toBe(2);
    expect(model.rows).toBe(2);
    expect(model.currentNode).toBe("room:42");
    expect(model.title).toBe("石板廣場");
    expect(model.edges.length).toBe(2);
    expect(model.legend.length).toBe(1);
    expect(model.remembered.length).toBe(0);

    // A snapshot without the panel wipes it: model back to null (wholesale
    // replacement semantics).
    store.receive(1, "ui_snapshot", [fx.snapshot({ revision: 3, presentation_epoch: fx.EPOCH_A })], {});
    expect(store.view.localMapModel).toBe(null);
  });

  it("drives the suggestions view model from the committed suggestions", () => {
    openActiveSession(store);
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          panels: { context_actions: fx.explorationActions() },
        }),
        {},
      ],
    );

    const readyCards = [
      {
        kind: "known_action",
        action_code: "explore.look",
        label: "查看房間",
        params: { room: true },
      },
      {
        kind: "known_action",
        action_code: "explore.wait",
        label: "等到黃昏",
        params: { daypart: "dusk" },
        hint: "先休息一會兒再行動",
      },
      {
        kind: "known_action",
        action_code: "explore.talk_scripted",
        label: "與灰婆婆交談",
        params: { npc_id: 7, keyword_id: "問候" },
      },
    ];
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 3,
          panels: {
            context_actions: fx.explorationActions({
              suggestions: { status: "ready", cards: readyCards },
            }),
          },
        }),
        {},
      ],
    );
    expect(store.view.suggestionsView.status).toBe("ready");
    expect(store.view.suggestionsView.cards.length).toBe(3);
    expect(store.view.suggestionsView.emptyState).toBe(false);

    const sigBefore = store.view.suggestionsSignature;
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 4,
          panels: {
            context_actions: fx.explorationActions({
              suggestions: { status: "unavailable" },
            }),
          },
        }),
        {},
      ],
    );
    expect(store.view.suggestionsView.status).toBe("unavailable");
    expect(store.view.suggestionsView.visible).toBe(false);
    expect(store.view.suggestionsSignature).not.toBe(sigBefore);
  });

  it("maps the committed transport state to the ConnectOverlay status slice", () => {
    expect(store.view.connectionStatus).toBe("offline");
    // A connected socket that has not logged in yet waits for login: an
    // anonymous session never receives a snapshot, so "connected, no
    // snapshot" is "waiting for login", never "connecting".
    store.beginTransport(1);
    store.setConnected(true);
    expect(store.view.connectionStatus).toBe("waiting");
    // The `logged_in` event marks the session authenticated; the overlay
    // shows "connecting" only while a snapshot is genuinely in flight.
    store.setLoggedIn(true);
    expect(store.view.connectionStatus).toBe("connecting");
    store.receive(1, "ui_snapshot", [fx.snapshot()], {});
    expect(store.view.connectionStatus).toBe("ready");
    store.setConnected(false);
    expect(store.view.connectionStatus).toBe("offline");
    // A disconnect ends the authenticated session: the next connect waits
    // for login again until the server re-emits `logged_in`.
    store.beginTransport(2);
    store.setConnected(true);
    expect(store.view.connectionStatus).toBe("waiting");
    store.setLoggedIn(true);
    expect(store.view.connectionStatus).toBe("connecting");
    store.receive(
      2,
      "ui_protocol_error",
      [
        fx.protocolError({
          code: "no_puppet",
          message: "你已離開角色",
          reload_required: false,
        }),
        {},
      ],
    );
    expect(store.view.connectionStatus).toBe("waiting");
  });

  it("exposes the committed panel slices for the B-wave panel families", () => {
    openActiveSession(store);
    expect(store.view.panels.status).toEqual(fx.statusPanel());
    expect(store.view.panels.local_map).toBeUndefined();
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          panels: {
            local_map: fx.localMapPanel(),
            context_actions: fx.explorationActions(),
          },
        }),
        {},
      ],
    );
    expect(store.view.panels.local_map).toEqual(fx.localMapPanel());
    expect(store.view.panels.context_actions).toEqual(fx.explorationActions());
  });

  // webclient-minimap-04-island-single-affordance (D5, tasks 3.1 & 3.2):
  // the top-meta locationLabel fallback order:
  // 1. local_map panel's current node label (when available, carries
  //    current_node, matches a node, and has non-empty string label)
  // 2. status panel's actor.location.label
  // 3. null (TopBar renders 「位置：--」)

  it("prefers the map current node label over the status panel label (wilderness case)", () => {
    openActiveSession(store);
    // Status panel alone gives raw room key "測試起點"
    expect(store.view.statusSlice.locationLabel).toBe("測試起點");

    // Commit a wilderness snapshot: status has Wilderness, map current node has 西部丘陵與谷地
    const wildernessMap = fx.localMapPanel({
      layer: "wilderness",
      current_node: "wild:plains:60:107",
      nodes: [
        {
          id: "wild:plains:60:107",
          label: "西部丘陵與谷地",
          x: 60,
          y: 107,
          visibility: "current",
          current: true,
          anchor: true,
          landmark: false,
          action: null,
        },
      ],
      edges: [],
});
    const wildernessStatus = fx.statusPanel({
      actor: {
        name: "影行者",
        identity: "42",
        location: { label: "Wilderness", identity: "17" },
      },
    });

    const res = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          panels: {
            status: wildernessStatus,
            local_map: wildernessMap,
          },
        }),
      ],
        {},
    );
    expect(res.accepted).toBe(true);
    expect(store.view.statusSlice.locationLabel).toBe("西部丘陵與谷地");
  });

  it("covers every fallback branch of locationLabel derivation (resolveLocationLabel)", () => {
    const status = { actor: { location: { label: "狀態位置" } } };

    // 1. Map panel absent -> falls back to status
    expect(resolveLocationLabel({ status })).toBe("狀態位置");

    // 2. Map panel available: false -> falls back to status
    expect(resolveLocationLabel({ status, local_map: { available: false } })).toBe("狀態位置");

    // 2b. Map panel available missing -> falls back to status
    expect(
      resolveLocationLabel({
        status,
        local_map: {
          current_node: "room:1",
          nodes: [{ id: "room:1", label: "地圖" }],
        },
      }),
    ).toBe("狀態位置");

    // 3. current_node naming a node the panel's nodes do not carry -> falls back to status
    expect(
      resolveLocationLabel({
        status,
        local_map: {
          available: true,
          current_node: "room:999",
          nodes: [{ id: "room:1", label: "節點" }],
        },
      }),
    ).toBe("狀態位置");

    // 4. Node whose label is an empty string -> falls back to status
    expect(
      resolveLocationLabel({
        status,
        local_map: {
          available: true,
          current_node: "room:1",
          nodes: [{ id: "room:1", label: "" }],
        },
      }),
    ).toBe("狀態位置");

    // 5. Node with non-empty label -> returns map label
    expect(
      resolveLocationLabel({
        status,
        local_map: {
          available: true,
          current_node: "room:1",
          nodes: [{ id: "room:1", label: "地圖節點" }],
        },
      }),
    ).toBe("地圖節點");

    // 6. Both panels absent / no location -> null
    expect(resolveLocationLabel({})).toBe(null);
    expect(resolveLocationLabel(null)).toBe(null);
    expect(resolveLocationLabel({ status: {} })).toBe(null);
    expect(resolveLocationLabel({ status: { actor: {} } })).toBe(null);
    expect(resolveLocationLabel({ status: { actor: { location: {} } } })).toBe(null);
    expect(resolveLocationLabel({ status: { actor: { location: { label: "" } } } })).toBe(null);
  });

  it("covers fallback in live store when local_map is unavailable or wiped", () => {
    openActiveSession(store);
    expect(store.view.statusSlice.locationLabel).toBe("測試起點");

    // When local_map is unavailable, falls back to status
    store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 2,
          panels: {
            status: fx.statusPanel({ actor: { location: { label: "狀態位置" } } }),
            local_map: {
              schema_version: 1,
              available: false,
              reason: { code: "fog", message: "無法顯示" },
            },
          },
        }),
      ],
      {},
    );
    expect(store.view.statusSlice.locationLabel).toBe("狀態位置");

    // Snapshot with no status and no local_map -> locationLabel is null (TopBar renders 「位置：--」)
    const emptySnap = fx.snapshot({
          revision: 3,
          panels: {
        status: fx.statusPanel({ actor: { location: null } }),
          },
    });
    const rNull = store.receive(
      1,
      "ui_snapshot",
      [emptySnap],
      {},
    );
    expect(rNull.accepted).toBe(true);
    expect(store.view.statusSlice.locationLabel).toBe(null);
  });

  it("updates locationLabel reactively when local_map current_node changes", () => {
    openActiveSession(store);
    const map = fx.localMapPanel({
      current_node: "room:42",
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
          action: null,
          },
      ],
      edges: [
        { source: "room:42", destination: "room:43", label: "東", known: true, traversable: true },
      ],
    });
    const r1 = store.receive(
      1,
      "ui_update",
      [
        fx.update({ revision: 2, panels: { local_map: map } }),
      ],
        {},
    );
    expect(r1.accepted).toBe(true);
    expect(store.view.statusSlice.locationLabel).toBe("石板廣場");

    // Move to room:43
    const updatedMap = {
      ...map,
      current_node: "room:43",
      nodes: map.nodes.map((n) =>
        n.id === "room:43"
          ? { ...n, visibility: "current", current: true }
          : { ...n, visibility: "visible_visited", current: false },
      ),
    };
    const r2 = store.receive(
      1,
      "ui_update",
      [
        fx.update({ revision: 3, panels: { local_map: updatedMap } }),
      ],
        {},
    );
    expect(r2.accepted).toBe(true);
    expect(store.view.statusSlice.locationLabel).toBe("西風酒館");
  });

  it("derives partyAvailable and partySlots reactively from committed party panel (webclient-align-05-party-hud)", () => {
    openActiveSession(store);
    // Initial snapshot has no party panel
    expect(store.view.partyAvailable).toBe(false);
    expect(store.partyAvailable).toBe(false);
    expect(store.view.partySlots).toEqual([]);
    expect(store.partySlots).toEqual([]);

    // Commit party panel with slots
    const partyData = {
      schema_version: 1,
      available: true,
      slots: [
        {
          identity: 101,
          display_name: "蕾娜",
          portrait_ref: null,
          hp_current: 180,
          hp_maximum: 220,
          bond_stage: "親睦",
        },
      ],
    };
    const r1 = store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, panels: { party: partyData } })],
      {},
    );
    expect(r1.accepted).toBe(true);
    expect(store.view.partyAvailable).toBe(true);
    expect(store.partyAvailable).toBe(true);
    expect(store.view.partySlots).toHaveLength(1);
    expect(store.partySlots[0].display_name).toBe("蕾娜");

    // Commit unavailable party panel
    const r2 = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 3,
          panels: {
            party: {
              schema_version: 1,
              available: false,
              reason: { code: "party_unavailable", message: "隊伍資訊目前無法顯示" },
            },
          },
        }),
      ],
      {},
    );
    expect(r2.accepted).toBe(true);
    expect(store.view.partyAvailable).toBe(false);
    expect(store.partyAvailable).toBe(false);
    expect(store.view.partySlots).toEqual([]);
  });

  it("derives objectivesAvailable and objectivesRows reactively from committed objectives panel (webclient-align-09-objective-tracker-ui)", () => {
    openActiveSession(store);
    // Initial snapshot has no objectives panel
    expect(store.view.objectivesAvailable).toBe(false);
    expect(store.objectivesAvailable).toBe(false);
    expect(store.view.objectivesRows).toEqual([]);
    expect(store.objectivesRows).toEqual([]);

    // Commit objectives panel with rows
    const objectivesData = {
      schema_version: 1,
      available: true,
      rows: [
        {
          quest_id: "q_1042",
          display_name: "磨坊糧運",
          objective_line: "抵達霧骨渡口",
          stage_index: 1,
          stage_total: 2,
          stage_progress: 1,
          objective_quantity: 1,
          reward_copper: null,
          deadline_line: null,
        },
      ],
    };
    const r1 = store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, panels: { objectives: objectivesData } })],
      {},
    );
    expect(r1.accepted).toBe(true);
    expect(store.view.objectivesAvailable).toBe(true);
    expect(store.objectivesAvailable).toBe(true);
    expect(store.view.objectivesRows).toHaveLength(1);
    expect(store.objectivesRows[0].objective_line).toBe("抵達霧骨渡口");

    // Commit unavailable objectives panel
    const r2 = store.receive(
      1,
      "ui_update",
      [
        fx.update({
          revision: 3,
          panels: {
            objectives: {
              schema_version: 1,
              available: false,
              reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
            },
          },
        }),
      ],
      {},
    );
    expect(r2.accepted).toBe(true);
    expect(store.view.objectivesAvailable).toBe(false);
    expect(store.objectivesAvailable).toBe(false);
    expect(store.view.objectivesRows).toEqual([]);
  });

  it("derives combatParticipants when context_actions is kind: combat (webclient-align-05-party-hud)", () => {
    openActiveSession(store);
    // In exploration mode (context_actions is kind: exploration)
    expect(store.view.combatParticipants).toEqual([]);
    expect(store.combatParticipants).toEqual([]);

    // Switch to combat mode with participants
    const combatActions = fx.combatActions({
      participants: [
        {
          identity: 101,
          token: "a2",
          display_name: "蕾娜",
          team: "party",
          state: "active",
          hp_current: 180,
          hp_maximum: 220,
          portrait_ref: null,
        },
        {
          identity: 201,
          token: "e1",
          display_name: "哥布林",
          team: "foes",
          state: "active",
          hp_current: 50,
          hp_maximum: 50,
          portrait_ref: null,
        },
      ],
    });
    const r = store.receive(
      1,
      "ui_update",
      [fx.update({ revision: 2, mode: "combat", panels: { context_actions: combatActions } })],
      {},
    );
    expect(r.accepted).toBe(true);
    expect(store.view.combatParticipants).toHaveLength(2);
    expect(store.combatParticipants[0].token).toBe("a2");
  });

  it("derives explorationInteract from committed exploration panel (webclient-align-05-party-hud)", () => {
    openActiveSession(store);
    expect(Array.isArray(store.view.explorationInteract)).toBe(true);
    expect(Array.isArray(store.explorationInteract)).toBe(true);
  });

  it("exposes roster slice when roster panel is available in snapshot", () => {
    openActiveSession(store);
    const rosterPanel = {
      schema_version: 1,
      available: true,
      characters: [
        {
          identity: 1,
          name: "艾莉亞",
          current: true,
          pending: false,
          portrait: {
            subject_key: "character:1",
            status: "done",
            url: "/art/portraits/character_1.png",
            aspect_ratio: "3:4",
            alt: "英雄肖像",
            placeholder: null,
          },
        },
        {
          identity: 2,
          name: "凱恩",
          current: false,
          pending: true,
          portrait: {
            subject_key: null,
            status: null,
            url: null,
            aspect_ratio: null,
            alt: "無肖像",
            placeholder: { kind: "unavailable", label: "無肖像" },
          },
        },
      ],
      max_characters: 5,
      can_create: true,
      switch_locked: false,
      lock_reason: null,
    };
    const result = store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 4,
          presentation_epoch: fx.EPOCH_A,
          panels: { status: fx.statusPanel(), roster: rosterPanel },
        }),
      ],
      {}
    );
    expect(result.accepted).toBe(true);
    expect(store.rosterAvailable).toBe(true);
    expect(store.rosterCharacters).toHaveLength(2);
    expect(store.rosterCharacters[0].name).toBe("艾莉亞");
    expect(store.rosterCanCreate).toBe(true);
    expect(store.rosterMaxCharacters).toBe(5);
    expect(store.rosterSwitchLocked).toBe(false);
    expect(store.rosterLockReason).toBe(null);
  });

  it("degrades roster slice to empty/unavailable when roster panel is unavailable or absent", () => {
    openActiveSession(store);
    const unavailableRoster = {
      schema_version: 1,
      available: false,
      reason: { code: "presentation_unavailable", message: "目前無法顯示此介面" },
    };
    store.receive(
      1,
      "ui_snapshot",
      [
        fx.snapshot({
          revision: 5,
          presentation_epoch: fx.EPOCH_A,
          panels: { status: fx.statusPanel(), roster: unavailableRoster },
        }),
      ],
      {}
    );
    expect(store.rosterAvailable).toBe(false);
    expect(store.rosterCharacters).toEqual([]);
    expect(store.rosterCanCreate).toBe(false);
    expect(store.rosterMaxCharacters).toBe(0);
    expect(store.rosterSwitchLocked).toBe(false);
    expect(store.rosterLockReason).toBe(null);
  });
});
