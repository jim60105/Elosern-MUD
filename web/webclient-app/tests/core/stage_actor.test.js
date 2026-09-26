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
});
