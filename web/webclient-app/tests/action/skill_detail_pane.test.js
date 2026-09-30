import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import SkillDetailPane from "../../components/SkillDetailPane.vue";

// webclient-zh-tw-copy-and-labels: the combat detail pane names the skill's
// validated target type and element instead of printing their identifiers;
// an identifier outside the known set reads as a neutral unknown, never as
// the raw key or a guessed mechanic.
function skill(overrides = {}) {
  return {
    label: "微光治癒",
    description: "凝聚光的魔力。",
    costText: "MP 11",
    targetSpec: "self",
    element: "light",
    enabled: true,
    ...overrides,
  };
}

describe("SkillDetailPane display vocabulary", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("names the target type and element in readable words", () => {
    wrapper = mount(SkillDetailPane, { props: { skill: skill() } });
    expect(wrapper.get(".skill-detail-pane__target").text()).toBe("目標類型 自身");
    const element = wrapper.get(".skill-detail-pane__rank");
    expect(element.text()).toBe("光屬性");
    expect(element.attributes("data-element")).toBe("light");
    expect(wrapper.text()).not.toMatch(/\b(self|light)\b/);
  });

  it("gives an unrecognised target type or element a neutral name, never the raw identifier", () => {
    wrapper = mount(SkillDetailPane, { props: { skill: skill({ targetSpec: "t_cone", element: "t_aether" }) } });
    expect(wrapper.get(".skill-detail-pane__target").text()).toBe("目標類型 未知目標類型");
    expect(wrapper.get(".skill-detail-pane__rank").text()).toBe("未知屬性");
    expect(wrapper.text()).not.toContain("t_cone");
    expect(wrapper.text()).not.toContain("t_aether");
  });
});
