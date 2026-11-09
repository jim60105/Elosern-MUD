import { h } from "vue";
import DetailFooter from "../../components/DetailFooter.vue";

// DetailFooter (handbook-primitives): the pinned action footer shared by the
// quest detail and the handbook detail column. Descriptor buttons render in
// order beside an optional reason line; a disabled button stays focusable
// (aria-disabled) and emits nothing, a toggle uses native disabled, and an
// armed confirmation shows its warning as an alert. Every fixture here is
// synthetic.

const renderFooter = (args) => ({
  render: () =>
    h("div", { style: "width: calc(760px * var(--ui-scale)); margin: calc(24px * var(--ui-scale)); background: #121418;" }, [
      h(DetailFooter, args),
    ]),
});

export default {
  title: "World/DetailFooter",
  component: DetailFooter,
};

// The quest footer's resting set: ghost abandon, the spacer, a pressed
// tracking toggle and the primary turn-in.
export const QuestButtons = {
  render: renderFooter,
  args: {
    buttons: [
      { key: "abandon", label: "放棄任務", tone: "ghost" },
      { key: "track", label: "追蹤中", tone: "plain", pressed: true, glyph: "track_flag", spacerBefore: true },
      { key: "turnin", label: "交派任務", tone: "primary" },
    ],
  },
};

// An armed confirmation: the danger reason as an alert, cancel and confirm.
export const ArmedDanger = {
  render: renderFooter,
  args: {
    reason: "確認後這一項會被移除，且無法回復。",
    reasonTone: "danger",
    reasonRole: "alert",
    buttons: [
      { key: "cancel", label: "取消", tone: "plain" },
      { key: "confirm", label: "確認", tone: "danger" },
    ],
  },
};

// A disabled primary that stays focusable beside the reason it points at.
export const DisabledAria = {
  render: renderFooter,
  args: {
    reason: "條件尚未達成。",
    buttons: [{ key: "accept", label: "接取", tone: "primary", enabled: false, describedByReason: true }],
  },
};
