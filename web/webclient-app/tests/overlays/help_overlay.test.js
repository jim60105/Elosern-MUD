import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import HelpOverlay from "../../components/HelpOverlay.vue";

describe("HelpOverlay (H5 body, webclient-hud-05-overlays-and-command-line)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function rowText(id) {
    return wrapper.get(`[data-testid="help-controls-row-${id}"]`).text();
  }

  it("renders the client's own control reference", () => {
    // The body is a plain block (task 6.1): no dialog role / aria-modal /
    // close control — those belong to the OverlayHost.
    wrapper = mount(HelpOverlay);
    const overlay = wrapper.get('[data-testid="help-overlay"]');
    expect(overlay.attributes("role")).toBeUndefined();
    expect(overlay.attributes("aria-modal")).toBeUndefined();
    const controls = wrapper.get('[data-testid="help-controls"]');
    expect(controls.findAll('[data-testid^="help-controls-row-"]').length).toBeGreaterThan(0);
    // `/` and the ⌨ toggle expand the command line; Escape and a successful
    // send collapse it (the help-surface contract).
    expect(rowText("slash")).toContain("展開收合中的指令列");
    expect(rowText("keyboard-toggle")).toContain("⌨");
    expect(rowText("keyboard-toggle")).toContain("再按一次則收合");
    expect(rowText("send")).toContain("送出成功後指令列收合");
    expect(rowText("collapse")).toContain("收合指令列");
    expect(rowText("log")).toContain("停在最新一行");
    const gameHelp = wrapper.get('[data-testid="help-controls-gamehelp"]');
    expect(gameHelp.get("code").text()).toBe("help");
    expect(gameHelp.text()).not.toContain("`");
  });

  it("names the dock's real positional picks (1–9), not a stale range", () => {
    // The dock digit handler accepts 1–9 (stores/elosern/interaction.js).
    wrapper = mount(HelpOverlay);
    const digits = wrapper.get('[data-testid="help-controls-row-digits"]');
    expect(digits.findAll("kbd").map((key) => key.text())).toEqual(["1", "9"]);
    expect(digits.text()).toContain("第 1 至 9 項");
    expect(wrapper.text()).not.toContain("1-4");
  });

  it("reads in Traditional Chinese apart from literal key names and command syntax", () => {
    wrapper = mount(HelpOverlay);
    const prose = wrapper
      .findAll(".help-controls__label, .help-controls__detail, .help-controls__title")
      .map((node) => node.text())
      .join(" ");
    const latinWords = prose.match(/[A-Za-z]{2,}/g) ?? [];
    const keyNames = new Set(["Enter", "Shift", "Tab", "Esc", "Space", "PageUp", "PageDown", "Home", "End"]);
    expect(latinWords.filter((word) => !keyNames.has(word))).toEqual([]);
  });

  it("renders no authored game-help sections", () => {
    // The guide payload is gone with the onboarding subsystem: the overlay
    // carries only the client-owned control reference.
    wrapper = mount(HelpOverlay);
    expect(wrapper.emitted().update).toBeUndefined();
    expect(wrapper.html()).not.toContain("guide");
  });
});
