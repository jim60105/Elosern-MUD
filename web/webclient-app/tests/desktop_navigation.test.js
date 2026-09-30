// webclient-avg-place-card-top-bar (design D2): the top navigation carries
// no home entry — no 探索 / 戰鬥 button names the screen the player is
// already on; the drawer entries, the map/settings controls, and the
// icon-only tool group (`工具`, webclient-collapsible-command-line D6) remain.
// webclient-chrome-navigation-polish: the primary controls pack into a
// fixed-width region (a missing entry is absent, never a stand-in), and the
// tools disclose their labels in one shared tooltip on hover and Tab focus.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import DesktopNavigation from "../components/DesktopNavigation.vue";
import { NAV_TOOLS, toolLabel } from "../components/nav-tools.js";

const ITEMS = [
  { key: "character", label: "角色狀態", enabled: true },
  { key: "quests", label: "任務", enabled: true },
  { key: "bag", label: "背包", enabled: true },
];

function labels(wrapper) {
  return wrapper.findAll('[data-testid="nav-primary"] > button').map((button) => button.text());
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
    props: { mode: "exploration", items: ITEMS, ...props },
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
  it.each(["exploration", "combat"])("carries no 探索 or 戰鬥 entry in %s mode", (mode) => {
    mountNav({ mode });
    const texts = labels(wrapper);
    expect(texts).not.toContain("探索");
    expect(texts).not.toContain("戰鬥");
    expect(texts.slice(0, 3)).toEqual(["角色狀態", "任務", "背包"]);
  });

  it("declares no home emit", () => {
    expect(DesktopNavigation.emits).toEqual(["navigate", "overlay", "drawer"]);
  });

  it("opens a drawer entry in one activation and marks the open drawer", async () => {
    mountNav({ drawer: "quest" });
    const quests = wrapper.findAll("button").find((button) => button.text() === "任務");
    expect(quests.attributes("aria-current")).toBe("page");
    await quests.trigger("click");
    expect(wrapper.emitted("navigate")).toEqual([["quests"]]);
  });

  it("drops the map control in combat and keeps settings", () => {
    mountNav();
    expect(labels(wrapper)).toEqual(["角色狀態", "任務", "背包", "地圖", "設定"]);
    wrapper.unmount();
    mountNav({ mode: "combat" });
    expect(labels(wrapper)).toEqual(["角色狀態", "任務", "背包", "設定"]);
  });

  it("renders a missing entry as nothing: no disabled, hidden, or aria-disabled stand-in", () => {
    // The combat root supplies only its 背包 entry.
    mountNav({ mode: "combat", items: [{ key: "bag", label: "背包", enabled: true }] });
    const primary = wrapper.get('[data-testid="nav-primary"]');
    expect(primary.findAll("*").filter((el) => el.element.parentElement === primary.element).map((el) => el.attributes("data-nav-slot"))).toEqual([
      "inventory",
      "settings",
    ]);
    expect(wrapper.findAll("[aria-disabled], [hidden]")).toHaveLength(0);
    expect(wrapper.findAll("button:disabled")).toHaveLength(0);
  });

  it("sizes each primary control from its concept's glyph count inside a fixed-width region", () => {
    mountNav();
    const slots = wrapper
      .findAll('[data-testid="nav-primary"] > button')
      .map((b) => [b.attributes("data-nav-slot"), b.element.style.getPropertyValue("--nav-glyphs").trim()]);
    expect(slots).toEqual([
      ["character", "4"],
      ["quests", "2"],
      ["inventory", "2"],
      ["map", "2"],
      ["settings", "2"],
    ]);
    // The glyph counts are the shipped labels' lengths, so the region's
    // fixed width (the sum of the five controls) fits them exactly; the
    // browser suite measures the rendered widths.
    for (const item of ITEMS) {
      const button = wrapper.get(`[data-nav-slot="${item.key === "bag" ? "inventory" : item.key}"]`);
      expect(Number(button.element.style.getPropertyValue("--nav-glyphs"))).toBe(Array.from(item.label).length);
    }
  });

  it("renders the tool group from the shared tool model with accessible names and no native title", () => {
    mountNav();
    const group = wrapper.get('[data-testid="nav-tools"]');
    expect(group.attributes("role")).toBe("group");
    expect(group.attributes("aria-label")).toBe("工具");
    const buttons = group.findAll("button");
    expect(buttons.map((b) => b.attributes("data-testid"))).toEqual([
      "nav-tool-lineage",
      "nav-tool-lore",
      "nav-tool-codex",
      "nav-tool-help",
    ]);
    expect(buttons.map((b) => b.attributes("aria-label"))).toEqual(["技能系譜", "圖鑑", "稱號冊", "說明"]);
    for (const button of buttons) {
      // The visible tooltip replaces the delayed, hover-only native one.
      expect(button.attributes("title")).toBeUndefined();
    }
    expect(NAV_TOOLS.map((tool) => tool.label)).toEqual(["技能系譜", "圖鑑", "稱號冊", "角色肖像圖庫", "說明"]);
    expect(toolLabel("gallery")).toBe("角色肖像圖庫");
    expect(toolLabel("map")).toBeNull();
    // The world codex (globe) and title codex (star book) carry distinct labels and glyphs.
    const lore = wrapper.get('[data-testid="nav-tool-lore"]');
    const codex = wrapper.get('[data-testid="nav-tool-codex"]');
    expect(lore.find("path").attributes("d")).not.toBe(codex.find("path").attributes("d"));
  });

  it("keeps a disabled primary entry's reason as its title", () => {
    mountNav({ items: [{ key: "character", label: "角色狀態", enabled: false, disabled_reason: { message: "尚未開放" } }] });
    expect(wrapper.get('[data-nav-slot="character"]').attributes("title")).toBe("尚未開放");
  });

  it("renders gallery-opener in the tool group only when galleryAvailable is true", async () => {
    mountNav({ galleryAvailable: false });
    expect(wrapper.find('[data-testid="gallery-opener"]').exists()).toBe(false);

    await wrapper.setProps({ galleryAvailable: true });
    const group = wrapper.get('[data-testid="nav-tools"]');
    expect(group.findAll("button").map((b) => b.attributes("data-testid"))).toEqual([
      "nav-tool-lineage",
      "nav-tool-lore",
      "nav-tool-codex",
      "gallery-opener",
      "nav-tool-help",
    ]);
    expect(wrapper.get('[data-testid="gallery-opener"]').attributes("aria-label")).toBe("角色肖像圖庫");
  });

  it("emits overlay for settings/lineage/codex/gallery/help and drawer for lore", async () => {
    mountNav({ galleryAvailable: true });
    await wrapper.get('[data-testid="nav-settings"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-lineage"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-lore"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-codex"]').trigger("click");
    await wrapper.get('[data-testid="gallery-opener"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-help"]').trigger("click");
    expect(wrapper.emitted("overlay")).toEqual([["settings"], ["lineage"], ["codex"], ["gallery"], ["help"]]);
    expect(wrapper.emitted("drawer")).toEqual([["lore"]]);
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
      const lineage = wrapper.get('[data-testid="nav-tool-lineage"]');
      await tabTo(lineage);
      expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(true);

      await lineage.trigger("keydown", { key: "Escape" });
      expect(wrapper.find('[data-testid="nav-tooltip"]').exists()).toBe(false);
      expect(document.activeElement).toBe(lineage.element);
      expect(seen).not.toContain("Escape");

      // With no tooltip showing, Escape reaches the document (the dock's router).
      await lineage.trigger("keydown", { key: "Escape" });
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
    const lineage = wrapper.get('[data-testid="nav-tool-lineage"]');
    await tabTo(lineage);
    const codexTool = wrapper.get('[data-testid="nav-tool-codex"]').element.parentElement;
    codexTool.dispatchEvent(new MouseEvent("mouseenter"));
    await wrapper.vm.$nextTick();
    expect(wrapper.get('[data-testid="nav-tooltip"]').text()).toBe("稱號冊");
    codexTool.dispatchEvent(new MouseEvent("mouseleave"));
    await wrapper.vm.$nextTick();
    // The focus tooltip of the focused control is back.
    expect(wrapper.get('[data-testid="nav-tooltip"]').text()).toBe("技能系譜");
    await lineage.trigger("keydown", { key: "Escape" });
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
