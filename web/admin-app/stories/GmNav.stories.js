import { h } from "vue";
import GmNav from "../components/GmNav.vue";
import { GM_SECTIONS } from "../lib/sections.js";

// GmNav: brand, ornament rule, and one entry per sub-project; undelivered
// sections are inert and tagged 「尚未開放」.
export default {
  title: "GM/GmNav",
  component: GmNav,
  args: { items: GM_SECTIONS, activeKey: "overview" },
  render: (args) => ({
    setup: () => () =>
      h(
        "div",
        { style: { width: "272px", minHeight: "100vh", background: "var(--ink-950)", borderRight: "var(--line)" } },
        [h(GmNav, { ...args, onNavigate: () => {} })],
      ),
  }),
};

export const OverviewActive = {};
export const NothingActive = { args: { activeKey: "" } };
