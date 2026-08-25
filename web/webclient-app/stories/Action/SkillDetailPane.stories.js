import { h } from "vue";
import SkillDetailPane from "../../components/SkillDetailPane.vue";

// SkillDetailPane (H3 webclient-hud-03-action-dock, task 6.8): the draft's
// `.skdetail` pane — the focused skill's name, description, cost, target
// spec and disabled reason, with deterministic offline args. No `戰鬥外`
// badge is rendered (design D14).

function makeSkill(overrides) {
  return Object.assign(
    {
      key: "fireball",
      label: "火球",
      description: "凝聚火焰魔力，對單一敵人造成魔法傷害。",
      costText: "MP 14",
      targetSpec: "single",
      element: "fire",
      enabled: true,
      disabledReason: null,
      freeformScales: [
        { scale: 0.25, label: "1/4", mp_cost: 4 },
        { scale: 0.5, label: "1/2", mp_cost: 7 },
        { scale: 1, label: "1", mp_cost: 14 },
        { scale: 2, label: "2", mp_cost: 28 },
      ],
      scale: 1,
    },
    overrides || {}
  );
}

const renderPane = (args) => ({
  render: () =>
    h("div", { style: "background: var(--ink-900); padding: 8px; border-radius: 8px;" }, [
      h(SkillDetailPane, args),
    ]),
});

export default {
  title: "Action/SkillDetailPane",
  component: SkillDetailPane,
};

// An enabled skill with its cost and target spec (task 6.8).
export const EnabledSkill = {
  render: renderPane,
  args: {
    skill: makeSkill(),
    selected: [],
    scales: makeSkill().freeformScales,
    scale: 1,
  },
};

// A disabled skill with its server-provided reason (task 6.8).
export const DisabledWithReason = {
  render: renderPane,
  args: {
    skill: makeSkill({
      key: "firestorm",
      label: "火風暴",
      targetSpec: "area",
      enabled: false,
      disabledReason: { code: "insufficient_mp", message: "魔力不足" },
      freeformScales: [],
      scale: null,
    }),
    selected: [2],
    scales: [],
    scale: null,
  },
};

// A freeform-capable skill with the 威力 scale step (task 6.6/6.8): the
// server-computed `mp_cost`, ascending, `1` preselected.
export const FreeformCapable = {
  render: renderPane,
  args: {
    skill: makeSkill(),
    selected: [],
    scales: makeSkill().freeformScales,
    scale: 2,
  },
};

// Each target spec (single / area / self) (task 6.8).
export const TargetSpecs = {
  render: renderPane,
  args: {
    skill: makeSkill({ key: "mend_glow", label: "微光治癒", targetSpec: "self", costText: "MP 11" }),
    selected: [],
    scales: [],
    scale: null,
  },
};
