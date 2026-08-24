import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ConnectOverlay from "../components/ConnectOverlay.vue";

describe("ConnectOverlay (B1 core family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it.each([
    ["connecting", "● 連線中…"],
    ["waiting", "◐ 等待登入…"],
    ["offline", "○ 連線中斷"],
  ])("shows the %s state as a live region with a glyph + label", (status, label) => {
    wrapper = mount(ConnectOverlay, { props: { status } });
    const overlay = wrapper.get('[data-testid="connect-overlay"]');
    expect(overlay.attributes("data-status")).toBe(status);
    expect(overlay.attributes("role")).toBe("status");
    expect(overlay.attributes("aria-live")).toBe("polite");
    expect(wrapper.get('[data-testid="connect-overlay-status"]').text()).toBe(label);
  });

  it("brands the overlay with the real game name", () => {
    wrapper = mount(ConnectOverlay, { props: { status: "waiting" } });
    expect(wrapper.get('[data-testid="connect-overlay-brand"]').text()).toBe("伊洛瑟恩");
  });

  it("is not rendered while connected and ready", () => {
    wrapper = mount(ConnectOverlay, { props: { status: "ready" } });
    expect(wrapper.find('[data-testid="connect-overlay"]').exists()).toBe(false);
  });
});
