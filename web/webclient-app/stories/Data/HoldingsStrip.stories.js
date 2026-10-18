import { h } from "vue";
import HoldingsStrip from "../../components/HoldingsStrip.vue";
import {
  ITEM_HOLDINGS_COMBAT,
  ITEM_HOLDINGS_CONSUMABLE,
  ITEM_HOLDINGS_EQUIPMENT,
  WINDOW_RAIL_MEMBERS,
} from "../fixtures/window_primitives.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// HoldingsStrip (webclient-window-primitives): the bag's and the shop's
// per-member strip for one selected item, rendered from `item_holdings` v1
// rows verbatim (the fixtures pass the wire validator in Vitest). Counts
// for a consumable; ▲/▼-prefixed server deltas or 無法裝備 for equipment; a
// give control only where the server enabled the receive; counts only in
// combat.

const DETAIL_FRAME = [
  "width: calc(640px * var(--ui-scale));",
  "margin: calc(24px * var(--ui-scale));",
  "padding: calc(16px * var(--ui-scale)) calc(20px * var(--ui-scale));",
  "background: linear-gradient(180deg, #16181dfa, #0e1014fa);",
  "border: 1px solid rgba(185, 154, 96, 0.45);",
].join("");

const render = ({ panel, ...args }) => ({
  render: () =>
    h("div", { style: DETAIL_FRAME }, [
      h(HoldingsStrip, { ...args, rows: panel.rows, giverId: panel.giver_id, members: WINDOW_RAIL_MEMBERS, onGive: () => {} }),
    ]),
});

export default {
  title: "Data/HoldingsStrip",
  component: HoldingsStrip,
  parameters: windowViewportParameters,
};

export const Reference = { render, args: { panel: ITEM_HOLDINGS_CONSUMABLE, giveQuantity: 1 }, ...atReference };
export const FullHd = { render, args: { panel: ITEM_HOLDINGS_CONSUMABLE, giveQuantity: 1 }, ...atFullHd };
export const Equipment = { render, args: { panel: ITEM_HOLDINGS_EQUIPMENT }, ...atReference };
export const InCombat = { render, args: { panel: ITEM_HOLDINGS_COMBAT, combat: true }, ...atReference };
