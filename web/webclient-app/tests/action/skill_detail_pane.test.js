import { readFileSync } from "node:fs";
import { join } from "node:path";
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

// webclient-combat-command-card-centred D5: the narrow card's detail strip.
describe("SkillDetailPane strip variant", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
  });

  it("states the cost, target and element on its first line and the description below it", () => {
    // Role: the strip's reading order. Detects a strip that drops the cost or
    // target line, or keeps the side pane's blocks.
    wrapper = mount(SkillDetailPane, { props: { skill: skill(), variant: "strip" } });
    const strip = wrapper.get('[data-testid="combat-detail"]');
    expect(strip.classes()).toContain("skill-detail-pane--strip");
    expect(strip.attributes("id")).toBe("action-dock-detail-strip");
    const meta = strip.get(".skill-detail-pane__meta");
    expect(meta.get(".skill-detail-pane__cost").text()).toBe("消耗MP 11");
    expect(meta.get(".skill-detail-pane__target").text()).toBe("目標類型自身");
    expect(meta.get(".skill-detail-pane__rank").text()).toBe("光屬性");
    const body = strip.get(".skill-detail-pane__body");
    expect(body.classes()).toContain("skill-detail-pane__desc");
    expect(body.text()).toBe("凝聚光的魔力。");
    // The full text rides `title` and stays in the DOM.
    expect(strip.attributes("title")).toBe("微光治癒 ‧ MP 11 ‧ 目標類型 自身 ‧ 光屬性 ‧ 凝聚光的魔力。");
    expect(strip.text()).toContain("微光治癒");
    // No control in the strip: the 威力 chips are the step's own rows.
    expect(strip.findAll("button")).toHaveLength(0);
  });

  it("clamps the body at two lines", () => {
    const source = readFileSync(join(process.cwd(), "web/webclient-app/components/SkillDetailPane.vue"), "utf8");
    const start = source.indexOf(".skill-detail-pane__body {");
    const rule = source.slice(start, source.indexOf("}", start));
    expect(rule).toContain("-webkit-line-clamp: 2;");
    expect(rule).toContain("overflow: hidden;");
  });

  it("states a disabled skill's reason in place of its description", () => {
    wrapper = mount(SkillDetailPane, {
      props: { skill: skill({ enabled: false, disabledReason: { message: "需要神聖親和。" } }), variant: "strip" },
    });
    const strip = wrapper.get('[data-testid="combat-detail"]');
    expect(strip.findAll(".skill-detail-pane__disabled")).toHaveLength(1);
    expect(strip.get(".skill-detail-pane__disabled").text()).toBe("需要神聖親和。");
    expect(strip.find(".skill-detail-pane__desc").exists()).toBe(false);
    expect(strip.attributes("title")).toContain("需要神聖親和。");
  });

  it("states the focused 威力 scale's cost in the step, and every scale's cost in its full text", () => {
    const scales = [
      { scale: 1, label: "1", mp_cost: 6 },
      { scale: 2, label: "2", mp_cost: 12 },
      { scale: 3, label: "3", mp_cost: 18 },
    ];
    wrapper = mount(SkillDetailPane, {
      props: { skill: skill({ costText: "MP 6" }), variant: "strip", scales, scale: 1, focusKey: "scale-2" },
    });
    const strip = wrapper.get('[data-testid="combat-detail"]');
    expect(strip.get(".skill-detail-pane__cost").text()).toBe("消耗MP 12");
    expect(strip.text()).toContain("威力×3 MP 18");
    expect(strip.attributes("title")).toContain("威力×2 MP 12");
    // Off the step, the chosen scale's cost.
    wrapper.setProps({ focusKey: "skill-x" });
    return wrapper.vm.$nextTick().then(() => {
      expect(strip.get(".skill-detail-pane__cost").text()).toBe("消耗MP 6");
    });
  });
});
