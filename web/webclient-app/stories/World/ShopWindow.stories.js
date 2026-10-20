import { h } from "vue";
import ShopWindow from "../../components/ShopWindow.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  SHOP_CHARACTER_SAMPLE,
  SHOP_HOLDINGS_EQUIPMENT,
  SHOP_HOLDINGS_POTION,
  SHOP_HOLDINGS_SELL,
  SHOP_PARTY_SAMPLE,
  SHOP_PARTY_SELLER_SAMPLE,
  SHOP_SERVICES_CLOSED_SAMPLE,
  SHOP_SERVICES_SAMPLE,
  SHOP_SERVICES_SELLER_SAMPLE,
} from "../fixtures.js";
import { atFullHd, atReference, windowViewportParameters } from "../window-viewports.js";

// ShopWindow (webclient-shop-window): the merchant's window on the shared
// WindowFrame with 購買 and 出售 and the member rail, for side by side review
// with Design/PartyMemberManagement's shop stories at both viewport sizes.
// 購買 shows 艾拉 (the viewed member) as the recipient with her committed
// deltas, the comparison and the other members' chips; 出售 shows the seller
// 卡恩's sellable rows with one sell price. Further states: a consumable with
// held counts, the closed shop (every control disabled with the committed
// reason), a trade's committed refusal, no shop here, and the unavailable
// services panel. Deterministic and offline; dispatching is inert.

export default {
  title: "World/ShopWindow",
  component: ShopWindow,
  parameters: windowViewportParameters,
};

const render = (args) => ({
  setup() {
    return () =>
      h("div", { style: "position: relative; width: 100%; height: 100vh; background: var(--ink-950, #0d0a12); overflow: hidden;" }, [
        h(ShopWindow, { ...args, onClose: () => {} }),
      ]);
  },
});

const BUY_EQUIPMENT = {
  services: SHOP_SERVICES_SAMPLE,
  party: SHOP_PARTY_SAMPLE,
  itemHoldings: SHOP_HOLDINGS_EQUIPMENT,
  character: SHOP_CHARACTER_SAMPLE,
};
const BUY_CONSUMABLE = { ...BUY_EQUIPMENT, itemHoldings: SHOP_HOLDINGS_POTION };
const SELL = {
  services: SHOP_SERVICES_SELLER_SAMPLE,
  party: SHOP_PARTY_SELLER_SAMPLE,
  itemHoldings: SHOP_HOLDINGS_SELL,
  initialTab: "sell",
};

export const BuyEquipmentReference = { render, args: BUY_EQUIPMENT, ...atReference };
export const BuyEquipmentFullHd = { render, args: BUY_EQUIPMENT, ...atFullHd };
export const SellReference = { render, args: SELL, ...atReference };
export const SellFullHd = { render, args: SELL, ...atFullHd };
export const BuyConsumableReference = { render, args: BUY_CONSUMABLE, ...atReference };
export const ClosedReference = {
  render,
  args: { ...BUY_EQUIPMENT, services: SHOP_SERVICES_CLOSED_SAMPLE },
  ...atReference,
};
export const RefusedTradeReference = {
  render,
  args: { ...BUY_CONSUMABLE, tradeNotice: { code: "possessed_shop", message: "附身狀態下無法進行交易。" } },
  ...atReference,
};
export const NoShopReference = { render, args: { services: SERVICES_PANEL_MINIMAL_SAMPLE, party: SHOP_PARTY_SAMPLE }, ...atReference };
export const UnavailableReference = {
  render,
  args: { services: SERVICES_PANEL_UNAVAILABLE_SAMPLE, party: SHOP_PARTY_SAMPLE },
  ...atReference,
};
