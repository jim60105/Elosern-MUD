// webclient-dialogue-stage-actors (design D1): StageActor stands one
// portrait on the stage. It wraps ReferenceArtwork, draws the truthful
// placeholder from the name when no entry exists, exposes its side and its
// static speaking state as data attributes, dims the listener through the
// shared `--actor-dim` token, and carries no focusable element.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import StageActor from "../../components/StageActor.vue";

const HOST_ENTRY = {
  subject_key: "npc_41",
  status: "done",
  url: "/art/portraits/npc_41.webp",
  aspect_ratio: "3:4",
  alt: "灰婆婆的肖像",
  placeholder: null,
  face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
  context: { name: "灰婆婆", role: "對話對象" },
};

const PENDING_ENTRY = {
  ...HOST_ENTRY,
  status: "pending",
  url: null,
  aspect_ratio: null,
  face_rect: null,
  placeholder: { kind: "missing", label: "肖像圖像尚未生成" },
};

describe("StageActor", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("preserves the supplied image and accessible actor identity", () => {
    wrapper = mount(StageActor, { props: { portrait: HOST_ENTRY, name: "灰婆婆", side: "right" } });
    const root = wrapper.get('[data-testid="stage-actor"]');
    expect(root.attributes("data-side")).toBe("right");
    const img = wrapper.get('[data-testid="reference-artwork"] img');
    expect(img.attributes("src")).toBe("/art/portraits/npc_41.webp");
    expect(wrapper.get("figcaption").text()).toBe("灰婆婆");
    expect(wrapper.find('[data-testid="reference-artwork__placeholder"]').exists()).toBe(false);
  });

  it("states pending availability separately from actor identity", () => {
    wrapper = mount(StageActor, { props: { portrait: PENDING_ENTRY, name: "灰婆婆", side: "right" } });
    expect(wrapper.find("img").exists()).toBe(false);
    const card = wrapper.get('[data-testid="reference-artwork__placeholder"]');
    expect(wrapper.get("figure").attributes("data-status")).toBe("pending");
    expect(wrapper.get("figcaption").text()).toBe("灰婆婆，肖像生成中");
    expect(card.attributes("aria-hidden")).toBe("true");
    expect(card.get(".reference-artwork__placeholder-glyph").text()).toBe("灰");
  });

  it("uses the catalog identity when no explicit name is known", () => {
    wrapper = mount(StageActor, { props: { portrait: PENDING_ENTRY } });
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("灰");
  });

  it("draws the name's initial and the name when no entry exists", () => {
    wrapper = mount(StageActor, { props: { portrait: null, name: "合成·旅人", side: "right" } });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("合");
    expect(wrapper.get("figcaption").text()).toBe("合成·旅人，無肖像");
    expect(wrapper.get("figure").attributes("data-status")).toBe("missing");
  });

  it("keeps the whole astral-plane initial of a name", () => {
    wrapper = mount(StageActor, { props: { portrait: null, name: "𠮟婆婆" } });
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("𠮟");
  });

  it("does not promise generation without an entry or identity", () => {
    wrapper = mount(StageActor, { props: { portrait: null } });
    expect(wrapper.get("figure").attributes("data-status")).toBe("missing");
    expect(wrapper.get("figcaption").text()).toBe("無肖像");
  });

  it("exposes the speaking state and dims the listener through the shared token", async () => {
    wrapper = mount(StageActor, { props: { portrait: HOST_ENTRY, side: "left", dimmed: false } });
    const root = wrapper.get('[data-testid="stage-actor"]');
    expect(root.attributes("data-speaking")).toBe("true");
    await wrapper.setProps({ dimmed: true });
    expect(root.attributes("data-speaking")).toBe("false");

  });

  it("carries no focusable element", () => {
    wrapper = mount(StageActor, { props: { portrait: HOST_ENTRY, name: "灰婆婆" } });
    expect(wrapper.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);
  });

  it("keeps missing, pending and failed authoritative across motion changes", async () => {
    wrapper = mount(StageActor, { props: { name: "旅人", motionLevel: "full" } });
    const state = () => wrapper.get("figure").attributes("data-status");
    expect(state()).toBe("missing");
    await wrapper.setProps({ portrait: PENDING_ENTRY });
    expect(state()).toBe("pending");
    for (const motionLevel of ["reduced", "off", "full"]) {
      await wrapper.setProps({ motionLevel });
      expect(state()).toBe("pending");
      expect(wrapper.get("figcaption").text()).toBe("旅人，肖像生成中");
    }
    await wrapper.setProps({ portrait: { ...PENDING_ENTRY, status: "failed" } });
    expect(state()).toBe("failed");
    expect(wrapper.get("figcaption").text()).toBe("旅人，肖像生成失敗");
  });

  it("reports a failed image without promising generation and recovers on a new URL", async () => {
    wrapper = mount(StageActor, { props: { portrait: HOST_ENTRY, name: "旅人" } });
    await wrapper.get("img").trigger("error");
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get("figure").attributes("data-status")).toBe("load-failed");
    expect(wrapper.get("figcaption").text()).toBe("旅人，肖像載入失敗");
    await wrapper.setProps({ portrait: { ...HOST_ENTRY, url: "/art/repaired.webp" } });
    expect(wrapper.get("img").attributes("src")).toBe("/art/repaired.webp");
    expect(wrapper.get("figure").attributes("data-status")).toBe("done");
  });

  // webclient-combat-beat-choreography (design D4): the combat beat gestures.
  describe("beat gestures", () => {
    const beat = () => wrapper.get('[data-testid="stage-actor"] > .stage-actor__beat');

    it("renders the rest state with no gesture", () => {
      wrapper = mount(StageActor, { props: { portrait: HOST_ENTRY, side: "right" } });
      expect(beat().attributes("data-beat")).toBeUndefined();
      expect(wrapper.find('[data-testid="stage-actor-float"]').exists()).toBe(false);
      // The portrait still stands inside the wrapper.
      expect(beat().find('[data-testid="reference-artwork"] img').exists()).toBe(true);
    });

    it("re-keys the gesture wrapper per step, so the same gesture restarts", async () => {
      wrapper = mount(StageActor, {
        props: { portrait: HOST_ENTRY, side: "right", gesture: "hit", gestureKey: "s-1/1:1", floatAmount: 12 },
      });
      const first = beat().element;
      expect(beat().attributes("data-beat")).toBe("hit");
      // The same step keeps its element (the animation runs once).
      await wrapper.setProps({ floatAmount: 12 });
      expect(beat().element).toBe(first);
      // The next step's hit on the same figure is a new element.
      await wrapper.setProps({ gestureKey: "s-1/1:2", floatAmount: 18 });
      expect(beat().element).not.toBe(first);
      expect(beat().attributes("data-beat")).toBe("hit");
      // Back to rest: the attribute drops, and the wrapper (with the portrait
      // inside it) is kept rather than remounted for the rest phase.
      const hit = beat().element;
      await wrapper.setProps({ gesture: null, gestureKey: null, floatAmount: null });
      expect(beat().attributes("data-beat")).toBeUndefined();
      expect(beat().element).toBe(hit);
      expect(wrapper.find('[data-testid="stage-actor-float"]').exists()).toBe(false);
      // The next gesture re-keys it again.
      await wrapper.setProps({ gesture: "lunge", gestureKey: "s-1/1:4" });
      expect(beat().element).not.toBe(hit);
      expect(beat().attributes("data-beat")).toBe("lunge");
    });

    it("raises a decorative damage number on a hit only", async () => {
      wrapper = mount(StageActor, {
        props: { portrait: HOST_ENTRY, side: "right", gesture: "hit", gestureKey: "s-1/1:1", floatAmount: 12 },
      });
      const float = wrapper.get('[data-testid="stage-actor-float"]');
      expect(float.text()).toBe("−12");
      expect(float.attributes("aria-hidden")).toBe("true");
      await wrapper.setProps({ gesture: "lunge" });
      expect(wrapper.find('[data-testid="stage-actor-float"]').exists()).toBe(false);
      expect(wrapper.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);
    });

  });
});
