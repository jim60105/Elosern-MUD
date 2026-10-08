// SkillUseDock (skillbook-authoritative-casting D8): a passive renderer of the
// router's skill-use frame — ☐/☑ AREA marks, the 開戰 divider before the
// first monster opening, disabled rows that keep their reason, the opening
// confirmation, and the detail card's consequence line. Pointer focus and
// activation are routed back to the store, never dispatched here.
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import SkillUseDock from "../../components/SkillUseDock.vue";
import SkillUseMenu from "../../lib/skill_use_menu.js";

function panel(spec) {
  return {
    schema_version: 1,
    available: true,
    kind: "skill_use",
    scale: 1,
    skill: {
      key: "t_soft_mend",
      label: "合成癒合",
      description: "合成用。",
      target_spec: spec,
      usable_out_of_combat: true,
      cost: { mp: 11 },
      enabled: true,
      disabled_reason: null,
      targets: [
        { identity: 42, label: "測試者（自己）", enabled: true, disabled_reason: null },
        { identity: 52, label: "村民", enabled: false, disabled_reason: { code: "target_dead", message: "目標已失去行動能力。" } },
      ],
      openings: [{ identity: 9, label: "合成狼等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null },
        { identity: 12, label: "灰狼等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null }],
    },
  };
}

function detail(focused) {
  return { skillKey: "t_soft_mend", label: "合成癒合", description: "合成用。", targetSpec: "area", costText: "MP 11", scale: 1, scaled: false, enabled: true, reason: null, selected: [], focused };
}

describe("SkillUseDock", () => {
  let wrapper;
  afterEach(() => wrapper?.unmount());

  it("renders AREA marks, the 開戰 divider, and keeps disabled reasons", () => {
    const model = SkillUseMenu.createModel(panel("area"));
    SkillUseMenu.toggle(model, 42);
    wrapper = mount(SkillUseDock, {
      props: { menu: SkillUseMenu.useMenu(model), focusedKey: "area-52", detail: detail({ key: "area-52", kind: "target", reason: "目標已失去行動能力。", lineUpCount: 0 }) },
    });
    expect(wrapper.get('[data-testid="skill-use-row--area-42"]').attributes("aria-checked")).toBe("true");
    expect(wrapper.get('[data-testid="skill-use-row--area-42"]').text()).toContain("☑");
    const disabled = wrapper.get('[data-testid="skill-use-row--area-52"]');
    expect(disabled.attributes("aria-disabled")).toBe("true");
    expect(disabled.text()).toContain("不可選");
    expect(wrapper.findAll(".skill-use-dock__divider")).toHaveLength(1);
    expect(wrapper.get('[data-testid="skill-use-detail__consequence"]').text()).toContain("目標已失去行動能力");
    expect(wrapper.get('[data-testid="dock-menu"]').attributes("aria-activedescendant")).toBe(
      wrapper.get('[data-testid="skill-use-row--area-52"]').attributes("id"),
    );
  });

  it("discloses the whole line-up for an AREA opening", () => {
    const model = SkillUseMenu.createModel(panel("area"));
    wrapper = mount(SkillUseDock, {
      props: { menu: SkillUseMenu.useMenu(model), focusedKey: "opening-12", detail: detail({ key: "opening-12", kind: "opening", reason: null, lineUpCount: 2 }) },
    });
    expect(wrapper.get('[data-testid="skill-use-detail__consequence"]').text()).toContain("全場 2 名敵人");
  });

  it("renders the opening confirmation and routes pointer clicks to the store", async () => {
    const model = SkillUseMenu.createModel(panel("area"));
    wrapper = mount(SkillUseDock, {
      props: { menu: SkillUseMenu.openingMenu(model, 9), focusedKey: "confirm-opening", detail: detail({ key: "confirm-opening", kind: "confirm", reason: null, lineUpCount: 2 }) },
    });
    expect(wrapper.get('[data-testid="skill-use-dock"]').attributes("data-frame")).toBe("opening");
    expect(wrapper.get('[data-testid="skill-use-row--confirm-opening"]').text()).toContain("開戰並施放");
    await wrapper.get('[data-testid="skill-use-row--cancel-opening"]').trigger("click");
    expect(wrapper.emitted("focus-change")).toEqual([["cancel-opening"]]);
    expect(wrapper.emitted("activate")).toEqual([[{ key: "cancel-opening" }]]);
  });
});
