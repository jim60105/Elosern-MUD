import { h } from "vue";
import GmStatusBadge from "../components/GmStatusBadge.vue";

// GmStatusBadge wraps the shared not-color-only `.status-marker`: each state
// pairs color with a glyph, a border style, and a text label.
export default {
  title: "GM/GmStatusBadge",
  component: GmStatusBadge,
  args: { status: "ok", label: "正常" },
  argTypes: { status: { control: "select", options: ["ok", "warn", "crit", "neutral"] } },
};

export const Ok = { args: { status: "ok", label: "正常" } };
export const Warn = { args: { status: "warn", label: "延遲" } };
export const Crit = { args: { status: "crit", label: "無法連線" } };
export const Neutral = { args: { status: "neutral", label: "未知" } };

export const AllStates = {
  args: {},
  render: () => ({
    setup: () => () =>
      h("div", { style: { display: "flex", gap: "12px", padding: "32px", flexWrap: "wrap" } }, [
        h(GmStatusBadge, { status: "ok", label: "正常" }),
        h(GmStatusBadge, { status: "warn", label: "延遲" }),
        h(GmStatusBadge, { status: "crit", label: "無法連線" }),
        h(GmStatusBadge, { status: "neutral", label: "未知" }),
      ]),
  }),
};
