import { h } from "vue";
import StatusPanel from "../../components/StatusPanel.vue";
import {
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_MINIMAL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../fixtures.js";

// StatusPanel: the expanded status surface. Props: status (the committed `status`
// v1 panel payload — gauges, conditions, combat) and visible. Read-only: no events.

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
    visible: true,
  },
};

export const CombatRounds = {
  render: renderPanel,
  args: {
    status: STATUS_PANEL_COMBAT_SAMPLE,
    visible: true,
  },
};

export const Minimal = {
  render: renderPanel,
  args: {
    status: STATUS_PANEL_MINIMAL_SAMPLE,
    visible: true,
  },
};

export const HiddenAtFullHealth = {
  render: renderPanel,
  args: {
    status: STATUS_PANEL_SAMPLE,
    visible: false,
  },
};
