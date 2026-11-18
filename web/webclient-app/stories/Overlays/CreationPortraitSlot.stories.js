import { h } from "vue";
import CreationPortraitSlot from "../../components/CreationPortraitSlot.vue";
import { CREATION_PANEL_SAMPLE, CREATION_PORTRAIT_STATES } from "../fixtures.js";

// CreationPortraitSlot (design §7.1): the custom form's persistent portrait
// column. Props only: the host passes the silhouette entry the server table
// names for the current sex and apparent age (or null when no single entry
// matches), the committed portrait state, and whether generation is offered
// and currently gated. The slot only emits generate / refresh-status.
const SILHOUETTES = CREATION_PANEL_SAMPLE.custom.silhouettes;
const entry = (sex, index) => SILHOUETTES.filter((row) => row.sex === sex)[index].artwork;

const frame = (args) => ({
  render: () =>
    h(
      "div",
      {
        class: "elosern",
        style:
          "position:absolute;inset:0;display:flex;justify-content:center;padding:24px;box-sizing:border-box;background:var(--ink-950)",
      },
      [h("div", { style: "display:flex;width:calc(300px * var(--ui-scale))" }, [h(CreationPortraitSlot, { style: "flex:1", ...args })])],
    ),
});

export default {
  title: "Overlays/CreationPortraitSlot",
  component: CreationPortraitSlot,
  render: frame,
};

// A named character with an adult silhouette.
export const Named = {
  args: { name: "林楓", silhouette: entry("male", 1) },
};

// -- The five committed states with generation offered (creation-draft-portrait)
const live = (state, extra = {}) => ({
  args: { name: "林楓", silhouette: entry("male", 1), canGenerate: true, portrait: CREATION_PORTRAIT_STATES[state], ...extra },
});

export const Empty = live("empty");
// Drawing: the silhouette breathes and a ring turns (both stop at the
// reduced and off motion levels); generation is disabled.
export const Pending = live("pending");
export const Ready = live("ready");
// The server's failure reason; a retry stays available.
export const Failed = live("failed");
// The server's offline reason; generation is disabled, refresh is offered.
export const Unavailable = live("unavailable");
// The shared single-mutation gate holds generation (another request waits).
export const GateHeld = live("empty", { disabled: true });

// No name yet: the unnamed label.
export const Unnamed = {
  args: { name: "", silhouette: entry("female", 1) },
};

// A younger interval of the table.
export const YoungInterval = {
  args: { name: "小禾", silhouette: entry("female", 0) },
};

// No single table entry matches the input: a neutral frame, no figure.
export const NoMatch = {
  args: { name: "", silhouette: null },
};
