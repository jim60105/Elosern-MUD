import { h } from "vue";
import LoreDrawer from "../../components/LoreDrawer.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// LoreDrawer (B4 services family): the 圖鑑 drawer. Prop: services — the
// committed `services` v2 payload. It renders only the world lore the player
// has learned: the host line, the player summary (wallet in thousands-separated
// copper, guild registration, rank, merit, next rank/threshold), and the
// guild lore (board objective/reward summaries + the active quest's detail).
// Read-only: no events. Unknown lore never leaks its existence (no
// invented codex cards — the 8-category codex has no OOB read model here).

const renderDrawer = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(LoreDrawer, args),
    ]),
});

export default {
  title: "World/LoreDrawer",
  component: LoreDrawer,
};

export const FullLore = {
  render: renderDrawer,
  args: {
    services: SERVICES_PANEL_SAMPLE,
  },
};

export const Bare = {
  render: renderDrawer,
  args: {
    services: SERVICES_PANEL_MINIMAL_SAMPLE,
  },
};

export const SectionUnavailable = {
  render: renderDrawer,
  args: {
    services: SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  },
};
