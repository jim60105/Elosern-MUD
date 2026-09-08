import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ReferenceArtwork from "../../components/ReferenceArtwork.vue";

describe("reference artwork provenance", () => {
  it("replaces decorative artwork with the committed portrait without retaining a sample caption", async () => {
    const wrapper = mount(ReferenceArtwork);
    const sampleUrl = wrapper.get("img").attributes("src");
    expect(wrapper.get("figcaption").attributes("data-sample")).toBe("true");
    await wrapper.setProps({ portrait: { url: "/art/portraits/actor.webp", alt: "艾琳的肖像" } });
    expect(wrapper.get("img").attributes("src")).toBe("/art/portraits/actor.webp");
    expect(wrapper.get("figcaption").text()).toBe("艾琳的肖像");
    expect(wrapper.get("figcaption").attributes("data-sample")).toBe("false");
    await wrapper.setProps({ portrait: null });
    expect(wrapper.get("img").attributes("src")).toBe(sampleUrl);
    expect(wrapper.get("figcaption").attributes("data-sample")).toBe("true");
    wrapper.unmount();
  });

  it("labels a failed portrait fallback as a sample and accepts a newly committed URL", async () => {
    const wrapper = mount(ReferenceArtwork, {
      props: { portrait: { url: "/art/portraits/missing.webp", alt: "艾琳的肖像" } },
    });
    await wrapper.get("img").trigger("error");
    expect(wrapper.get("img").attributes("src")).not.toBe("/art/portraits/missing.webp");
    expect(wrapper.get("figcaption").attributes("data-sample")).toBe("true");
    await wrapper.setProps({ portrait: { url: "/art/portraits/replacement.webp", alt: "新肖像" } });
    expect(wrapper.get("img").attributes("src")).toBe("/art/portraits/replacement.webp");
    expect(wrapper.get("figcaption").attributes("data-sample")).toBe("false");
    wrapper.unmount();
  });
});
