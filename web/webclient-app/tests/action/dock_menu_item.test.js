import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import DockMenuItem from "../../components/DockMenuItem.vue";

describe("DockMenuItem (B2 action-dock family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountCell(props = {}) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(DockMenuItem, {
      attachTo: host,
      props: {
        itemKey: "action-explore.move",
        label: "走往北岸大道",
        enabled: true,
        reason: null,
        focused: false,
        rowId: "dock-row-0",
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the preserved data-item-key and a stable data-testid", () => {
    const w = mountCell();
    const cell = w.get('[data-testid="dock-item"]');
    expect(cell.attributes("data-item-key")).toBe("action-explore.move");
    expect(cell.attributes("id")).toBe("dock-row-0");
    expect(cell.attributes("role")).toBe("option");
    expect(cell.text()).toContain("走往北岸大道");
  });

  it("marks the focused cell as the dispatch target without color alone", () => {
    const w = mountCell({ focused: true });
    const cell = w.get('[data-testid="dock-item"]');
    expect(cell.classes()).toContain("dock-menu-item--focused");
    expect(cell.attributes("aria-selected")).toBe("true");
    // The focus glyph "▶" is a CSS ::before pseudo-element (not a child
    // node), so the cell's text is just the label — the glyph is styled in
    // `.dock-menu-item--focused::before`.
    expect(cell.text()).toBe("走往北岸大道");
  });

  it("renders the disabled cell with the preserved suffix and readable reason", () => {
    const w = mountCell({
      enabled: false,
      reason: "正在調息，無法行動",
      rowId: "dock-row-3",
    });
    const cell = w.get('[data-testid="dock-item"]');
    expect(cell.classes()).toContain("dock-menu-item--disabled");
    expect(cell.attributes("aria-disabled")).toBe("true");
    expect(cell.text()).toContain("（無法使用）");
    expect(cell.attributes("aria-describedby")).toBe("dock-row-3-reason");
    const note = w.get("#dock-row-3-reason");
    expect(note.text()).toBe("正在調息，無法行動");
  });

  it("emits focus and activate on pointer activation of an enabled cell", async () => {
    const w = mountCell();
    await w.get('[data-testid="dock-item"]').trigger("click");
    expect(w.emitted("focus")).toEqual([["action-explore.move"]]);
    expect(w.emitted("activate")).toHaveLength(1);
    expect(w.emitted("activate")[0]).toEqual(["action-explore.move"]);
  });

  it("moves focus but emits no activate for a disabled cell", async () => {
    const w = mountCell({
      enabled: false,
      reason: "已倒地",
      itemKey: "target-e2",
      rowId: "combat-row-1",
    });
    await w.get('[data-testid="dock-item"]').trigger("click");
    expect(w.emitted("focus")).toEqual([["target-e2"]]);
    expect(w.emitted("activate")).toBeUndefined();
  });
});
