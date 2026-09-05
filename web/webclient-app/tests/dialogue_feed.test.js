// webclient-align-08-dialogue-surface (tasks 2.1/2.2/4.1): the feed dialogue
// variant. The `.dlg` box mirrors the committed panel (avatar/who/serif), the
// numbered picks dispatch `explore.talk_scripted` payloads, the trailing free
// row borrows the command line without dispatching, the session line renders
// exactly once, and the head/capsule matrix holds across the visible modes.

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import NarrativeFeed from "../components/NarrativeFeed.vue";
import { dialogueViewModel } from "../stores/dialogue-view.js";

const PANEL = {
  schema_version: 1,
  available: true,
  kind: "dialogue",
  host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
  bond_stage: "親睦",
  line: "「渡河要五枚銅板，多一子我也不走。」",
  choices: [
    { keyword_id: "fare", label: "「就五枚，走嗎？」" },
    { keyword_id: "smell", label: "含糊帶過氣味" },
    { keyword_id: "chest", label: "直接問箱櫃下落" },
    { keyword_id: "silence", label: "保持沉默，觀察她下一步" },
  ],
};

const vm = dialogueViewModel(PANEL);

describe("NarrativeFeed dialogue variant", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountFeed(props = {}) {
    wrapper = mount(NarrativeFeed, {
      props: {
        lines: [{ kind: "out", text: "码头的水声。" }],
        mode: "dialogue",
        dialogue: vm,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the box: gold initial avatar, speaker line with bond stage, serif reply", () => {
    const w = mountFeed();
    const box = w.get('[data-testid="dialogue-box"]');
    expect(box.find(".av img").exists()).toBe(false);
    expect(box.get(".av").text()).toBe("灰");
    expect(w.get('[data-testid="dialogue-who"]').text()).toContain("灰婆婆");
    expect(w.get('[data-testid="dialogue-bond"]').text()).toContain("羈絆 親睦");
    expect(w.get('[data-testid="dialogue-say"]').text()).toBe(PANEL.line);
  });

  it("drops the bond segment when bond_stage is null", () => {
    const w = mountFeed({ dialogue: dialogueViewModel({ ...PANEL, bond_stage: null }) });
    expect(w.find('[data-testid="dialogue-bond"]').exists()).toBe(false);
    expect(w.get('[data-testid="dialogue-who"]').text()).toBe("灰婆婆");
  });

  it("renders numbered picks in payload order plus the trailing free-dialogue row", () => {
    const w = mountFeed();
    const picks = w.findAll('[data-testid="dialogue-pick"]');
    expect(picks).toHaveLength(4);
    expect(picks.map((p) => p.get(".k").text())).toEqual(["1", "2", "3", "4"]);
    expect(picks[1].get(".t").text()).toBe("含糊帶過氣味");
    const free = w.get('[data-testid="dialogue-freeform"]');
    expect(free.get(".k").text()).toBe("⌨");
    expect(free.get(".t").text()).toBe("自由對話（輸入任意話語）→ 指令列");
  });

  it("a pick activation emits exactly one row payload through the shared contract", async () => {
    const w = mountFeed();
    await w.findAll('[data-testid="dialogue-pick"]')[1].trigger("click");
    expect(w.emitted("dialogue-pick")).toHaveLength(1);
    const [row] = w.emitted("dialogue-pick")[0];
    expect(row).toMatchObject({
      actionId: "explore.talk_scripted",
      payload: { npc_id: 41, keyword_id: "smell" },
    });
    expect(w.emitted("dialogue-freeform")).toBeUndefined();
  });

  it("the free-dialogue row emits the borrow without any pick", async () => {
    const w = mountFeed();
    await w.get('[data-testid="dialogue-freeform"]').trigger("click");
    expect(w.emitted("dialogue-freeform")).toHaveLength(1);
    expect(w.emitted("dialogue-pick")).toBeUndefined();
  });

  it("suppresses the verbatim duplicate tail so the session line renders once", () => {
    const w = mountFeed({
      lines: [{ kind: "out", text: "码头的水声。" }, { kind: "out", text: PANEL.line }],
    });
    expect(w.findAll('[data-testid="dialogue-say"]')).toHaveLength(1);
    const streamTexts = w.findAll(".narrative-line.out").map((l) => l.text());
    expect(streamTexts).toEqual(["码头的水声。"]);
  });

  it("cuts the anchored 說：echo of the committed reply out of the stream", () => {
    const w = mountFeed({
      lines: [
        { kind: "out", text: "码头的水声。" },
        { kind: "in", text: "talk 灰婆婆 客套" },
        { kind: "out", text: `灰婆婆說：${PANEL.line}` },
      ],
    });
    // The box owns the reply; the input echo stays; the echo line is gone.
    expect(w.findAll(".narrative-line.out").map((l) => l.text())).toEqual(["码头的水声。"]);
    expect(w.findAll(".narrative-line.inp")).toHaveLength(1);
  });

  it("keeps only the daily-affinity hint residual of a capped echo", () => {
    const hint = "（今天你們之間的交流已經夠多了，她看起來有些疲憊。）";
    // The stored text carries the markup pipeline's shape: the newline before
    // the hint arrives as a tag the strip removes, gluing 緊接 directly after
    // the reply (the live-observed seam).
    const w = mountFeed({
      lines: [
        { kind: "out", text: "码头的水声。" },
        { kind: "out", text: `灰婆婆說：${PANEL.line}<br>${hint}` },
      ],
    });
    expect(w.findAll(".narrative-line.out").map((l) => l.text())).toEqual([
      "码头的水声。",
      hint,
    ]);
  });

  it("never suppresses a player input echo that repeats the reply text", () => {
    const w = mountFeed({
      lines: [{ kind: "out", text: "码头的水声。" }, { kind: "in", text: PANEL.line }],
    });
    // kind "in" keeps its literal line even when the text coincides.
    expect(w.findAll(".narrative-line")).toHaveLength(2);
    expect(w.findAll(".narrative-line.inp").map((l) => l.text())).toEqual([PANEL.line]);
  });

  it("never removes an older identical line when the tail differs", () => {
    const w = mountFeed({
      lines: [
        { kind: "out", text: PANEL.line },
        { kind: "out", text: "她轉身續抽菸。" },
      ],
    });
    // The older duplicate stays; the box renders the committed line once.
    expect(w.findAll(".narrative-line.out").map((l) => l.text())).toEqual([
      PANEL.line,
      "她轉身續抽菸。",
    ]);
  });

  it("never swallows a sys tail whose text coincides with the reply", () => {
    const w = mountFeed({
      lines: [{ kind: "out", text: "码头的水声。" }, { kind: "sys", text: PANEL.line }],
    });
    // A system record is a distinct event: the box never owns its kind.
    expect(w.findAll(".narrative-line")).toHaveLength(2);
    expect(w.findAll(".narrative-line.sys").map((l) => l.text())).toEqual([PANEL.line]);
  });

  it("keeps literal angle-bracket prose in the hint residual", () => {
    const hint = "（提示：<任務名> 要寫全名）";
    const w = mountFeed({
      lines: [{ kind: "out", text: `灰婆婆說：${PANEL.line}<br>${hint}` }],
    });
    const out = w.findAll(".narrative-line.out");
    expect(out).toHaveLength(1);
    // The unrecognized tag survives the pipeline-normalizing strip verbatim.
    expect(out[0].text()).toBe(hint);
  });

  it("the head reads 對話 without the 完整日誌 capsule while the panel is available", () => {
    const w = mountFeed();
    expect(w.get('[data-testid="narrative-mode-label"]').text()).toBe("對話");
    expect(w.find('[data-testid="narrative-fulllog-control"]').exists()).toBe(false);
  });

  it("falls back plainly with the 對話 label when the panel is transiently unavailable", () => {
    const w = mountFeed({ dialogue: null });
    expect(w.find('[data-testid="dialogue-box"]').exists()).toBe(false);
    expect(w.find('[data-testid="dialogue-pick"]').exists()).toBe(false);
    expect(w.get('[data-testid="narrative-mode-label"]').text()).toBe("對話");
    // The capsule rule is scoped to the available window: the fallback keeps it.
    expect(w.find('[data-testid="narrative-fulllog-control"]').exists()).toBe(true);
    expect(w.findAll(".narrative-line.out").map((l) => l.text())).toEqual(["码头的水声。"]);
  });

  it("keeps 敘述/戰鬥日誌 labels and the capsule in the regular modes", () => {
    const w = mountFeed({ mode: "exploration" });
    expect(w.get('[data-testid="narrative-mode-label"]').text()).toBe("敘述");
    expect(w.find('[data-testid="narrative-fulllog-control"]').exists()).toBe(true);
    w.unmount();
    wrapper = w;
    const c = mountFeed({ mode: "combat", dialogue: null });
    expect(c.get('[data-testid="narrative-mode-label"]').text()).toBe("戰鬥日誌");
    expect(c.find('[data-testid="dialogue-box"]').exists()).toBe(false);
    expect(c.find('[data-testid="narrative-fulllog-control"]').exists()).toBe(true);
  });
});
