import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import App from "../App.vue";

describe("foundation root (A2 build stub)", () => {
  it("renders the offline stub root with its fixture marker", () => {
    const wrapper = mount(App);
    const root = wrapper.get('[data-testid="elosern-vue-root"]');
    expect(root.attributes("data-elosern-stage")).toBe("foundation-stub");
    expect(root.text()).toContain("霧落");
  });
});

describe("ESM lib wrappers (Vite CommonJS interop over the preserved UMD logic)", () => {
  it("re-exports the preserved pure-model APIs unchanged", async () => {
    const [protocol, keyboard, markup, localMap] = await Promise.all([
      import("../lib/protocol.js"),
      import("../lib/keyboard_router.js"),
      import("../lib/narrative_markup.js"),
      import("../lib/local_map.js"),
    ]);
    expect(protocol.default.PROTOCOL_VERSION).toBe(1);
    expect(protocol.default.syncEnvelope()).toEqual({ protocol_version: 1 });
    expect(typeof protocol.default.createStore).toBe("function");
    expect(typeof keyboard.default.createRouter).toBe("function");
    expect(markup.default.tokenize("<br>")).toHaveLength(1);
    expect(typeof localMap.default.reducePanel).toBe("function");
  });
});
