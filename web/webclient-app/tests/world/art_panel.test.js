import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ArtPanel from "../../components/ArtPanel.vue";
import {
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  ART_PANEL_UNAVAILABLE_SAMPLE,
} from "../../stories/fixtures.js";

describe("ArtPanel (B4 world family)", () => {
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

  it("renders the done scene as a 16:9 cover image with label and alt as DOM text outside the bitmap", () => {
    const w = mountPanel();
    const img = w.get('[data-testid="art-panel__scene"]');
    expect(img.attributes("src")).toBe("/art/scenes/scene_river_dawn.png");
    // The label and alt render as sibling <p> DOM nodes, never baked into the image.
    expect(img.attributes("alt")).toBeUndefined();
    expect(w.get('[data-testid="art-panel__scene-label"]').text()).toBe("河畔清晨");
    expect(w.get('[data-testid="art-panel__scene-alt"]').text()).toBe("河畔清晨的場景");
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

  it("degrades the pending scene without a prior image to the truthful placeholder (no invented <img>)", () => {
    const w = mountPanel({ art: ART_PANEL_PENDING_SAMPLE });
    // No scene bitmap: the frame carries the payload's own missing/placeholder wording.
    expect(w.find('[data-testid="art-panel__scene"]').exists()).toBe(false);
    const placeholder = w.get('[data-testid="art-panel__scene-placeholder"]');
    expect(placeholder.attributes("data-kind")).toBe("missing");
    expect(w.get('[data-testid="art-panel__scene-placeholder-kind"]').text()).toBe("missing");
    expect(w.get('[data-testid="art-panel__scene-placeholder-label"]').text()).toBe("場景圖像尚未生成");
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

  it("keeps the prior scene image with a generating note when the scene is pending", () => {
    const art = {
      ...ART_PANEL_PENDING_SAMPLE,
      scene: {
        ...ART_PANEL_PENDING_SAMPLE.scene,
        url: "/art/scenes/scene_river_dawn_prev.png",
        aspect_ratio: "16:9",
      },
    };
    const w = mountPanel({ art });
    expect(w.get('[data-testid="art-panel__scene"]').attributes("src")).toBe("/art/scenes/scene_river_dawn_prev.png");
    expect(w.get('[data-testid="art-panel__generating"]').text()).toBe("場景圖像生成中，顯示上一版圖像");
  });

  it("degrades the OOB-unavailable channel to the truthful 16:9 scene placeholder", () => {
    const w = mountPanel({ art: ART_PANEL_UNAVAILABLE_SAMPLE });
    // The unavailable form degrades to the truthful scene placeholder — a
    // 16:9 frame carrying the registry-owned reason (scenario: Art degrades
    // to a truthful placeholder; the OOB channel is unavailable).
    const frame = w.get('[data-testid="art-panel__scene-placeholder"]');
    expect(frame.attributes("data-kind")).toBe("art_unavailable");
    expect((frame.attributes("style") ?? "").toLowerCase()).toContain("aspect-ratio");
    const reason = w.get('[data-testid="art-panel__unavailable"]');
    expect(reason.text()).toBe("場景圖像目前無法顯示");
    // Neither the scene bitmap nor the portrait catalog renders when unavailable.
    expect(w.find('[data-testid="art-panel__scene"]').exists()).toBe(false);
    expect(w.find('[data-testid="art-panel__portraits"]').exists()).toBe(false);
  });

  it("applies the 16:9 scene and 3:4 portrait aspect frames from the design draft", () => {
    const w = mountPanel();
    const sceneImg = w.get('[data-testid="art-panel__scene"]');
    expect((sceneImg.attributes("style") ?? "").toLowerCase()).toContain("aspect-ratio");
    expect(sceneImg.element.style.aspectRatio.replace(/\s+/g, "")).toBe("16/9");

    const portraitImg = w.get('[data-testid="art-panel__portrait-img--101"]');
    expect((portraitImg.attributes("style") ?? "").toLowerCase()).toContain("aspect-ratio");
    expect(portraitImg.element.style.aspectRatio.replace(/\s+/g, "")).toBe("3/4");
  });
});
