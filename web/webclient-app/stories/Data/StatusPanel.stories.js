import { h, onBeforeUnmount, onMounted, ref } from "vue";
import StatusPanel from "../../components/StatusPanel.vue";
import {
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_MINIMAL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../fixtures.js";

// StatusPanel: the lower-left vitals dock (vitals-bar-redesign) — the
// chromeless condition icons over the three compact bars, on one chromed
// plate at the dock's width. Props: status (the committed `status` v1 panel
// payload — gauges, conditions, combat) and visible. Read-only: no events.

const renderPanel = (args) => ({
  render: () =>
    h("div", { style: "width: 25vw; min-width: 320px; padding: 12px;" }, [
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
// seconds the dock is shown or hidden — it fades in while rising 12px out of
// the band's edge, and fades out while sinking back, keeping its trailing-bar
// memory while hidden. The frame bottom-aligns the dock as the stage does.
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
        h("div", { style: "width: 25vw; min-width: 320px; padding: 12px; min-height: 260px; display: flex; flex-direction: column; justify-content: flex-end;" }, [
          h(StatusPanel, { status: STATUS_PANEL_SAMPLE, visible: visible.value }),
        ]);
    },
  }),
};
