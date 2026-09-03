// C1 (webclient-vue-07-wire-store) view-slice tests: the store holds only
// data derived from the OOB panel allowlist and the transport text stream
// (the "truthful data scope" scenario), and its slice shapes match the B-wave
// component props (the A2 architecture-reference contract — no drift between
// the mock-driven showcase and the live store-backed views).

import { beforeEach, describe, expect, it } from "vitest";
import { createPinia, setActivePinia } from "pinia";

import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "./protocol_fixtures.js";
import { MARKUP_STRESS_SAMPLE, NARRATIVE_SAMPLE, STATUS_SLICE_SAMPLE } from "../../stories/fixtures.js";

const PANEL_ALLOWLIST = [
  "art",
  "status",
  "context_actions",
  "local_map",
  "services",
  "creation",
  "exploration",
  "character",
  "title_ballot",
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

  it("drives the choice-point state machine from the committed suggestions", () => {
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
    expect(store.view.choicePoint.state).toBe("generating");

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
    expect(store.view.choicePoint.state).toBe("ready");
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
    expect(store.view.choicePoint.state).toBe("absent");
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
});
