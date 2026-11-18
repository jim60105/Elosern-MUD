import { h } from "vue";
import CreationConceptGuide from "../../components/CreationConceptGuide.vue";
import { CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE } from "../fixtures.js";

// CreationConceptGuide (creation-stepped-form; design §8): the concept page's
// guide column. Each fill item is marked only when the current proposal
// carries a value for it; sex and portrait are never listed as filled.
const frame = (args) => ({
  render: () =>
    h(
      "div",
      {
        class: "elosern",
        style:
          "position:absolute;inset:0;display:flex;padding:24px;box-sizing:border-box;background:var(--ink-950)",
      },
      [h("div", { style: "display:flex;width:calc(340px * var(--ui-scale))" }, [h(CreationConceptGuide, { style: "flex:1", ...args })])],
    ),
});

export default {
  title: "Overlays/CreationConceptGuide",
  component: CreationConceptGuide,
  render: frame,
};

// Before any proposal: nothing is marked.
export const Empty = {
  args: { proposal: null },
};

// A partial proposal: zeros count as values, omitted items stay open.
export const Partial = {
  args: {
    proposal: {
      revision: 1,
      race: "human",
      subrace: null,
      allocations: { hp: 0, mp: 0, sp: 0, atk_phys: 0, agility: 0, defense: 0, magic_power: 0 },
      persona: { personality: "謹慎多疑", life_story: "", habit: "" },
      age: 0,
    },
  },
};

// A complete proposal: every listed item is marked.
export const Full = {
  args: { proposal: CREATION_PANEL_PROPOSAL_TRANSIENT_SAMPLE.proposal },
};
