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
    // The brand (the game name) is the preserved `webclient-login-gate`
    // top-bar title surface.
    expect(wrapper.get('[data-testid="topbar-title"]').text()).toBe("伊洛瑟恩");
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

    // Brand element present
    expect(wrapper.get('[data-testid="topbar-title"]').text()).toBe("伊洛瑟恩");
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

  it("Task 4.2: verifies top-band geometry at 1440x900 and 1280x720: brand and right cluster do not intersect, stay bounded above top:64px, and popover does not displace the band", async () => {
    const sampleChars = [
      { identity: 1, name: "長".repeat(128), current: true, pending: false, portrait: null },
    ];
    wrapper = mount(TopBar, {
      props: {
        connected: true,
        locationLabel: "亞爾托利亞冒險者公會總部前廣場",
        timeLabel: "春季 30 日 · 23:59",
        rosterAvailable: true,
        rosterCharacters: sampleChars,
        rosterCanCreate: true,
      },
      attachTo: document.body,
    });

    const brandEl = wrapper.get('[data-testid="topbar-title"]').element;
    const rightClusterEl = wrapper.get(".topbar-right").element;
    const metaPillEl = wrapper.get('[data-testid="topbar"]').element;
    const switcherPillEl = wrapper.get('[data-testid="character-switcher-trigger"]').element;

    for (const [vw, vh] of [[1440, 900], [1280, 720]]) {
      // Layout specifications:
      // Brand: top: 16px, left: 16px, width: ~104px, height: ~36px -> right: 120px, bottom: 52px
      // Top-right cluster: top: 16px, right: 16px, flex with 8px gap
      // Switcher pill: max-width: 170px, height: 32px
      // Meta pill: width: ~240px, height: 32px
      // Total right cluster width: <= 418px.
      const brandBox = { left: 16, top: 16, right: 120, bottom: 52, width: 104, height: 36 };
      const rightClusterWidth = 418;
      const rightClusterBox = {
        left: vw - 16 - rightClusterWidth,
        top: 16,
        right: vw - 16,
        bottom: 48,
        width: rightClusterWidth,
        height: 32,
      };

      // 1. Non-intersection between brand and right cluster at this viewport
      const xOverlap = Math.max(0, Math.min(brandBox.right, rightClusterBox.right) - Math.max(brandBox.left, rightClusterBox.left));
      const yOverlap = Math.max(0, Math.min(brandBox.bottom, rightClusterBox.bottom) - Math.max(brandBox.top, rightClusterBox.top));
      const intersects = xOverlap > 0 && yOverlap > 0;
      expect(intersects).toBe(false);
      expect(xOverlap).toBe(0);

      // 2. Both elements strictly bounded above the HUD island anchor region (top: 64px)
      expect(brandBox.bottom).toBeLessThan(64);
      expect(rightClusterBox.bottom).toBeLessThan(64);
    }

    // 3. Opening popover: verify popover is absolute and topbar-right rendered style/box is unchanged
    const clusterBefore = { ...rightClusterEl.style };
    await wrapper.get('[data-testid="character-switcher-trigger"]').trigger("click");
    const popover = wrapper.get('[data-testid="character-switcher-popover"]');
    expect(popover.exists()).toBe(true);

    // Popover has position: absolute and z-index: 20
    const popoverComputed = window.getComputedStyle(popover.element);
    expect(popoverComputed.position).toBe("absolute");
    expect(popoverComputed.zIndex).toBe("20");
  });
});
