// SceneBackdrop (change unified-scene-rendering): the full-bleed stage backdrop
// renders the committed `art` v4 scene descriptor truthfully. Every assertion
// here drives the REAL loading core: an image layer reports its own observed
// natural dimensions through the element it owns, so a state is reached by
// dispatching that element's load/error event — never by stubbing the driver.
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import SceneBackdrop from "../components/SceneBackdrop.vue";
import {
  ART_PANEL_FAILED_SAMPLE,
  ART_PANEL_MALFORMED_SAMPLE,
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  ART_PANEL_UNAVAILABLE_SAMPLE,
  sceneBlock,
  sceneDescriptor,
} from "../stories/fixtures.js";
import { observeError, observeLoad, panelWithScene } from "./support/scene_layers.js";

describe("SceneBackdrop scene descriptor rendering", () => {
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

  it("renders the descriptor's successful source, with label and alt as DOM text outside the bitmap", async () => {
    const w = mountBackdrop();
    // A probe layer reports the generated candidate's pixels; only then is
    // that resource the displayed bitmap.
    expect(w.find('[data-testid="scene-backdrop-image"]').exists()).toBe(false);
    await observeLoad(w, ART_PANEL_SAMPLE.scene.artwork.attempts[0].resource.url);
    const img = w.get('[data-testid="scene-backdrop-image"]');
    expect(img.attributes("src")).toBe(ART_PANEL_SAMPLE.scene.artwork.attempts[0].resource.url);
    expect(w.get('[data-testid="scene-backdrop-label"]').text()).toBe("河畔清晨");
    expect(w.get('[data-testid="scene-backdrop-alt"]').text()).toBe("河畔清晨的場景");
    // The root reports the descriptor's own generation truth and availability.
    const root = w.get('[data-testid="scene-backdrop"]');
    expect(root.attributes("data-scene-state")).toBe("done");
    expect(root.attributes("data-available")).toBe("true");
    // A successfully resolved scene carries no error marker at all.
    expect(w.find('[data-testid="scene-backdrop-placeholder"]').exists()).toBe(false);
  });

  it("keeps the label, the alt text, and the full-view control on one caption plate", async () => {
    const w = mountBackdrop();
    await observeLoad(w, ART_PANEL_SAMPLE.scene.artwork.attempts[0].resource.url);
    const plate = w.get('[data-testid="scene-backdrop-caption"] .scene-backdrop__plate');
    for (const id of ["scene-backdrop-label", "scene-backdrop-alt", "scene-backdrop-control"]) {
      expect(plate.find(`[data-testid="${id}"]`).exists()).toBe(true);
    }
    // The one-line plate may end a long label or alt in an ellipsis; the full
    // text stays in the DOM and in the hover title.
    expect(plate.get('[data-testid="scene-backdrop-label"]').attributes("title")).toBe("河畔清晨");
    expect(plate.get('[data-testid="scene-backdrop-alt"]').attributes("title")).toBe("河畔清晨的場景");
    // The progress notice belongs to a pending regeneration only.
    expect(plate.find('[data-testid="scene-backdrop-generating"]').exists()).toBe(false);
    expect(plate.find('[data-testid="scene-backdrop-failure"]').exists()).toBe(false);
  });

  it("states a missing generation plainly, with no invented image and no error styling", () => {
    const art = panelWithScene(
      sceneBlock(
        { label: "河畔清晨", alt: "河畔清晨的場景" },
        sceneDescriptor({
          generation_state: "missing",
          // Nothing at all to try: the chain exhausts, which is exactly the
          // state the status badge speaks for.
          attempts: [],
          terminal: null,
          retention_sources: [],
        }),
      ),
    );
    const w = mountBackdrop({ art });
    expect(w.find('[data-testid="scene-backdrop-image"]').exists()).toBe(false);
    const placeholder = w.get('[data-testid="scene-backdrop-placeholder"]');
    expect(placeholder.attributes("data-kind")).toBe("missing");
    expect(w.get('[data-testid="scene-backdrop-placeholder-label"]').text()).toBe("尚未生成");
    // No caption row and no full-view control without a real scene image.
    expect(w.find('[data-testid="scene-backdrop-caption"]').exists()).toBe(false);
    expect(w.find('[data-testid="scene-backdrop-control"]').exists()).toBe(false);
  });

  it("keeps the retained image under the progress notice while the same scene regenerates", async () => {
    const w = mountBackdrop({ art: ART_PANEL_PENDING_SAMPLE, mode: "exploration" });
    // Seed the retained content through the exposed seam: it carries the
    // descriptor's own retention authorization, exactly like content this
    // browser really had on screen.
    w.vm.setPriorImage("/art/scenes/scene_river_dawn_prev.png");
    await w.vm.$nextTick();
    const img = w.get('[data-testid="scene-backdrop-image"]');
    expect(img.attributes("src")).toBe("/art/scenes/scene_river_dawn_prev.png");
    // A retained good image is not dimmed and not an error: the plate states
    // the factual progress instead.
    expect(img.classes()).not.toContain("scene-backdrop__image--dimmed");
    expect(w.get('[data-testid="scene-backdrop-generating"]').text()).toBe("目前場景圖片生成中");
    expect(w.find('[data-testid="scene-backdrop-failure"]').exists()).toBe(false);
    expect(w.find('[data-testid="scene-backdrop-placeholder"]').exists()).toBe(false);
  });

  it("shows the reached regeneration failure beside the healthy bundled fallback", async () => {
    const w = mountBackdrop({ art: ART_PANEL_FAILED_SAMPLE });
    // The descriptor's reached generation fault renders at once, and the
    // healthy bundled illustration follows it as the current attempt.
    expect(w.get('[data-testid="scene-backdrop-placeholder"]').attributes("data-kind")).toBe(
      "generation_failed",
    );
    const bundled = ART_PANEL_FAILED_SAMPLE.scene.artwork.attempts[1].resource.url;
    await observeLoad(w, bundled);
    expect(w.get('[data-testid="scene-backdrop-image"]').attributes("src")).toBe(bundled);
    // The failure stays visible: a healthy fallback never hides it.
    expect(w.get('[data-testid="scene-backdrop-failure"]').text()).toBe("此圖片生成失敗。");
    expect(w.find('[data-testid="scene-backdrop-generating"]').exists()).toBe(false);
  });

  it("states invalid scene metadata and still shows the permitted town terminal", async () => {
    const w = mountBackdrop({ art: ART_PANEL_MALFORMED_SAMPLE });
    expect(w.get('[data-testid="scene-backdrop-placeholder"]').attributes("data-kind")).toBe(
      "configuration_invalid",
    );
    const terminal = ART_PANEL_MALFORMED_SAMPLE.scene.artwork.terminal.resource.url;
    await observeLoad(w, terminal);
    expect(w.get('[data-testid="scene-backdrop-image"]').attributes("src")).toBe(terminal);
    expect(w.get('[data-testid="scene-backdrop-failure"]').text()).toBe("圖片設定有誤。");
  });

  it("degrades the unavailable panel to its own local availability indication", () => {
    const w = mountBackdrop({ art: ART_PANEL_UNAVAILABLE_SAMPLE });
    const frame = w.get('[data-testid="scene-backdrop-placeholder"]');
    expect(frame.attributes("data-kind")).toBe("panel_unavailable");
    expect(w.get('[data-testid="scene-backdrop-placeholder-label"]').text()).toBe(
      "圖片面板目前無法提供資料。",
    );
    expect(w.get('[data-testid="scene-backdrop"]').attributes("data-available")).toBe("false");
    expect(w.find('[data-testid="scene-backdrop-image"]').exists()).toBe(false);
    expect(w.find('[data-testid="scene-backdrop-caption"]').exists()).toBe(false);
  });

  it("omits the alternative text when it is identical to the scene label", async () => {
    const art = panelWithScene(
      sceneBlock(
        { label: "神秘森林", alt: "神秘森林" },
        ART_PANEL_SAMPLE.scene.artwork,
      ),
    );
    const w = mountBackdrop({ art });
    await observeLoad(w, ART_PANEL_SAMPLE.scene.artwork.attempts[0].resource.url);
    expect(w.get('[data-testid="scene-backdrop-label"]').text()).toBe("神秘森林");
    expect(w.find('[data-testid="scene-backdrop-alt"]').exists()).toBe(false);
  });

  it("marks one local image-load failure and takes the bitmap down with it", async () => {
    const w = mountBackdrop();
    const url = ART_PANEL_SAMPLE.scene.artwork.attempts[0].resource.url;
    await observeError(w, url);
    // The failed candidate is not presented as the current scene, and the
    // reached browser fact is stated locally.
    expect(w.find('[data-testid="scene-backdrop-image"]').exists()).toBe(false);
    expect(w.get('[data-testid="scene-backdrop-placeholder"]').attributes("data-kind")).toBe(
      "image_load_failed",
    );
  });

  it("opens a full-screen scene view from the control; Escape closes and restores focus", async () => {
    const w = mountBackdrop();
    const url = ART_PANEL_SAMPLE.scene.artwork.attempts[0].resource.url;
    await observeLoad(w, url);
    const control = w.get('[data-testid="scene-backdrop-control"]');
    expect(w.find('[data-testid="scene-backdrop-fullview"]').exists()).toBe(false);

    control.trigger("click");
    await w.vm.$nextTick();
    const fullView = w.get('[data-testid="scene-backdrop-fullview"]');
    expect(fullView.exists()).toBe(true);
    expect(fullView.attributes("role")).toBe("dialog");
    // The full view shows the SAME displayed resource — no second resolution.
    expect(w.get('[data-testid="scene-backdrop-fullview-image"]').attributes("src")).toBe(url);

    fullView.element.focus();
    fullView.trigger("keydown", { key: "Escape" });
    await w.vm.$nextTick();
    expect(w.find('[data-testid="scene-backdrop-fullview"]').exists()).toBe(false);
    expect(document.activeElement).toBe(control.element);
  });

  it("never leaves a full view open on a scene that lost its image", async () => {
    const w = mountBackdrop();
    const url = ART_PANEL_SAMPLE.scene.artwork.attempts[0].resource.url;
    await observeLoad(w, url);
    w.get('[data-testid="scene-backdrop-control"]').trigger("click");
    await flushPromises();
    expect(w.find('[data-testid="scene-backdrop-fullview"]').exists()).toBe(true);
    // The same subject moves to a state with nothing to show.
    await w.setProps({ art: ART_PANEL_UNAVAILABLE_SAMPLE });
    await flushPromises();
    expect(w.find('[data-testid="scene-backdrop-fullview"]').exists()).toBe(false);
  });
});
