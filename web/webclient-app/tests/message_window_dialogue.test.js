// webclient-align-08-dialogue-surface / webclient-message-window-swap (design
// D3; webclient-dialogue-stage-actors D5/D7): the message window's dialogue
// variant. The name plate names the host (plus the bond stage), the `.dlg`
// box carries the serif reply with no avatar or speaker line (the host
// stands on the stage), `focusHome()` finds the first row, the numbered picks dispatch
// `explore.talk_scripted` payloads, the trailing free row borrows the command
// line without dispatching, the exit row dispatches `explore.dialogue_leave`,
// the session line renders once in the current response, and a transiently
// unavailable panel falls back to the paged presentation.

import { readFileSync } from "node:fs";
import { join } from "node:path";
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
  schema_version: 2,
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

  it("heads the variant with the name plate and renders the reply box with no avatar or speaker line", () => {
    const w = mountWindow();
    const plate = w.get('[data-testid="message-name-plate"]');
    expect(plate.text()).toBe("灰婆婆 · 羈絆 親睦");
    expect(plate.get('[data-testid="dialogue-bond"]').element.textContent).toBe(" · 羈絆 親睦");
    // The plate is the window's first row, above the text area.
    const root = w.get('[data-testid="message-window"]').element;
    expect(root.firstElementChild).toBe(plate.element);
    const box = w.get('[data-testid="dialogue-box"]');
    expect(box.find(".av").exists()).toBe(false);
    expect(box.find("img").exists()).toBe(false);
    expect(w.find('[data-testid="dialogue-who"]').exists()).toBe(false);
    expect(w.find(".who").exists()).toBe(false);
    expect(w.get('[data-testid="dialogue-say"]').text()).toBe(PANEL.line);
  });

  it("truncates only the host's name, so the bond segment stays readable", () => {
    // `text-overflow` does not apply to a flex row: the name carries its own
    // ellipsis box and the bond never shrinks (source-level guard; jsdom has
    // no layout).
    const source = readFileSync(join(process.cwd(), "web/webclient-app/components/MessageWindow.vue"), "utf-8");
    const rule = (sel) => (source.match(new RegExp(sel.replace(/[.]/g, "\\.") + "\\s*\\{[^}]*\\}")) || [""])[0];
    expect(rule(".message-window__plate-name")).toMatch(/text-overflow: ellipsis/);
    expect(rule(".message-window__plate-name")).toMatch(/min-width: 0/);
    expect(rule(".message-window__plate-bond")).toMatch(/flex: none/);
    const w = mountWindow();
    const plate = w.get('[data-testid="message-name-plate"]');
    expect(plate.get(".message-window__plate-name").text()).toBe("灰婆婆");
  });

  it("names only the host when bond_stage is null", () => {
    const w = mountWindow({ dialogue: dialogueViewModel({ ...PANEL, bond_stage: null }) });
    expect(w.find('[data-testid="dialogue-bond"]').exists()).toBe(false);
    expect(w.get('[data-testid="message-name-plate"]').text()).toBe("灰婆婆");
    expect(w.text()).not.toContain("羈絆");
  });

  it("renders no name plate outside the dialogue variant", async () => {
    const w = mountWindow({ dialogue: null });
    await nextTick();
    expect(w.find('[data-testid="message-name-plate"]').exists()).toBe(false);
  });

  it("focusHome() focuses the first dialogue row, else the page surface", async () => {
    const w = mountWindow();
    w.vm.focusHome();
    expect(document.activeElement).toBe(w.findAll('[data-testid="dialogue-pick"]')[0].element);
    // Without picks the free row, then the exit row, is the first row.
    await w.setProps({ dialogue: dialogueViewModel({ ...PANEL, choices: [] }) });
    w.vm.focusHome();
    expect(["dialogue-freeform", "dialogue-exit"]).toContain(document.activeElement.dataset.testid);
    // The paged variant's home is the page surface.
    await w.setProps({ mode: "exploration", dialogue: null });
    w.vm.focusHome();
    expect(document.activeElement).toBe(w.get('[data-testid="message-page"]').element);
  });

  it("keeps focus in the conversation when a reply replaces the focused row", async () => {
    const w = mountWindow();
    w.findAll('[data-testid="dialogue-pick"]')[1].element.focus();
    await w.setProps({
      dialogue: dialogueViewModel({
        ...PANEL,
        line: "「五枚就五枚。」",
        choices: [{ keyword_id: "board", label: "上船" }],
      }),
    });
    await nextTick();
    expect(document.activeElement).toBe(w.get('[data-testid="dialogue-pick"]').element);
  });

  it("moves focus from the page surface to the first row when the panel turns available", async () => {
    const w = mountWindow({ dialogue: null });
    await nextTick();
    w.get('[data-testid="message-page"]').element.focus();
    await w.setProps({ dialogue: vm });
    await nextTick();
    expect(document.activeElement).toBe(w.findAll('[data-testid="dialogue-pick"]')[0].element);
  });

  it("does not re-home focus when the mode leaves dialogue (the shell owns that case)", async () => {
    const w = mountWindow();
    w.findAll('[data-testid="dialogue-pick"]')[0].element.focus();
    await w.setProps({ mode: "exploration", dialogue: null });
    await nextTick();
    expect(document.activeElement).toBe(document.body);
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
