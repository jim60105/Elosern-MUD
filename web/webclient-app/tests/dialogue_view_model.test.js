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

function availablePanel(overrides = {}) {
  return {
    schema_version: 1,
    available: true,
    kind: "dialogue",
    host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
    bond_stage: "親睦",
    line: "「渡河要五枚銅板。」",
    choices: [
      { keyword_id: "fare", label: "「就五枚，走嗎？」" },
      { keyword_id: "smell", label: "含糊帶過氣味" },
    ],
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
      actionId: "explore.talk_scripted",
      payload: { npc_id: 41, keyword_id: "fare" },
      commandDisplay: { npcLabel: "灰婆婆", keywordLabel: "「就五枚，走嗎？」" },
    });
  });

  it("keeps the bond stage null when the panel carries none", () => {
    const vm = dialogueViewModel(availablePanel({ bond_stage: null }));
    expect(vm.bondStage).toBeNull();
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
      dialogueViewModel({ schema_version: 1, available: false, kind: "dialogue", reason: { code: "dialogue_unavailable", message: "對話目前無法顯示" } }),
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
