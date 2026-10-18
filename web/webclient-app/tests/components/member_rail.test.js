// webclient-window-primitives: MemberRail is a roving-focus member list whose
// knocked-out and unread states are never colour-only.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { nextTick } from "vue";
import MemberRail, { EMPTY_SLOT } from "../../components/MemberRail.vue";
import { glyphPath } from "../../components/dock-icons.js";
import { WINDOW_RAIL_MEMBERS } from "../../stories/fixtures/window_primitives.js";

describe("MemberRail (webclient-window-primitives)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountRail(props = {}) {
    wrapper = mount(MemberRail, {
      attachTo: document.body,
      props: {
        members: WINDOW_RAIL_MEMBERS,
        selected: 11,
        onSelect: (id) => wrapper.setProps({ selected: id }),
        ...props,
      },
    });
    return wrapper;
  }

  const entry = (id) => wrapper.get(`[data-testid="member-rail__entry--${id}"]`);
  const entries = () => wrapper.findAll(".member-rail__entry");

  it("lists the members in the given order with portrait or initial and name", () => {
    mountRail();
    expect(entries().map((e) => e.get(".member-rail__name").text())).toEqual(["莉瑟", "艾拉", "卡恩"]);
    expect(entry(11).get("img").attributes("src")).toBe("/art/defaults/woman.webp");
    expect(entry(11).get("img").attributes("alt")).toBe("");
    // No portrait: the name's first character stands in.
    expect(entry(13).find("img").exists()).toBe(false);
    expect(entry(13).get(".member-rail__avatar").text()).toBe("卡");
    expect(wrapper.get("nav").attributes("aria-label")).toBe("隊伍成員");
  });

  it("marks the selected entry with aria-current only", () => {
    mountRail();
    expect(entry(11).attributes("aria-current")).toBe("true");
    expect(entry(12).attributes("aria-current")).toBeUndefined();
  });

  it("states a knocked-out member by the ▼ shape and the text 倒地, also in the accessible name", () => {
    mountRail();
    const down = entry(13).get('[data-testid="member-rail__down"]');
    expect(down.text()).toBe("倒地");
    expect(down.get("path").attributes("d")).toBe(glyphPath("knocked_out"));
    expect(entry(13).attributes("aria-label")).toBe("卡恩，倒地");
    expect(entry(11).find('[data-testid="member-rail__down"]').exists()).toBe(false);
  });

  it("names the unread dot in text", () => {
    mountRail();
    expect(entry(12).find('[data-testid="member-rail__dot"]').attributes("aria-hidden")).toBe("true");
    expect(entry(12).attributes("aria-label")).toBe("艾拉，有新解鎖的技能");
    expect(entry(11).attributes("aria-label")).toBe("莉瑟");
    expect(entry(11).find('[data-testid="member-rail__dot"]').exists()).toBe(false);
  });

  it("ends with a dashed 空位 entry only while a slot is free", async () => {
    mountRail();
    expect(wrapper.find('[data-testid="member-rail__entry--empty"]').exists()).toBe(false);
    await wrapper.setProps({ emptySlot: true });
    const empty = wrapper.get('[data-testid="member-rail__entry--empty"]');
    expect(entries().at(-1).element).toBe(empty.element);
    expect(empty.text()).toBe("空位");
    expect(empty.attributes("aria-label")).toBe("空位");
    expect(empty.get("path").attributes("d")).toBe(glyphPath("plus"));
    await empty.trigger("click");
    expect(wrapper.emitted("select")).toEqual([[EMPTY_SLOT]]);
    expect(empty.attributes("aria-current")).toBe("true");
  });

  it("ArrowDown moves focus without selecting; Enter selects", async () => {
    mountRail();
    entry(11).element.focus();
    await entry(11).trigger("keydown", { key: "ArrowDown" });
    await nextTick();
    expect(document.activeElement).toBe(entry(12).element);
    expect(wrapper.emitted("select")).toBeUndefined();
    expect(entry(11).attributes("aria-current")).toBe("true");
    expect(entry(12).attributes("tabindex")).toBe("0");
    expect(entry(11).attributes("tabindex")).toBe("-1");
    await entry(12).trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("select")).toEqual([[12]]);
  });

  it("Space selects once, ArrowUp/Home/End wrap and jump", async () => {
    mountRail({ emptySlot: true });
    entry(11).element.focus();
    await entry(11).trigger("keydown", { key: "ArrowUp" });
    await nextTick();
    expect(document.activeElement).toBe(wrapper.get('[data-testid="member-rail__entry--empty"]').element);
    await wrapper.get('[data-testid="member-rail__entry--empty"]').trigger("keydown", { key: "ArrowDown" });
    await nextTick();
    expect(document.activeElement).toBe(entry(11).element);
    await entry(11).trigger("keydown", { key: "End" });
    await nextTick();
    expect(document.activeElement).toBe(wrapper.get('[data-testid="member-rail__entry--empty"]').element);
    await wrapper.get('[data-testid="member-rail__entry--empty"]').trigger("keydown", { key: "Home" });
    await nextTick();
    expect(document.activeElement).toBe(entry(11).element);
    await entry(11).trigger("keydown", { key: "ArrowDown" });
    await nextTick();
    const event = new KeyboardEvent("keydown", { key: " ", bubbles: true, cancelable: true });
    entry(12).element.dispatchEvent(event);
    expect(event.defaultPrevented).toBe(true);
    expect(wrapper.emitted("select")).toEqual([[12]]);
    // Selecting the selected entry again emits nothing.
    await nextTick();
    await entry(12).trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("select")).toEqual([[12]]);
  });

  it("ignores modified arrow keys", async () => {
    mountRail();
    entry(11).element.focus();
    await entry(11).trigger("keydown", { key: "ArrowDown", altKey: true });
    await nextTick();
    expect(document.activeElement).toBe(entry(11).element);
  });

  it("keeps one tab stop when nothing (or a departed member) is selected", async () => {
    mountRail({ selected: null });
    expect(entries().filter((e) => e.attributes("tabindex") === "0").map((e) => e.attributes("data-testid"))).toEqual([
      "member-rail__entry--11",
    ]);
    await wrapper.setProps({ selected: 99 });
    expect(entry(11).attributes("tabindex")).toBe("0");
    expect(entries().every((e) => e.attributes("aria-current") === undefined)).toBe(true);
  });

  it("returns the tab stop to the selected entry when focus leaves the rail", async () => {
    const outside = document.createElement("button");
    document.body.appendChild(outside);
    mountRail();
    entry(11).element.focus();
    await entry(11).trigger("keydown", { key: "ArrowDown" });
    await nextTick();
    outside.focus();
    await nextTick();
    expect(entry(11).attributes("tabindex")).toBe("0");
    expect(entry(12).attributes("tabindex")).toBe("-1");
  });
});
