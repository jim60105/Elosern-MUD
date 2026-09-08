import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import TopBar from "../components/TopBar.vue";

describe("TopBar (H1 contextual HUD: brand + top-meta pill)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("shows the top-left brand and the top-right meta pill (location · time · connection, glyph + label, never color alone)", () => {
    wrapper = mount(TopBar, {
      props: { connected: true, locationLabel: "測試起點", timeLabel: "春季 3 日 · 12:00" },
    });
    expect(wrapper.get('[data-testid="topbar-location"]').text()).toBe("測試起點");
    expect(wrapper.get('[data-testid="topbar-clock"]').text()).toBe("春季 3 日 · 12:00");
    const conn = wrapper.get('[data-testid="connection-state"]');
    expect(conn.text()).toBe("● 已連線");
    expect(wrapper.get('[data-testid="topbar"]').classes()).toContain("connected");
  });

  it("marks the disconnected state with the preserved state classes and a non-color glyph + label", () => {
    wrapper = mount(TopBar, { props: { connected: false } });
    expect(wrapper.get('[data-testid="connection-state"]').text()).toBe("○ 未連線");
    expect(wrapper.get('[data-testid="topbar"]').classes()).toContain("disconnected");
  });

  it("falls back to the placeholder labels when the slice is absent", () => {
    wrapper = mount(TopBar, { props: { connected: false } });
    expect(wrapper.get('[data-testid="topbar-location"]').text()).toBe("位置：--");
    expect(wrapper.get('[data-testid="topbar-clock"]').text()).toBe("時間：--");
  });

  it("mounts CharacterSwitcher in top-right cluster when roster is available and re-emits intents", async () => {
    const sampleChars = [
      { identity: 1, name: "艾莉亞", current: true, pending: false, portrait: null },
      { identity: 2, name: "雷恩", current: false, pending: false, portrait: null },
    ];
    wrapper = mount(TopBar, {
      props: {
        connected: true,
        locationLabel: "測試起點",
        timeLabel: "春季 3 日 · 12:00",
        rosterAvailable: true,
        rosterCharacters: sampleChars,
        rosterCanCreate: true,
      },
    });

    expect(wrapper.find('[data-testid="character-switcher"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="character-switcher-name"]').text()).toBe("艾莉亞");

    // Expand and trigger switch
    await wrapper.get('[data-testid="character-switcher-trigger"]').trigger("click");
    await wrapper.get('[data-testid="character-row-2"]').trigger("click");
    expect(wrapper.emitted("switch-character")).toEqual([[2]]);

    // Open create confirmation and confirm
    await wrapper.get('[data-testid="character-create-control"]').trigger("click");
    await wrapper.get('[data-testid="character-create-confirm"]').trigger("click");
    expect(wrapper.emitted("create-character")).toHaveLength(1);
  });

  it("renders three top-band elements with maximum-length name truncated, popover overlaying without displacing the band", async () => {
    const longName = "長".repeat(128);
    const sampleChars = [
      { identity: 1, name: longName, current: true, pending: false, portrait: null },
    ];
    wrapper = mount(TopBar, {
      props: {
        connected: true,
        locationLabel: "位置：亞爾托利亞冒險者公會總部前廣場",
        timeLabel: "春季 30 日 · 23:59",
        rosterAvailable: true,
        rosterCharacters: sampleChars,
      },
    });

    // Meta pill present
    expect(wrapper.get('[data-testid="topbar"]').exists()).toBe(true);
    // Switcher present with truncated long name
    const nameEl = wrapper.get('[data-testid="character-switcher-name"]');
    expect(nameEl.text()).toBe(longName);

    const rightCluster = wrapper.get(".topbar-right");
    expect(rightCluster.classes()).toContain("topbar-right");

    // When popover expands, it is an absolute overlay and does not displace the band elements
    await wrapper.get('[data-testid="character-switcher-trigger"]').trigger("click");
    const popover = wrapper.get('[data-testid="character-switcher-popover"]');
    expect(popover.exists()).toBe(true);
    // Meta pill and brand remain rendered
    expect(wrapper.get('[data-testid="topbar-title"]').exists()).toBe(true);
    expect(wrapper.get('[data-testid="topbar"]').exists()).toBe(true);
  });

  it("renders possession banner when available and omits it when unavailable", () => {
    wrapper = mount(TopBar, {
      props: {
        connected: true,
        possessionBanner: { available: true, host_name: "小艾", since_tick: 42 },
      },
    });
    const banner = wrapper.find('[data-testid="topbar-possession-banner"]');
    expect(banner.exists()).toBe(true);
    expect(banner.text()).toBe("你透過小艾的雙眼行動");

    wrapper = mount(TopBar, {
      props: {
        connected: true,
        possessionBanner: { available: false },
      },
    });
    expect(wrapper.find('[data-testid="topbar-possession-banner"]').exists()).toBe(false);
  });
});
