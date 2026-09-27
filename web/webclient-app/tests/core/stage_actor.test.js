// webclient-dialogue-stage-actors (design D1): StageActor stands one
// portrait on the stage. It wraps ReferenceArtwork, draws the truthful
// placeholder from the name when no entry exists, exposes its side and its
// static speaking state as data attributes, dims the listener through the
// shared `--actor-dim` token, and carries no focusable element.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import StageActor from "../../components/StageActor.vue";

const APP_ROOT = join(process.cwd(), "web/webclient-app");

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

  it("renders the entry's image with its face-rect crop", () => {
    wrapper = mount(StageActor, { props: { portrait: HOST_ENTRY, name: "灰婆婆", side: "right" } });
    const root = wrapper.get('[data-testid="stage-actor"]');
    expect(root.attributes("data-side")).toBe("right");
    const img = wrapper.get('[data-testid="reference-artwork"] img');
    expect(img.attributes("src")).toBe("/art/portraits/npc_41.webp");
    expect(img.element.style.objectPosition).toBe("50% 31%");
    expect(wrapper.find('[data-testid="reference-artwork__placeholder"]').exists()).toBe(false);
  });

  it("shows a pending entry's own placeholder label with the name's initial in the ring", () => {
    wrapper = mount(StageActor, { props: { portrait: PENDING_ENTRY, name: "灰婆婆", side: "right" } });
    expect(wrapper.find("img").exists()).toBe(false);
    const card = wrapper.get('[data-testid="reference-artwork__placeholder"]');
    expect(card.get(".reference-artwork__placeholder-label").text()).toBe("肖像圖像尚未生成");
    expect(card.get(".reference-artwork__placeholder-glyph").text()).toBe("灰");
  });

  it("keeps the entry label's initial when no name is known", () => {
    wrapper = mount(StageActor, { props: { portrait: PENDING_ENTRY } });
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("肖");
  });

  it("draws the name's initial and the name when no entry exists", () => {
    wrapper = mount(StageActor, { props: { portrait: null, name: "合成·旅人", side: "right" } });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("合");
    expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe("合成·旅人");
  });

  it("keeps the whole astral-plane initial of a name", () => {
    wrapper = mount(StageActor, { props: { portrait: null, name: "𠮟婆婆" } });
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("𠮟");
  });

  it("falls back to ReferenceArtwork's own placeholder with neither entry nor name", () => {
    wrapper = mount(StageActor, { props: { portrait: null } });
    expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe("肖像生成中");
  });

  it("exposes the speaking state and dims the listener through the shared token", async () => {
    wrapper = mount(StageActor, { props: { portrait: HOST_ENTRY, side: "left", dimmed: false } });
    const root = wrapper.get('[data-testid="stage-actor"]');
    expect(root.attributes("data-speaking")).toBe("true");
    await wrapper.setProps({ dimmed: true });
    expect(root.attributes("data-speaking")).toBe("false");

    const source = readFileSync(join(APP_ROOT, "components/StageActor.vue"), "utf-8");
    const rule = source.match(/\.stage-actor\[data-speaking="false"\]\s*\{[^}]*\}/);
    expect(rule && rule[0]).toContain("filter: brightness(var(--actor-dim))");
    // The dim is a static state: the motion layer owns any transition.
    expect(rule && rule[0]).not.toContain("transition");
    const tokens = readFileSync(join(APP_ROOT, "styles/tokens.css"), "utf-8");
    expect(tokens).toMatch(/--actor-dim:\s*0\.6;/);
  });

  it("carries no focusable element", () => {
    wrapper = mount(StageActor, { props: { portrait: HOST_ENTRY, name: "灰婆婆" } });
    expect(wrapper.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);
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

    it("steps toward the centre by side and takes every duration from the beat tokens", () => {
      const source = readFileSync(join(APP_ROOT, "components/StageActor.vue"), "utf-8");
      const rule = (selector) => {
        const escaped = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
        const match = source.match(new RegExp(`${escaped}\\s*\\{([^}]*)\\}`));
        return match ? match[1] : "";
      };
      expect(rule('.stage-actor[data-side="left"] > [data-beat="lunge"]')).toContain(
        "elosern-beat-lunge-right var(--motion-beat-step)",
      );
      expect(rule('.stage-actor[data-side="right"] > [data-beat="lunge"]')).toContain(
        "elosern-beat-lunge-left var(--motion-beat-step)",
      );
      expect(rule('.stage-actor > [data-beat="hit"]')).toContain("elosern-beat-hit var(--motion-beat-hit)");
      expect(rule('.stage-actor > [data-beat="defeat"]')).toMatch(
        /elosern-beat-defeat var\(--motion-beat-defeat\)[^;]*forwards/,
      );
      expect(rule(".stage-actor__float")).toMatch(/elosern-beat-float var\(--motion-beat-float\)[^;]*forwards/);
      expect(rule(".stage-actor__float")).toContain("pointer-events: none");
    });
  });
});
