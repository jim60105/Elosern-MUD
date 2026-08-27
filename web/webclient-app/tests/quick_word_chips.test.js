import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import QuickWordChips from "../components/QuickWordChips.vue";

// The component renders both mode groups in the DOM; the inactive group is
// hidden by the stage root's `data-elosern-mode` gate with `display:none`
// (jsdom does not compute that CSS, so all seven chips are inspectable).
// `說` appears in both the exploration and combat sets, so scope by the
// testid prefix to enumerate every rendered chip.
describe("QuickWordChips chip icons (H5, webclient-hud-05-overlays-and-command-line)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  function mountChips(props = {}) {
    wrapper = mount(QuickWordChips, { props });
    return wrapper;
  }

  it("every exploration and combat chip carries exactly one aria-hidden icon beside its label", () => {
    const w = mountChips();
    const chips = w.findAll('[data-testid^="quick-word-chip-"]');
    // 5 exploration chips (看/拿/說/交談/等待) + 2 combat chips (說/施法) = 7.
    expect(chips.length).toBe(7);
    for (const chip of chips) {
      const icons = chip.findAll("svg[aria-hidden='true']");
      expect(icons.length).toBe(1, "exactly one decorative icon per chip");
      expect(icons[0].attributes("width")).toBe("14");
      expect(icons[0].attributes("fill")).toBe("none");
      const label = chip.text().trim();
      expect(label.length).toBeGreaterThan(0, "the icon is always paired with its text label");
      const path = icons[0].find("path");
      expect(path.exists()).toBe(true, "the icon renders a glyph path");
      expect(path.attributes("stroke")).toBe("currentColor");
    }
  });

  it("the exploration set and the combat set each carry their own icon set", () => {
    const w = mountChips();
    // The exploration group's five chips.
    const exploration = w.findAll('.qwc-exploration [data-testid^="quick-word-chip-"]');
    expect(exploration.length).toBe(5);
    for (const chip of exploration) {
      expect(chip.findAll("svg[aria-hidden='true']").length).toBe(1);
    }
    // The combat group's two chips.
    const combat = w.findAll('.qwc-combat [data-testid^="quick-word-chip-"]');
    expect(combat.length).toBe(2);
    for (const chip of combat) {
      expect(chip.findAll("svg[aria-hidden='true']").length).toBe(1);
    }
  });
});
