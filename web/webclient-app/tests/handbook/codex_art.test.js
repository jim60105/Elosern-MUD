import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import { mount } from "@vue/test-utils";
import CodexArt from "../../components/handbook/CodexArt.vue";
import { codexArt } from "../../stories/fixtures/lore_codex_panels.js";

// The committed panel the descriptor came from (its `available` is the
// availability fact the art is judged against).
const PANEL = { schema_version: 2, available: true };

// jsdom reports naturalWidth/naturalHeight 0; the shared lifecycle counts a
// load as a success only once the element declares a real size.
function declareImage(element, width = 640, height = 640) {
  Object.defineProperty(element, "naturalWidth", { value: width, configurable: true });
  Object.defineProperty(element, "naturalHeight", { value: height, configurable: true });
}

describe("CodexArt (handbook-codex-tab)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
  });

  const mountArt = (props) => {
    wrapper = mount(CodexArt, { props: { panel: PANEL, emblem: "cat_synthetic", variant: "hero", ...props } });
    return wrapper;
  };
  const emblem = () => wrapper.find('[data-testid="handbook__art-emblem"]');
  const image = () => wrapper.find("img");

  it("shows the category emblem for a null art", () => {
    mountArt({ art: null });
    expect(emblem().exists()).toBe(true);
    expect(image().exists()).toBe(false);
  });

  it("renders the image of a descriptor's single attempt", () => {
    mountArt({ art: codexArt("subject:one", "/art/synthetic/one.webp") });
    expect(image().attributes("src")).toBe("/art/synthetic/one.webp");
  });

  it("falls back to the emblem when the only attempt fails and no terminal exists", async () => {
    mountArt({ art: codexArt("subject:two", "/art/synthetic/two.webp") });
    await image().trigger("error");
    await nextTick();
    expect(image().exists()).toBe(false);
    expect(emblem().exists()).toBe(true);
  });

  it("keeps a loaded image and drops the emblem", async () => {
    mountArt({ art: codexArt("subject:three", "/art/synthetic/three.webp") });
    declareImage(image().element);
    await image().trigger("load");
    await nextTick();
    expect(image().attributes("src")).toBe("/art/synthetic/three.webp");
    expect(emblem().exists()).toBe(false);
    expect(wrapper.get(".codex-art").attributes("data-art-state")).toBe("loaded");
  });
});
