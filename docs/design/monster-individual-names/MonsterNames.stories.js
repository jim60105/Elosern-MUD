import { h } from "vue";
import MonsterNamesPrototype from "./MonsterNamesPrototype.vue";

// Design/MonsterIndividualNames: a monster shows its species name, the variant
// stays on the readout and target prompt, and an individual name gets existing
// rank language: an inner double rule and two gold hairlines, which take no
// layout space. Reference only, synthetic fixtures; not imported by the app. See
// docs/superpowers/specs/2026-11-05-monster-individual-names-design.md.

const render = (args) => ({ render: () => h(MonsterNamesPrototype, { ...args, key: JSON.stringify(args) }) });

export default {
  title: "Design/MonsterIndividualNames",
  component: MonsterNamesPrototype,
  parameters: { layout: "fullscreen" },
  render,
};

// Named and unnamed side by side, including the longest name and a fallen plate.
export const Specimen = { args: { view: "specimen" } };
// Hover the rail: the readout follows.
export const Exploration = { args: { view: "exploration" } };
// Hover a figure: the target prompt follows.
export const Combat = { args: { view: "combat" } };
