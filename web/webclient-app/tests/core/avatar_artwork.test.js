import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import AvatarArtwork from "../../components/AvatarArtwork.vue";
import {
  artworkDescriptor,
  artworkResource,
  artworkTerminal,
  fixtureDigest,
} from "../../stories/fixtures/art_panels.js";

// The committed panel every avatar is judged against.
const PANEL = { schema_version: 3, available: true };

// jsdom reports naturalWidth/naturalHeight 0 for every image, and the shared
// lifecycle reads the decoded dimensions off the element: a load is only a
// success once the element declares a real size.
function declareImage(element, width = 768, height = 1024) {
  Object.defineProperty(element, "naturalWidth", { value: width, configurable: true });
  Object.defineProperty(element, "naturalHeight", { value: height, configurable: true });
}

function candidate(url, faceRect, rank = 10, overrides = {}) {
  return {
    type: "image",
    source_id: `portrait.default:${url}`,
    rank,
    resource: artworkResource({
      resource_id: `portrait/character/${url.replace(/\W+/g, "_")}.webp`,
      version: fixtureDigest(url),
      url,
      geometry: {
        image_size: null,
        face_rect: faceRect,
        // A nonidentity stage triple: an avatar crop must ignore it entirely.
        stage: { scale: 1.7, x: -0.4, y: 0.3 },
        aspect_ratio: "3:4",
      },
      ...overrides,
    }),
  };
}

function avatarProps(overrides = {}) {
  return { panel: PANEL, name: "艾莉亞", ...overrides };
}

describe("avatar artwork (shared small-avatar renderer)", () => {
  it("paints the in-flight candidate's own rectangle with the zoom crop", () => {
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({
        artwork: artworkDescriptor({ attempts: [candidate("/art/a.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 })] }),
      }),
    });
    const img = wrapper.get("img.avatar-artwork__figure");
    expect(img.attributes("src")).toBe("/art/a.webp");
    // 1/w = 1/h = 2.5, anchored at -x·2.5 / -y·2.5; the stage triple is ignored.
    expect(img.element.style.width).toBe("250%");
    expect(img.element.style.height).toBe("250%");
    expect(img.element.style.left).toBe("-75%");
    expect(img.element.style.top).toBe("-25%");
    expect(img.element.style.transform).toBe("");
    wrapper.unmount();
  });

  it("uses the later successful candidate's own rectangle after an earlier failure", async () => {
    const first = candidate("/art/first.webp", { x: 0.6, y: 0.1, w: 0.2, h: 0.2 }, 10);
    const second = candidate("/art/second.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }, 20);
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({ artwork: artworkDescriptor({ attempts: [first, second] }) }),
    });
    expect(wrapper.get("img").attributes("src")).toBe("/art/first.webp");
    await wrapper.get("img").trigger("error");
    const img = wrapper.get("img.avatar-artwork__figure");
    expect(img.attributes("src")).toBe("/art/second.webp");
    // The second image's rectangle — not the failed first source's.
    expect(img.element.style.width).toBe("250%");
    expect(img.element.style.left).toBe("-75%");
    wrapper.unmount();
  });

  it("re-crops in place when the successful resource's geometry is revised", async () => {
    const first = candidate("/art/only.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 });
    const descriptor = () => artworkDescriptor({ attempts: [first] });
    const wrapper = mount(AvatarArtwork, { props: avatarProps({ artwork: descriptor() }) });
    const img = wrapper.get("img.avatar-artwork__figure");
    declareImage(img.element);
    await img.trigger("load");
    const token = img.attributes("data-attempt-token");
    // A geometry-only revision: the same resource bytes, a new rectangle.
    const revised = candidate("/art/only.webp", { x: 0.25, y: 0.25, w: 0.5, h: 0.5 });
    await wrapper.setProps({ artwork: artworkDescriptor({ attempts: [revised] }) });
    const next = wrapper.get("img.avatar-artwork__figure");
    expect(next.attributes("data-attempt-token")).toBe(token);
    expect(next.element.style.width).toBe("200%");
    expect(next.element.style.left).toBe("-50%");
    wrapper.unmount();
  });

  it("falls back to the centered cover crop for a malformed rectangle", () => {
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({
        artwork: artworkDescriptor({ attempts: [candidate("/art/bad.webp", { x: 0.6, y: 0.1, w: 0.2, h: 0.02 })] }),
      }),
    });
    // A degenerate rectangle clamps at the cap instead of throwing.
    expect(wrapper.get("img.avatar-artwork__figure").element.style.height).toBe("800%");
    wrapper.unmount();

    for (const rect of [null, undefined, { x: 0.9, y: 0.9, w: 0.4, h: 0.4 }, { x: 0.1, y: 0.1, w: 0, h: 0.4 }, { x: 0.1, y: 0.1, w: Number.NaN, h: 0.4 }]) {
      const w = mount(AvatarArtwork, {
        props: avatarProps({ artwork: artworkDescriptor({ attempts: [candidate("/art/bad.webp", rect)] }) }),
      });
      const style = w.get("img.avatar-artwork__figure").element.style;
      expect(style.objectPosition).toBe("50% 50%");
      expect(style.width).toBe("");
      expect(style.height).toBe("");
      w.unmount();
    }
  });

  it("keeps the recenters-only crop for the combat row policy", () => {
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({
        crop: "recenter",
        artwork: artworkDescriptor({ attempts: [candidate("/art/row.webp", { x: 0.25, y: 0.06, w: 0.5, h: 0.5 })] }),
      }),
    });
    const style = wrapper.get("img.avatar-artwork__figure").element.style;
    expect(style.objectPosition).toBe("50% 31%");
    expect(style.width).toBe("");
    wrapper.unmount();
  });

  it("draws the first grapheme of the trimmed name as the identity fallback", () => {
    const cases = [
      ["艾莉亞", "艾"],
      ["  樣本甲", "樣"],
      ["𠮟婆婆", "𠮟"],
      ["\u{1F469}\u200D\u{1F4BB}技師", "\u{1F469}\u200D\u{1F4BB}"],
      ["\u{1F1F9}\u{1F1FC}旅人", "\u{1F1F9}\u{1F1FC}"],
    ];
    for (const [name, glyph] of cases) {
      const wrapper = mount(AvatarArtwork, {
        props: avatarProps({
          name,
          artwork: artworkDescriptor({ generation_state: "pending", attempts: [], terminal: null }),
        }),
      });
      expect(wrapper.find("img").exists()).toBe(false);
      expect(wrapper.get(".avatar-artwork__initial").text()).toBe(glyph);
      expect(wrapper.find('[data-testid="artwork-failure"]').exists()).toBe(false);
      wrapper.unmount();
    }
  });

  it("renders a neutral symbol — never a blank tile — for an empty name", () => {
    for (const name of ["", "   ", null, undefined]) {
      const wrapper = mount(AvatarArtwork, {
        props: avatarProps({
          name,
          artwork: artworkDescriptor({ generation_state: "pending", attempts: [], terminal: null }),
        }),
      });
      const initial = wrapper.get(".avatar-artwork__initial").text();
      expect(initial).not.toBe("");
      expect(initial).toBe("？");
      wrapper.unmount();
    }
  });

  it("never mounts the descriptor's silhouette terminal resource", async () => {
    const terminalUrl = "/art/defaults/alpha_silhouette.webp";
    const terminal = artworkTerminal({
      resource: artworkResource({
        resource_id: "defaults/alpha_silhouette.webp",
        version: fixtureDigest("avatar-terminal"),
        url: terminalUrl,
        origin: "silhouette",
      }),
    });
    const first = candidate("/art/one.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }, 10);
    const second = candidate("/art/two.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 }, 20);
    const descriptor = artworkDescriptor({ attempts: [first, second], terminal });
    const wrapper = mount(AvatarArtwork, { props: avatarProps({ artwork: descriptor }) });
    const seen = [];
    seen.push(wrapper.get("img").attributes("src"));
    await wrapper.get("img").trigger("error");
    seen.push(wrapper.get("img").attributes("src"));
    await wrapper.get("img").trigger("error");
    // Every permitted real source was tried and spent; the terminal never was.
    expect(seen).toEqual(["/art/one.webp", "/art/two.webp"]);
    expect(seen).not.toContain(terminalUrl);
    expect(wrapper.find("img").exists()).toBe(false);
    expect(wrapper.get(".avatar-artwork__initial").exists()).toBe(true);
    wrapper.unmount();
  });

  it("keeps a reached fault as a focusable compact marker with its explanation", async () => {
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({
        artwork: artworkDescriptor({
          attempts: [candidate("/art/one.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 })],
          terminal: null,
        }),
      }),
    });
    await wrapper.get("img").trigger("error");
    const marker = wrapper.get('[data-testid="artwork-failure"]');
    // A real focusable control: the keyboard route to the explanation exists
    // without a pointer hover and the meaning is not color-only.
    expect(marker.element.tagName).toBe("BUTTON");
    expect(marker.text()).toContain("圖片載入失敗");
    expect(wrapper.find(".avatar-artwork__initial").exists()).toBe(true);
    wrapper.unmount();
  });

  it("adds no second focusable control when the caller hosts the explanation", async () => {
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({
        failureTextId: "avatar-explanation",
        artwork: artworkDescriptor({
          attempts: [candidate("/art/one.webp", { x: 0.3, y: 0.1, w: 0.4, h: 0.4 })],
          terminal: null,
        }),
      }),
    });
    await wrapper.get("img").trigger("error");
    expect(wrapper.find('[data-testid="artwork-failure"]').element.tagName).toBe("SPAN");
    expect(wrapper.findAll("button")).toHaveLength(0);
    const explanation = wrapper.get("#avatar-explanation");
    expect(explanation.attributes("role")).toBe("status");
    expect(explanation.text()).toContain("圖片載入失敗");
    wrapper.unmount();
  });

  it("carries no marker for expected absence, in-progress generation, or an unfinished load", () => {
    const cases = [
      // A position the committed payload admits no reference for.
      avatarProps({ artwork: null, hasReference: false }),
      // An admitted row whose own generation is still pending.
      avatarProps({ artwork: artworkDescriptor({ generation_state: "pending", attempts: [], terminal: null }) }),
      // An ordinary attempt still in flight.
      avatarProps({ artwork: artworkDescriptor({ attempts: [candidate("/art/slow.webp", null)] }) }),
    ];
    for (const props of cases) {
      const wrapper = mount(AvatarArtwork, { props });
      expect(wrapper.find('[data-testid="artwork-failure"]').exists()).toBe(false);
      wrapper.unmount();
    }
  });

  it("states a required panel's own availability failure through the shared mapping", () => {
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({
        artwork: artworkDescriptor(),
        panel: { schema_version: 3, available: false },
      }),
    });
    expect(wrapper.get('[data-testid="artwork-failure"]').text()).toContain("圖片面板目前無法提供資料");
    wrapper.unmount();
  });

  it("treats an admitted reference the committed catalog did not carry as a failure", () => {
    // `artwork` is null although the payload admitted one: the dangling
    // reference is a local failure, not an expected absence. The shared
    // availability input classifies it as the panel fact that could not supply
    // its data, and the shared category mapping owns the sentence.
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({ artwork: null, hasReference: true, name: "旅人" }),
    });
    const marker = wrapper.get('[data-testid="artwork-failure"]');
    expect(marker.text()).toContain("圖片面板目前無法提供資料");
    expect(wrapper.get(".avatar-artwork__initial").text()).toBe("旅");
    wrapper.unmount();
  });

  it("never surfaces a raw reason code in the explanation", () => {
    const wrapper = mount(AvatarArtwork, {
      props: avatarProps({
        artwork: artworkDescriptor({
          attempts: [
            { type: "fault", source_id: "portrait.default:9", rank: 10, reason: "totally_unknown_reason" },
          ],
          terminal: null,
        }),
      }),
    });
    const marker = wrapper.get('[data-testid="artwork-failure"]');
    expect(marker.text()).toContain("圖片無法顯示");
    expect(marker.text()).not.toContain("totally_unknown_reason");
    wrapper.unmount();
  });
});
