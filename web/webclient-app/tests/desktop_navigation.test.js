// webclient-avg-place-card-top-bar (design D2): the top navigation carries
// no home entry — no 探索 / 戰鬥 button names the screen the player is
// already on; the drawer entries and the map/settings controls remain.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import DesktopNavigation from "../components/DesktopNavigation.vue";

const ITEMS = [
  { key: "character", label: "角色狀態", enabled: true },
  { key: "quests", label: "任務", enabled: true },
  { key: "bag", label: "背包", enabled: true },
];

function labels(wrapper) {
  return wrapper.findAll("button").map((button) => button.text());
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
    expect(DesktopNavigation.emits).toEqual(["navigate", "overlay"]);
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
});
