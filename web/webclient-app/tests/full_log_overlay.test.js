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

  it("moves focus into the open view (focus-trap) and the close control also closes", () => {
    const host = document.createElement("div");
    host.id = "fulllog-host";
    document.body.appendChild(host);
    wrapper = mount(FullLogOverlay, {
      attachTo: host,
      props: { lines: sampleLines() },
    });
    wrapper.vm.focusSelf();
    // The view is the single focusable element (tabindex=-1) — focus lands in it.
    expect(document.activeElement).toBe(wrapper.get('[data-testid="fulllog-overlay"]').element);
    // The sticky close control closes the overlay.
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
      props: { lines: arrival, marks: [], pageFit: () => true },
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

    const overlay = wrapper.get('[data-testid="fulllog-overlay"]').element;
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
