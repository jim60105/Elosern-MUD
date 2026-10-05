import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ReferenceArtwork from "../../components/ReferenceArtwork.vue";

describe("reference artwork gallery consumption", () => {
  it("renders the committed portrait with its face-rect crop offset", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        portrait: {
          url: "/art/portraits/actor.webp",
          alt: "艾琳的肖像",
          face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
        },
      },
    });
    const img = wrapper.get("img");
    expect(img.attributes("src")).toBe("/art/portraits/actor.webp");
    expect(img.element.style.objectPosition).toBe("50% 31%");
    expect(wrapper.get("figcaption").text()).toBe("艾琳的肖像");
    expect(wrapper.find('[data-testid="reference-artwork__placeholder"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it("renders a truthful placeholder without an img when no url resolves", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        portrait: { url: null, alt: "艾琳的肖像", face_rect: null, placeholder: { kind: "pending", label: "肖像生成中" } },
      },
    });
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get('[data-testid="reference-artwork__placeholder"]').text()).toContain("肖像生成中");
    // One state line: the placeholder's label is not repeated as a caption.
    expect(wrapper.find("figcaption").exists()).toBe(false);
    expect(wrapper.text().split("肖像生成中")).toHaveLength(2);
    wrapper.unmount();
  });

  it("never claims a pending portrait the payload does not carry", () => {
    const cases = [
      [null, "無肖像"],
      [{ url: null, status: null, placeholder: null }, "無肖像"],
      [{ url: null, status: "pending", placeholder: null }, "肖像生成中"],
      [{ url: null, status: "failed", placeholder: null }, "肖像生成失敗"],
    ];
    for (const [portrait, label] of cases) {
      const wrapper = mount(ReferenceArtwork, { props: { portrait, initialOf: "艾莉亞" } });
      expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe(label);
      expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("艾");
      wrapper.unmount();
    }
  });

  it("falls back to a truthful placeholder on load failure and accepts a new URL afterwards", async () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        portrait: { url: "/art/portraits/broken.webp", alt: "舊肖像", face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 } },
      },
    });
    await wrapper.get("img").trigger("error");
    // The failed image unmounts (no retry loop) and the placeholder takes over.
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get('[data-testid="reference-artwork__placeholder"]').exists()).toBe(true);
    // A newly committed URL renders with its own face-rect offset (recovery).
    await wrapper.setProps({
      portrait: { url: "/art/portraits/replacement.webp", alt: "新肖像", face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 } },
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
      props: { portrait: { placeholder: { kind: "missing", label: "𠮟婆婆" } } },
    });
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("𠮟");
    expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe("𠮟婆婆");
    wrapper.unmount();
  });

  it("draws the initial of `initialOf` when given, keeping the placeholder's own label", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: { portrait: { placeholder: { kind: "unavailable", label: "無肖像" } }, initialOf: "灰婆婆" },
    });
    expect(wrapper.get(".reference-artwork__placeholder-glyph").text()).toBe("灰");
    expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe("無肖像");
    wrapper.unmount();
  });
});

// builtin-silhouette-stage-fallback: the stage draws the server-selected
// built-in silhouette as the committed image's own alpha mask, in place of the
// former inline SVG, and keeps every label outside it.
describe("stage silhouette mask", () => {
  const MASK = '[data-testid="reference-artwork__mask"]';
  const MASK_FILL = ".reference-artwork__mask-fill";
  const PROBE = ".reference-artwork__mask-probe";
  const fallback = (key) => ({
    key,
    url: `/art/defaults/${key}.webp`,
    face_rect: { x: 0.35, y: 0.02, w: 0.28, h: 0.16 },
  });
  const silhouetteEntry = (key, overrides = {}) => ({
    subject_key: "portrait:character:7",
    status: "missing",
    url: null,
    aspect_ratio: null,
    alt: "無肖像",
    placeholder: { kind: "missing", label: "未生成" },
    face_rect: null,
    stage: null,
    origin: "silhouette",
    fallback: fallback(key),
    context: { name: "灰婆婆", role: "對話對象" },
    ...overrides,
  });
  const maskedKey = (wrapper) =>
    wrapper.get(MASK_FILL).element.style.getPropertyValue("--silhouette-mask");
  const mountStage = async (portrait, props = {}) => {
    const wrapper = mount(ReferenceArtwork, {
      props: { portrait, initialOf: "灰婆婆", stage: true, ...props },
    });
    await wrapper.get(PROBE).trigger("load");
    return wrapper;
  };

  it("renders each built-in key's own mask identity and no inline SVG", async () => {
    const keys = ["man", "woman", "boy", "girl", "elder", "monster_anon"];
    const identities = new Set();
    for (const key of keys) {
      const wrapper = await mountStage(silhouetteEntry(key));
      expect(maskedKey(wrapper)).toBe(`url('/art/defaults/${key}.webp')`);
      expect(wrapper.find("svg").exists()).toBe(false);
      expect(wrapper.get(MASK).attributes("aria-hidden")).toBe("true");
      identities.add(maskedKey(wrapper));
      wrapper.unmount();
    }
    // Never one shared shape for every missing actor.
    expect(identities.size).toBe(keys.length);
  });

  it("paints nothing until the carried identity has loaded", async () => {
    const wrapper = mount(ReferenceArtwork, {
      props: { portrait: silhouetteEntry("woman"), stage: true },
    });
    expect(wrapper.find(MASK_FILL).exists()).toBe(false);
    await wrapper.get(PROBE).trigger("load");
    expect(wrapper.find(MASK_FILL).exists()).toBe(true);
    expect(maskedKey(wrapper)).toBe("url('/art/defaults/woman.webp')");
    wrapper.unmount();
  });

  it("keeps the actor name and the truthful label when the bundled mask fails", async () => {
    const wrapper = mount(ReferenceArtwork, {
      props: { portrait: silhouetteEntry("man"), initialOf: "灰婆婆", stage: true },
    });
    await wrapper.get(PROBE).trigger("error");
    expect(wrapper.find(MASK).exists()).toBe(false);
    expect(wrapper.find("svg").exists()).toBe(false);
    const card = wrapper.get('[data-testid="reference-artwork__placeholder"]');
    expect(card.text()).toContain("灰婆婆");
    expect(card.text()).toContain("無肖像");
    expect(wrapper.get("figure").attributes("data-status")).toBe("missing");
    wrapper.unmount();
  });

  it("keeps the grounded standing silhouette when no identity is carried", () => {
    const wrapper = mount(ReferenceArtwork, {
      props: {
        portrait: { url: null, status: "pending", placeholder: { kind: "missing", label: "肖像生成中" } },
        stage: true,
      },
    });
    expect(wrapper.find("svg").exists()).toBe(true);
    expect(wrapper.find(MASK).exists()).toBe(false);
    expect(wrapper.get(".reference-artwork__placeholder-label").text()).toBe("肖像生成中");
    wrapper.unmount();
  });

  it("returns to the carried silhouette when the real image fails, with no refetch", async () => {
    const portrait = {
      subject_key: "portrait:character:7",
      status: "done",
      url: "/art/portrait/x.webp",
      aspect_ratio: "3:4",
      alt: "肖像",
      placeholder: null,
      face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
      stage: { scale: 1, x: 0, y: 0 },
      origin: "runtime",
      fallback: fallback("man"),
    };
    const wrapper = mount(ReferenceArtwork, {
      props: { portrait, initialOf: "旅人", stage: true },
    });
    expect(wrapper.get("img").attributes("src")).toBe("/art/portrait/x.webp");
    expect(wrapper.find(MASK).exists()).toBe(false);
    await wrapper.get("img").trigger("error");
    // Only the portrait image unmounts; the probe is the mask's load signal.
    expect(wrapper.find("img:not(.reference-artwork__mask-probe)").exists()).toBe(false);
    expect(wrapper.get("figure").attributes("data-status")).toBe("load-failed");
    // The already-resolved silhouette: the failed URL is never re-requested.
    expect(wrapper.get(PROBE).attributes("src")).toBe("/art/defaults/man.webp");
    await wrapper.get(PROBE).trigger("load");
    expect(maskedKey(wrapper)).toBe("url('/art/defaults/man.webp')");
    expect(wrapper.text()).toContain("肖像載入失敗");
    expect(wrapper.text()).not.toContain("已生成");
    wrapper.unmount();
  });

  it("keeps the name and state labels outside the decorative mask", async () => {
    const wrapper = await mountStage(silhouetteEntry("elder"));
    expect(wrapper.get(MASK).element.querySelector(".reference-artwork__chest")).toBe(null);
    const chest = wrapper.get(".reference-artwork__chest");
    expect(chest.text()).toContain("灰婆婆");
    expect(chest.text()).toContain("無肖像");
    expect(wrapper.get("figcaption").text()).toBe("灰婆婆，無肖像");
    wrapper.unmount();
  });

  it("keeps the pending shimmer's level contract on the masked figure", async () => {
    const wrapper = await mountStage(
      silhouetteEntry("girl", { status: "pending", placeholder: { kind: "missing", label: "肖像生成中" } })
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
        portrait: {
          url: "/art/portrait/x.webp",
          alt: "肖像",
          face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 },
          origin: "runtime",
          fallback: fallback("man"),
        },
      },
    });
    expect(wrapper.find(MASK).exists()).toBe(false);
    expect(wrapper.find("svg").exists()).toBe(false);
    expect(wrapper.get("img").element.style.objectPosition).toBe("50% 31%");
    wrapper.unmount();
  });

  it("re-arms the mask when the carried identity changes on a live frame", async () => {
    // A failure must not suppress a LATER identity: the probe's URL change
    // re-fires the load signal, so a re-pushed entry paints again.
    const wrapper = mount(ReferenceArtwork, {
      props: { portrait: silhouetteEntry("man"), initialOf: "灰婆婆", stage: true },
    });
    await wrapper.get(PROBE).trigger("load");
    expect(maskedKey(wrapper)).toBe("url('/art/defaults/man.webp')");
    await wrapper.setProps({ portrait: silhouetteEntry("girl") });
    expect(wrapper.get(PROBE).attributes("src")).toBe("/art/defaults/girl.webp");
    expect(wrapper.find(MASK_FILL).exists()).toBe(false, "the new identity reloads first");
    await wrapper.get(PROBE).trigger("load");
    expect(maskedKey(wrapper)).toBe("url('/art/defaults/girl.webp')");
    wrapper.unmount();
  });
});
