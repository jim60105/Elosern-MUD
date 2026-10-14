// Focused lifecycle tests for the shared local resource driver and its first
// production consumer, the gallery face-rectangle original editor
// (change unified-image-loading-core). The driver cases use a minimal harness
// component; the editor cases mount the real GalleryFaceRectModal over the
// committed gallery rows.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { defineComponent, h, onBeforeUnmount, ref } from "vue";
import ArtworkFailure from "../../components/ArtworkFailure.vue";
import GalleryFaceRectModal from "../../components/GalleryFaceRectModal.vue";
import { useImageAttempts } from "../../composables/useImageAttempts.js";
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
