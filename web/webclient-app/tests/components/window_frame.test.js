// webclient-window-primitives: WindowFrame carries the drawer chrome and the
// HudDrawer focus contract, and selects its first-level tab through IconTabs.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import { h, nextTick } from "vue";
import MemberRail from "../../components/MemberRail.vue";
import WindowFrame from "../../components/WindowFrame.vue";
import { glyphPath } from "../../components/dock-icons.js";

const TABS = [
  { key: "member", label: "成員", glyph: "member" },
  { key: "bag", label: "背包", glyph: "inventory" },
  { key: "status", label: "狀態", glyph: "status", disabled: true, reason: "尚未開放" },
];

describe("WindowFrame (webclient-window-primitives)", () => {
  let wrapper;
  let opener;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = undefined;
    document.body.innerHTML = "";
  });

  function mountFrame(props = {}, slots = {}) {
    opener = document.createElement("button");
    opener.textContent = "隊伍";
    document.body.appendChild(opener);
    opener.focus();
    wrapper = mount(WindowFrame, {
      attachTo: document.body,
      props: {
        title: "隊伍",
        seal: "party",
        tabs: TABS,
        modelValue: "member",
        tabsLabel: "隊伍分頁",
        drawerKey: "party",
        "onUpdate:modelValue": (value) => wrapper.setProps({ modelValue: value }),
        ...props,
      },
      slots: Object.fromEntries(
        Object.entries({
          extras: () => h("span", { "data-testid": "purse" }, "1,240 銅"),
          default: () => h("p", "body"),
          ...slots,
        }).filter(([, slot]) => slot),
      ),
    });
    return wrapper;
  }

  it("renders the seal, title, tabs, header extras and close control", () => {
    mountFrame();
    expect(wrapper.get(".drawer-header__icon path").attributes("d")).toBe(glyphPath("party"));
    expect(wrapper.get('[data-testid="hud-drawer__title"]').text()).toBe("隊伍");
    expect(wrapper.get('[data-testid="hud-drawer-close"]').attributes("aria-label")).toBe("關閉");
    const tabs = wrapper.findAll('[data-testid="window-frame__tabs"] [role="tab"]');
    expect(tabs.map((tab) => tab.attributes("aria-label"))).toEqual(["成員", "背包", "狀態"]);
    expect(wrapper.get('[data-testid="window-frame__extras"]').text()).toBe("1,240 銅");
    // The drawer is the shared HudDrawer chrome with a flush body.
    expect(wrapper.get('[data-testid="hud-drawer"]').attributes("data-drawer-key")).toBe("party");
    expect(wrapper.find(".hud-drawer__body--flush").exists()).toBe(true);
    // Every tab controls the frame's one tabpanel, labelled by the tab.
    const panel = wrapper.get('[data-testid="window-frame__body"]');
    expect(panel.attributes("role")).toBe("tabpanel");
    expect(panel.attributes("aria-label")).toBe("成員");
    expect(tabs[0].attributes("aria-controls")).toBe(panel.attributes("id"));
  });

  it("moves focus into the window on open; Escape closes it and restores focus to the opener", async () => {
    mountFrame();
    expect(document.activeElement).toBe(wrapper.get('[data-testid="hud-drawer-close"]').element);
    await wrapper.get('[data-testid="icon-tabs__tab--bag"]').trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(document.activeElement).toBe(opener);
  });

  it("the close control closes and restores focus, as the quest drawer does", async () => {
    mountFrame();
    await wrapper.get('[data-testid="hud-drawer-close"]').trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(document.activeElement).toBe(opener);
  });

  it("a close guard that refuses keeps the window and its focus", async () => {
    mountFrame({ closeGuard: () => false });
    const close = wrapper.get('[data-testid="hud-drawer-close"]');
    await close.trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toBeUndefined();
    expect(document.activeElement).toBe(close.element);
  });

  it("Escape from a member rail entry inside the body still reaches the drawer", async () => {
    mountFrame({}, {
      default: () => h(MemberRail, { members: [{ id: 1, name: "莉瑟", portrait: null }], selected: 1 }),
    });
    const entry = wrapper.get('[data-testid="member-rail__entry--1"]');
    entry.element.focus();
    await entry.trigger("keydown", { key: "Escape" });
    expect(wrapper.emitted("close")).toHaveLength(1);
    expect(document.activeElement).toBe(opener);
  });

  it("selects a tab through IconTabs: arrows move focus, Enter selects, a disabled tab never selects", async () => {
    mountFrame();
    const member = wrapper.get('[data-testid="icon-tabs__tab--member"]');
    member.element.focus();
    await member.trigger("keydown", { key: "ArrowRight" });
    await nextTick();
    const bag = wrapper.get('[data-testid="icon-tabs__tab--bag"]');
    expect(document.activeElement).toBe(bag.element);
    expect(wrapper.emitted("update:modelValue")).toBeUndefined();
    await bag.trigger("keydown", { key: "Enter" });
    expect(wrapper.emitted("update:modelValue")).toEqual([["bag"]]);
    await nextTick();
    expect(wrapper.get('[data-testid="window-frame__body"]').attributes("aria-label")).toBe("背包");

    await wrapper.get('[data-testid="icon-tabs__tab--status"]').trigger("click");
    expect(wrapper.emitted("update:modelValue")).toEqual([["bag"]]);
  });

  it("renders no tab strip or extras when none are given", () => {
    mountFrame({ tabs: [] }, { extras: undefined });
    expect(wrapper.find('[data-testid="window-frame__tabs"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="window-frame__extras"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="window-frame__body"]').attributes("aria-label")).toBe("隊伍");
  });
});
