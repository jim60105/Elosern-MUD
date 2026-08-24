import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ArtPanel from "../../components/ArtPanel.vue";
import {
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// H1 (webclient-hud-01-shell-and-scene): the scene section re-homed to
// SceneBackdrop; the ArtPanel is now the portrait catalog + the per-portrait
// full-view control. The scene assertions live in tests/scene_backdrop.test.js.
describe("ArtPanel (B4 world family — portrait catalog)", () => {
  let wrapper;

  function mountPanel(props = {}) {
    wrapper = mount(ArtPanel, {
      props: {
        art: ART_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("renders one 3:4 portrait tile per catalog ID, each with its contextual name and role overlay", () => {
    const w = mountPanel();
    // Two catalog IDs → exactly two tiles.
    expect(w.get('[data-testid="art-panel__portrait--101"]').attributes("data-placeholder")).toBe("false");
    expect(w.get('[data-testid="art-panel__portrait--217"]').attributes("data-placeholder")).toBe("false");
    expect(w.get('[data-testid="art-panel__portrait-img--101"]').attributes("src")).toBe("/art/portraits/port_harbor_master.png");
    expect(w.get('[data-testid="art-panel__portrait-img--217"]').attributes("src")).toBe("/art/portraits/port_river_ogre.png");
    const ctx101 = w.get('[data-testid="art-panel__portrait-context--101"]');
    expect(ctx101.find(".art-panel__portrait-context-name").text()).toBe("老周");
    expect(ctx101.find(".art-panel__portrait-context-role").text()).toBe("對話對象");
    const ctx217 = w.get('[data-testid="art-panel__portrait-context--217"]');
    expect(ctx217.find(".art-panel__portrait-context-name").text()).toBe("河灣巨魔");
    expect(ctx217.find(".art-panel__portrait-context-role").text()).toBe("敵方");
  });

  it("degrades a pending portrait to its own placeholder tile, keeping the context overlay", () => {
    const w = mountPanel({ art: ART_PANEL_PENDING_SAMPLE });
    // The portrait tile is flagged as a placeholder, with its own missing label.
    expect(w.get('[data-testid="art-panel__portrait--101"][data-placeholder="true"]').exists()).toBe(true);
    const ph = w.get('[data-testid="art-panel__portrait-placeholder--101"]');
    expect(ph.text()).toContain("missing");
    expect(ph.text()).toContain("肖像圖像尚未生成");
    // The contextual overlay still renders for the pending portrait.
    const ctx = w.get('[data-testid="art-panel__portrait-context--101"]');
    expect(ctx.text()).toContain("老周");
    expect(ctx.text()).toContain("對話對象");
  });

  it("applies the 3:4 portrait aspect frame from the design draft", () => {
    const w = mountPanel();
    const portraitImg = w.get('[data-testid="art-panel__portrait-img--101"]');
    expect((portraitImg.attributes("style") ?? "").toLowerCase()).toContain("aspect-ratio");
    expect(portraitImg.element.style.aspectRatio.replace(/\s+/g, "")).toBe("3/4");
  });

  it("opens a full-screen 3:4 portrait view from the per-portrait control; Escape closes and restores focus", async () => {
    const w = mountPanel();
    const control = w.get('[data-testid="art-panel__portrait-fullview--101"]');
    expect(w.find('[data-testid="art-panel__fullview"]').exists()).toBe(false);

    // The per-portrait control's click opens the full view (openFullView(entry)).
    await control.trigger("click");
    const fullView = w.get('[data-testid="art-panel__fullview"]');
    expect(fullView.exists()).toBe(true);
    expect(fullView.attributes("role")).toBe("dialog");
    expect(w.get('[data-testid="art-panel__fullview-img--101"]').attributes("src")).toBe("/art/portraits/port_harbor_master.png");

    // Escape closes the full view and restores focus to the opener.
    fullView.element.focus();
    await fullView.trigger("keydown", { key: "Escape" });
    expect(w.find('[data-testid="art-panel__fullview"]').exists()).toBe(false);
  });
});
