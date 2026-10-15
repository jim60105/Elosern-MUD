// Scene display retention and provisional resolution (change
// unified-scene-rendering, tasks.md 1.3/1.7).
//
// The rules under test are exactly the shared contract's: a scene keeps a
// previously successful image only while the backend still authorizes that
// source FOR THIS logical place and generation subject; a lower-priority
// healthy fallback never displaces it; the scene's own bundled/terminal
// background may be requested outside the ordered walk while a preferred
// source is still loading, and its outcome is reused — never re-requested — at
// its own precedence position.
import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick, ref } from "vue";
import { artworkFailureCategory } from "../lib/artwork-failure.js";
import SceneBackdrop from "../components/SceneBackdrop.vue";
import { useArtwork } from "../composables/useArtwork.js";
import {
  displayedScene,
  retainedEntry,
} from "../lib/scene-artwork.js";
import {
  ART_PANEL_PENDING_SAMPLE,
  ART_PANEL_SAMPLE,
  SCENE_PLACE,
  SCENE_SUBJECT,
  sceneBlock,
  sceneBundledResource,
  sceneDescriptor,
  sceneResource,
} from "../stories/fixtures.js";
import {
  displayedUrl,
  observeError,
  observeLoad,
  panelWithScene,
  renderedUrls,
} from "./support/scene_layers.js";

const REAL = { global: { stubs: { transition: false, "transition-group": false } } };

const GENERATED_URL = "/art/scene/river_dawn.png?v=" + "a".repeat(64);
const BUNDLED_URL = sceneBundledResource("river_dawn").url;
const RETAINED_URL = "/art/scene/river_dawn_known_good.png";

function descriptor(overrides = {}) {
  return sceneDescriptor({
    attempts: [
      {
        type: "image",
        source_id: `scene.generated:${SCENE_SUBJECT}`,
        rank: 20,
        resource: sceneResource({ url: GENERATED_URL, version: "a".repeat(64) }),
      },
      {
        type: "image",
        source_id: "scene.bundled:river_dawn",
        rank: 40,
        resource: sceneBundledResource("river_dawn"),
      },
    ],
    terminal: null,
    ...overrides,
  });
}

function panel(overrides = {}) {
  return panelWithScene(sceneBlock({}, descriptor(overrides)));
}

// One descriptor whose FIRST position is an authored room override: the
// operator image at rank 10 in front of the same generated/bundled positions.
const ROOM_URL = "/art/official/" + "e".repeat(64) + "/room/t_synth_room/a.png";

function panelWithRoomBinding(overrides = {}) {
  return panelWithScene(
    sceneBlock(
      {},
      descriptor({
        attempts: [
          {
            type: "image",
            source_id: "scene.room:t_synth_room",
            rank: 10,
            resource: {
              resource_id: "room/t_synth_room/a.png",
              version: "e".repeat(64),
              url: ROOM_URL,
              origin: "official",
              geometry: { image_size: null, face_rect: null, stage: null, aspect_ratio: null },
            },
          },
          {
            type: "image",
            source_id: `scene.generated:${SCENE_SUBJECT}`,
            rank: 20,
            resource: sceneResource({ url: GENERATED_URL, version: "a".repeat(64) }),
          },
          {
            type: "image",
            source_id: "scene.bundled:river_dawn",
            rank: 40,
            resource: sceneBundledResource("river_dawn"),
          },
        ],
        terminal: null,
        ...overrides,
      }),
    ),
  );
}

// The same place without the room binding: the chain continues to the
// generated artwork and then to the bundled illustration.
function panelWithoutRoomBinding() {
  return panelWithScene(
    sceneBlock(
      {},
      descriptor({
        attempts: [
          {
            type: "image",
            source_id: `scene.generated:${SCENE_SUBJECT}`,
            rank: 20,
            resource: sceneResource({ url: GENERATED_URL, version: "a".repeat(64) }),
          },
          {
            type: "image",
            source_id: "scene.bundled:river_dawn",
            rank: 40,
            resource: sceneBundledResource("river_dawn"),
          },
        ],
        terminal: null,
      }),
    ),
  );
}

// A selected result as the shared driver reports one.
function selected(sourceId, rank, url) {
  return { sourceId, rank, url, key: `${url}@v`, resourceId: url, version: "v", geometry: null, dimensions: { width: 16, height: 9 } };
}

// Two animation frames and a macrotask: long enough for Vue to end a leave
// whose computed duration jsdom reports as zero.
async function frames() {
  await new Promise((resolve) => setTimeout(resolve, 60));
  await nextTick();
}

describe("scene retention rules (pure)", () => {
  it("keeps retained content only for the same place and an authorized source", () => {
    const art = descriptor();
    const previous = {
      subjectId: SCENE_PLACE,
      generationSubject: SCENE_SUBJECT,
      sourceId: `scene.generated:${SCENE_SUBJECT}`,
      token: descriptor().retention_sources[0].token,
      rank: 20,
      url: RETAINED_URL,
    };
    // The same place + the same authorization keeps the pixels.
    expect(retainedEntry(previous, art, null)?.url).toBe(RETAINED_URL);
    // A different logical place drops them, whatever else matches.
    const moved = { ...art, subject_id: "grid:t_synth_map:1,1" };
    expect(retainedEntry(previous, moved, null)).toBe(null);
    // A different generation subject (a different scene archetype) drops them.
    const otherScene = { ...art, generation_subject: "scene:t_synth_other" };
    expect(retainedEntry(previous, otherScene, null)).toBe(null);
    // A revoked authorization (a new token) drops them.
    const revoked = {
      ...art,
      retention_sources: [{ source_id: previous.sourceId, token: "f".repeat(64) }],
    };
    expect(retainedEntry(previous, revoked, null)).toBe(null);
    // A scene that claims no generation at all cannot inherit pixels.
    const malformed = { ...art, generation_subject: null, retention_sources: [] };
    expect(retainedEntry(previous, malformed, null)).toBe(null);
  });

  it("does not let a lower-priority success displace retained content", () => {
    const art = descriptor();
    const retained = {
      subjectId: SCENE_PLACE,
      generationSubject: SCENE_SUBJECT,
      sourceId: `scene.generated:${SCENE_SUBJECT}`,
      token: art.retention_sources[0].token,
      rank: 20,
      url: RETAINED_URL,
    };
    // The bundled fallback (rank 40) is NOT retained over the rank-20 image.
    const afterFallback = retainedEntry(
      retained,
      art,
      selected("scene.bundled:river_dawn", 40, BUNDLED_URL),
    );
    expect(afterFallback.rank).toBe(20);
    expect(afterFallback.url).toBe(RETAINED_URL);
    // …and it never reaches the screen while the retained image stands.
    expect(
      displayedScene({
        retained: afterFallback,
        selected: selected("scene.bundled:river_dawn", 40, BUNDLED_URL),
        available: "ready",
      }).url,
    ).toBe(RETAINED_URL);
    // A same-priority replacement wins.
    const replacement = selected(`scene.generated:${SCENE_SUBJECT}`, 20, GENERATED_URL);
    expect(displayedScene({ retained: afterFallback, selected: replacement, available: "ready" }).url).toBe(
      GENERATED_URL,
    );
  });

  it("shows nothing at all when the required panel cannot provide data", () => {
    const retained = {
      subjectId: SCENE_PLACE,
      generationSubject: SCENE_SUBJECT,
      sourceId: `scene.generated:${SCENE_SUBJECT}`,
      token: descriptor().retention_sources[0].token,
      rank: 20,
      url: RETAINED_URL,
    };
    expect(
      displayedScene({
        retained,
        selected: selected("scene.generated:" + SCENE_SUBJECT, 20, GENERATED_URL),
        available: "failed",
      }),
    ).toBe(null);
  });
});

describe("the loading core's provisional scene background", () => {
  it("fetches the scene's own bundled resource once and reuses it at its position", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    // The requested generated source (rank 20) is still loading, so the
    // provisional bundled resource (rank 40) is fetched out of band.
    const driver = useArtwork(
      ref(descriptor()),
      ref({ state: "ready" }),
      { provisionalSource: ref(sceneBundledResource("river_dawn")) },
    );
    expect(driver.attempt.value?.url).toBe(GENERATED_URL);
    expect(driver.provisionalAttempt.value?.url).toBe(BUNDLED_URL);
    // The ordered walk knows the resource is in flight, so reaching it parks
    // rather than issuing a second request.
    expect(driver.provisionalAttempt.value.key).toContain("bundled-scene/river_dawn");
    driver.dispose();
  });
});

describe("SceneBackdrop retention and provisional behaviour", () => {
  let wrapper;

  function mountBackdrop(props = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(SceneBackdrop, { ...REAL, attachTo: host, props: { art: panel(), ...props } });
    return wrapper;
  }

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  it("shows the scene's own provisional background while the preferred source is delayed", async () => {
    wrapper = mountBackdrop();
    // Both resources are being fetched, and neither is displayed yet.
    expect(new Set(renderedUrls(wrapper))).toEqual(new Set([GENERATED_URL, BUNDLED_URL]));
    expect(displayedUrl(wrapper)).toBe(null);
    // The provisional bundled background arrives first and takes the stage.
    await observeLoad(wrapper, BUNDLED_URL);
    expect(displayedUrl(wrapper)).toBe(BUNDLED_URL);
    // The preferred source then wins and replaces it without another request
    // for either resource.
    await observeLoad(wrapper, GENERATED_URL);
    await frames();
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
    expect(renderedUrls(wrapper)).toEqual([GENERATED_URL]);
  });

  it("keeps a provisional failure latent until its own position is reached", async () => {
    wrapper = mountBackdrop();
    await observeError(wrapper, BUNDLED_URL);
    // The failed provisional source is not a reached fault while the preferred
    // source is still loading: nothing is displayed, no error is claimed, and
    // no badge claims absence either — the stage is simply still resolving.
    expect(wrapper.find('[data-testid="scene-backdrop-placeholder"]').exists()).toBe(false);
    expect(displayedUrl(wrapper)).toBe(null);
    await observeLoad(wrapper, GENERATED_URL);
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
    const chip = wrapper.find('[data-testid="scene-backdrop-failure"]');
    expect(chip.exists() ? chip.text() : null).toBe(null);
  });

  it("records a provisional failure once — and only once — at its own position", async () => {
    wrapper = mountBackdrop();
    await observeError(wrapper, BUNDLED_URL);
    await observeError(wrapper, GENERATED_URL);
    await frames();
    // The provisional outcome is reused at its precedence position: the
    // bundled resource is never requested again.
    expect(renderedUrls(wrapper)).toEqual([]);
    expect(wrapper.get('[data-testid="scene-backdrop-placeholder"]').attributes("data-kind")).toBe(
      "image_load_failed",
    );
  });

  it("changes nothing on a mode-only commit and does not re-request the image", async () => {
    wrapper = mountBackdrop();
    await observeLoad(wrapper, GENERATED_URL);
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
    await wrapper.setProps({ mode: "combat" });
    await wrapper.setProps({ motionLevel: "reduced" });
    await frames();
    // Identical artwork, identical bitmap: no new layer, no new fetch.
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
    expect(renderedUrls(wrapper)).toEqual([GENERATED_URL]);
  });

  it("never keeps a previous place's pixels across a delayed move", async () => {
    wrapper = mountBackdrop();
    await observeLoad(wrapper, GENERATED_URL);
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
    const movedPlace = panelWithScene(
      sceneBlock(
        {},
        descriptor({
          subject_id: "grid:t_synth_map:1,1",
          retention_sources: [
            { source_id: `scene.generated:${SCENE_SUBJECT}`, token: "b".repeat(64) },
          ],
        }),
      ),
    );
    await wrapper.setProps({ art: movedPlace });
    await frames();
    // The retained authorization belonged to the OLD place, so the pixels are
    // discarded at commit; only the new place's own resources are fetched.
    expect(displayedUrl(wrapper)).toBe(null);
    expect(renderedUrls(wrapper)).toEqual([GENERATED_URL, BUNDLED_URL]);
  });

  it("keeps a good generated image while the same scene regenerates, over a healthy fallback", async () => {
    wrapper = mountBackdrop();
    await observeLoad(wrapper, GENERATED_URL);
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
    // The same place and generation subject commits a pending regeneration:
    // no generated candidate at all, and only the bundled fallback to try.
    await wrapper.setProps({ art: ART_PANEL_PENDING_SAMPLE });
    await flushPromises();
    // The retained pixels are still the ones on screen, with factual progress.
    await observeLoad(wrapper, BUNDLED_URL);
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
    expect(wrapper.get('[data-testid="scene-backdrop-generating"]').text()).toBe("目前場景圖片生成中");
    expect(wrapper.find('[data-testid="scene-backdrop-failure"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="scene-backdrop-placeholder"]').exists()).toBe(false);
  });

  it("drops retained pixels on the commit that revokes their authorization", async () => {
    wrapper = mountBackdrop();
    await observeLoad(wrapper, GENERATED_URL);
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
    // The same place and generation subject now commit a pending regeneration
    // whose retained authorization carries a NEW token: the backend no longer
    // vouches for the output this browser is holding, so those pixels must go
    // even though the logical place has not changed.
    const revoked = panelWithScene(
      sceneBlock(
        {},
        descriptor({
          generation_state: "pending",
          attempts: [
            {
              type: "image",
              source_id: "scene.bundled:river_dawn",
              rank: 40,
              resource: sceneBundledResource("river_dawn"),
            },
          ],
          retention_sources: [
            { source_id: `scene.generated:${SCENE_SUBJECT}`, token: "c".repeat(64) },
          ],
        }),
      ),
    );
    await wrapper.setProps({ art: revoked });
    await frames();
    expect(displayedUrl(wrapper)).toBe(null);
    expect(renderedUrls(wrapper)).toEqual([BUNDLED_URL]);
  });

  it("discards retained pixels and states the availability failure synchronously", async () => {
    wrapper = mountBackdrop();
    await observeLoad(wrapper, GENERATED_URL);
    await wrapper.setProps({ art: { available: false, reason: { code: "art_unavailable", message: "場景圖像目前無法顯示" } } });
    await frames();
    expect(displayedUrl(wrapper)).toBe(null);
    expect(renderedUrls(wrapper)).toEqual([]);
    expect(wrapper.get('[data-testid="scene-backdrop-placeholder"]').attributes("data-kind")).toBe(
      "panel_unavailable",
    );
  });

  it("reuses a provisional failure observed under a higher-priority success", async () => {
    // The room override is the preferred source and the bundled illustration is
    // the provisional one. The provisional FAILS first (latently), then the
    // room image wins.
    wrapper = mountBackdrop({ art: panelWithRoomBinding() });
    await observeError(wrapper, BUNDLED_URL);
    await observeLoad(wrapper, ROOM_URL);
    await frames();
    expect(displayedUrl(wrapper)).toBe(ROOM_URL);
    const requestsBefore = renderedUrls(wrapper);
    expect(requestsBefore).not.toContain(BUNDLED_URL);

    // The binding is removed for the SAME place: the chain now walks the
    // generated artwork and, once that fails in the browser too, reaches the
    // bundled illustration at its own position and reuses the observed failure
    // — it is never requested a second time, and the reached fault is stated.
    await wrapper.setProps({ art: panelWithoutRoomBinding() });
    await observeError(wrapper, GENERATED_URL);
    await frames();
    expect(renderedUrls(wrapper)).not.toContain(BUNDLED_URL);
    expect(
      wrapper.get('[data-testid="scene-backdrop-placeholder"]').attributes("data-kind"),
    ).toBe("image_load_failed");
  });

  it("states the pending progress AND the reached failure at once", async () => {
    // A retained good image whose generation is pending while a lower source
    // has already been reached and failed: both facts are true, so both are
    // stated — the failure once, and the progress independently.
    wrapper = mountBackdrop({
      art: panelWithScene(
        sceneBlock(
          {},
          descriptor({
            generation_state: "pending",
            attempts: [
              {
                type: "fault",
                source_id: `scene.operator:${SCENE_SUBJECT}`,
                rank: 30,
                reason: "metadata_invalid",
              },
              {
                type: "image",
                source_id: "scene.bundled:river_dawn",
                rank: 40,
                resource: sceneBundledResource("river_dawn"),
              },
            ],
            terminal: null,
          }),
        ),
      ),
    });
    wrapper.vm.setPriorImage(RETAINED_URL);
    await frames();
    expect(displayedUrl(wrapper)).toBe(RETAINED_URL);
    expect(wrapper.get('[data-testid="scene-backdrop-generating"]').text()).toBe(
      "目前場景圖片生成中",
    );
    expect(wrapper.get('[data-testid="scene-backdrop-failure"]').text()).toBe(
      artworkFailureCategory("metadata_invalid"),
    );
    // ONE failure indication: the badge belongs to the states with no bitmap.
    expect(wrapper.find('[data-testid="scene-backdrop-placeholder"]').exists()).toBe(false);
  });

  it("does not inherit a previous scene's provisional observation", async () => {
    // Scene A observes the bundled resource failing.
    wrapper = mountBackdrop();
    await observeError(wrapper, BUNDLED_URL);
    await frames();
    expect(renderedUrls(wrapper)).not.toContain(BUNDLED_URL);
    // Scene B is a DIFFERENT logical place with the same resources: the
    // observation belonged to A, so B fetches its own provisional background.
    await wrapper.setProps({
      art: panel({ subject_id: "grid:t_synth_map:7,7" }),
    });
    await frames();
    expect(renderedUrls(wrapper)).toContain(BUNDLED_URL);
    // Returning to A must not resurrect A's retired observation either.
    await observeError(wrapper, BUNDLED_URL);
    await wrapper.setProps({
      art: panel({ subject_id: "grid:t_synth_map:8,8" }),
    });
    await frames();
    await wrapper.setProps({ art: panel() });
    await frames();
    expect(renderedUrls(wrapper)).toContain(BUNDLED_URL);
  });

  it("settles a resource whose element is already complete", async () => {
    // A commit can re-issue a load for a resource the element already holds
    // (the browser cached it, or a re-resolution followed the first paint). No
    // second load event ever arrives, so the component reports the element's
    // own completeness instead of leaving the resolution parked.
    wrapper = mountBackdrop();
    const layer = wrapper.findAll("img").find((img) => img.attributes("src") === GENERATED_URL);
    Object.defineProperty(layer.element, "complete", { value: true, configurable: true });
    Object.defineProperty(layer.element, "naturalWidth", { value: 1536, configurable: true });
    Object.defineProperty(layer.element, "naturalHeight", { value: 864, configurable: true });
    // A fresh commit re-issues the load for the SAME resource (its facts
    // changed, its bytes did not): the element is already complete, so no new
    // load event can arrive and the component reports what the element holds.
    await wrapper.setProps({
      art: panel({ subject_id: "grid:t_synth_map:5,5", revision: "e".repeat(64) }),
    });
    await frames();
    expect(displayedUrl(wrapper)).toBe(GENERATED_URL);
  });

  it("ignores a late load event from a retired element", async () => {
    wrapper = mountBackdrop();
    const stale = wrapper.findAll("img").find((img) => img.attributes("src") === BUNDLED_URL);
    // The place moves before that element settles: the new place resolves its
    // own resources, so the retired element's late event belongs to no
    // resolution and must settle nothing.
    await wrapper.setProps({
      art: panelWithScene(
        sceneBlock(
          {},
          descriptor({
            subject_id: "grid:t_synth_map:2,2",
            retention_sources: [],
            attempts: [
              {
                type: "image",
                source_id: `scene.generated:${SCENE_SUBJECT}`,
                rank: 20,
                resource: sceneResource({
                  version: "d".repeat(64),
                  url: "/art/scene/other_place.png?v=" + "d".repeat(64),
                }),
              },
            ],
          }),
        ),
      ),
    });
    await frames();
    Object.defineProperty(stale.element, "naturalWidth", { value: 16, configurable: true });
    Object.defineProperty(stale.element, "naturalHeight", { value: 9, configurable: true });
    await stale.trigger("load");
    await frames();
    // The retired element's event settled nothing: nothing is presented.
    expect(displayedUrl(wrapper)).toBe(null);
  });
});
