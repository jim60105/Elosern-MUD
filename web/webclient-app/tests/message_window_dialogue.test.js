// webclient-dialogue-choices-overlay D1/D3 (on webclient-dialogue-stage-
// actors D7): the message window in dialogue mode. The name plate names the
// host (plus the bond stage) above a paged, typed text area that shows the
// session line verbatim as the narrative delivered it; the window renders
// no choice row and no reply box; `reading-change` reports whether the
// current response's last page is on screen, fully shown, with no pending
// action mark; `focusHome()` focuses the page surface; and a transiently
// unavailable panel drops the plate.

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

describe("MessageWindow in dialogue mode (paged, under the name plate)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountWindow(props = {}, global = undefined) {
    const rawLines = props.lines || [{ kind: "out", text: "码头的水声。" }];
    wrapper = mount(MessageWindow, {
      attachTo: document.body,
      global,
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

  it("heads the page with the name plate and renders no reply box, avatar, or speaker line", () => {
    // The real Transition (webclient-mode-transitions D4) renders no element
    // of its own, so the plate is the window's first element child.
    const w = mountWindow({}, { stubs: { transition: false } });
    const plate = w.get('[data-testid="message-name-plate"]');
    expect(plate.text()).toBe("灰婆婆 ‧ 羈絆 親睦");
    expect(plate.get('[data-testid="dialogue-bond"]').element.textContent).toBe(" ‧ 羈絆 親睦");
    // The plate is the window's first row, above the text area.
    const root = w.get('[data-testid="message-window"]').element;
    expect(root.firstElementChild).toBe(plate.element);
    expect(w.find('[data-testid="dialogue-box"]').exists()).toBe(false);
    expect(w.find('[data-testid="message-dialogue"]').exists()).toBe(false);
    expect(w.find(".av").exists()).toBe(false);
    expect(w.find("img").exists()).toBe(false);
    expect(w.find(".who").exists()).toBe(false);
    expect(w.get('[data-testid="message-window"]').attributes("data-variant")).toBe("paged");
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
    // The underlined line between the plate and its spans shrinks with it.
    expect(rule(".message-window__plate-line")).toMatch(/min-width: 0/);
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

  it("renders no name plate while the panel is unavailable", async () => {
    const w = mountWindow({ dialogue: null });
    await nextTick();
    expect(w.find('[data-testid="message-name-plate"]').exists()).toBe(false);
  });

  it("pages the session line verbatim, the host's 說： prefix included", async () => {
    const line = `灰婆婆說：${PANEL.line}`;
    const w = mountWindow({ lines: [{ kind: "in", text: "talk 灰婆婆" }, { kind: "out", text: line }] });
    await nextTick();
    expect(w.get('[data-testid="message-page"]').text()).toBe(line);
    expect(w.findAll(".narrative-line.inp")).toHaveLength(0);
    expect(w.get('[data-testid="message-page-marker"]').text()).toBe("■");
  });

  it("renders no choice, free-dialogue, or exit row and emits no dialogue intent", async () => {
    const w = mountWindow({ lines: [{ kind: "out", text: PANEL.line }] });
    await nextTick();
    for (const id of ["dialogue-pick", "dialogue-freeform", "dialogue-exit", "dialogue-choices", "dialogue-move"]) {
      expect(w.find(`[data-testid="${id}"]`).exists()).toBe(false);
    }
    await w.get('[data-testid="message-page"]').trigger("keydown", { key: "Enter" });
    expect(Object.keys(w.emitted()).filter((name) => name.startsWith("dialogue-"))).toEqual([]);
  });

  it("reports reading complete on mount on the last page (a reconnect shows the choices at once)", async () => {
    const w = mountWindow({ lines: [{ kind: "out", text: PANEL.line }] });
    await nextTick();
    expect(w.emitted("reading-change").at(-1)).toEqual([true]);
    expect(w.get('[data-testid="message-window"]').attributes("data-reading-complete")).toBe("true");
  });

  it("flips reading-change with the reader: a further page, the last page, a pending mark", async () => {
    // Two sentences of 10 code points: two pages at a budget of 12.
    const two = "一二三四五六七八九。甲乙丙丁戊己庚辛壬。";
    const w = mountWindow({ lines: [{ kind: "out", text: "渡口。" }], pageFit: codePointFit(12), textSpeed: "instant" });
    await nextTick();
    const last = () => w.emitted("reading-change").at(-1)[0];
    expect(last()).toBe(true);
    // A new response opens on page 1 of 2: not complete.
    await w.setProps({ lines: withSeq([{ kind: "out", text: "渡口。" }, { kind: "in", text: "talk" }, { kind: "out", text: two }]) });
    await nextTick();
    await nextTick();
    const page = w.get('[data-testid="message-page"]');
    expect(page.attributes("data-page")).toBe("1");
    expect(page.attributes("data-pages")).toBe("2");
    expect(last()).toBe(false);
    // Enter on the page surface advances to the last page: complete.
    await page.trigger("keydown", { key: "Enter" });
    await nextTick();
    expect(page.attributes("data-page")).toBe("2");
    expect(last()).toBe(true);
    // A dispatched action marks a pending response: not complete until its
    // reply arrives.
    await w.setProps({ marks: [4] });
    await nextTick();
    expect(last()).toBe(false);
    await w.setProps({ lines: withSeq([{ kind: "out", text: "渡口。" }, { kind: "in", text: "talk" }, { kind: "out", text: two }, { kind: "out", text: "好。" }]) });
    await nextTick();
    await nextTick();
    expect(w.get('[data-testid="message-page"]').text()).toBe("好。");
    expect(last()).toBe(true);
  });

  it("is not reading-complete while the page types", async () => {
    const w = mountWindow({ lines: [{ kind: "out", text: "渡口。" }], textSpeed: "slow", motionLevel: "full" });
    await nextTick();
    await w.setProps({ lines: withSeq([{ kind: "out", text: "渡口。" }, { kind: "in", text: "talk" }, { kind: "out", text: PANEL.line }]) });
    await nextTick();
    await nextTick();
    expect(w.get('[data-testid="message-window"]').attributes("data-typing")).toBe("true");
    expect(w.emitted("reading-change").at(-1)).toEqual([false]);
    // Enter completes the typing page, which is the last one.
    await w.get('[data-testid="message-page"]').trigger("keydown", { key: "Enter" });
    await nextTick();
    expect(w.emitted("reading-change").at(-1)).toEqual([true]);
  });

  it("focusHome() focuses the page surface", async () => {
    const w = mountWindow();
    await nextTick();
    w.vm.focusHome();
    expect(document.activeElement).toBe(w.get('[data-testid="message-page"]').element);
  });

  it("starts the dialogue text column under the player anchor (source guard; jsdom has no layout)", () => {
    const source = readFileSync(join(process.cwd(), "web/webclient-app/components/MessageWindow.vue"), "utf-8");
    const rule = source.match(/\.message-window\[data-mode="dialogue"\] \.message-window__page\s*\{[^}]*\}/);
    expect(rule && rule[0]).toMatch(/padding-left: var\(--dialogue-inset\)/);
    expect(rule && rule[0]).toMatch(/margin: 0;/);
  });

  it("shows the current response's pages with their marker and no plate when the panel is unavailable", async () => {
    const w = mountWindow({ dialogue: null });
    await nextTick();
    expect(w.get('[data-testid="message-window"]').attributes("data-variant")).toBe("paged");
    expect(w.get('[data-testid="message-page"]').text()).toBe("码头的水声。");
    expect(w.get('[data-testid="message-page-marker"]').text()).toBe("■");
  });

  it("presents the same paged window in exploration and combat modes", async () => {
    const w = mountWindow({ mode: "exploration" });
    await nextTick();
    expect(w.get('[data-testid="message-window"]').attributes("data-variant")).toBe("paged");
    expect(w.find('[data-testid="message-name-plate"]').exists()).toBe(false);
    expect(w.get('[data-testid="message-page-marker"]').text()).toBe("■");
    w.unmount();
    wrapper = w;
    const c = mountWindow({ mode: "combat", dialogue: null });
    await nextTick();
    expect(c.get('[data-testid="message-window"]').attributes("data-variant")).toBe("paged");
    expect(c.get('[data-testid="message-page-marker"]').text()).toBe("■");
  });
});
