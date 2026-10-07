import { h } from "vue";
import GmSourceText from "../components/GmSourceText.vue";
import { PROMPT_SOURCE, RULE_SOURCE } from "./world-fixtures.js";

// GmSourceText: read-only, line-numbered YAML with anchorable line numbers,
// dimmed comment lines, a highlighted line and optional soft wrapping.
const LONG = Array.from({ length: 160 }, (_, index) =>
  index % 9 === 0 ? `# 第 ${index / 9 + 1} 段合成設定` : `  t_key_${index}: ${"合成值 ".repeat((index % 5) + 1).trim()}`,
).join("\n");

export default {
  title: "GM/GmSourceText",
  component: GmSourceText,
  args: { text: RULE_SOURCE.text, name: RULE_SOURCE.source_path, highlight: null },
  render: (args) => ({
    setup: () => () => h("div", { style: { padding: "32px", maxWidth: "1040px" } }, [h(GmSourceText, args)]),
  }),
};

export const Rulebook = {};

export const Prompt = { args: { text: PROMPT_SOURCE.text, name: PROMPT_SOURCE.source_path } };

export const LongHighlighted = { args: { text: LONG, name: "world/rules/rulebook/t_long.yaml", highlight: 42 } };

export const EmptyFile = { args: { text: "", name: "world/rules/rulebook/t_empty.yaml" } };
