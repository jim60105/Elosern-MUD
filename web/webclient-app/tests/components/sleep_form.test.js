// redesign-rest-entry: the sleep form keeps its recovery button and duration
// input but no longer carries its own 睡眠模式 caption — the second-layer
// shell's caption (睡眠) names it.
import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import SleepForm from "../../components/SleepForm.vue";

describe("SleepForm (redesign-rest-entry)", () => {
  it("renders the recovery button and no 睡眠模式 caption", () => {
    const wrapper = mount(SleepForm, { props: { autofocus: false } });
    expect(wrapper.get('[data-testid="sleep-form-recovery"]').text()).toBe("睡眠至完全恢復");
    expect(wrapper.text()).not.toContain("睡眠模式");
    expect(wrapper.find(".exploration-sleep-caption").exists()).toBe(false);
    wrapper.unmount();
  });
});
