import { h } from "vue";
import PartyBagTab from "../../components/PartyBagTab.vue";
import PartyWindow from "../../components/PartyWindow.vue";
import { rememberPartyWindowTab } from "../../components/party-window-memory.js";
import {
  PARTY_BAG_HOLDINGS_CONSUMABLE,
  PARTY_BAG_HOLDINGS_EQUIPMENT,
  PARTY_BAG_INVENTORY_SAMPLE,
  PARTY_MEMBER_COMPANION_SAMPLE,
  PARTY_WINDOW_PANEL_SAMPLE,
} from "../fixtures/party_panels.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// PartyBagTab (webclient-party-bag-tab): the party window's 背包 tab for the
// viewed companion 蕾娜 — the committed equipment doll above her bag, the
// selected item's ribbon, name and summary over every member's committed
// holdings, and the action bar's give stepper, 使用… and 裝備 naming the
// replaced main hand. Rendered inside the real PartyWindow for side by side
// review with Design/PartyMemberManagement at both viewport sizes. Each
// story is one committed selection — a consumable (苦艾藥水) and equipment
// (鋼製短劍). Deterministic and offline; selecting and dispatching are inert.

export default {
  title: "Overlays/PartyBagTab",
  component: PartyBagTab,
  parameters: windowViewportParameters,
};

const HOLDINGS = {
  consumable: PARTY_BAG_HOLDINGS_CONSUMABLE,
  equipment: PARTY_BAG_HOLDINGS_EQUIPMENT,
};

const render = (args) => ({
  setup() {
    const scope = `story|bag|${args.item}`;
    rememberPartyWindowTab(scope, "bag");
    return () =>
      h("div", { style: "position: relative; width: 100%; height: 100vh; background: var(--ink-950, #0d0a12); overflow: hidden;" }, [
        h(PartyWindow, {
          party: PARTY_WINDOW_PANEL_SAMPLE,
          partyMember: PARTY_MEMBER_COMPANION_SAMPLE,
          partyInventory: PARTY_BAG_INVENTORY_SAMPLE,
          itemHoldings: HOLDINGS[args.item],
          memoryScope: scope,
          onClose: () => {},
        }),
      ]);
  },
});

export const ConsumableReference = { render, args: { item: "consumable" }, ...atReference };
export const ConsumableFullHd = { render, args: { item: "consumable" }, ...atFullHd };
export const EquipmentReference = { render, args: { item: "equipment" }, ...atReference };
export const EquipmentFullHd = { render, args: { item: "equipment" }, ...atFullHd };
