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
import { dialoguePanel as v3Panel, nativeDelivery, sceneDelivery, speech } from "./support/dialogue_panel.js";

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
      key: "dlg-kw-fare",
      label: "「就五枚，走嗎？」",
      enabled: true,
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
});
