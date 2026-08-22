import { h } from "vue";
import StatusPanel from "../../components/StatusPanel.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_MINIMAL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../fixtures.js";

// StatusPanel: the expanded status surface. Props: status (the committed
// `status` v1 panel payload — gauges, conditions, disguise flag, combat) and
// character (the committed `character` v3 panel payload — counters, static
// traits, wallet). Read-only: no events.

const renderPanel = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(StatusPanel, args),
    ]),
});

export default {
  title: "Data/StatusPanel",
  component: StatusPanel,
};

export const FullPayload = {
  render: renderPanel,
  args: {
    status: STATUS_PANEL_SAMPLE,
    character: CHARACTER_PANEL_SAMPLE,
  },
};

export const CombatRounds = {
  render: renderPanel,
  args: {
    status: STATUS_PANEL_COMBAT_SAMPLE,
    character: CHARACTER_PANEL_SAMPLE,
  },
};

export const Minimal = {
  render: renderPanel,
  args: {
    status: STATUS_PANEL_MINIMAL_SAMPLE,
    character: CHARACTER_PANEL_SAMPLE,
  },
};
