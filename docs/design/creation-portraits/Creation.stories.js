import { h } from "vue";
import CreationPrototype from "./CreationPrototype.vue";

// Design/CreationPortraits: the approved creation layout (design document
// docs/superpowers/specs/2026-11-17-creation-portrait-redesign-design.md).
// Reference only, synthetic data; not imported by the app. The tabs in every
// story switch between the three modes.

export default {
  title: "Design/CreationPortraits",
  component: CreationPrototype,
  parameters: { layout: "fullscreen" },
  render: (args, context) => ({ render: () => h(CreationPrototype, { ...args, key: context.id }) }),
};

// 預設角色: eight art cards; the opened one carries its dossier and the choose action.
export const Preset = { args: { mode: "preset" } };
// 自由創建: the silhouette slot beside the three steps.
export const CustomIdentity = { args: { mode: "custom" } };
export const CustomStory = { args: { mode: "custom", step: 1 } };
export const CustomAllocation = { args: { mode: "custom", step: 2 } };
// The portrait slot while a generation is queued, and once it has settled.
export const CustomPortraitPending = { args: { mode: "custom", portrait: "pending" } };
export const CustomPortraitReady = { args: { mode: "custom", step: 2, portrait: "ready" } };
// 生成肖像 opens the existing gallery generate drawer.
export const CustomGenerateDrawer = { args: { mode: "custom", drawer: true } };
// 概念生成: guiding questions and the fields a concept fills.
export const Concept = { args: { mode: "concept" } };
