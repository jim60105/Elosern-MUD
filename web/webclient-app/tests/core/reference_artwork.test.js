import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ReferenceArtwork from "../../components/ReferenceArtwork.vue";
import {
  artworkDescriptor,
  artworkResource,
  artworkTerminal,
} from "../../stories/fixtures/art_panels.js";

// The frame's position: a committed panel that admits the descriptor. The
// renderer judges a descriptor against the panel it came from, so every mount
// here carries the committed available panel too.
const PANEL = { schema_version: 3, available: true };

// jsdom reports naturalWidth/naturalHeight 0 for every image, and the shared
// lifecycle reads the decoded dimensions off the element: a load is only a
// success once the element declares a real size.
function declareImage(element, width = 768, height = 1024) {
  Object.defineProperty(element, "naturalWidth", { value: width, configurable: true });
  Object.defineProperty(element, "naturalHeight", { value: height, configurable: true });
}

// One descriptor with a single resolved runtime candidate.
const candidateDescriptor = (overrides = {}) =>
  artworkDescriptor({
    subject_id: "portrait:character:1",
    generation_subject: "portrait:character:1",
    generation_state: "done",
    ...overrides,
  });

// One descriptor whose real candidate is the given resource.
const withCandidate = (resource, overrides = {}) =>
  candidateDescriptor({
    attempts: [
      { type: "image", source_id: "portrait.default:1", rank: 30, resource },
    ],
    ...overrides,
  });

describe("reference artwork gallery consumption", () => {
  it("renders the committed portrait with its face-rect crop offset", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        artwork: withCandidate(
          artworkResource({
            resource_id: "portrait/character/actor.webp",
            url: "/art/portraits/actor.webp",
            geometry: {
              image_size: null,
              face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
              stage: { scale: 1, x: 0, y: 0 },
              aspect_ratio: "3:4",
            },
          }),
        ),
        panel: PANEL,
        name: "艾琳的肖像",
      },
    });
    const img = wrapper.get("img");
    expect(img.attributes("src")).toBe("/art/portraits/actor.webp");
    expect(img.element.style.objectPosition).toBe("50% 31%");
    expect(wrapper.find('[data-testid="reference-artwork__placeholder"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("renders a truthful placeholder without an img when no candidate resolves", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        artwork: candidateDescriptor({
          generation_state: "pending",
          attempts: [],
          terminal: null,
        }),
        panel: PANEL,
        name: "艾琳的肖像",
      },
    });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get('[data-testid="reference-artwork__placeholder"]').text()).toContain("肖像生成中");
    // One state line: the placeholder's label is not repeated as a caption.
    expect(wrapper.find("figcaption").exists()).toBe(false);
    expect(wrapper.text().split("肖像生成中")).toHaveLength(2);
    wrapper.unmount();
  });

  it("never claims a generation state the descriptor does not carry", () => {
    const cases = [
      // An intentional no-reference position: no claim at all.
      [{ artwork: null, hasReference: false }, "無肖像"],
      // An admitted row with a factual null state.
      [{ artwork: candidateDescriptor({ generation_subject: null, generation_state: null, attempts: [], terminal: null }) }, "無肖像"],
      [{ artwork: candidateDescriptor({ generation_state: "pending", attempts: [], terminal: null }) }, "肖像生成中"],
      [{ artwork: candidateDescriptor({ generation_state: "failed", attempts: [], terminal: null }) }, "肖像生成失敗"],
    ];
    for (const [props, label] of cases) {
      const wrapper = mount(ReferenceArtwork, { props: { panel: PANEL, initialOf: "艾莉亞", ...props } });
      expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe(label);
      expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("艾");
      wrapper.unmount();
    }
  });

  it("falls back to a truthful placeholder on load failure and accepts a new source afterwards", async () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        artwork: withCandidate(
          artworkResource({
            resource_id: "portrait/character/broken.webp",
            url: "/art/portraits/broken.webp",
            geometry: {
              image_size: null,
              face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
              stage: { stage: 1, x: 0, y: 0 },
              aspect_ratio: "3:4",
            },
          }),
          // No terminal: the one broken candidate is the whole chain, so its
          // failure exhausts the position.
          { terminal: null },
        ),
        panel: PANEL,
        name: "舊肖像",
      },
    });
    await wrapper.get("img").trigger("error");
    // The failed attempt is stepped past (no retry loop) and the truthful
    // placeholder takes over; the reached fault keeps its local marker.
    expect(wrapper.get('[data-testid="reference-artwork__placeholder"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="artwork-failure"]').exists()).toBe(true);
    // A newly committed source renders with its own face-rect offset.
    await wrapper.setProps({
      artwork: withCandidate(
        artworkResource({
          resource_id: "portrait/character/replacement.webp",
          url: "/art/portraits/replacement.webp",
          geometry: {
            image_size: null,
            face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
            stage: { scale: 1, x: 0, y: 0 },
            aspect_ratio: "3:4",
          },
        }),
      ),
    });
    const img = wrapper.get("img");
    expect(img.attributes("src")).toBe("/art/portraits/replacement.webp");
    expect(img.element.style.objectPosition).toBe("50% 30%");
    wrapper.unmount();
  });

  it("draws the placeholder initial as a whole grapheme, even outside the BMP", () => {
    // An astral-plane initial (U+20B9F 𠮟) is a surrogate pair: slicing one
    // code unit would draw half of it (webclient-dialogue-stage-actors D1).
    const wrapper = mount(ReferenceArtwork, {
      props: { artwork: null, panel: PANEL, initialOf: "𠮟婆婆" },
    });
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("𠮟");
    wrapper.unmount();
  });

  it("draws the identity glyph when a required panel admits no reference", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: { artwork: null, panel: PANEL, hasReference: false, initialOf: "灰婆婆" },
    });
    // An intentional no-reference is expected absence: the identity glyph
    // stands with NO local failure marker.
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("灰");
    expect(wrapper.find('[data-testid="artwork-failure"]').exists()).toBe(false);
    wrapper.unmount();
  });
});

// builtin-silhouette-stage-fallback: the stage draws the descriptor's own
// alpha terminal as the committed image's mask, in place of the former inline
// SVG, and keeps every label outside it.
describe("stage silhouette mask", () => {
  const ALPHA = '[data-testid="artwork-alpha"]';
  const ALPHA_FILL = '[data-testid="artwork-alpha-fill"]';
  const maskedKey = (wrapper) =>
    wrapper.get(ALPHA_FILL).element.style.getPropertyValue("--artwork-alpha-mask");
  const terminal = (key) =>
    artworkTerminal({
      source_id: `portrait.alpha:${key}`,
      resource: artworkResource({
        resource_id: `defaults/${key}.webp`,
        version: `v-${key}`.padEnd(64, "0"),
        url: `/art/defaults/${key}.webp`,
        origin: "silhouette",
        geometry: {
          image_size: null,
          face_rect: { x: 0.35, y: 0.02, w: 0.28, h: 0.16 },
          stage: null,
          aspect_ratio: "3:4",
        },
      }),
    });
  // A descriptor with no real candidate: the terminal is the presented figure.
  const silhouetteEntry = (key, overrides = {}) =>
    artworkDescriptor({
      subject_id: "portrait:character:7",
      generation_subject: "portrait:character:7",
      generation_state: "missing",
      attempts: [],
      terminal: terminal(key),
      ...overrides,
    });
  // The same descriptor with a real candidate that precedes the terminal.
  const resolvedEntry = (overrides = {}) =>
    artworkDescriptor({
      subject_id: "portrait:character:7",
      generation_subject: "portrait:character:7",
      generation_state: "done",
      attempts: [
        {
          type: "image",
          source_id: "portrait.default:1",
          rank: 30,
          resource: artworkResource({
            resource_id: "portrait/character/x.webp",
            url: "/art/portrait/x.webp",
          }),
        },
      ],
      ...overrides,
    });
  const mountStage = async (artwork, props = {}) => {
    const wrapper = mount(ReferenceArtwork, {
      props: { artwork, panel: PANEL, name: "灰婆婆", initialOf: "灰婆婆", stage: true, ...props },
    });
    // The presented resource's own element carries the load signal.
    const img = wrapper.get("img");
    declareImage(img.element);
    await img.trigger("load");
    return wrapper;
  };

  it("renders each built-in key's own mask identity and no inline SVG", async () => {
    const keys = ["man", "woman", "boy", "girl", "elder", "monster_anon"];
    const identities = new Set();
    for (const key of keys) {
      const wrapper = await mountStage(silhouetteEntry(key));
      expect(maskedKey(wrapper)).toBe(`url('/art/defaults/${key}.webp')`);
      expect(wrapper.find("svg").exists()).toBe(false);
      expect(wrapper.get(ALPHA).exists()).toBe(true);
      identities.add(maskedKey(wrapper));
      wrapper.unmount();
    }
    // Never one shared shape for every missing actor.
    expect(identities.size).toBe(keys.length);
  });

  it("paints nothing until the carried identity has loaded", async () => {
    const wrapper = mount(ReferenceArtwork, {
      props: { artwork: silhouetteEntry("woman"), panel: PANEL, stage: true },
    });
    expect(wrapper.find(ALPHA_FILL).exists()).toBe(false);
    declareImage(wrapper.get("img").element);
    await wrapper.get("img").trigger("load");
    expect(wrapper.find(ALPHA_FILL).exists()).toBe(true);
    expect(maskedKey(wrapper)).toBe("url('/art/defaults/woman.webp')");
    wrapper.unmount();
  });

  it("keeps the actor name and the truthful label when the terminal fails", async () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        artwork: silhouetteEntry("man"),
        panel: PANEL,
        name: "灰婆婆",
        initialOf: "灰婆婆",
        stage: true,
      },
    });
    await wrapper.get("img").trigger("error");
    expect(wrapper.find(ALPHA).exists()).toBe(false);
    expect(wrapper.find("svg").exists()).toBe(false);
    const card = wrapper.get('[data-testid="reference-artwork__placeholder"]');
    expect(card.text()).toContain("灰婆婆");
    // The terminal itself failed to load, so the local fact is a load failure
    // rather than an absent portrait.
    expect(card.text()).toContain("肖像載入失敗");
    expect(wrapper.get("figure").attributes("data-status")).toBe("load-failed");
    // A persistent local indication explains the failure.
    expect(wrapper.get('[data-testid="artwork-failure"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it("renders text only and no svg when no identity is carried", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        artwork: artworkDescriptor({
          generation_state: "pending",
          attempts: [],
          terminal: null,
        }),
        panel: PANEL,
        stage: true,
      },
    });
    expect(wrapper.find("svg").exists()).toBe(false);
    expect(wrapper.find(ALPHA).exists()).toBe(false);
    expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe("肖像生成中");
    wrapper.unmount();
  });

  it("returns to the carried terminal when the real image fails, with no refetch", async () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        artwork: resolvedEntry(),
        panel: PANEL,
        name: "旅人",
        initialOf: "旅人",
        stage: true,
      },
    });
    expect(wrapper.get("img").attributes("src")).toBe("/art/portrait/x.webp");
    expect(wrapper.find(ALPHA).exists()).toBe(false);
    await wrapper.get("img").trigger("error");
    // The failed candidate is stepped past: the descriptor's own terminal
    // becomes the presented resource, on its own element.
    expect(wrapper.get("img").attributes("src")).toBe("/art/defaults/man.webp");
    expect(wrapper.get("figure").attributes("data-status")).toBe("load-failed");
    declareImage(wrapper.get("img").element);
    await wrapper.get("img").trigger("load");
    expect(maskedKey(wrapper)).toBe("url('/art/defaults/man.webp')");
    expect(wrapper.text()).toContain("肖像載入失敗");
    expect(wrapper.text()).not.toContain("已生成");
    wrapper.unmount();
  });

  it("keeps the name and state labels outside the decorative mask", async () => {
    const wrapper = await mountStage(silhouetteEntry("elder"));
    expect(wrapper.get(ALPHA).element.querySelector(".reference-artwork__chest")).toBe(null);
    const chest = wrapper.get(".reference-artwork__chest");
    expect(chest.text()).toContain("灰婆婆");
    expect(chest.text()).toContain("無肖像");
    expect(wrapper.get("figcaption").text()).toBe("灰婆婆，無肖像");
    wrapper.unmount();
  });

  it("keeps the pending shimmer's level contract on the masked figure", async () => {
    const wrapper = await mountStage(
      silhouetteEntry("girl", { generation_state: "pending" }),
    );
    const figure = wrapper.get("figure");
    expect(figure.attributes("data-status")).toBe("pending");
    expect(figure.attributes("data-motion")).toBe("full");
    await wrapper.setProps({ motionLevel: "off" });
    expect(wrapper.get("figure").attributes("data-motion")).toBe("off");
    expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe("肖像生成中");
    wrapper.unmount();
  });

  it("leaves the cover surface free of the silhouette", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        artwork: resolvedEntry(),
        panel: PANEL,
        name: "肖像",
      },
    });
    expect(wrapper.find(ALPHA).exists()).toBe(false);
    expect(wrapper.find("svg").exists()).toBe(false);
    expect(wrapper.get("img").element.style.objectPosition).toBe("50% 31%");
    wrapper.unmount();
  });

  it("re-arms the mask when the carried identity changes on a live frame", async () => {
    // A failure must not suppress a LATER identity: a new resource identity
    // re-arms the resolution, so a re-pushed descriptor paints again.
    const wrapper = mount(ReferenceArtwork, {
      props: {
        artwork: silhouetteEntry("man"),
        panel: PANEL,
        name: "灰婆婆",
        initialOf: "灰婆婆",
        stage: true,
      },
    });
    declareImage(wrapper.get("img").element);
    await wrapper.get("img").trigger("load");
    expect(maskedKey(wrapper)).toBe("url('/art/defaults/man.webp')");
    await wrapper.setProps({ artwork: silhouetteEntry("girl") });
    expect(wrapper.get("img").attributes("src")).toBe("/art/defaults/girl.webp");
    expect(wrapper.find(ALPHA_FILL).exists()).toBe(false, "the new identity loads first");
    declareImage(wrapper.get("img").element);
    await wrapper.get("img").trigger("load");
    expect(maskedKey(wrapper)).toBe("url('/art/defaults/girl.webp')");
    wrapper.unmount();
  });
});
