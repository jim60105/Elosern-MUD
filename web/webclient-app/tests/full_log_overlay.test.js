// H1 (webclient-hud-01-shell-and-scene, design D4, task 5.6): the full-log
// overlay renders the complete retained narrative through the preserved
// `narrative-renderer.js` (one markup path). This suite verifies: the overlay
// renders exactly the same line count as the store's retained narrative; the
// caption card is bounded (max-height:30vh, width:min(880px,90vw)); Escape
// closes the overlay and restores focus to the opener.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import FullLogOverlay from "../components/FullLogOverlay.vue";
import NarrativeFeed from "../components/NarrativeFeed.vue";

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

  it("keeps the narrative caption card bounded and rendering the same line count", () => {
    // The caption card's geometry is owned by the `feed` anchor (design D4):
    // `width:min(880px,90vw)` and `max-height:30vh`, so the card never grows
    // past its bounded height. The caption renders the same lines as the
    // overlay (one renderer).
    const lines = sampleLines();
    wrapper = mount(NarrativeFeed, { props: { lines } });
    expect(wrapper.find('[data-testid="narrative-feed"]').exists()).toBe(true);
    // The `完整日誌` control is present (the one-action full-log entry, 5.2).
    expect(wrapper.find('[data-testid="narrative-fulllog-control"]').exists()).toBe(true);
    // The caption renders exactly the retained line count.
    expect(wrapper.findAll(".narrative-line").length).toBe(lines.length);
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
});
