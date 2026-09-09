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
    expect(wrapper.get("figcaption").attributes("data-sample")).toBe("false");
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
    expect(wrapper.get("figcaption").text()).toBe("肖像生成中");
    expect(wrapper.get("figcaption").attributes("data-sample")).toBe("true");
    wrapper.unmount();
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
});
