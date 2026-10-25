import { h } from "vue";
import NpcServiceMenuPrototype from "./NpcServiceMenuPrototype.vue";
import { NPC } from "./npc-service-fixtures.js";

// Design/NpcServiceMenu: the approved NPC service-menu design as an
// interactive prototype (reference only, synthetic fixtures; not imported by
// the app and outside the webclient component-coverage manifest). The real
// exploration stage, presence rail, standee, person-focus ChoiceCard, and
// drawer chrome; one card per NPC in the `choices` anchor with the common
// interactions (1 交談, 2 查看人物), the conditional interactions, and the
// services the NPC's synthetic descriptors supply, last. Service rows open a
// named demonstration pane; nothing dispatches a command, mutates state, or
// calls the network, and the prototype does not simulate the server's
// validation. The dashed strip at the top holds the prototype-only
// simulation controls (departure, service-read failure, reset).
//
// Keyboard: on the rail ←/→ and Enter; on the card ↑/↓ (wrap), Home/End,
// Enter/Space, the digit on a row's badge (1–9), Escape back to the rail
// entry. In a demonstration pane Escape, ✕, the scrim, or 返回人物選單 return
// focus to the service row that opened it.

const render = (args) => ({ render: () => h(NpcServiceMenuPrototype, args) });

export default {
  title: "Design/NpcServiceMenu",
  component: NpcServiceMenuPrototype,
  parameters: { layout: "fullscreen" },
};

// Every NPC on the rail, no card open: open any person, try the services,
// and use the top strip to simulate a departure or a service-read failure.
export const InteractiveScenario = {
  render,
  args: { initialNpc: null },
};

// 蘿珊 has no service capability: 交談, 查看人物, one conditional 邀請同行,
// and no services group at all.
export const NoServices = {
  render,
  args: { initialNpc: NPC.noServices },
};

// 托班 supplies one trade descriptor: row 3 買賣貨物 opens the trade
// demonstration pane.
export const ServiceAvailable = {
  render,
  args: { initialNpc: NPC.merchant },
};

// 米菈's trade descriptor is paused: the row keeps number 3, states 暫停 and
// its reason inline, takes focus, and does nothing on Enter, Space, its
// digit, or a click.
export const ServicePaused = {
  render,
  args: { initialNpc: NPC.paused },
};

// 薇絲妲's 交談 is unavailable: row 1 stays in place with its reason; the
// card opens on row 2.
export const TalkUnavailable = {
  render,
  args: { initialNpc: NPC.talkUnavailable },
};

// 艾德溫 at the guild counter: two conditional interactions (supplied out of
// order, listed in the fixed order; one disabled but still numbered) and
// three guild services, one paused. Rows 1 and 2 are the same as on every
// other card; only the variable rows' numbers differ.
export const FixedNumberingWithConditionals = {
  render,
  args: { initialNpc: NPC.guildCounter },
};

// 艾德溫 again, with the service read failing: the conditional rows keep
// their numbers, and the services group is one unnumbered, non-actionable
// line 服務資訊暫時無法讀取。 instead of any (stale) service row.
export const ServiceInfoReadFailure = {
  render,
  args: { initialNpc: NPC.guildCounter, unreadable: [NPC.guildCounter] },
};

// 托班 leaves the room 2.5s after the story mounts: the card closes, the
// readout flashes 托班 已經離開了。, and focus lands on the rail.
export const NpcDeparture = {
  render,
  args: { initialNpc: NPC.merchant, autoDepartMs: 2500 },
};

// The trade demonstration pane already open from 托班's 買賣貨物: close it to
// see focus return to that row.
export const ServiceFlowOpen = {
  render,
  args: { initialNpc: NPC.merchant, initialService: "service:goods" },
};

// 哈洛 (a stress fixture): thirteen numbered rows. Digits stop at 9; rows
// 10–13 carry `·` and stay reachable with ↓/End and the card's scroller.
export const Overflow = {
  render,
  args: { initialNpc: NPC.overflow },
};
