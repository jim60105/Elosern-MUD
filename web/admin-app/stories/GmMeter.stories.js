import { h } from "vue";
import GmMeter from "../components/GmMeter.vue";

// GmMeter: a pure-CSS micro bar; tones always pair with a fill pattern.
export default {
  title: "GM/GmMeter",
  component: GmMeter,
  args: { value: 113, max: 500, label: "LLM 緩衝 113 / 500", width: "160px" },
  render: (args) => ({
    setup: () => () =>
      h("div", { style: { padding: "32px", display: "flex", gap: "12px", alignItems: "center" } }, [
        h(GmMeter, args),
        h("span", { class: "gm-mono", style: { color: "var(--paper-200)" } }, `${args.value ?? ""}`),
      ]),
  }),
};

export const SingleValue = {};
export const Full = { args: { value: 500, max: 500, tone: "warn", pattern: "hatch", label: "已滿" } };
export const Zero = { args: { value: 0, max: 500, label: "空" } };
export const Segmented = {
  args: {
    width: "240px",
    label: "成功 14，降級 7，拒絕 1",
    segments: [
      { key: "ok", value: 14, tone: "ok", pattern: "solid" },
      { key: "degraded", value: 7, tone: "warn", pattern: "hatch" },
      { key: "rejected", value: 1, tone: "crit", pattern: "cross" },
    ],
  },
};
