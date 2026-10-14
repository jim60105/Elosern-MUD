// Focused lifecycle tests for the shared local resource driver and the gallery
// original editors that consume it (changes unified-image-loading-core,
// unified-gallery-image-contract and unified-gallery-original-editors). The
// driver cases use a minimal harness component; the editor cases mount the real
// GalleryFaceRectModal and GalleryStageTransformModal over the committed
// gallery rows.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, h, onBeforeUnmount, ref } from "vue";
import ArtworkFailure from "../../components/ArtworkFailure.vue";
import GalleryFaceRectModal from "../../components/GalleryFaceRectModal.vue";
import GalleryStageTransformModal from "../../components/GalleryStageTransformModal.vue";
import { useImageAttempts } from "../../composables/useImageAttempts.js";
import { useOriginalEligibility } from "../../composables/useOriginalEligibility.js";
import { canonicalOrder } from "../../lib/image-attempts.js";
import { GALLERY_SAMPLE } from "../../stories/gallery-fixtures.js";

const wrappers = [];
function mountSurface(component, props) {
  const wrapper = mount(component, { props, attachTo: document.body });
  wrappers.push(wrapper);
  return wrapper;
}
function button(wrapper, text) {
  return wrapper.findAll("button").find((item) => item.text() === text);
}
afterEach(() => {
  wrappers.reverse().forEach((wrapper) => wrapper.unmount());
  wrappers.length = 0;
  document.body.replaceChildren();
});

const READY = { state: "ready", view_subject_id: "subject" };

// One single-source normalized internal request; `version` is the resource
// identity/version key, so a new version is a repaired source.
function singleRequest(url, { epoch = 1, version = url, rank = 10, geometry = null } = {}) {
  return {
    subjectId: "subject",
    epoch,
    attempts: [{
      type: "image",
      source_id: `original:${url}`,
      rank,
      resource: { resource_id: url, version, url, origin: "runtime", geometry },
    }],
    terminal: null,
  };
}

const Harness = defineComponent({
  props: {
    request: { type: Object, default: null },
    availability: { type: Object, default: () => ({ ...READY }) },
    provisional: { type: Object, default: null },
  },
  setup(props, { expose }) {
    const driver = useImageAttempts(
      () => props.request,
      () => props.availability,
      { provisional: () => props.provisional },
    );
    onBeforeUnmount(() => driver.dispose());
    expose({ driver });
    return () => {
      const attempt = driver.attempt.value;
      const selected = driver.selected.value;
      return h("div", [
        attempt?.url
          ? h("img", {
              key: attempt.token,
              src: attempt.url,
              "data-attempt-token": attempt.token,
              onLoad: driver.onImageLoad,
              onError: driver.onImageError,
            })
          : null,
        h("span", { class: "phase" }, driver.phase.value),
        h("span", { class: "dims" }, driver.dimensions.value ? `${driver.dimensions.value.width}x${driver.dimensions.value.height}` : ""),
        h("span", { class: "eligible" }, String(driver.saveEligible.value)),
        h("span", { class: "unavailable" }, String(driver.panelUnavailable.value)),
        h("span", { class: "faults" }, driver.reachedFaults.value.map((fault) => `${fault.sourceId}:${fault.reason}`).join(",")),
        h("span", { class: "geometry" }, JSON.stringify(selected?.geometry ?? null)),
      ]);
    };
  },
});

function declareImage(element, width, height) {
  Object.defineProperty(element, "naturalWidth", { value: width, configurable: true });
  Object.defineProperty(element, "naturalHeight", { value: height, configurable: true });
}

describe("useImageAttempts local driver", () => {
  it("starts unavailable on the first render without issuing a request", () => {
    const wrapper = mountSurface(Harness, {
      request: singleRequest("/art/a.webp"),
      availability: { state: "failed", view_subject_id: "subject" },
    });
    expect(wrapper.get(".unavailable").text()).toBe("true");
    expect(wrapper.get(".eligible").text()).toBe("false");
    expect(wrapper.get(".phase").text()).toBe("exhausted");
    expect(wrapper.find("img").exists()).toBe(false);
  });

  it("treats expected absence as a normal, non-error absence", () => {
    const wrapper = mountSurface(Harness, {
      request: singleRequest("/art/a.webp"),
      availability: { state: "expected_absent", view_subject_id: "subject" },
    });
    expect(wrapper.get(".unavailable").text()).toBe("false");
    expect(wrapper.get(".phase").text()).toBe("exhausted");
    expect(wrapper.find("img").exists()).toBe(false);
  });

  it("invalidates a success when availability turns failed", async () => {
    const wrapper = mountSurface(Harness, { request: singleRequest("/art/a.webp"), availability: { ...READY } });
    const img = wrapper.get("img");
    declareImage(img.element, 100, 200);
    await img.trigger("load");
    expect(wrapper.get(".phase").text()).toBe("success");
    expect(wrapper.get(".eligible").text()).toBe("true");
    expect(wrapper.get(".dims").text()).toBe("100x200");

    await wrapper.setProps({ availability: { state: "failed", view_subject_id: "subject" } });
    expect(wrapper.get(".unavailable").text()).toBe("true");
    expect(wrapper.get(".eligible").text()).toBe("false");
    expect(wrapper.find("img").exists()).toBe(false);
  });

  it("re-renders an unchanged descriptor without a new request and keeps the reached failure", async () => {
    const wrapper = mountSurface(Harness, { request: singleRequest("/art/a.webp"), availability: { ...READY } });
    const img = wrapper.get("img");
    await img.trigger("error");
    expect(wrapper.get(".faults").text()).toBe("original:/art/a.webp:image_load_failed");
    expect(wrapper.get(".phase").text()).toBe("exhausted");

    // An identical-facts request object must not restart resolution.
    await wrapper.setProps({ request: singleRequest("/art/a.webp") });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".phase").text()).toBe("exhausted");
    expect(wrapper.get(".faults").text()).toBe("original:/art/a.webp:image_load_failed");
  });

  it("rejects a retired subject's stale decode after a replacement", async () => {
    const wrapper = mountSurface(Harness, { request: singleRequest("/art/a.webp"), availability: { ...READY } });
    const first = wrapper.get("img");
    declareImage(first.element, 768, 1024);

    await wrapper.setProps({ request: singleRequest("/art/b.webp", { epoch: 2 }) });
    const second = wrapper.get("img");
    expect(second.element).not.toBe(first.element);

    // A late decode from the retired element cannot touch the new subject.
    await first.trigger("load");
    expect(wrapper.get(".dims").text()).toBe("");
    expect(wrapper.get(".phase").text()).toBe("loading");

    declareImage(second.element, 10, 20);
    await second.trigger("load");
    expect(wrapper.get(".dims").text()).toBe("10x20");
    expect(wrapper.get(".phase").text()).toBe("success");
  });

  it("binds each event to the attempt that created its element, even at an identical URL", async () => {
    // A same-resource, new-epoch revision must still start a real load (a fresh
    // element, so the browser re-requests), and the retired element's late
    // event must not settle it.
    const wrapper = mountSurface(Harness, { request: singleRequest("/art/a.webp"), availability: { ...READY } });
    const first = wrapper.get("img");
    declareImage(first.element, 768, 1024);
    await first.trigger("load");
    expect(wrapper.get(".phase").text()).toBe("success");

    await wrapper.setProps({ request: singleRequest("/art/a.webp", { epoch: 2 }) });
    const second = wrapper.get("img");
    expect(second.element).not.toBe(first.element);
    expect(second.attributes("data-attempt-token")).not.toBe(first.attributes("data-attempt-token"));
    expect(wrapper.get(".phase").text()).toBe("loading");
    expect(wrapper.get(".dims").text()).toBe("");
    expect(wrapper.get(".eligible").text()).toBe("false");

    // The retired element's late load and error are both rejected.
    await first.trigger("load");
    await first.trigger("error");
    expect(wrapper.get(".phase").text()).toBe("loading");
    expect(wrapper.get(".dims").text()).toBe("");
    expect(wrapper.get(".faults").text()).toBe("");

    declareImage(second.element, 30, 40);
    await second.trigger("load");
    expect(wrapper.get(".phase").text()).toBe("success");
    expect(wrapper.get(".dims").text()).toBe("30x40");
  });

  it("treats a load with unusable natural dimensions as a decode failure", async () => {
    const wrapper = mountSurface(Harness, { request: singleRequest("/art/a.webp"), availability: { ...READY } });
    const img = wrapper.get("img");
    // A load event with no decodable size (the browser reports zero for an
    // undecodable body) is an observed decode failure, not a success.
    await img.trigger("load");
    expect(wrapper.get(".phase").text()).toBe("exhausted");
    expect(wrapper.get(".eligible").text()).toBe("false");
    expect(wrapper.get(".faults").text()).toBe("original:/art/a.webp:image_decode_failed");
  });

  it("reuses decoded bytes on a geometry-only update with no request", async () => {
    const wrapper = mountSurface(Harness, {
      request: singleRequest("/art/a.webp", { geometry: { face_rect: { x: 0, y: 0, w: 1, h: 1 } } }),
      availability: { ...READY },
    });
    const img = wrapper.get("img");
    declareImage(img.element, 768, 1024);
    await img.trigger("load");
    const element = img.element;

    await wrapper.setProps({
      request: singleRequest("/art/a.webp", { geometry: { face_rect: { x: 0.5, y: 0.5, w: 0.25, h: 0.25 } } }),
    });
    // Same resource identity/version: the element is not recreated, so no
    // source request or crossfade happens, and the known dimensions survive.
    expect(wrapper.get("img").element).toBe(element);
    expect(wrapper.get(".phase").text()).toBe("success");
    expect(wrapper.get(".dims").text()).toBe("768x1024");
    expect(wrapper.get(".geometry").text()).toContain('"x":0.5');
  });

  it("disposes listeners on teardown so a late callback changes nothing", async () => {
    const wrapper = mountSurface(Harness, { request: singleRequest("/art/a.webp"), availability: { ...READY } });
    const img = wrapper.get("img");
    declareImage(img.element, 50, 60);
    wrapper.vm.driver.dispose();
    await wrapper.vm.$nextTick();
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".phase").text()).toBe("exhausted");
    await img.trigger("load");
    expect(wrapper.get(".phase").text()).toBe("exhausted");
    expect(wrapper.get(".dims").text()).toBe("");
  });

  it("parks on a delayed preferred source and resumes when the provisional map changes", async () => {
    const A = { resource_id: "a", version: "v1", url: "/art/a.webp", origin: "runtime", geometry: null };
    const B = { resource_id: "b", version: "v1", url: "/art/b.webp", origin: "runtime", geometry: null };
    const request = {
      subjectId: "subject",
      epoch: 1,
      attempts: [
        { type: "image", source_id: "preferred", rank: 10, resource: A },
        { type: "image", source_id: "fallback", rank: 20, resource: B },
      ],
      terminal: null,
    };
    const wrapper = mountSurface(Harness, {
      request,
      availability: { ...READY },
      provisional: new Map([
        ["a@v1", { epoch: 1, phase: "loading" }],
        ["b@v1", { epoch: 1, phase: "failed", reason: "image_load_failed" }],
      ]),
    });
    // The preferred source is still loading: no fallback request yet.
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".faults").text()).toBe("");

    await wrapper.setProps({
      provisional: new Map([
        ["a@v1", { epoch: 1, phase: "failed", reason: "image_load_failed" }],
        ["b@v1", { epoch: 1, phase: "success", dimensions: { width: 6, height: 6 } }],
      ]),
    });
    expect(wrapper.get(".phase").text()).toBe("success");
    expect(wrapper.get(".dims").text()).toBe("6x6");
    expect(wrapper.get(".faults").text()).toBe("preferred:image_load_failed");
    expect(wrapper.get("img").attributes("src")).toBe("/art/b.webp");
  });

  it("takes the newest provisional snapshot when it changes during a real request", async () => {
    const A = { resource_id: "a", version: "v1", url: "/art/a.webp", origin: "runtime", geometry: null };
    const B = { resource_id: "b", version: "v1", url: "/art/b.webp", origin: "runtime", geometry: null };
    const request = {
      subjectId: "subject",
      epoch: 1,
      attempts: [
        { type: "image", source_id: "preferred", rank: 10, resource: A },
        { type: "image", source_id: "fallback", rank: 20, resource: B },
      ],
      terminal: null,
    };
    const wrapper = mountSurface(Harness, {
      request,
      availability: { ...READY },
      provisional: new Map([["b@v1", { epoch: 1, phase: "loading" }]]),
    });
    // The preferred source is a real in-flight DOM request.
    const img = wrapper.get("img");
    expect(img.attributes("src")).toBe("/art/a.webp");

    // The fallback's provisional outcome arrives while A is still loading.
    await wrapper.setProps({
      provisional: new Map([["b@v1", { epoch: 1, phase: "success", dimensions: { width: 6, height: 6 } }]]),
    });
    expect(wrapper.get(".phase").text()).toBe("loading");

    // A's failure then resolves against the fresh snapshot, not the stale one.
    await img.trigger("error");
    expect(wrapper.get(".phase").text()).toBe("success");
    expect(wrapper.get(".dims").text()).toBe("6x6");
    expect(wrapper.get(".faults").text()).toBe("preferred:image_load_failed");
  });
});

describe("face-rect original editor lifecycle", () => {
  const PANEL = GALLERY_SAMPLE;
  const CARD = GALLERY_SAMPLE.cards[0];
  // One exact-original row in the v3 shape the editor reads: the media URL and
  // the committed rectangle live inside the row's own canonical descriptor.
  function row(imageId, rect = CARD.artwork.attempts[0].resource.geometry.face_rect, revision = CARD.artwork.revision) {
    const next = structuredClone(CARD);
    next.image_id = imageId;
    const candidate = next.artwork.attempts[0].resource;
    candidate.resource_id = `gallery/character/7001/${imageId}.webp`;
    candidate.url = `/art/gallery/character/7001/${imageId}.webp`;
    candidate.geometry.face_rect = { ...rect };
    next.artwork.revision = revision;
    return next;
  }
  const OTHER = row("10000000-0000-4000-8000-000000000002");

  it("keeps a loading or failed original unsaveable and removes the broken image", async () => {
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: CARD });
    // Loading: no save, no crop preview yet.
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeDefined();
    expect(wrapper.get(".gallery-face__original > img").exists()).toBe(true);
    expect(wrapper.find(".gallery-face__preview img").exists()).toBe(false);

    await wrapper.get(".gallery-face__original > img").trigger("error");
    // Failed: the broken original and its crop are gone, the local explanation
    // persists, and saving stays impossible.
    expect(wrapper.find(".gallery-face__original > img").exists()).toBe(false);
    expect(wrapper.find(".gallery-face__preview img").exists()).toBe(false);
    const marker = wrapper.get('[data-testid="artwork-failure"]');
    expect(marker.attributes("role")).toBe("status");
    expect(marker.text()).toContain("圖片載入失敗");
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeDefined();
    expect(wrapper.emitted("submit")).toBeUndefined();
  });

  it("cannot restore save eligibility from a retired original's late decode and recovers on a new exact original", async () => {
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: CARD });
    const first = wrapper.get(".gallery-face__original > img");
    declareImage(first.element, 768, 1024);
    await first.trigger("load");
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeUndefined();

    // A new exact original arrives: the retired element's late decode must not
    // re-enable saving, and the new resource loads on its own.
    await wrapper.setProps({ card: OTHER });
    expect(wrapper.get(".gallery-face__original > img").element).not.toBe(first.element);
    await first.trigger("load");
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeDefined();

    const second = wrapper.get(".gallery-face__original > img");
    declareImage(second.element, 512, 512);
    await second.trigger("load");
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeUndefined();
    await button(wrapper, "儲存框選").trigger("click");
    expect(wrapper.emitted("submit")).toHaveLength(1);
    expect(Object.keys(wrapper.emitted("submit")[0][0])).toEqual(["face_rect"]);
  });

  it("seeds a replacement original's crop from its own committed rectangle", async () => {
    const REPLACEMENT = row("10000000-0000-4000-8000-000000000003", { x: 0.1, y: 0.1, w: 0.2, h: 0.2 });
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: CARD });
    const first = wrapper.get(".gallery-face__original > img");
    declareImage(first.element, 768, 1024);
    await first.trigger("load");
    // The first original's own committed rectangle is the seed.
    await button(wrapper, "儲存框選").trigger("click");
    expect(wrapper.emitted("submit")[0][0].face_rect.w).toBeCloseTo(0.5);

    await wrapper.setProps({ card: REPLACEMENT });
    const second = wrapper.get(".gallery-face__original > img");
    declareImage(second.element, 512, 512);
    await second.trigger("load");
    await button(wrapper, "儲存框選").trigger("click");
    const payload = wrapper.emitted("submit")[1][0].face_rect;
    // Seeded from the replacement's committed rect, not the retired draft.
    expect(payload.x).toBeCloseTo(0.1);
    expect(payload.y).toBeCloseTo(0.1);
    expect(payload.w).toBeCloseTo(0.2);
    expect(payload.h).toBeCloseTo(0.2);
  });

  it("reuses the decoded original on a geometry-only committed change", async () => {
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: CARD });
    const img = wrapper.get(".gallery-face__original > img");
    declareImage(img.element, 768, 1024);
    await img.trigger("load");
    const element = img.element;

    // Same image id and url, a different committed rectangle: no refetch.
    await wrapper.setProps({ card: row(CARD.image_id, { x: 0.2, y: 0.2, w: 0.4, h: 0.3 }, "f".repeat(64)) });
    expect(wrapper.get(".gallery-face__original > img").element).toBe(element);
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeUndefined();
    await button(wrapper, "儲存框選").trigger("click");
    const payload = wrapper.emitted("submit")[0][0];
    expect(Math.abs(payload.face_rect.w * 768 - payload.face_rect.h * 1024)).toBeLessThanOrEqual(1);
  });

  it("preserves numeric draft editing, the pixel-square payload and Escape cancel", async () => {
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: CARD });
    const img = wrapper.get(".gallery-face__original > img");
    declareImage(img.element, 768, 1024);
    await img.trigger("load");

    await wrapper.get('input[aria-label="寬度"]').setValue(0.2);
    expect(Number(wrapper.get('input[aria-label="高度"]').element.value)).toBeCloseTo(0.15);
    await button(wrapper, "儲存框選").trigger("click");
    const payload = wrapper.emitted("submit")[0][0];
    expect(Object.keys(payload)).toEqual(["face_rect"]);
    expect(payload.face_rect.w).toBeCloseTo(0.2);
    expect(payload.face_rect.h).toBeCloseTo(0.15);

    const cancel = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: CARD });
    await cancel.get('[role="dialog"]').trigger("keydown", { key: "Escape" });
    expect(cancel.emitted("close")).toHaveLength(1);
    expect(cancel.emitted("submit")).toBeUndefined();
  });

  it("tells a loading original apart from a failed one", async () => {
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: CARD });
    // Loading: its own sentence and its own indicator, never the failure one.
    expect(wrapper.text()).toContain("原始圖片載入中，暫時無法儲存框選。");
    expect(wrapper.text()).not.toContain("原始圖片載入失敗，無法儲存框選。");
    expect(wrapper.find('[data-testid="artwork-failure"]').exists()).toBe(false);

    await wrapper.get(".gallery-face__original > img").trigger("error");
    // Failed: the loading frame is gone and the persistent failure frame, with
    // its own bounded text, is what remains.
    expect(wrapper.text()).not.toContain("原始圖片載入中，暫時無法儲存框選。");
    expect(wrapper.text()).toContain("原始圖片載入失敗，無法儲存框選。");
    const marker = wrapper.get('[data-testid="artwork-failure"]');
    expect(marker.attributes("role")).toBe("status");
    expect(marker.text()).toContain("圖片載入失敗");
    // A failed original may still be drafted numerically, but never saved.
    await wrapper.get('input[aria-label="寬度"]').setValue(0.2);
    await button(wrapper, "儲存框選").trigger("click");
    expect(wrapper.emitted("submit")).toBeUndefined();
  });

  it("keeps a decoded proof and the player's draft across a harmless republish", async () => {
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: CARD });
    const img = wrapper.get(".gallery-face__original > img");
    declareImage(img.element, 768, 1024);
    await img.trigger("load");
    await wrapper.get('input[aria-label="寬度"]').setValue(0.3);

    // The same original republished: same resource identity, so no reload, no
    // re-seeded draft and no lost eligibility.
    await wrapper.setProps({ card: row(CARD.image_id) });
    expect(wrapper.get(".gallery-face__original > img").element).toBe(img.element);
    expect(Number(wrapper.get('input[aria-label="寬度"]').element.value)).toBeCloseTo(0.3);
    expect(Number(wrapper.get('input[aria-label="高度"]').element.value)).toBeCloseTo(0.225);
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeUndefined();
    await button(wrapper, "儲存框選").trigger("click");
    expect(wrapper.emitted("submit")).toHaveLength(1);
  });

  it("never turns a silhouette terminal into the edit target", async () => {
    // The row's descriptor permits a silhouette but carries no exact original:
    // the editor's request excludes the terminal, so there is nothing to
    // measure and nothing to save.
    const silhouette = structuredClone(CARD);
    silhouette.artwork.attempts = [];
    silhouette.image_id = "10000000-0000-4000-8000-00000000000f";
    const wrapper = mountSurface(GalleryFaceRectModal, { panel: PANEL, card: silhouette });
    expect(wrapper.find(".gallery-face__original > img").exists()).toBe(false);
    expect(wrapper.find(".gallery-face__preview img").exists()).toBe(false);
    expect(button(wrapper, "儲存框選").attributes("disabled")).toBeDefined();
    expect(wrapper.text()).toContain("這張肖像沒有可編輯的原始圖片，無法儲存框選。");
    await button(wrapper, "儲存框選").trigger("click");
    expect(wrapper.emitted("submit")).toBeUndefined();
  });
});

// The gate both editors hand their save to. Its own harness drives the same
// reads the editors make: a live descriptor, the driver's phase and the
// driver's observed dimensions.
const GateHarness = defineComponent({
  props: { artwork: { type: Object, default: null } },
  setup(props, { expose }) {
    const artwork = ref(props.artwork);
    const phase = ref("exhausted");
    const dimensions = ref(null);
    const gate = useOriginalEligibility(artwork, phase, dimensions, null);
    // Driving state through the harness's own methods keeps the reads and the
    // writes on the same refs the gate holds. The gate's answers are read
    // through the composable itself — synchronously, without waiting for a
    // render — because that is exactly what the editors' save handlers do.
    expose({
      decoded: () => gate.decoded.value,
      saveReady: () => gate.saveReady.value,
      setArtwork: (value) => { artwork.value = value; },
      setPhase: (value) => { phase.value = value; },
      setDimensions: (value) => { dimensions.value = value; },
      read: () => ({ phase: phase.value, dimensions: dimensions.value }),
    });
    return () => h("span");
  },
});

describe("exact-original eligibility gate", () => {
  function original(imageId, version = "a".repeat(64)) {
    return {
      subject_id: `portrait:character:7001:${imageId}`,
      revision: "0".repeat(64),
      attempts: [{
        type: "image",
        source_id: `gallery.original:${imageId}`,
        rank: 10,
        resource: {
          resource_id: `gallery/character/7001/${imageId}.webp`,
          version,
          url: `/art/gallery/character/7001/${imageId}.webp`,
          origin: "runtime",
          geometry: null,
        },
      }],
      terminal: null,
    };
  }
  const A = original("10000000-0000-4000-8000-00000000000a");
  const B = original("10000000-0000-4000-8000-00000000000b");

  it("retires a decoded proof the moment the live descriptor changes", () => {
    const wrapper = mountSurface(GateHarness, { artwork: A });
    const gate = wrapper.vm;
    gate.setPhase("success");
    gate.setDimensions({ width: 768, height: 1024 });
    expect(gate.saveReady()).toBe(true);

    // The live descriptor becomes another exact original while the driver still
    // reports the retired success: the very next synchronous read refuses.
    gate.setArtwork(B);
    expect(gate.read()).toEqual({ phase: "success", dimensions: { width: 768, height: 1024 } });
    expect(gate.decoded()).toBe(false);
    expect(gate.saveReady()).toBe(false);

    // Only the replacement's own decode authorizes it.
    gate.setPhase("loading");
    expect(gate.saveReady()).toBe(false);
    gate.setDimensions({ width: 512, height: 512 });
    gate.setPhase("success");
    expect(gate.saveReady()).toBe(true);

    // A geometry-only revision of the SAME original keeps the proof: the shared
    // lifecycle deliberately reuses those decoded bytes.
    gate.setArtwork({ ...B, revision: "f".repeat(64) });
    expect(gate.saveReady()).toBe(true);

    // A new resource version of the same card is a new original.
    gate.setArtwork(original("10000000-0000-4000-8000-00000000000b", "c".repeat(64)));
    expect(gate.saveReady()).toBe(false);
    wrapper.unmount();
  });

  it("never authorizes a save without a usable decoded size", () => {
    const wrapper = mountSurface(GateHarness, { artwork: A });
    const gate = wrapper.vm;
    gate.setPhase("success");
    expect(gate.saveReady()).toBe(false);
    gate.setDimensions({ width: 0, height: 0 });
    expect(gate.saveReady()).toBe(false);
    gate.setDimensions({ width: 768, height: 1024 });
    expect(gate.saveReady()).toBe(true);
    // A reported failure retires the proof even with a size still in hand.
    gate.setPhase("exhausted");
    expect(gate.saveReady()).toBe(false);
    wrapper.unmount();
  });

  it("never proves a descriptor that carries only a display substitute", () => {
    const silhouette = {
      ...A,
      attempts: [],
      terminal: {
        kind: "alpha_mask",
        source_id: "gallery.alpha:man",
        rank: 100,
        resource: {
          resource_id: "defaults/man.webp",
          version: "b".repeat(64),
          url: "/art/defaults/man.webp",
          origin: "silhouette",
          geometry: null,
        },
      },
    };
    const wrapper = mountSurface(GateHarness, { artwork: silhouette });
    wrapper.vm.setPhase("success");
    wrapper.vm.setDimensions({ width: 864, height: 1536 });
    expect(wrapper.vm.decoded()).toBe(false);
    expect(wrapper.vm.saveReady()).toBe(false);
    wrapper.unmount();
  });
});

describe("stage-transform original editor lifecycle", () => {
  const PANEL = GALLERY_SAMPLE;
  const CARD = GALLERY_SAMPLE.cards[0];
  const ADULT = ".stage-transform__adult";
  const RULER = ".stage-transform__ruler";
  const FIGURE = ".stage-transform__figure";
  const RULER_MARKER = '.stage-transform__ruler-status [data-testid="artwork-failure"]';
  function row(imageId, stage = { scale: 1, x: 0, y: 0 }, revision = CARD.artwork.revision) {
    const next = structuredClone(CARD);
    next.image_id = imageId;
    const candidate = next.artwork.attempts[0].resource;
    candidate.resource_id = `gallery/character/7001/${imageId}.webp`;
    candidate.url = `/art/gallery/character/7001/${imageId}.webp`;
    candidate.geometry.stage = { ...stage };
    next.artwork.revision = revision;
    return next;
  }
  const OTHER = row("10000000-0000-4000-8000-000000000002");
  // The ruler is observed through its own probe image, exactly like the shared
  // preview's silhouette probe: the masked fill paints the shape, the probe
  // carries only the ruler resource's own load or error signal.
  function rulerOf(wrapper) {
    return wrapper.get(RULER);
  }
  function figureOf(wrapper) {
    return wrapper.get(FIGURE);
  }
  // The footer's primary action is the one save control: its label changes
  // while a save is in flight, so it is addressed by its own class rather than
  // by text.
  function saveOf(wrapper) {
    return wrapper.get(".stage-transform__footer .gallery-primary");
  }
  async function loadFigure(wrapper, width = 768, height = 1024) {
    const figure = figureOf(wrapper);
    declareImage(figure.element, width, height);
    await figure.trigger("load");
    return figure;
  }

  it("observes the ruler separately and keeps a healthy original the save target", async () => {
    const wrapper = mountSurface(GalleryStageTransformModal, { panel: PANEL, card: CARD });
    // The ruler is its own subject with its own resource: the probe requests
    // the bundled adult reference, never the edited card's media.
    expect(rulerOf(wrapper).attributes("src")).toBe("/art/defaults/man.webp");
    expect(rulerOf(wrapper).attributes("aria-hidden")).toBe("true");
    expect(rulerOf(wrapper).attributes("src")).not.toBe(
      wrapper.get(FIGURE).attributes("src"),
    );
    expect(wrapper.get(ADULT).attributes("aria-hidden")).toBe("true");
    expect(wrapper.find(RULER_MARKER).exists()).toBe(false);

    // The ruler's own decode is what removes its fill on failure, and the
    // failure gets its own local, accessible indication.
    await rulerOf(wrapper).trigger("error");
    expect(wrapper.find(ADULT).exists()).toBe(false);
    const marker = wrapper.get(RULER_MARKER);
    expect(marker.attributes("role")).toBe("status");
    expect(marker.text()).toContain("圖片載入失敗");
    expect(wrapper.text()).toContain("成人身形參照無法載入");

    // The original is untouched by the ruler's failure: it still decodes with
    // real dimensions and remains the one save target.
    await loadFigure(wrapper);
    expect(saveOf(wrapper).attributes("disabled")).toBeUndefined();
    await saveOf(wrapper).trigger("click");
    expect(wrapper.emitted("submit")).toHaveLength(1);
    expect(wrapper.emitted("submit")[0][0]).toEqual({ stage: { scale: 1, x: 0, y: 0 } });
  });

  it("never lets a healthy ruler authorize saving a failed original", async () => {
    const wrapper = mountSurface(GalleryStageTransformModal, { panel: PANEL, card: CARD });
    await figureOf(wrapper).trigger("error");
    // The ruler itself decodes with usable dimensions...
    const ruler = rulerOf(wrapper);
    declareImage(ruler.element, 864, 1536);
    await ruler.trigger("load");
    expect(wrapper.find(RULER_MARKER).exists()).toBe(false);
    // ...and none of them reach the original: the editor cannot save, and the
    // failure explanation is the original's own.
    expect(wrapper.text()).toContain("圖片載入失敗，無法儲存調整。");
    expect(saveOf(wrapper).attributes("disabled")).toBeDefined();
    await saveOf(wrapper).trigger("click");
    expect(wrapper.emitted("submit")).toBeUndefined();
    expect(wrapper.find(FIGURE).exists()).toBe(false);
  });

  it("discards eligibility for a replacement published while a save is pending", async () => {
    const wrapper = mountSurface(GalleryStageTransformModal, { panel: PANEL, card: CARD });
    await loadFigure(wrapper);
    await saveOf(wrapper).trigger("click");
    expect(wrapper.emitted("submit")).toHaveLength(1);
    // The save is in flight: the editor is locked, so only a rejection can
    // hand it back to the player.
    expect(saveOf(wrapper).attributes("disabled")).toBeDefined();
    expect(saveOf(wrapper).text()).toBe("儲存中…");

    // A replacement arrives and the rejection unlocks the editor: the retired
    // original must not authorize a second dispatch for the new card.
    await wrapper.setProps({ card: OTHER, rejected: true });
    expect(saveOf(wrapper).attributes("disabled")).toBeDefined();
    await saveOf(wrapper).trigger("click");
    expect(wrapper.emitted("submit")).toHaveLength(1);

    // The replacement's own decode, and only that, enables the next save.
    await loadFigure(wrapper, 512, 512);
    expect(saveOf(wrapper).attributes("disabled")).toBeUndefined();
    await saveOf(wrapper).trigger("click");
    expect(wrapper.emitted("submit")).toHaveLength(2);
    expect(wrapper.emitted("submit")[1][0]).toEqual({ stage: { scale: 1, x: 0, y: 0 } });
  });
});

describe("ArtworkFailure mapping", () => {
  it("renders the bounded category for a reached failure and nothing for expected absence", () => {
    const failed = mountSurface(ArtworkFailure, { kind: "failure", reason: "image_decode_failed" });
    expect(failed.get('[data-testid="artwork-failure"]').text()).toContain("圖片無法解碼");
    const expected = mountSurface(ArtworkFailure, { kind: "expected", reason: null });
    expect(expected.find('[data-testid="artwork-failure"]').exists()).toBe(false);
    expect(expected.text()).toBe("");
    const loading = mountSurface(ArtworkFailure, { kind: "loading" });
    expect(loading.get('[data-testid="artwork-loading"]').exists()).toBe(true);
    const unknown = mountSurface(ArtworkFailure, { kind: "failure", reason: "totally_unknown" });
    expect(unknown.get('[data-testid="artwork-failure"]').text()).toContain("圖片無法顯示");
    expect(unknown.get('[data-testid="artwork-failure"]').text()).not.toContain("totally_unknown");
  });

  it("never invents a reached fault for an unpermitted candidate", () => {
    // A single permitted original with no terminal is the editor's whole
    // request shape: no extra resource and no extra fault enter the order.
    const order = canonicalOrder(singleRequest("/art/a.webp"));
    expect(order).toHaveLength(1);
    expect(order[0].terminal).toBeNull();
  });
});
