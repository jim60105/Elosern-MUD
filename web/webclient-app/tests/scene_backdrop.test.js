// H1 (webclient-hud-01-shell-and-scene, design D3/D8): the full-bleed scene
// backdrop. It renders the committed `art` panel's scene truthfully — the
// done cover image, the dimmed prior image for a pending scene, or the mode
// gradient with a truthful placeholder. The label and alt always render as DOM
// text outside the bitmap. A failed image URL is remembered client-locally.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import SceneBackdrop from "../components/SceneBackdrop.vue";
import {
  ART_PANEL_SAMPLE,
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_UNAVAILABLE_SAMPLE,
} from "../stories/fixtures.js";

describe("SceneBackdrop (H1 D3/D8)", () => {
  let wrapper;

  function mountBackdrop(props = {}) {
    const host = document.createElement("div");
    host.id = "scene-backdrop-host";
    document.body.appendChild(host);
    wrapper = mount(SceneBackdrop, {
      attachTo: host,
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
    const w = mountBackdrop();
    const img = w.get('[data-testid="scene-backdrop-image"]');
    expect(img.attributes("src")).toBe("/art/scenes/scene_river_dawn.png");
    expect(w.get('[data-testid="scene-backdrop-label"]').text()).toBe("河畔清晨");
    expect(w.get('[data-testid="scene-backdrop-alt"]').text()).toBe("河畔清晨的場景");
    // The root reports the scene status and availability.
    expect(w.get('[data-testid="scene-backdrop"]').attributes("data-scene-status")).toBe("done");
    expect(w.get('[data-testid="scene-backdrop"]').attributes("data-available")).toBe("true");
  });

  it("keeps the label, the alt text, and the full-view control on one caption plate", () => {
    const w = mountBackdrop();
    const plate = w.get('[data-testid="scene-backdrop-caption"] .scene-backdrop__plate');
    for (const id of ["scene-backdrop-label", "scene-backdrop-alt", "scene-backdrop-control"]) {
      expect(plate.find(`[data-testid="${id}"]`).exists()).toBe(true);
    }
    // The one-line plate may end a long label or alt in an ellipsis; the
    // full text stays in the DOM and in the hover title.
    expect(plate.get('[data-testid="scene-backdrop-label"]').attributes("title")).toBe("河畔清晨");
    expect(plate.get('[data-testid="scene-backdrop-alt"]').attributes("title")).toBe("河畔清晨的場景");
    // The pending notice renders only for a pending scene with a prior image.
    expect(plate.find('[data-testid="scene-backdrop-generating"]').exists()).toBe(false);
  });

  it("degrades the pending scene without a prior image to the truthful placeholder (no invented image)", () => {
    const w = mountBackdrop({ art: ART_PANEL_PENDING_SAMPLE });
    // No scene bitmap: exactly one status badge renders stating both sample and truthful placeholder label, with no raw kind code.
    expect(w.find('[data-testid="scene-backdrop-image"]').exists()).toBe(false);
    const placeholder = w.get('[data-testid="scene-backdrop-placeholder"]');
    expect(placeholder.attributes("data-kind")).toBe("missing");
    expect(w.find('[data-testid="scene-backdrop-placeholder-kind"]').exists()).toBe(false);
    expect(w.get('[data-testid="scene-backdrop-placeholder-label"]').text()).toBe("範例場景 ‧ 場景圖像尚未生成");
    // No scene caption row rendered without an actual image.
    expect(w.find('[data-testid="scene-backdrop-caption"]').exists()).toBe(false);
    expect(w.find('[data-testid="scene-backdrop-control"]').exists()).toBe(false);
  });

  it("keeps the prior scene image with a generating note when the scene is pending", async () => {
    const w = mountBackdrop({ art: ART_PANEL_PENDING_SAMPLE, mode: "exploration" });
    // Seed the client-local prior image memory (a pending scene keeps the last
    // rendered image, visibly dimmed).
    w.vm.setPriorImage("/art/scenes/scene_river_dawn_prev.png");
    await w.vm.$nextTick();
    const img = w.get('[data-testid="scene-backdrop-image"]');
    expect(img.attributes("src")).toBe("/art/scenes/scene_river_dawn_prev.png");
    expect(img.classes()).toContain("scene-backdrop__image--dimmed");
    expect(w.get('[data-testid="scene-backdrop-generating"]').text()).toBe("目前場景圖片生成中");
    expect(w.find('[data-testid="scene-backdrop-caption"]').exists()).toBe(true);
  });

  it("degrades the OOB-unavailable channel to the truthful gradient placeholder", () => {
    const w = mountBackdrop({ art: ART_PANEL_UNAVAILABLE_SAMPLE });
    const frame = w.get('[data-testid="scene-backdrop-placeholder"]');
    expect(frame.attributes("data-kind")).toBe("art_unavailable");
    expect(w.find('[data-testid="scene-backdrop-placeholder-kind"]').exists()).toBe(false);
    expect(w.get('[data-testid="scene-backdrop-placeholder-label"]').text()).toBe("範例場景 ‧ 場景圖像目前無法顯示");
    expect(w.get('[data-testid="scene-backdrop"]').attributes("data-available")).toBe("false");
    expect(w.find('[data-testid="scene-backdrop-image"]').exists()).toBe(false);
    expect(w.find('[data-testid="scene-backdrop-caption"]').exists()).toBe(false);
  });

  it("omits the alternative text when it is identical to the scene label", () => {
    const w = mountBackdrop({
      art: {
        ...ART_PANEL_SAMPLE,
        scene: {
          ...ART_PANEL_SAMPLE.scene,
          label: "神秘森林",
          alt: "神秘森林",
        },
      },
    });
    expect(w.get('[data-testid="scene-backdrop-label"]').text()).toBe("神秘森林");
    expect(w.find('[data-testid="scene-backdrop-alt"]').exists()).toBe(false);
  });

  it("does not render full-view control or caption row for empty gradient / missing scene", () => {
    const w = mountBackdrop({ art: { available: true, scene: { status: "missing" } } });
    expect(w.find('[data-testid="scene-backdrop-caption"]').exists()).toBe(false);
    expect(w.find('[data-testid="scene-backdrop-control"]').exists()).toBe(false);
  });

  it("remembers a failed image URL so it is not re-fetched until a new URL or reload (task 4.7)", async () => {
    const w = mountBackdrop();
    // Simulate the done scene's image failing to load.
    const img = w.get('[data-testid="scene-backdrop-image"]');
    img.trigger("error");
    await w.vm.$nextTick();
    // The failed URL is remembered: the bitmap is removed and the placeholder
    // reports the load failure.
    expect(w.find('[data-testid="scene-backdrop-image"]').exists()).toBe(false);
    expect(w.get('[data-testid="scene-backdrop-placeholder"]').attributes("data-kind")).toBe("load_failed");
  });

  it("opens a full-screen scene view from the control; Escape closes and restores focus (task 4.6)", async () => {
    const w = mountBackdrop();
    const control = w.get('[data-testid="scene-backdrop-control"]');
    expect(w.find('[data-testid="scene-backdrop-fullview"]').exists()).toBe(false);

    control.trigger("click");
    await w.vm.$nextTick();
    const fullView = w.get('[data-testid="scene-backdrop-fullview"]');
    expect(fullView.exists()).toBe(true);
    expect(fullView.attributes("role")).toBe("dialog");
    expect(w.get('[data-testid="scene-backdrop-fullview-image"]').attributes("src")).toBe("/art/scenes/scene_river_dawn.png");

    // Escape closes the full view and restores focus to the opener.
    fullView.element.focus();
    fullView.trigger("keydown", { key: "Escape" });
    await w.vm.$nextTick();
    expect(w.find('[data-testid="scene-backdrop-fullview"]').exists()).toBe(false);
    expect(document.activeElement).toBe(control.element);
  });
});
