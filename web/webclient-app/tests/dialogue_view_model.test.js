// webclient-align-08-dialogue-surface (task 1.1): the ONE derived view model
// over the committed `dialogue` panel, shared by the feed variant, the dock's
// `dialogue.root` resolver, and the ArrowRight borrow. Row shapes are
// byte-identical to the exploration scripted/freeform rows so activation
// routes through the same dispatch contract.

import { describe, expect, it } from "vitest";
import {
  dialogueViewModel,
  DIALOGUE_FREE_ROW_KEY,
} from "../stores/dialogue-view.js";
import { choiceRow, dialoguePanel as v3Panel, nativeDelivery, sceneDelivery, speech } from "./support/dialogue_panel.js";

function availablePanel(overrides = {}) {
  return {
    ...v3Panel({ keywords: ["fare", "smell"], labels: ["「就五枚，走嗎？」", "含糊帶過氣味"] }),
    ...overrides,
  };
}

describe("dialogue view model", () => {
  it("derives host, bond stage, line, and verbatim scripted picks from the available panel", () => {
    const vm = dialogueViewModel(availablePanel());
    expect(vm.host).toEqual({ identity: 41, displayName: "灰婆婆", portraitRef: null });
    expect(vm.bondStage).toBe("親睦");
    expect(vm.line).toBe("「渡河要五枚銅板。」");
    expect(vm.picks).toHaveLength(2);
    expect(vm.picks[0]).toEqual({
      key: "dlg-topic-host.fare",
      label: "「就五枚，走嗎？」",
      enabled: true,
      availability: "open",
      locked: false,
      hint: null,
      unread: false,
      keywordId: "fare",
      topicId: "host.fare",
      actionId: "explore.talk_scripted",
      payload: { npc_id: 41, topic_id: "host.fare", context_id: "ctx-1" },
      commandDisplay: { npcLabel: "灰婆婆", keywordLabel: "「就五枚，走嗎？」" },
    });
  });

  it("carries the acting body, the context and the delivery verbatim", () => {
    const delivery = sceneDelivery([speech("actor", "消息？"), speech("host", "不太平。")]);
    const vm = dialogueViewModel(availablePanel({ delivery }));
    expect(vm.actor).toEqual({ identity: 1, displayName: "測試者", portraitRef: null });
    expect(vm.contextId).toBe("ctx-1");
    expect(vm.delivery).toBe(delivery);
    // A native delivery's one host line is the session line.
    expect(dialogueViewModel(availablePanel({ delivery: nativeDelivery("歡迎。") })).line).toBe("歡迎。");
  });

  it("keeps the bond stage null when the panel carries none", () => {
    const vm = dialogueViewModel(availablePanel({ bond_stage: null }));
    expect(vm.bondStage).toBeNull();
  });

  it("carries the host's server-authored catalog key through verbatim", () => {
    // The client never constructs a catalog key: the panel's opaque key rides
    // into the stage's portrait lookup unchanged, and null stays null.
    const vm = dialogueViewModel(
      availablePanel({
        host: { identity: 41, display_name: "灰婆婆", portrait_ref: "41" },
      }),
    );
    expect(vm.host.portraitRef).toBe("41");
    expect(dialogueViewModel(availablePanel()).host.portraitRef).toBeNull();
  });

  it("builds the trailing free-dialogue row on the same host identity", () => {
    const vm = dialogueViewModel(availablePanel());
    expect(vm.freeRow).toEqual({
      key: DIALOGUE_FREE_ROW_KEY,
      label: "自由對話（輸入任意話語）→ 指令列",
      freeform: true,
      npcId: 41,
      npcLabel: "灰婆婆",
      actionId: null,
    });
  });

  it("yields null for the unavailable, absent, or foreign-kind forms", () => {
    expect(
      dialogueViewModel({ schema_version: 3, available: false, kind: "dialogue", reason: { code: "dialogue_unavailable", message: "對話目前無法顯示" } }),
    ).toBeNull();
    expect(dialogueViewModel(null)).toBeNull();
    expect(dialogueViewModel(undefined)).toBeNull();
  });

  it("survives an available panel with an empty choices list (free row stays reachable)", () => {
    const vm = dialogueViewModel(availablePanel({ choices: [] }));
    expect(vm.picks).toHaveLength(0);
    expect(vm.freeRow).not.toBeNull();
  });

  // authored-dialogue-locked-ui: server availability is rendered, never
  // re-evaluated. Only open and locked rows reach the client.
  describe("locked topics", () => {
    const LONG_ID = `g.${"p".repeat(64)}.${"x".repeat(2048 - 67)}`;
    const choices = [
      choiceRow("fare", { topicId: "host.fare" }),
      { ...choiceRow("gate", { topicId: "host.gate" }), availability: "locked", requirement_hint: "  需要持有通行證  " },
      { ...choiceRow("vault", { topicId: "host.vault" }), availability: "hidden" },
      { ...choiceRow("odd", { topicId: "host.odd" }), availability: "unknown" },
      { ...choiceRow("blank", { topicId: "host.blank" }), availability: "locked", requirement_hint: "   " },
      { ...choiceRow("generated", { topicId: LONG_ID }), availability: "locked", requirement_hint: "需要好感階段至少為熟識", unread: true },
    ];
    const vm = () => dialogueViewModel(availablePanel({ choices }));

    it("drops hidden and unknown availability rows, keeping payload order", () => {
      expect(vm().picks.map((pick) => pick.topicId)).toEqual(["host.fare", "host.gate", "host.blank", LONG_ID]);
    });

    it("keeps a locked row selectable with its trimmed canonical hint", () => {
      const gate = vm().picks[1];
      expect(gate).toMatchObject({ enabled: true, locked: true, availability: "locked", hint: "需要持有通行證" });
      expect(gate.payload).toEqual({ npc_id: 41, topic_id: "host.gate", context_id: "ctx-1" });
      // An open row never carries a hint; an empty hint is no hint.
      expect(vm().picks[0].hint).toBeNull();
      expect(vm().picks[2]).toMatchObject({ locked: true, hint: null });
    });

    it("keeps a full generated identity opaque and untruncated, keyed by topic", () => {
      const generated = vm().picks[3];
      expect(generated.topicId).toBe(LONG_ID);
      expect(generated.topicId).toHaveLength(2048);
      expect(generated.payload.topic_id).toBe(LONG_ID);
      expect(generated.key).toBe(`dlg-topic-${LONG_ID}`);
      // The lock marker wins over unread (authored-dialogue-unread-notices):
      // a locked row never carries the unread marker, even if flagged.
      expect(generated.unread).toBe(false);
    });
  });
});
