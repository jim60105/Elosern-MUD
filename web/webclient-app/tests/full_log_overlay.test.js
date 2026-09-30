// H1 (webclient-hud-01-shell-and-scene, design D4, task 5.6): the full-log
// overlay renders the complete retained narrative through the preserved
// `narrative-renderer.js` (one markup path). This suite verifies: the overlay
// renders exactly the same line count as the store's retained narrative; its
// semantic line classes match MessageWindow's page fragments (design D3); Escape
// closes the overlay and restores focus to the opener.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import FullLogOverlay from "../components/FullLogOverlay.vue";
import MessageWindow from "../components/MessageWindow.vue";

function sampleLines() {
  return [
    { kind: "out", text: "你來到了霧骨渡口。" },
    { kind: "in", text: "look" },
    { kind: "out", text: "碼頭上空無一人，只有浪聲。" },
    { kind: "sys", text: "（系統）進入探索模式" },
  ];
}

describe("FullLogOverlay (H1 D4)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders exactly the same line count as the retained narrative (one renderer, no second markup path)", () => {
    const lines = sampleLines();
    wrapper = mount(FullLogOverlay, { props: { lines } });
    // Each line renders as exactly one `.narrative-line` node.
    const lineCount = wrapper.findAll(".narrative-line").length;
    expect(lineCount).toBe(lines.length);
    // The player-input line renders as a literal `.inp` line.
    expect(wrapper.find(".narrative-line.inp").exists()).toBe(true);
  });

  it("closes on Escape (the parent wires it to the full-log open state)", () => {
    wrapper = mount(FullLogOverlay, { props: { lines: sampleLines() } });
    wrapper.get('[data-testid="fulllog-overlay"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
  });

  it("moves focus to the log's scroll region (focus-trap) and the header close control closes", () => {
    const host = document.createElement("div");
    host.id = "fulllog-host";
    document.body.appendChild(host);
    wrapper = mount(FullLogOverlay, {
      attachTo: host,
      props: { lines: sampleLines() },
    });
    wrapper.vm.focusSelf();
    // The scroll region takes the initial focus, so the reading keys scroll at once.
    expect(document.activeElement).toBe(wrapper.get('[data-testid="fulllog-scroll"]').element);
    // The shared header's close control closes the overlay.
    wrapper.get('[data-testid="fulllog-close"]').trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);
  });

  it("renders out and sys lines with the same classes and data-line-kind as MessageWindow page fragments", async () => {
    const arrival = [{ seq: 1, kind: "out", text: "你來到了霧骨渡口。" }];
    const lines = [
      { seq: 2, kind: "in", text: "look" },
      { seq: 3, kind: "out", text: "碼頭上空無一人，只有浪聲。" },
      { seq: 4, kind: "sys", text: "（系統）進入探索模式" },
    ];
    const overlayWrapper = mount(FullLogOverlay, { props: { lines: lines.slice(1) } });
    wrapper = mount(MessageWindow, {
      attachTo: document.body,
      props: { lines: arrival, marks: [], pageFit: () => true, textSpeed: "instant" },
    });
    await nextTick();
    await wrapper.setProps({ lines: [...arrival, ...lines] });
    await nextTick();
    await nextTick();
    try {
      const overlayLines = overlayWrapper.findAll(".narrative-line");
      // `sys` starts its own page in paginate(), so page 1 has `out` and page 2 has `sys`.
      const pageSurface = wrapper.get('[data-testid="message-page"]');
      const page1Line = pageSurface.get(".narrative-line");
      expect(page1Line.classes()).toEqual(overlayLines[0].classes());
      expect(page1Line.attributes("data-line-kind")).toBe(overlayLines[0].attributes("data-line-kind"));
      expect(page1Line.text()).toBe(overlayLines[0].text());

      await wrapper.get('[data-testid="message-window"]').trigger("click");
      const page2Line = pageSurface.get(".narrative-line");
      expect(page2Line.classes()).toEqual(overlayLines[1].classes());
      expect(page2Line.attributes("data-line-kind")).toBe(overlayLines[1].attributes("data-line-kind"));
      expect(page2Line.text()).toBe(overlayLines[1].text());
    } finally {
      overlayWrapper.unmount();
    }
  });

  it("renders sys lines with the .sys class and never mounts a choice-point in the full log", () => {
    const lines = sampleLines();
    wrapper = mount(FullLogOverlay, {
      props: {
        lines,
        suggestions: {
          status: "ready",
          cards: [{ kind: "known_action", action_code: "explore.look", label: "查看房間" }],
        },
      },
    });
    const sysLine = wrapper.find(".narrative-line.sys");
    expect(sysLine.exists()).toBe(true);
    expect(sysLine.attributes("data-line-kind")).toBe("sys");

    // The stream choice-point block never renders in the full log
    expect(wrapper.find('[data-testid="choicepoint-block"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="option-card"]').exists()).toBe(false);
  });

  it("opens at latest line: sets scrollTop to scrollHeight upon focusSelf() with 80 lines and leaves scrollTop unchanged when appending a line while open", async () => {
    const lines = Array.from({ length: 80 }, (_, i) => ({
      kind: "out",
      text: `第 ${i + 1} 行敘事內容。`,
    }));
    const host = document.createElement("div");
    host.id = "fulllog-host-80";
    document.body.appendChild(host);

    wrapper = mount(FullLogOverlay, {
      attachTo: host,
      props: { lines },
    });

    const overlay = wrapper.get('[data-testid="fulllog-scroll"]').element;
    let currentScrollTop = 0;
    Object.defineProperty(overlay, "scrollHeight", { value: 1600, configurable: true });
    Object.defineProperty(overlay, "scrollTop", {
      get: () => currentScrollTop,
      set: (val) => {
        currentScrollTop = val;
      },
      configurable: true,
    });

    wrapper.vm.focusSelf();
    expect(overlay.scrollTop).toBe(1600);

    // Appending a line while open leaves scrollTop unchanged
    await wrapper.setProps({
      lines: [...lines, { kind: "out", text: "第 81 行敘事內容。" }],
    });
    expect(overlay.scrollTop).toBe(1600);
  });
});

// webclient-full-log-frame: the shared frame, echoes as in-place response
// headings, and the end-aware return control.
describe("FullLogOverlay frame and return-to-latest", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  // Mount attached, with an opener button focused, and give the scroll
  // region a controllable geometry (jsdom lays nothing out).
  function mountOpen(lines, { height = 2000, client = 500 } = {}) {
    const opener = document.createElement("button");
    opener.textContent = "日誌";
    document.body.appendChild(opener);
    opener.focus();
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(FullLogOverlay, { attachTo: host, props: { lines } });
    const scroll = wrapper.get('[data-testid="fulllog-scroll"]').element;
    const geometry = { top: 0, height, client };
    Object.defineProperty(scroll, "scrollHeight", { get: () => geometry.height, configurable: true });
    Object.defineProperty(scroll, "clientHeight", { get: () => geometry.client, configurable: true });
    Object.defineProperty(scroll, "scrollTop", {
      get: () => geometry.top,
      set: (value) => {
        geometry.top = Math.max(0, Math.min(value, geometry.height - geometry.client));
      },
      configurable: true,
    });
    wrapper.vm.focusSelf();
    return { opener, scroll, geometry };
  }

  function responses(count) {
    const lines = [{ seq: 1, kind: "out", text: "你站在公會大廳。" }];
    for (let r = 1; r <= count; r++) {
      lines.push({ seq: lines.length + 1, kind: "in", text: `look ${r}` });
      lines.push({ seq: lines.length + 1, kind: "out", text: `第 ${r} 則回應。` });
    }
    return lines;
  }

  it("is one dialog under the shared header, over a scrim outside the dialog", () => {
    const { scroll } = mountOpen(responses(2));
    const dialog = wrapper.get('[role="dialog"]');
    expect(dialog.attributes("aria-modal")).toBe("true");
    const title = wrapper.get('[data-testid="fulllog__title"]');
    expect(title.text()).toBe("日誌");
    expect(dialog.attributes("aria-labelledby")).toBe(title.attributes("id"));
    expect(wrapper.findAll('[role="dialog"]')).toHaveLength(1);
    const scrim = wrapper.get('[data-testid="fulllog-scrim"]').element;
    expect(dialog.element.contains(scrim)).toBe(false);
    expect(dialog.element.contains(scroll)).toBe(true);
    expect(scroll.getAttribute("aria-label")).toBe("日誌內容");
  });

  it("keeps every line once and in order, each echo in place after its divider", () => {
    const lines = [
      { seq: 1, kind: "in", text: "look" },
      { seq: 2, kind: "out", text: "廣場。" },
      { seq: 3, kind: "sys", text: "（系統）存檔完成" },
      { seq: 4, kind: "in", text: "移動 北" },
      { seq: 5, kind: "out", text: "┌──┐\n│北│\n└──┘" },
      { seq: 6, kind: "err", text: "你無法往那個方向走。" },
    ];
    mountOpen(lines);
    const rendered = wrapper.findAll(".narrative-line");
    expect(rendered.map((node) => node.text())).toEqual(lines.map((line) => line.text));
    const echoes = wrapper.findAll(".narrative-line.inp");
    expect(echoes.map((node) => node.text())).toEqual(["look", "移動 北"]);
    // The first echo heads the log without a divider; the second follows one.
    expect(echoes[0].element.previousElementSibling).toBeNull();
    expect(echoes[1].element.previousElementSibling.classList.contains("narrative-divider")).toBe(true);
    expect(wrapper.findAll(".narrative-divider")).toHaveLength(1);
    expect(wrapper.find(".narrative-line.map-art").exists()).toBe(true);
  });

  it("offers no return control at the end, and one after the reader scrolls up", async () => {
    const { scroll } = mountOpen(responses(20));
    await nextTick();
    expect(scroll.scrollTop).toBe(1500);
    expect(wrapper.find('[data-testid="fulllog-latest"]').exists()).toBe(false);
    scroll.scrollTop = 300;
    await wrapper.get('[data-testid="fulllog-scroll"]').trigger("scroll");
    const latest = wrapper.get('[data-testid="fulllog-latest"]');
    expect(latest.text()).toBe("回到最新");
    expect(latest.attributes("data-fresh")).toBe("false");
    // The control sits in the footer strip, outside the scrolling text.
    expect(scroll.contains(latest.element)).toBe(false);
  });

  it("marks an arrival without moving the reader, and the control reveals the end without closing", async () => {
    const lines = responses(20);
    const { scroll, geometry } = mountOpen(lines);
    scroll.scrollTop = 300;
    await wrapper.get('[data-testid="fulllog-scroll"]').trigger("scroll");
    geometry.height = 2100;
    await wrapper.setProps({ lines: [...lines, { seq: 99, kind: "out", text: "港口傳來鐘聲。" }] });
    await nextTick();
    await nextTick();
    expect(scroll.scrollTop).toBe(300);
    const latest = wrapper.get('[data-testid="fulllog-latest"]');
    expect(latest.attributes("data-fresh")).toBe("true");
    expect(latest.text()).toContain("新內容");

    latest.element.focus();
    await latest.trigger("click");
    expect(scroll.scrollTop).toBe(1600);
    // Focus moved to the region before the control left.
    expect(document.activeElement).toBe(scroll);
    await nextTick();
    expect(wrapper.find('[data-testid="fulllog-latest"]').exists()).toBe(false);
    expect(wrapper.emitted("close")).toBeUndefined();
  });

  it("marks an arrival at the retention cap, where the line count no longer grows", async () => {
    const lines = Array.from({ length: 500 }, (_, i) => ({ seq: i + 1, kind: "out", text: `第 ${i + 1} 行。` }));
    const { scroll, geometry } = mountOpen(lines, { height: 20000 });
    geometry.height = 20040;
    await wrapper.setProps({ lines: [...lines.slice(1), { seq: 501, kind: "out", text: "新的一行。" }] });
    await nextTick();
    await nextTick();
    expect(scroll.scrollTop).toBe(19500);
    expect(wrapper.get('[data-testid="fulllog-latest"]').attributes("data-fresh")).toBe("true");
  });

  it("hands focus to the region when the end comes into view while the control is focused", async () => {
    const { scroll } = mountOpen(responses(20));
    scroll.scrollTop = 300;
    await wrapper.get('[data-testid="fulllog-scroll"]').trigger("scroll");
    const latest = wrapper.get('[data-testid="fulllog-latest"]');
    latest.element.focus();
    scroll.scrollTop = 1500;
    await wrapper.get('[data-testid="fulllog-scroll"]').trigger("scroll");
    expect(wrapper.find('[data-testid="fulllog-latest"]').exists()).toBe(false);
    expect(document.activeElement).toBe(scroll);
  });

  it("routes reading keys from its controls to the scroll region", async () => {
    const { scroll } = mountOpen(responses(20));
    const close = wrapper.get('[data-testid="fulllog-close"]');
    close.element.focus();
    await close.trigger("keydown", { key: "Home" });
    expect(scroll.scrollTop).toBe(0);
    expect(document.activeElement).toBe(scroll);
  });

  it("keeps Escape after a click on the frame's chrome, restoring focus to the opener", async () => {
    const { opener } = mountOpen(responses(2));
    const root = wrapper.get('[data-testid="fulllog-overlay"]');
    // A pointer press on non-focusable chrome focuses the nearest focusable
    // ancestor: the root, which owns the key handling.
    expect(root.attributes("tabindex")).toBe("-1");
    root.element.focus();
    await root.trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(document.activeElement).toBe(opener);
  });

  it("never marks an arrival the reader can already see, before or after a clear", async () => {
    const { geometry } = mountOpen(responses(1), { height: 400, client: 500 });
    await wrapper.setProps({ lines: [] });
    await nextTick();
    await wrapper.setProps({ lines: [{ seq: 50, kind: "out", text: "新的一行。" }] });
    await nextTick();
    await nextTick();
    expect(geometry.top).toBe(0);
    // Content that fits shows its end: no control and no pending cue.
    expect(wrapper.find('[data-testid="fulllog-latest"]').exists()).toBe(false);
    geometry.height = 2000;
    const scroll = wrapper.get('[data-testid="fulllog-scroll"]');
    await scroll.trigger("scroll");
    expect(wrapper.get('[data-testid="fulllog-latest"]').attributes("data-fresh")).toBe("false");
  });

  it("enters the Tab cycle at the last control on Shift+Tab from the surface itself", async () => {
    const { scroll } = mountOpen(responses(2));
    const root = wrapper.get('[data-testid="fulllog-overlay"]');
    root.element.focus();
    await root.trigger("keydown", { key: "Tab", shiftKey: true });
    expect(document.activeElement).toBe(scroll);
  });

  it("leaves modified reading keys on its controls alone", async () => {
    const { scroll } = mountOpen(responses(20));
    const close = wrapper.get('[data-testid="fulllog-close"]');
    close.element.focus();
    await close.trigger("keydown", { key: "Home", ctrlKey: true });
    expect(scroll.scrollTop).toBe(1500);
    expect(document.activeElement).toBe(close.element);
  });
});
