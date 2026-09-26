import { h, onBeforeUnmount, onMounted, ref } from "vue";
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

// The vitals reveal (webclient-scene-transitions, design D6): every few
// seconds the island is shown or hidden — it fades in while dropping 12px
// into place, and fades out while lifting away, keeping its trailing-bar
// memory while hidden.
export const RevealToggle = {
  render: () => ({
    setup() {
      const visible = ref(true);
      let timer = null;
      onMounted(() => {
        timer = setInterval(() => {
          visible.value = !visible.value;
        }, 1600);
      });
      onBeforeUnmount(() => clearInterval(timer));
      return () =>
        h("div", { style: "width: 262px; padding: 12px; min-height: 260px;" }, [
          h(StatusPanel, { status: STATUS_PANEL_SAMPLE, visible: visible.value }),
        ]);
    },
  }),
};
