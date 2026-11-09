import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import CodexEmblem from "../../components/handbook/CodexEmblem.vue";
import { glyphPath } from "../../components/dock-icons.js";

describe("CodexEmblem (handbook-primitives)", () => {
  it("renders the emblem_<name> path for a known name, decoratively", () => {
    const wrapper = mount(CodexEmblem, { props: { name: "combat" } });
    const svg = wrapper.get("svg");
    expect(svg.attributes("aria-hidden")).toBe("true");
    expect(wrapper.get("path").attributes("d")).toBe(glyphPath("emblem_combat"));
    expect(wrapper.get("path").attributes("stroke-width")).toBe("1.6");
  });

  it("passes the stroke width through", () => {
    const wrapper = mount(CodexEmblem, { props: { name: "ballot", strokeWidth: 1.1 } });
    expect(wrapper.get("path").attributes("d")).toBe(glyphPath("emblem_ballot"));
    expect(wrapper.get("path").attributes("stroke-width")).toBe("1.1");
  });

  it("falls back to the emblem_unknown path for an unknown or missing name", () => {
    const unknown = glyphPath("emblem_unknown");
    expect(unknown).toBeTruthy();
    expect(mount(CodexEmblem, { props: { name: "no-such-emblem" } }).get("path").attributes("d")).toBe(unknown);
    expect(mount(CodexEmblem).get("path").attributes("d")).toBe(unknown);
  });
});
