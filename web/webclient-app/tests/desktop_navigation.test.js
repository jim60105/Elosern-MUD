// webclient-avg-place-card-top-bar (design D2): the top navigation carries
// no home entry — no 探索 / 戰鬥 button names the screen the player is
// already on; the drawer entries, the map/settings controls, and the
// icon-only tool group (`工具`, webclient-collapsible-command-line D6) remain.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import DesktopNavigation from "../components/DesktopNavigation.vue";

const ITEMS = [
  { key: "character", label: "角色狀態", enabled: true },
  { key: "quests", label: "任務", enabled: true },
  { key: "bag", label: "背包", enabled: true },
];

function labels(wrapper) {
  return wrapper.findAll("nav > button").map((button) => button.text());
}

describe("DesktopNavigation", () => {
  it.each(["exploration", "combat"])("carries no 探索 or 戰鬥 entry in %s mode", (mode) => {
    const wrapper = mount(DesktopNavigation, { props: { mode, items: ITEMS } });
    const texts = labels(wrapper);
    expect(texts).not.toContain("探索");
    expect(texts).not.toContain("戰鬥");
    expect(texts.slice(0, 3)).toEqual(["角色狀態", "任務", "背包"]);
  });

  it("declares no home emit", () => {
    expect(DesktopNavigation.emits).toEqual(["navigate", "overlay", "drawer"]);
  });

  it("opens a drawer entry in one activation and marks the open drawer", async () => {
    const wrapper = mount(DesktopNavigation, {
      props: { mode: "exploration", items: ITEMS, drawer: "quest" },
    });
    const quests = wrapper.findAll("button").find((button) => button.text() === "任務");
    expect(quests.attributes("aria-current")).toBe("page");
    await quests.trigger("click");
    expect(wrapper.emitted("navigate")).toEqual([["quests"]]);
  });

  it("drops the map control in combat and keeps settings", () => {
    const explore = mount(DesktopNavigation, { props: { mode: "exploration", items: ITEMS } });
    expect(labels(explore)).toEqual(["角色狀態", "任務", "背包", "地圖", "設定"]);
    const combat = mount(DesktopNavigation, { props: { mode: "combat", items: ITEMS } });
    expect(labels(combat)).toEqual(["角色狀態", "任務", "背包", "設定"]);
  });

  it("renders the tool group with its four permanent buttons in order and aria-label = title", () => {
    const wrapper = mount(DesktopNavigation, { props: { mode: "exploration", items: ITEMS } });
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
    expect(buttons.map((b) => b.attributes("aria-label"))).toEqual([
      "技能系譜",
      "圖鑑",
      "稱號冊",
      "說明",
    ]);
    for (const button of buttons) {
      expect(button.attributes("title")).toBe(button.attributes("aria-label"));
    }
    // The world codex (globe) and title codex (star book) carry distinct labels and glyphs.
    const lore = wrapper.get('[data-testid="nav-tool-lore"]');
    const codex = wrapper.get('[data-testid="nav-tool-codex"]');
    expect(lore.attributes("aria-label")).not.toBe(codex.attributes("aria-label"));
    const lorePaths = lore.findAll("path, circle, ellipse").map((n) => n.attributes("d") ?? n.attributes("r") + n.attributes("rx"));
    const codexPaths = codex.findAll("path, circle, ellipse").map((n) => n.attributes("d") ?? n.attributes("r") + n.attributes("rx"));
    expect(lorePaths).not.toEqual(codexPaths);
  });

  it("renders gallery-opener in the tool group only when galleryAvailable is true", async () => {
    const wrapper = mount(DesktopNavigation, {
      props: { mode: "exploration", items: ITEMS, galleryAvailable: false },
    });
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
    const gallery = wrapper.get('[data-testid="gallery-opener"]');
    expect(gallery.attributes("aria-label")).toBe("角色肖像圖庫");
    expect(gallery.attributes("title")).toBe("角色肖像圖庫");
  });

  it("emits overlay for settings/lineage/codex/gallery/help and drawer for lore", async () => {
    const wrapper = mount(DesktopNavigation, {
      props: { mode: "exploration", items: ITEMS, galleryAvailable: true },
    });
    await wrapper.get('[data-testid="nav-settings"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-lineage"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-lore"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-codex"]').trigger("click");
    await wrapper.get('[data-testid="gallery-opener"]').trigger("click");
    await wrapper.get('[data-testid="nav-tool-help"]').trigger("click");
    expect(wrapper.emitted("overlay")).toEqual([
      ["settings"],
      ["lineage"],
      ["codex"],
      ["gallery"],
      ["help"],
    ]);
    expect(wrapper.emitted("drawer")).toEqual([["lore"]]);
  });
});
