import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import UnreadIndicator from "../components/UnreadIndicator.vue";

describe("UnreadIndicator (B1 core family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("exposes the preserved live-region contract and a labeled jump control at count > 0", () => {
    wrapper = mount(UnreadIndicator, { props: { count: 3 } });
    const marker = wrapper.get('[data-testid="unread-indicator"]');
    expect(marker.attributes("id")).toBe("narrative-unread");
    expect(marker.attributes("role")).toBe("status");
    expect(marker.attributes("aria-live")).toBe("polite");
    expect(marker.attributes("aria-atomic")).toBe("true");
    expect(marker.attributes("data-count")).toBe("3");
    const button = wrapper.get('[data-testid="unread-indicator-button"]');
    expect(button.classes()).toContain("narrative-unread-button");
    expect(button.text()).toBe("↓ 3 則新訊息（點擊返回最新）");
  });

  it("hides entirely at count 0 (no empty pill) and emits jump on activation", async () => {
    wrapper = mount(UnreadIndicator, { props: { count: 0 } });
    expect(wrapper.find('[data-testid="unread-indicator-button"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="unread-indicator"]').attributes("data-visible")).toBe(
      "false",
    );

    await wrapper.setProps({ count: 2 });
    await wrapper.get('[data-testid="unread-indicator-button"]').trigger("click");
    expect(wrapper.emitted("jump")).toHaveLength(1);
  });
});
