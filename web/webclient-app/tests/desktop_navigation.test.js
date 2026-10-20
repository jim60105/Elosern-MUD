// webclient-avg-place-card-top-bar (design D2): the top navigation carries
// no home entry — no 探索 / 戰鬥 button names the screen the player is
// already on. webclient-chrome-navigation-polish: the primary controls pack
// into a fixed-width region (a missing entry is absent, never a stand-in),
// and the tools disclose their labels in one shared tooltip on hover and
// Tab focus. webclient-main-navigation-hotkeys: the labelled entries are
// 隊伍 / 任務 / 地圖 with their hotkey chips, the tools 信件 / 圖鑑 / 稱號冊 /
// 角色肖像圖庫 / 說明, and 設定 ends the bar.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import DesktopNavigation from "../components/DesktopNavigation.vue";
import { NAV_SETTINGS, NAV_TOOLS, toolLabel } from "../components/nav-tools.js";
import { NAV_PRIMARY, NAV_PRIMARY_GLYPHS, primaryEntries } from "../components/nav-primary.js";

// The exploration panel's navigation rows: the bar reads only `quests`.
const ITEMS = [
  { key: "character", label: "角色狀態", enabled: true },
  { key: "quests", label: "任務", enabled: true },
  { key: "inventory", label: "背包", enabled: true },
];
// The combat root's own navigation row (its client-local 背包).
const COMBAT_ITEMS = [{ key: "bag", label: "背包", enabled: true }];

function slots(wrapper) {
  return wrapper.findAll('[data-testid="nav-primary"] > *').map((node) => node.attributes("data-nav-slot"));
}
function labels(wrapper) {
  return wrapper.findAll(".desktop-navigation__label").map((node) => node.text());
}
// The bar's controls in DOM (and visual) order, by accessible name.
function names(wrapper) {
  return wrapper.findAll(".desktop-navigation button").map((button) => button.attributes("aria-label") ?? button.get(".desktop-navigation__label").text());
}

let wrapper;
afterEach(() => {
  wrapper?.unmount();
  wrapper = null;
  document.body.innerHTML = "";
});

function mountNav(props = {}) {
  const host = document.createElement("div");
  document.body.appendChild(host);
  wrapper = mount(DesktopNavigation, {
    attachTo: host,
    props: { mode: "exploration", items: ITEMS, partyAvailable: true, ...props },
  });
  return wrapper;
}

// Keyboard focus arriving by Tab: the capture listener records the Tab
// press, then the control takes focus.
async function tabTo(button) {
  document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
  button.element.focus();
  await button.trigger("focus");
}

describe("DesktopNavigation", () => {
  it("orders the whole bar: 隊伍, 任務, 地圖, the tool group, then 設定", () => {
    mountNav({ galleryAvailable: true });
    expect(names(wrapper)).toEqual(["隊伍", "任務", "地圖", "信件", "圖鑑", "稱號冊", "角色肖像圖庫", "說明", "設定"]);
    // 設定 stands after the tool group, outside it.
    const settings = wrapper.get('[data-testid="nav-settings"]');
    expect(wrapper.get('[data-testid="nav-tools"]').element.contains(settings.element)).toBe(false);
    expect(wrapper.get('[data-testid="nav-primary"]').element.contains(settings.element)).toBe(false);
    expect(settings.attributes("aria-label")).toBe("設定");
  });

  it.each([
    ["exploration", ITEMS, ["party", "quests", "map"]],
    ["dialogue", ITEMS, ["party", "quests", "map"]],
    ["combat", COMBAT_ITEMS, ["party"]],
  ])("carries the %s entries and no 探索, 戰鬥, 角色狀態 or 背包 entry", (mode, items, expected) => {
    mountNav({ mode, items });
    expect(slots(wrapper)).toEqual(expected);
    for (const gone of ["探索", "戰鬥", "角色狀態", "背包", "技能系譜"]) {
      expect(names(wrapper)).not.toContain(gone);
    }
  });

  it("renders nothing in creation", () => {
    mountNav({ mode: "creation" });
    expect(wrapper.find("nav").exists()).toBe(false);
    expect(primaryEntries({ mode: "creation", partyAvailable: true, items: ITEMS })).toEqual([]);
  });

  it("declares no home emit", () => {
    expect(DesktopNavigation.emits).toEqual(["navigate", "overlay", "drawer"]);
  });

  it("draws each entry's hotkey as a decorative chip and exposes it as aria-keyshortcuts", () => {
    mountNav();
    const buttons = wrapper.findAll('[data-testid="nav-primary"] > button');
    expect(buttons.map((b) => b.attributes("aria-keyshortcuts"))).toEqual(["P", "J", "M"]);
    expect(buttons.map((b) => b.get("kbd").text())).toEqual(["P", "J", "M"]);
    for (const button of buttons) expect(button.get("kbd").attributes("aria-hidden")).toBe("true");
    expect(labels(wrapper)).toEqual(["隊伍", "任務", "地圖"]);
    expect(NAV_PRIMARY.map((entry) => entry.hotkey)).toEqual(["P", "J", "M"]);
  });

  it("emits navigate for 隊伍 and 任務 and overlay for 地圖 and 設定", async () => {
    mountNav();
    await wrapper.get('[data-nav-slot="party"]').trigger("click");
    await wrapper.get('[data-nav-slot="quests"]').trigger("click");
    await wrapper.get('[data-nav-slot="map"]').trigger("click");
    await wrapper.get('[data-testid="nav-settings"]').trigger("click");
    expect(wrapper.emitted("navigate")).toEqual([["party"], ["quests"]]);
    expect(wrapper.emitted("overlay")).toEqual([["map"], ["settings"]]);
  });

  it("marks 隊伍 current while the party window is open, whatever its tab, and 任務 for the quest board", async () => {
    const current = () => wrapper.findAll('[aria-current="page"]').map((button) => button.attributes("data-nav-slot"));
    mountNav({ drawer: "party" });
    expect(current()).toEqual(["party"]);
    await wrapper.setProps({ drawer: "quest" });
    expect(current()).toEqual(["quests"]);
    await wrapper.setProps({ drawer: "letters" });
    expect(current()).toEqual([]);
  });

  it("follows the committed party panel: no party panel, no 隊伍 and no placeholder", async () => {
    mountNav({ partyAvailable: false });
    expect(slots(wrapper)).toEqual(["quests", "map"]);
    await wrapper.setProps({ partyAvailable: true });
    expect(slots(wrapper)).toEqual(["party", "quests", "map"]);
  });

  it("renders a missing entry as nothing: no disabled, hidden, or aria-disabled stand-in", () => {
    // Combat: no quest row and no map; the quest surface unavailable outside it.
    mountNav({ mode: "combat", items: COMBAT_ITEMS, partyAvailable: false });
    expect(slots(wrapper)).toEqual([]);
    expect(wrapper.findAll("[aria-disabled], [hidden]")).toHaveLength(0);
    expect(wrapper.findAll("button:disabled")).toHaveLength(0);
    wrapper.unmount();
    mountNav({ items: [{ key: "character", label: "角色狀態", enabled: true }] });
    expect(slots(wrapper)).toEqual(["party", "map"]);
    expect(wrapper.findAll("button:disabled")).toHaveLength(0);
  });

  it("sizes each entry from its label's glyph count inside a region sized for all three", () => {
    mountNav();
    const sized = wrapper
      .findAll('[data-testid="nav-primary"] > button')
      .map((b) => [b.attributes("data-nav-slot"), b.element.style.getPropertyValue("--nav-glyphs").trim()]);
    expect(sized).toEqual([
      ["party", "2"],
      ["quests", "2"],
      ["map", "2"],
    ]);
    // The region's fixed width in DesktopNavigation.vue is written for six
    // glyphs and three control chromes: the sum of the three entries.
    expect(NAV_PRIMARY_GLYPHS).toBe(6);
  });

  it("keeps the region width independent of the mode (the 1px stability input)", () => {
    // Every mode lays out inside the same fixed region; only which entries
    // render varies, never their individual widths, so the trailing edge
    // (the tool group's and 設定's anchor) is mode-independent.
    const widthOf = (mode, items, partyAvailable) =>
      primaryEntries({ mode, partyAvailable, items }).map((entry) => [entry.key, entry.glyphs]);
    const explore = Object.fromEntries(widthOf("exploration", ITEMS, true));
    for (const [key, glyphs] of widthOf("combat", COMBAT_ITEMS, true)) expect(glyphs).toBe(explore[key]);
    for (const [key, glyphs] of widthOf("dialogue", ITEMS, false)) expect(glyphs).toBe(explore[key]);
    const sum = Object.values(explore).reduce((a, b) => a + b, 0);
    expect(sum).toBe(NAV_PRIMARY_GLYPHS);
  });

  it("renders the tool group from the shared tool model with accessible names and no native title", () => {
    mountNav();
    const group = wrapper.get('[data-testid="nav-tools"]');
    expect(group.attributes("role")).toBe("group");
    expect(group.attributes("aria-label")).toBe("工具");
    const buttons = group.findAll("button");
    expect(buttons.map((b) => b.attributes("data-testid"))).toEqual([
      "nav-tool-letters",
      "nav-tool-lore",
      "nav-tool-codex",
      "nav-tool-help",
    ]);
    expect(buttons.map((b) => b.attributes("aria-label"))).toEqual(["信件", "圖鑑", "稱號冊", "說明"]);
    for (const button of [...buttons, wrapper.get('[data-testid="nav-settings"]')]) {
      // The visible tooltip replaces the delayed, hover-only native one.
      expect(button.attributes("title")).toBeUndefined();
    }
    expect(NAV_TOOLS.map((tool) => tool.label)).toEqual(["信件", "圖鑑", "稱號冊", "角色肖像圖庫", "說明"]);
    expect(toolLabel("gallery")).toBe("角色肖像圖庫");
    expect(toolLabel("settings")).toBe(NAV_SETTINGS.label);
    expect(toolLabel("lineage")).toBeNull();
    expect(toolLabel("map")).toBeNull();
    // The world codex (globe) and title codex (star book) carry distinct labels and glyphs.
    const lore = wrapper.get('[data-testid="nav-tool-lore"]');
    const codex = wrapper.get('[data-testid="nav-tool-codex"]');
    expect(lore.find("path").attributes("d")).not.toBe(codex.find("path").attributes("d"));
  });

  it("keeps a disabled primary entry's reason as its title", () => {
    mountNav({ items: [{ key: "quests", label: "任務", enabled: false, disabled_reason: { message: "尚未開放" } }] });
    const quests = wrapper.get('[data-nav-slot="quests"]');
    expect(quests.attributes("title")).toBe("尚未開放");
    expect(quests.attributes("disabled")).toBeDefined();
  });

  it("renders gallery-opener in the tool group only when galleryAvailable is true", async () => {
    mountNav({ galleryAvailable: false });
    expect(wrapper.find('[data-testid="gallery-opener"]').exists()).toBe(false);

    await wrapper.setProps({ galleryAvailable: true });
    const group = wrapper.get('[data-testid="nav-tools"]');
    expect(group.findAll("button").map((b) => b.attributes("data-testid"))).toEqual([
      "nav-tool-letters",
      "nav-tool-lore",
      "nav-tool-codex",
      "gallery-opener",
      "nav-tool-help",
    ]);
    expect(wrapper.get('[data-testid="gallery-opener"]').attributes("aria-label")).toBe("角色肖像圖庫");
  });

  it("emits overlay for codex/gallery/help and drawer for letters and lore", async () => {
    mountNav({ galleryAvailable: true });
    await wrapper.get('[data-testid="nav-tool-letters"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-lore"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-codex"]').trigger("click");
    await wrapper.get('[data-testid="gallery-opener"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-help"]').trigger("click");
    expect(wrapper.emitted("overlay")).toEqual([["codex"], ["gallery"], ["help"]]);
    expect(wrapper.emitted("drawer")).toEqual([["letters"], ["lore"]]);
  });

  it("renders identically with and without possession (the bar takes no possession input)", () => {
    expect(Object.keys(DesktopNavigation.props).sort()).toEqual(["drawer", "galleryAvailable", "items", "mode", "partyAvailable"]);
    mountNav();
    const plain = wrapper.html();
    wrapper.unmount();
    // A possessed session commits the same panels to the bar.
    mountNav();
    expect(wrapper.html()).toBe(plain);
    expect(wrapper.text()).not.toMatch(/附身|你/);
  });
});

describe("DesktopNavigation tool tooltip", () => {
  it("shows the label on Tab focus, hidden from assistive technology", async () => {
    mountNav();
    const help = wrapper.get('[data-testid="nav-tool-help"]');
    await tabTo(help);
    const tip = wrapper.get('[data-testid="nav-tooltip"]');
    expect(tip.text()).toBe("說明");
    expect(tip.attributes("aria-hidden")).toBe("true");
    expect(document.activeElement).toBe(help.element);
    expect(wrapper.findAll('[data-testid="nav-tooltip"]')).toHaveLength(1);
  });

  it("Escape hides a focused tool's tooltip, keeps focus, and is consumed; the next Escape passes through", async () => {
    mountNav();
    const seen = [];
    const listener = (event) => seen.push(event.key);
    document.addEventListener("keydown", listener);
    try {
      const letters = wrapper.get('[data-testid="nav-tool-letters"]');
      await tabTo(letters);
      expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(true);

      await letters.trigger("keydown", { key: "Escape" });
      expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);
      expect(document.activeElement).toBe(letters.element);
      expect(seen).not.toContain("Escape");

      // With no tooltip showing, Escape reaches the document (the dock's router).
      await letters.trigger("keydown", { key: "Escape" });
      expect(seen).toContain("Escape");
    } finally {
      document.removeEventListener("keydown", listener);
    }
  });

  it("stays quiet when focus returns without a Tab (an overlay restoring its opener)", async () => {
    mountNav();
    const codex = wrapper.get('[data-testid="nav-tool-codex"]');
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
    codex.element.focus();
    await codex.trigger("focus");
    expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);
  });

  it("shows on hover, stays over the tooltip, and yields to Escape without consuming it", async () => {
    mountNav();
    const tool = wrapper.get('[data-testid="nav-tool-lore"]').element.parentElement;
    await tool.dispatchEvent(new MouseEvent("mouseenter"));
    await wrapper.vm.$nextTick();
    const tip = wrapper.get('[data-testid="nav-tooltip"]');
    expect(tip.text()).toBe("圖鑑");
    // The tooltip is inside the hovered wrapper, so moving onto it keeps it.
    expect(tool.contains(tip.element)).toBe(true);

    const escape = new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true });
    document.body.dispatchEvent(escape);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);
    expect(escape.defaultPrevented).toBe(false);

    await tool.dispatchEvent(new MouseEvent("mouseleave"));
    await tool.dispatchEvent(new MouseEvent("mouseenter"));
    await wrapper.vm.$nextTick();
    expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(true);
  });

  it("keeps pointer and keyboard sources apart: hovering B leaves A's focus tooltip to its own Escape", async () => {
    mountNav();
    const letters = wrapper.get('[data-testid="nav-tool-letters"]');
    await tabTo(letters);
    const codexTool = wrapper.get('[data-testid="nav-tool-codex"]').element.parentElement;
    codexTool.dispatchEvent(new MouseEvent("mouseenter"));
    await wrapper.vm.$nextTick();
    expect(wrapper.get('[data-testid="nav-tooltip"]').text()).toBe("稱號冊");
    codexTool.dispatchEvent(new MouseEvent("mouseleave"));
    await wrapper.vm.$nextTick();
    // The focus tooltip of the focused control is back.
    expect(wrapper.get('[data-testid="nav-tooltip"]').text()).toBe("信件");
    await letters.trigger("keydown", { key: "Escape" });
    expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);
  });

  it("drops the tooltip of a tool that stops rendering and never revives it without a new hover", async () => {
    mountNav({ galleryAvailable: true });
    const galleryTool = wrapper.get('[data-testid="gallery-opener"]').element.parentElement;
    galleryTool.dispatchEvent(new MouseEvent("mouseenter"));
    await wrapper.vm.$nextTick();
    expect(wrapper.get('[data-testid="nav-tooltip"]').text()).toBe("角色肖像圖庫");
    await wrapper.setProps({ galleryAvailable: false });
    await wrapper.setProps({ galleryAvailable: true });
    expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);

    const help = wrapper.get('[data-testid="nav-tool-help"]');
    await tabTo(help);
    await wrapper.setProps({ mode: "creation" });
    await wrapper.setProps({ mode: "exploration" });
    expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);
  });

  it("stays quiet when focus returns with the window after a Tab", async () => {
    mountNav();
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "Tab", bubbles: true }));
    window.dispatchEvent(new Event("blur"));
    const codex = wrapper.get('[data-testid="nav-tool-codex"]');
    codex.element.focus();
    await codex.trigger("focus");
    expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);
  });

  it("hides on activation", async () => {
    mountNav();
    const help = wrapper.get('[data-testid="nav-tool-help"]');
    await tabTo(help);
    await help.trigger("click");
    expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);
    expect(wrapper.emitted("overlay")).toEqual([["help"]]);
  });
});
