// The scene surface's transition rules (change unified-scene-rendering,
// MODIFIED webclient-contextual-hud): the stage crossfades a same-place
// replacement only once its pixels are observed, and a move commits the new
// place's own background at once — the previous place's painting is never kept
// and never crossfaded across a logical place change.
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import SceneBackdrop from "../components/SceneBackdrop.vue";
import {
  ART_PANEL_SAMPLE,
  SCENE_PLACE,
  SCENE_SUBJECT,
  sceneBlock,
  sceneDescriptor,
  sceneResource,
} from "../stories/fixtures.js";
import { displayedUrl, observeError, observeLoad, panelWithScene, renderedUrls } from "./support/scene_layers.js";

// The real `<Transition>`/`<TransitionGroup>` (not the test-utils stub), so
// the leaving copies and their `inert` state are observable.
const REAL = { global: { stubs: { transition: false, "transition-group": false } } };

// Two animation frames and a macrotask: long enough for Vue to end a leave
// whose computed duration jsdom reports as zero.
async function frames() {
  await new Promise((resolve) => setTimeout(resolve, 60));
  await nextTick();
}

let wrapper = null;

afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  document.body.innerHTML = "";
});

// One scene panel whose generated candidate paints `url`, at the SAME logical
// place and generation subject as the next one unless overridden.
function panelFor(url, overrides = {}) {
  const { subjectId = SCENE_PLACE, retainToken = "t".repeat(64), ...sceneOverrides } = overrides;
  return panelWithScene(
    sceneBlock(
      { label: sceneOverrides.label ?? "河畔清晨", alt: sceneOverrides.alt ?? "河畔清晨的場景" },
      sceneDescriptor({
        subject_id: subjectId,
        attempts: [
          {
            type: "image",
            source_id: `scene.generated:${SCENE_SUBJECT}`,
            rank: 20,
            resource: sceneResource({ url, version: url }),
          },
        ],
        terminal: null,
        retention_sources: [
          { source_id: `scene.generated:${SCENE_SUBJECT}`, token: retainToken },
        ],
      }),
    ),
  );
}

describe("SceneBackdrop transitions", () => {
  it("crossfades a same-place replacement once its pixels are observed", async () => {
    const first = "/art/scenes/river_dawn_first.png";
    const second = "/art/scenes/river_dawn_second.png";
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: panelFor(first) } });
    await observeLoad(wrapper, first);
    expect(displayedUrl(wrapper)).toBe(first);

    // The replacement commits: the label and alt switch at once while the
    // image on screen stays the one whose pixels are known.
    await wrapper.setProps({ art: panelFor(second, { label: "新場景", alt: "新的場景" }) });
    expect(wrapper.get('[data-testid="scene-backdrop-label"]').text()).toBe("新場景");
    expect(displayedUrl(wrapper)).toBe(first);

    await observeLoad(wrapper, second);
    // Both layers exist while the fade runs: the entering one is the new
    // scene, the leaving one is inert.
    const leaving = wrapper.findAll("img").find((img) => img.attributes("src") === first);
    const entering = wrapper.findAll("img").find((img) => img.attributes("src") === second);
    expect(leaving?.element.inert).toBe(true);
    expect(entering?.element.inert).toBe(false);

    await frames();
    expect(displayedUrl(wrapper)).toBe(second);
    expect(renderedUrls(wrapper)).toEqual([second]);
  });

  it("drops a move's previous place at once and shows the new place's own background", async () => {
    const first = "/art/scenes/place_one.png";
    const second = "/art/scenes/place_two.png";
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: panelFor(first) } });
    await observeLoad(wrapper, first);
    expect(displayedUrl(wrapper)).toBe(first);

    // A DIFFERENT logical place commits while its own image is still loading.
    await wrapper.setProps({ art: panelFor(second, { subjectId: "grid:t_synth_map:1,1" }) });
    await flushPromises();
    // The previous place's painting is gone from the presentation — no
    // crossfade, no retained copy — and only the new place's own probe is on
    // the page.
    expect(displayedUrl(wrapper)).toBe(null);
    expect(renderedUrls(wrapper)).toEqual([second]);

    await observeLoad(wrapper, second);
    expect(displayedUrl(wrapper)).toBe(second);
  });

  it("keeps the previous place's pixels out of the new place's caption", async () => {
    const first = "/art/scenes/place_one.png";
    const second = "/art/scenes/place_two.png";
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: panelFor(first) } });
    await observeLoad(wrapper, first);
    await wrapper.setProps({
      art: panelFor(second, { subjectId: "grid:t_synth_map:1,1", label: "北岸大道", alt: "林蔭覆蓋的河岸大道" }),
    });
    // Even before the new image resolves, the caption names the new place and
    // renders no control for a bitmap the backdrop does not show.
    expect(wrapper.find('[data-testid="scene-backdrop-caption"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="scene-backdrop-control"]').exists()).toBe(false);
    await observeLoad(wrapper, second);
    expect(wrapper.get('[data-testid="scene-backdrop-label"]').text()).toBe("北岸大道");
    expect(wrapper.get('[data-testid="scene-backdrop-alt"]').text()).toBe("林蔭覆蓋的河岸大道");
  });

  it("keeps the retained same-place bitmap and marks the failed replacement", async () => {
    const first = "/art/scenes/place_one.png";
    const broken = "/art/scenes/place_two_broken.png";
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: panelFor(first) } });
    await observeLoad(wrapper, first);
    await wrapper.setProps({ art: panelFor(broken) });
    await observeError(wrapper, broken);
    await frames();
    // A same-place replacement that fails does not blank the stage: the good
    // image this browser is still authorized to show stays, and the reached
    // failure is stated beside it.
    expect(displayedUrl(wrapper)).toBe(first);
    expect(wrapper.get('[data-testid="scene-backdrop-failure"]').text()).toBe("圖片載入失敗。");
    expect(wrapper.find('[data-testid="scene-backdrop-generating"]').exists()).toBe(false);
  });

  it("renders the final state in the commit frame at the off motion level", async () => {
    const first = "/art/scenes/place_one.png";
    const second = "/art/scenes/place_two.png";
    wrapper = mount(SceneBackdrop, {
      ...REAL,
      props: { art: panelFor(first), motionLevel: "off" },
    });
    await observeLoad(wrapper, first);
    await wrapper.setProps({ art: panelFor(second) });
    await observeLoad(wrapper, second);
    // No CSS phase on the transition: the swap leaves no second layer, even
    // for a frame.
    await flushPromises();
    expect(renderedUrls(wrapper)).toEqual([second]);
    expect(displayedUrl(wrapper)).toBe(second);
  });

  it("does not re-fetch a resource whose failure the driver already observed", async () => {
    const first = "/art/scenes/place_one.png";
    const broken = "/art/scenes/broken_candidate.png";
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: panelFor(first) } });
    await observeLoad(wrapper, first);
    await wrapper.setProps({ art: panelFor(broken) });
    await observeError(wrapper, broken);
    await frames();
    // The failed source is never requested again: the driver records the
    // observation and re-committing the same descriptor recommends nothing.
    expect(renderedUrls(wrapper)).not.toContain(broken);
    await wrapper.setProps({ art: panelFor(broken, { label: "再看一次" }) });
    await frames();
    expect(renderedUrls(wrapper)).not.toContain(broken);
  });

  it("renders the panel's own sample scene without a second fetching layer", () => {
    // The committed fixture's descriptor is already resolved by the driver's
    // own element: exactly one layer per resource is on the page at a time.
    wrapper = mount(SceneBackdrop, { ...REAL, props: { art: ART_PANEL_SAMPLE } });
    const urls = renderedUrls(wrapper);
    expect(new Set(urls).size).toBe(urls.length);
  });
});
