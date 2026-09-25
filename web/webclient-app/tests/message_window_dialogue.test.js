// webclient-align-08-dialogue-surface / webclient-message-window-swap (design
// D3): the message window's dialogue variant. The `.dlg` box mirrors the
// committed panel (avatar/who/serif), the numbered picks dispatch
// `explore.talk_scripted` payloads, the trailing free row borrows the command
// line without dispatching, the exit row dispatches `explore.dialogue_leave`,
// the session line renders once in the current response, and a transiently
// unavailable panel falls back to the paged presentation.

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import MessageWindow from "../components/MessageWindow.vue";
import { dialogueViewModel } from "../stores/dialogue-view.js";

function codePointFit(budget) {
  return (fragments) =>
    fragments.reduce((sum, fragment) => sum + (fragment.end - fragment.start), 0) <= budget;
}

function withSeq(lines) {
  return lines.map((line, index) => ({ seq: index + 1, ...line }));
}

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

describe("MessageWindow dialogue variant (D3)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountWindow(props = {}) {
    const rawLines = props.lines || [{ kind: "out", text: "码头的水声。" }];
    wrapper = mount(MessageWindow, {
      attachTo: document.body,
      props: {
        mode: "dialogue",
        dialogue: vm,
        marks: [],
        pageFit: codePointFit(60),
        ...props,
        lines: withSeq(rawLines),
      },
    });
    return wrapper;
  }

  it("renders the box: gold initial avatar, speaker line with bond stage, serif reply", () => {
    const w = mountWindow();
    const box = w.get('[data-testid="dialogue-box"]');
    expect(box.find(".av img").exists()).toBe(false);
    expect(box.get(".av").text()).toBe("灰");
    expect(w.get('[data-testid="dialogue-who"]').text()).toContain("灰婆婆");
    expect(w.get('[data-testid="dialogue-bond"]').text()).toContain("羈絆 親睦");
    expect(w.get('[data-testid="dialogue-say"]').text()).toBe(PANEL.line);
  });

  it("renders the host's catalog portrait with its face-rect crop offset", () => {
    const hostedPanel = { ...PANEL, host: { identity: 41, display_name: "灰婆婆", portrait_ref: "p41" } };
    const w = mountWindow({
      dialogue: dialogueViewModel(hostedPanel),
      artPanel: {
        portrait_catalog: {
          p41: { url: "/art/portraits/granny.png", face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 } },
        },
      },
    });
    const img = w.get('[data-testid="dialogue-box"] img.av');
    expect(img.attributes("src")).toBe("/art/portraits/granny.png");
    expect(img.element.style.objectPosition).toBe("50% 31%");
  });

  it("drops the bond segment when bond_stage is null", () => {
    const w = mountWindow({ dialogue: dialogueViewModel({ ...PANEL, bond_stage: null }) });
    expect(w.find('[data-testid="dialogue-bond"]').exists()).toBe(false);
    expect(w.get('[data-testid="dialogue-who"]').text()).toBe("灰婆婆");
  });

  it("renders numbered picks in payload order plus the trailing free-dialogue row", () => {
    const w = mountWindow();
    const picks = w.findAll('[data-testid="dialogue-pick"]');
    expect(picks).toHaveLength(4);
    expect(picks.map((p) => p.get(".k").text())).toEqual(["1", "2", "3", "4"]);
    expect(picks[1].get(".t").text()).toBe("含糊帶過氣味");
    const free = w.get('[data-testid="dialogue-freeform"]');
    expect(free.get(".k").text()).toBe("⌨");
    expect(free.get(".t").text()).toBe("自由對話（輸入任意話語）→ 指令列");
  });

  it("renders the trailing exit row after the free row with no digit badge (align-11)", () => {
    const w = mountWindow();
    const exit = w.get('[data-testid="dialogue-exit"]');
    expect(exit.classes()).toContain("pick-exit");
    expect(exit.get(".k").text()).toBe("✕");
    expect(exit.get(".t").text()).toBe("結束對話");
    // The exit row sits LAST in the choices unit, after the free row.
    const rows = w.findAll(".choices .pick");
    expect(rows[rows.length - 1].element).toBe(exit.element);
    expect(rows.map((r) => r.element)).toContain(w.get('[data-testid="dialogue-freeform"]').element);
  });

  it("the exit row emits exactly one dialogue-leave and nothing else", async () => {
    const w = mountWindow();
    await w.get('[data-testid="dialogue-exit"]').trigger("click");
    expect(w.emitted("dialogue-leave")).toHaveLength(1);
    expect(w.emitted("dialogue-pick")).toBeUndefined();
    expect(w.emitted("dialogue-freeform")).toBeUndefined();
  });

  it("a pick activation emits exactly one row payload through the shared contract", async () => {
    const w = mountWindow();
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
    const w = mountWindow();
    await w.get('[data-testid="dialogue-freeform"]').trigger("click");
    expect(w.emitted("dialogue-freeform")).toHaveLength(1);
    expect(w.emitted("dialogue-pick")).toBeUndefined();
  });

  it("suppresses the verbatim duplicate tail so the session line renders once", () => {
    const w = mountWindow({
      lines: [{ kind: "out", text: "码头的水声。" }, { kind: "out", text: PANEL.line }],
    });
    expect(w.findAll('[data-testid="dialogue-say"]')).toHaveLength(1);
    const streamTexts = w.findAll('[data-testid="message-dialogue"] .narrative-line.out').map((l) => l.text());
    expect(streamTexts).toEqual(["码头的水声。"]);
  });

  it("cuts the anchored 說：echo of the committed reply out of the stream", () => {
    const w = mountWindow({
      lines: [
        { kind: "in", text: "talk 灰婆婆 客套" },
        { kind: "out", text: "码头的水声。" },
        { kind: "out", text: `灰婆婆說：${PANEL.line}` },
      ],
    });
    // The box owns the reply; the input line heads the response and never
    // renders in the window; the response's non-echo block stays.
    expect(w.findAll('[data-testid="message-dialogue"] .narrative-line.out').map((l) => l.text())).toEqual([
      "码头的水声。",
    ]);
    expect(w.findAll(".narrative-line.inp")).toHaveLength(0);
  });

  it("keeps only the daily-affinity hint residual of a capped echo", () => {
    const hint = "（今天你們之間的交流已經夠多了，她看起來有些疲憊。）";
    // The stored text carries the markup pipeline's shape: the newline before
    // the hint arrives as a tag the strip removes, gluing 緊接 directly after
    // the reply (the live-observed seam).
    const w = mountWindow({
      lines: [
        { kind: "out", text: "码头的水声。" },
        { kind: "out", text: `灰婆婆說：${PANEL.line}<br>${hint}` },
      ],
    });
    expect(w.findAll('[data-testid="message-dialogue"] .narrative-line.out').map((l) => l.text())).toEqual([
      "码头的水声。",
      hint,
    ]);
  });

  it("treats a player input line as a response header and never renders .inp in the window", () => {
    const w = mountWindow({
      lines: [
        { kind: "in", text: PANEL.line },
        { kind: "out", text: "码头的水声。" },
      ],
    });
    expect(w.findAll('[data-testid="message-dialogue"] .narrative-line.out').map((l) => l.text())).toEqual([
      "码头的水声。",
    ]);
    expect(w.findAll(".narrative-line.inp")).toHaveLength(0);
  });

  it("never removes an older identical line when the tail differs", () => {
    const w = mountWindow({
      lines: [
        { kind: "out", text: PANEL.line },
        { kind: "out", text: "她轉身續抽菸。" },
      ],
    });
    // The older duplicate stays; the box renders the committed line once.
    expect(w.findAll('[data-testid="message-dialogue"] .narrative-line.out').map((l) => l.text())).toEqual([
      PANEL.line,
      "她轉身續抽菸。",
    ]);
  });

  it("never swallows a sys tail whose text coincides with the reply", () => {
    const w = mountWindow({
      lines: [{ kind: "out", text: "码头的水声。" }, { kind: "sys", text: PANEL.line }],
    });
    // A system record is a distinct event: the box never owns its kind.
    expect(w.findAll('[data-testid="message-dialogue"] .narrative-line')).toHaveLength(2);
    expect(w.findAll('[data-testid="message-dialogue"] .narrative-line.sys').map((l) => l.text())).toEqual([
      PANEL.line,
    ]);
  });

  it("keeps literal angle-bracket prose in the hint residual", () => {
    const hint = "（提示：<任務名> 要寫全名）";
    const w = mountWindow({
      lines: [{ kind: "out", text: `灰婆婆說：${PANEL.line}<br>${hint}` }],
    });
    const out = w.findAll('[data-testid="message-dialogue"] .narrative-line.out');
    expect(out).toHaveLength(1);
    // The unrecognized tag survives the pipeline-normalizing strip verbatim.
    expect(out[0].text()).toBe(hint);
  });

  it("falls back to the paged presentation when the dialogue panel is transiently unavailable", async () => {
    const w = mountWindow({ dialogue: null });
    await nextTick();
    expect(w.get('[data-testid="message-window"]').attributes("data-variant")).toBe("paged");
    expect(w.find('[data-testid="dialogue-box"]').exists()).toBe(false);
    expect(w.find('[data-testid="dialogue-pick"]').exists()).toBe(false);
    expect(w.get('[data-testid="message-page"]').text()).toBe("码头的水声。");
    expect(w.get('[data-testid="message-page-marker"]').text()).toBe("■");
  });

  it("presents the paged variant in exploration and combat modes", async () => {
    const w = mountWindow({ mode: "exploration" });
    await nextTick();
    expect(w.get('[data-testid="message-window"]').attributes("data-variant")).toBe("paged");
    expect(w.find('[data-testid="dialogue-box"]').exists()).toBe(false);
    expect(w.get('[data-testid="message-page-marker"]').text()).toBe("■");
    w.unmount();
    wrapper = w;
    const c = mountWindow({ mode: "combat", dialogue: null });
    await nextTick();
    expect(c.get('[data-testid="message-window"]').attributes("data-variant")).toBe("paged");
    expect(c.find('[data-testid="dialogue-box"]').exists()).toBe(false);
    expect(c.get('[data-testid="message-page-marker"]').text()).toBe("■");
  });
});
