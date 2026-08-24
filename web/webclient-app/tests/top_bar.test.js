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
});
