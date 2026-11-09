import { afterEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { nextTick } from "vue";
import TileWall from "../../components/handbook/TileWall.vue";

// Synthetic groups: two groups, five items, one not selectable. Up/Down step
// by the grid's measured column count; the row test stubs that measurement.
const GROUPS = [
  {
    key: "g1",
    label: "group-one",
    items: [
      { id: "a", selectable: true, label: "item-a" },
      { id: "b", selectable: true, label: "item-b" },
      { id: "c", selectable: false, label: "item-c" },
    ],
  },
  {
    key: "g2",
    label: null,
    items: [
      { id: "d", selectable: true, label: "item-d" },
      { id: "e", selectable: true, label: "item-e" },
    ],
  },
];

describe("TileWall (handbook-primitives)", () => {
  let wrapper;

  afterEach(() => {
    vi.restoreAllMocks();
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountWall(props = {}) {
    wrapper = mount(TileWall, {
      attachTo: document.body,
      props: { groups: GROUPS, ariaLabel: "wall", ...props },
      slots: { tile: ({ item, selected }) => `${item.id}${selected ? "*" : ""}` },
    });
    return wrapper;
  }

  const cell = (id) => wrapper.get(`[data-tile="${id}"]`);
  const tabStops = () => wrapper.findAll('[role="option"]').filter((el) => el.attributes("tabindex") === "0");

  async function press(key) {
    await wrapper.get('[data-testid="tile-wall"]').trigger("keydown", { key });
    await nextTick();
  }

  it("renders the groups in order as one listbox with grouped options", () => {
    mountWall();
    const root = wrapper.get('[data-testid="tile-wall"]');
    expect(root.attributes("role")).toBe("listbox");
    expect(root.attributes("aria-label")).toBe("wall");
    expect(wrapper.findAll('[role="group"]').map((g) => g.attributes("aria-label"))).toEqual(["group-one", "wall"]);
    expect(wrapper.findAll('[role="option"]').map((o) => o.attributes("data-tile"))).toEqual(["a", "b", "c", "d", "e"]);
    expect(cell("a").text()).toBe("a");
  });

  it("has exactly one tab stop: the first item without a selection", () => {
    mountWall();
    expect(tabStops().map((el) => el.attributes("data-tile"))).toEqual(["a"]);
  });

  it("puts the one tab stop on the selected item when present", () => {
    mountWall({ selectedId: "d" });
    expect(tabStops().map((el) => el.attributes("data-tile"))).toEqual(["d"]);
    expect(cell("d").attributes("aria-selected")).toBe("true");
    expect(cell("a").attributes("aria-selected")).toBe("false");
    expect(cell("d").text()).toBe("d*");
  });

  it("moves focus with ArrowRight, End and Home across groups without selecting", async () => {
    mountWall();
    cell("a").element.focus();
    await cell("a").trigger("focus");
    await press("ArrowRight");
    expect(document.activeElement).toBe(cell("b").element);
    await press("End");
    expect(document.activeElement).toBe(cell("e").element);
    await press("Home");
    expect(document.activeElement).toBe(cell("a").element);
    expect(wrapper.emitted("select")).toBeUndefined();
    expect(tabStops().map((el) => el.attributes("data-tile"))).toEqual(["a"]);
  });

  it("steps ArrowDown and ArrowUp by the measured column count and clamps at the ends", async () => {
    const real = window.getComputedStyle.bind(window);
    vi.spyOn(window, "getComputedStyle").mockImplementation((el) =>
      el.classList?.contains("tile-wall__grid") ? { gridTemplateColumns: "100px 100px" } : real(el),
    );
    mountWall();
    cell("a").element.focus();
    await press("ArrowUp");
    expect(document.activeElement).toBe(cell("a").element);
    await press("ArrowDown");
    expect(document.activeElement).toBe(cell("c").element);
    await press("ArrowDown");
    expect(document.activeElement).toBe(cell("e").element);
    await press("ArrowDown");
    expect(document.activeElement).toBe(cell("e").element);
    await press("ArrowUp");
    expect(document.activeElement).toBe(cell("c").element);
    await press("ArrowLeft");
    expect(document.activeElement).toBe(cell("b").element);
    expect(wrapper.emitted("select")).toBeUndefined();
  });

  it("selects once on Enter, Space or click of a selectable item", async () => {
    mountWall();
    cell("a").element.focus();
    await press("ArrowRight");
    await press("Enter");
    expect(wrapper.emitted("select")).toEqual([["b"]]);
    await press(" ");
    expect(wrapper.emitted("select")).toEqual([["b"], ["b"]]);
    await cell("d").trigger("click");
    expect(wrapper.emitted("select")).toEqual([["b"], ["b"], ["d"]]);
  });

  it("keeps a non-selectable item focusable and inert", async () => {
    mountWall();
    expect(cell("c").attributes("aria-disabled")).toBe("true");
    expect(cell("a").attributes("aria-disabled")).toBeUndefined();
    cell("a").element.focus();
    await press("ArrowRight");
    await press("ArrowRight");
    expect(document.activeElement).toBe(cell("c").element);
    await press("Enter");
    await press(" ");
    await cell("c").trigger("click");
    expect(wrapper.emitted("select")).toBeUndefined();
  });
});
