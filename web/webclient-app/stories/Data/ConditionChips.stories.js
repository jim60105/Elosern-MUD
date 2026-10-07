import { h, nextTick, onMounted, ref } from "vue";
import ConditionChips from "../../components/ConditionChips.vue";

// ConditionChips (H2, webclient-hud-02-status-islands, design D6/D7/D8;
// vitals-bar-redesign design D3): the chromeless condition icon row stories —
// none / one / six / thirty-two conditions, every severity, with and without
// durations and modifiers, framed at the dock's 25vw width on the dock's ink.
// Hover or focus an icon for its tooltip; the `+N` icon discloses the
// remainder in a bounded, scrollable column (FocusedTooltip opens one).

function condition(code, severity, label, remainingSeconds, modifiers) {
  const c = { code, severity, label, provenance: { kind: "non_equipment", equipment_sources: [] } };
  if (typeof remainingSeconds === "number") {
    c.remaining_seconds = remainingSeconds;
  }
  if (modifiers) {
    c.modifiers = modifiers;
  }
  return c;
}

// One entry per severity (all five), each with the fields it carries.
const SEVERITY_SET = [
  condition("swift", "beneficial", "疾風", 60),
  condition("fog", "informational", "霧隱", null),
  condition("caution", "warning", "警戒", 30, { defense: -15 }),
  condition("poisoned", "harmful", "中毒", 120, { agility: "-10%" }),
  condition("wounded", "critical", "重傷", 45, { hp_regen: "-50%" }),
];

// Thirty-two committed conditions: the payload's bound. The island shows six
// chips and a `+26` overflow chip.
const MANY_CONDITIONS = Array.from({ length: 32 }, (_, i) =>
  condition(
    `cond_${i}`,
    ["beneficial", "informational", "warning", "harmful", "critical"][i % 5],
    `狀態${i + 1}`,
    i % 4 === 0 ? i * 10 : null,
    i % 3 === 0 ? { agility: "-10%" } : null,
  ),
);

const SIX_CONDITIONS = SEVERITY_SET.concat([
  condition("shield", "beneficial", "護體", 90, { defense: 25 }),
]);

const ONE_CONDITION = [SEVERITY_SET[3]]; // the harmful poisoned buff.
const NONE_CONDITIONS = [];

// The dock frame: the row is chromeless; StatusPanel's root carries the dock
// chrome. The top margin leaves room for the tooltip hung above an icon.
const DOCK_FRAME = "margin-top: 120px; width: 25vw; min-width: 320px; box-sizing: border-box; padding: 10px 18px 10px 26px; background: var(--panel);";

const renderChips = (args) => ({
  render: () =>
    h("div", { style: DOCK_FRAME }, [h(ConditionChips, args)]),
});

export default {
  title: "Data/ConditionChips",
  component: ConditionChips,
};

export const None = {
  render: renderChips,
  args: { conditions: NONE_CONDITIONS },
};

export const One = {
  render: renderChips,
  args: { conditions: ONE_CONDITION },
};

export const AllSeverities = {
  render: renderChips,
  args: { conditions: SEVERITY_SET },
};

export const Six = {
  render: renderChips,
  args: { conditions: SIX_CONDITIONS },
};

export const ThirtyTwo = {
  render: renderChips,
  args: { conditions: MANY_CONDITIONS },
};

// Long server labels (webclient-zh-tw-copy-and-labels): no icon is sized by
// its label; the full names and localized modifiers stay in each icon's
// accessible name and tooltip, plus one in the overflow.
export const LongNames = {
  render: renderChips,
  args: {
    conditions: [
      condition("long_arousal", "harmful", "高度興奮敏捷與準度減損", null, { agility: "-20%", accuracy: -15 }),
      condition("long_mana", "beneficial", "精準魔力控制魔力消耗降低", null, { mp_cost: "-10%" }),
      condition("long_stun", "critical", "靜電麻痺微階鎖定行動", 12, { actions_per_turn: 0, chance: 15 }),
      condition("long_focus", "beneficial", "專注", 60, { accuracy: 10 }),
      condition("long_fear", "warning", "恐懼", 30, { agility: "-15%" }),
      condition("long_poison", "harmful", "中毒", 120),
      condition("long_more", "informational", "轉生祝福‧悠花敏捷提升", null, { agility_flat: 3 }),
    ],
  },
};

// The tooltip open state: keyboard focus on the harmful icon opens the same
// tooltip a hover does — its label, verbatim duration, and readable modifiers.
export const FocusedTooltip = {
  render: () => ({
    setup() {
      const frame = ref(null);
      onMounted(async () => {
        await nextTick();
        frame.value?.querySelector('[data-testid="status-panel__condition--poisoned"]')?.focus();
      });
      return () => h("div", { ref: frame, style: DOCK_FRAME }, [h(ConditionChips, { conditions: SEVERITY_SET })]);
    },
  }),
};
