import { h } from "vue";
import DockBreadcrumb from "../../components/DockBreadcrumb.vue";

// DockBreadcrumb (H3 webclient-hud-03-action-dock, task 4.9): the draft's
// `.crumb` strip — hidden at depth 1, rendering `parent › current` from
// `view.dockTrail` with a back chevron bound to `focusEscape()`.

const renderCrumb = (args) => ({
  render: () =>
    h("div", { style: "height: 32px; background: var(--ink-900); padding: 4px 8px; border-radius: 8px;" }, [
      h(DockBreadcrumb, args),
    ]),
});

export default {
  title: "Action/DockBreadcrumb",
  component: DockBreadcrumb,
};

// Hidden at depth 1 (the root frame has no parent to return to, task 4.9).
export const HiddenAtDepth1 = {
  render: renderCrumb,
  args: {
    trail: ["探索"],
    depth: 1,
    guidancePrefix: "附近動作",
  },
};

// Depth 2: `parent › current` with the back chevron (pops one level).
export const Depth2 = {
  render: renderCrumb,
  args: {
    trail: ["探索", "查看"],
    depth: 2,
    guidancePrefix: "附近動作",
  },
};

// Depth 3: a three-level trail (root → parent → current).
export const Depth3 = {
  render: renderCrumb,
  args: {
    trail: ["探索", "互動", "南門守衛"],
    depth: 3,
  },
};
