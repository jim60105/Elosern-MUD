import { afterEach, describe, expect, it } from "vitest";
import { h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import IconTabs from "../../components/IconTabs.vue";

const STATE_TABS = [
  { key: "in_progress", label: "進行中", glyph: "quest_in_progress", count: 3 },
  { key: "completed", label: "已完成", glyph: "quest_completed", count: 2, hot: true },
  { key: "failed", label: "失敗", glyph: "quest_failed", count: 0 },
];

const TOP_TABS = [
  { key: "book", label: "任務簿", glyph: "quest_book", controls: "panel-book" },
  { key: "counter", label: "公會櫃檯", glyph: "guild_counter", disabled: true, reason: "需在公會職員面前" },
  { key: "extra", label: "其他", glyph: "lock" },
];

describe("IconTabs (quest-drawer-ui-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  // A v-model host: the parent writes every emitted selection back, as the
  // drawer will.
  function mountTabs(props = {}, slots = {}) {
    wrapper = mount(IconTabs, {
      attachTo: document.body,
      props: {
        tabs: STATE_TABS,
        modelValue: "in_progress",
        orientation: "vertical",
        ariaLabel: "任務狀態",
        "onUpdate:modelValue": (value) => wrapper.setProps({ modelValue: value }),
        ...props,
      },
      slots,
    });
    return wrapper;
  }

  const tab = (key) => wrapper.get(`[data-testid="icon-tabs__tab--${key}"]`);
  const tabindexes = () => wrapper.findAll('[role="tab"]').map((t) => t.attributes("tabindex"));
  const focused = () => document.activeElement?.dataset.tabKey;

  async function press(key, target = document.activeElement) {
    target.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
    await nextTick();
    await nextTick();
  }

  it("renders a labelled tablist with its orientation", () => {
    mountTabs();
    const list = wrapper.get('[role="tablist"]');
    expect(list.attributes("aria-label")).toBe("任務狀態");
    expect(list.attributes("aria-orientation")).toBe("vertical");
    expect(list.classes()).toContain("icon-tabs--vertical");
    expect(tab("in_progress").attributes("aria-selected")).toBe("true");
    expect(tab("completed").attributes("aria-selected")).toBe("false");
  });

  it("keeps exactly one roving tab stop, on the selected tab", () => {
    mountTabs({ modelValue: "completed" });
    expect(tabindexes()).toEqual(["-1", "0", "-1"]);
  });

  it("keeps a tab stop when the selection or the tabs change underneath it", async () => {
    mountTabs({ modelValue: "missing" });
    expect(tabindexes()).toEqual(["0", "-1", "-1"]);
    await wrapper.setProps({ modelValue: "failed" });
    expect(tabindexes()).toEqual(["-1", "-1", "0"]);
    await wrapper.setProps({ tabs: STATE_TABS.slice(0, 2) });
    expect(tabindexes()).toEqual(["0", "-1"]);
  });

  it("moves focus with ArrowDown/ArrowUp, Home, and End on a vertical rail, wrapping", async () => {
    mountTabs();
    tab("in_progress").element.focus();
    await press("ArrowDown");
    expect(focused()).toBe("completed");
    expect(tabindexes()).toEqual(["-1", "0", "-1"]);
    await press("ArrowDown");
    await press("ArrowDown");
    expect(focused()).toBe("in_progress");
    await press("ArrowUp");
    expect(focused()).toBe("failed");
    await press("Home");
    expect(focused()).toBe("in_progress");
    await press("End");
    expect(focused()).toBe("failed");
    // The horizontal axis does nothing on a vertical rail.
    await press("ArrowRight");
    expect(focused()).toBe("failed");
  });

  it("moves focus with ArrowRight/ArrowLeft on a horizontal list, wrapping", async () => {
    mountTabs({ tabs: TOP_TABS, modelValue: "book", orientation: "horizontal" });
    tab("book").element.focus();
    await press("ArrowLeft");
    expect(focused()).toBe("extra");
    await press("ArrowRight");
    expect(focused()).toBe("book");
    await press("ArrowRight");
    expect(focused()).toBe("counter");
    await press("ArrowDown");
    expect(focused()).toBe("counter");
  });

  it("does not select on focus; Enter and Space select the focused tab", async () => {
    mountTabs();
    tab("in_progress").element.focus();
    await press("ArrowDown");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    expect(tab("in_progress").attributes("aria-selected")).toBe("true");
    await press("Enter");
    expect(wrapper.emitted("update:modelValue")).toEqual([["completed"]]);
    await press("ArrowDown");
    await press(" ");
    expect(wrapper.emitted("update:modelValue")).toEqual([["completed"], ["failed"]]);
  });

  it("selects once from the keyboard path, cancelling the native click Enter and Space would synthesize", async () => {
    mountTabs();
    let clicks = 0;
    wrapper.element.addEventListener("click", () => clicks++);
    const enter = new KeyboardEvent("keydown", { key: "Enter", bubbles: true, cancelable: true });
    tab("completed").element.dispatchEvent(enter);
    expect(enter.defaultPrevented).toBe(true);
    await nextTick();
    const spaceDown = new KeyboardEvent("keydown", { key: " ", bubbles: true, cancelable: true });
    tab("failed").element.dispatchEvent(spaceDown);
    expect(spaceDown.defaultPrevented).toBe(true);
    const spaceUp = new KeyboardEvent("keyup", { key: " ", bubbles: true, cancelable: true });
    tab("failed").element.dispatchEvent(spaceUp);
    expect(spaceUp.defaultPrevented).toBe(true);
    await nextTick();
    // The keyboard path selected without any click handler running.
    expect(clicks).toBe(0);
    expect(wrapper.emitted("update:modelValue")).toEqual([["completed"], ["failed"]]);
  });

  it("leaves modified keys to the browser", async () => {
    mountTabs({ tabs: TOP_TABS, modelValue: "book", orientation: "horizontal" });
    tab("book").element.focus();
    for (const init of [{ key: "ArrowRight", altKey: true }, { key: "Home", ctrlKey: true }, { key: "Enter", metaKey: true }]) {
      const event = new KeyboardEvent("keydown", { ...init, bubbles: true, cancelable: true });
      tab("book").element.dispatchEvent(event);
      expect(event.defaultPrevented).toBe(false);
    }
    await nextTick();
    expect(focused()).toBe("book");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
  });

  it("selects on click and emits only on change", async () => {
    mountTabs();
    await tab("failed").trigger("click");
    await tab("failed").trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([["failed"]]);
  });

  it("returns the tab stop to the selected tab when focus leaves the list", async () => {
    mountTabs();
    const list = wrapper.get('[role="tablist"]').element;
    tab("in_progress").element.focus();
    await press("ArrowDown");
    // Focus moving to another tab inside the list keeps the roving stop.
    list.dispatchEvent(new FocusEvent("focusout", { relatedTarget: tab("failed").element, bubbles: true }));
    await nextTick();
    expect(tabindexes()).toEqual(["-1", "0", "-1"]);
    const outside = document.createElement("button");
    document.body.appendChild(outside);
    list.dispatchEvent(new FocusEvent("focusout", { relatedTarget: outside, bubbles: true }));
    await nextTick();
    expect(tabindexes()).toEqual(["0", "-1", "-1"]);
  });

  it("keeps a disabled tab focusable but never selects it, describing its reason", async () => {
    mountTabs({ tabs: TOP_TABS, modelValue: "book", orientation: "horizontal" });
    const counter = tab("counter");
    expect(counter.attributes("disabled")).toBeUndefined();
    expect(counter.attributes("aria-disabled")).toBe("true");
    const describedBy = counter.attributes("aria-describedby");
    expect(document.getElementById(describedBy).textContent).toBe("需在公會職員面前");
    expect(counter.attributes("data-tip")).toBe("公會櫃檯 · 需在公會職員面前");
    tab("book").element.focus();
    await press("ArrowRight");
    expect(focused()).toBe("counter");
    await press("Enter");
    await press(" ");
    await counter.trigger("click");
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    expect(tab("book").attributes("aria-describedby")).toBeUndefined();
    expect(tab("book").attributes("data-tip")).toBe("任務簿");
  });

  it("wires aria-controls only when the tab names a panel", () => {
    mountTabs({ tabs: TOP_TABS, modelValue: "book", orientation: "horizontal" });
    expect(tab("book").attributes("aria-controls")).toBe("panel-book");
    expect(tab("counter").attributes("aria-controls")).toBeUndefined();
  });

  it("hides the badge at zero and carries the count in the accessible name", () => {
    mountTabs();
    expect(tab("in_progress").get('[data-testid="icon-tabs__count"]').text()).toBe("3");
    expect(tab("failed").find('[data-testid="icon-tabs__count"]').exists()).toBe(false);
    expect(tab("in_progress").attributes("aria-label")).toBe("進行中（3）");
    expect(tab("failed").attributes("aria-label")).toBe("失敗（0）");
    expect(tab("completed").get('[data-testid="icon-tabs__count"]').attributes("aria-hidden")).toBe("true");
  });

  it("applies the hot, locked, dim, and mark states", () => {
    mountTabs({
      tabs: [
        { key: "E", label: "E 級", mark: true, reason: "你的等級" },
        { key: "D", label: "D 級", dim: true },
        { key: "C", label: "C 級", locked: true, reason: "尚未開放" },
      ],
      modelValue: "E",
    });
    expect(tab("E").classes()).toContain("is-mark");
    expect(tab("E").find(".icon-tabs__mark").exists()).toBe(true);
    expect(tab("D").classes()).toContain("is-dim");
    expect(tab("C").classes()).toContain("is-locked");
    expect(tab("C").find(".icon-tabs__lock").exists()).toBe(true);
    // Locked and dim tabs stay selectable; their reason is still described.
    expect(tab("C").attributes("aria-disabled")).toBeUndefined();
    expect(tab("C").attributes("aria-describedby")).toBeDefined();
    wrapper.unmount();

    mountTabs();
    expect(tab("completed").get('[data-testid="icon-tabs__count"]').classes()).toContain("icon-tabs__count--hot");
    expect(tab("in_progress").get('[data-testid="icon-tabs__count"]').classes()).not.toContain(
      "icon-tabs__count--hot",
    );
  });

  it("renders the glyph by default and the icon slot when given", () => {
    mountTabs();
    expect(tab("in_progress").find(".icon-tabs__icon svg path").exists()).toBe(true);
    wrapper.unmount();

    mountTabs({}, { icon: ({ tab: t }) => h("b", { class: "slot-icon" }, t.key) });
    expect(tab("completed").get(".slot-icon").text()).toBe("completed");
    expect(tab("completed").find(".icon-tabs__icon svg").exists()).toBe(false);
  });
});
