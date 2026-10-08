import { h } from "vue";
import SkillUseDock from "../../components/SkillUseDock.vue";
import SkillUseMenu from "../../lib/skill_use_menu.js";

// SkillUseDock (skillbook-authoritative-casting D8): the dock pane of the
// SkillBook casting flow, rendered from the same menu model the router
// resolves. Synthetic, deterministic offline panels only.

function panel(spec, skill = {}) {
  const base = {
    schema_version: 1,
    available: true,
    kind: "skill_use",
    scale: 1,
    skill: {
      key: "t_soft_mend",
      label: "靜謐癒合",
      description: "以無聲的暖流癒合單一傷口。對同場魔物施放會直接開啟戰鬥。",
      target_spec: spec,
      usable_out_of_combat: true,
      cost: { mp: 11 },
      enabled: true,
      disabled_reason: null,
      targets: [
        { identity: 42, label: "影行者（自己）", enabled: true, disabled_reason: null },
        { identity: 51, label: "村民（1）", enabled: true, disabled_reason: null },
        { identity: 52, label: "村民（2）", enabled: false, disabled_reason: { code: "target_dead", message: "目標已失去行動能力。" } },
      ],
      openings: [
        { identity: 9, label: "灰狼（開戰）", target_ids: [9], enabled: true, disabled_reason: null },
      ],
      ...skill,
    },
  };
  return base;
}

function detailFor(p, focused = null) {
  return {
    skillKey: p.skill.key,
    label: p.skill.label,
    description: p.skill.description,
    targetSpec: p.skill.target_spec,
    costText: SkillUseMenu.costText(p.skill.cost),
    scale: p.scale,
    scaled: false,
    enabled: p.skill.enabled,
    reason: null,
    selected: [],
    focused,
  };
}

const renderDock = (args) => ({
  render: () =>
    h(
      "div",
      { style: "width: 470px; height: 200px; padding: 8px; background: var(--ink-900); display: flex;" },
      [h(SkillUseDock, args)],
    ),
});

export default {
  title: "Action/SkillUseDock",
  component: SkillUseDock,
};

const singlePanel = panel("single");
export const SingleTargets = {
  render: renderDock,
  args: {
    menu: SkillUseMenu.useMenu(SkillUseMenu.createModel(singlePanel)),
    focusedKey: "target-51",
    detail: detailFor(singlePanel, { key: "target-51", kind: "target", reason: null, lineUpCount: 0 }),
    locked: false,
  },
};

const areaPanel = panel("area", {
  label: "靜謐合唱",
  openings: [
    { identity: 9, label: "灰狼等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null },
    { identity: 12, label: "岩蜥等 2 名（全體開戰）", target_ids: [9, 12], enabled: true, disabled_reason: null },
  ],
});
const areaModel = SkillUseMenu.createModel(areaPanel);
SkillUseMenu.toggle(areaModel, 42);
export const AreaSelection = {
  render: renderDock,
  args: {
    menu: SkillUseMenu.useMenu(areaModel),
    focusedKey: "opening-9",
    detail: detailFor(areaPanel, { key: "opening-9", kind: "opening", reason: null, lineUpCount: 2 }),
    locked: false,
  },
};

export const OpeningConfirmation = {
  render: renderDock,
  args: {
    menu: SkillUseMenu.openingMenu(SkillUseMenu.createModel(singlePanel), 9),
    focusedKey: "confirm-opening",
    detail: detailFor(singlePanel, { key: "confirm-opening", kind: "confirm", reason: null, lineUpCount: 1 }),
    locked: false,
  },
};
